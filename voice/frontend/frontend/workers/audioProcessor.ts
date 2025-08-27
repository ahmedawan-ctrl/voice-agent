// Audio processing worker for handling audio analysis in a separate thread
class AudioProcessorWorker {
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private dataArray: Uint8Array | null = null;
  private animationId: number | null = null;
  private isProcessing = false;

  constructor() {
    self.onmessage = this.handleMessage.bind(this);
  }

  private handleMessage(event: MessageEvent) {
    const { type, data } = event.data;

    switch (type) {
      case 'INIT_AUDIO_CONTEXT':
        this.initializeAudioContext(data.sampleRate);
        break;
      case 'START_PROCESSING':
        this.startProcessing();
        break;
      case 'STOP_PROCESSING':
        this.stopProcessing();
        break;
      case 'PROCESS_AUDIO_DATA':
        this.processAudioData(data.audioData);
        break;
      case 'CLEANUP':
        this.cleanup();
        break;
      default:
        console.warn('Unknown message type:', type);
    }
  }

  private initializeAudioContext(sampleRate: number = 44100) {
    try {
      this.audioContext = new AudioContext({ sampleRate });
      
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 256;
      this.analyser.smoothingTimeConstant = 0.8;

      const bufferLength = this.analyser.frequencyBinCount;
      this.dataArray = new Uint8Array(bufferLength);

      self.postMessage({
        type: 'AUDIO_CONTEXT_INITIALIZED',
        data: { success: true, bufferLength }
      });
    } catch (error) {
      self.postMessage({
        type: 'AUDIO_CONTEXT_ERROR',
        data: { error: error instanceof Error ? error.message : 'Failed to initialize audio context' }
      });
    }
  }

  private startProcessing() {
    this.isProcessing = true;
    this.processLoop();
  }

  private stopProcessing() {
    this.isProcessing = false;
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
      this.animationId = null;
    }
  }

  private processLoop() {
    if (!this.isProcessing || !this.analyser || !this.dataArray) return;

    this.analyser.getByteFrequencyData(this.dataArray);
    
    // Send frequency data to main thread
    self.postMessage({
      type: 'FREQUENCY_DATA',
      data: { frequencyData: Array.from(this.dataArray) }
    });

    this.animationId = requestAnimationFrame(() => this.processLoop());
  }

  private processAudioData(audioData: Float32Array) {
    // Process raw audio data for additional analysis if needed
    const rms = this.calculateRMS(audioData);
    const peak = this.calculatePeak(audioData);
    
    self.postMessage({
      type: 'AUDIO_ANALYSIS',
      data: { rms, peak, sampleCount: audioData.length }
    });
  }

  private calculateRMS(audioData: Float32Array): number {
    let sum = 0;
    for (let i = 0; i < audioData.length; i++) {
      sum += audioData[i] * audioData[i];
    }
    return Math.sqrt(sum / audioData.length);
  }

  private calculatePeak(audioData: Float32Array): number {
    let peak = 0;
    for (let i = 0; i < audioData.length; i++) {
      const abs = Math.abs(audioData[i]);
      if (abs > peak) peak = abs;
    }
    return peak;
  }

  private cleanup() {
    this.stopProcessing();
    
    if (this.audioContext) {
      this.audioContext.close().catch(console.error);
      this.audioContext = null;
    }
    
    this.analyser = null;
    this.dataArray = null;
    
    self.postMessage({
      type: 'CLEANUP_COMPLETE',
      data: { success: true }
    });
  }
}

// Initialize the worker
new AudioProcessorWorker();
