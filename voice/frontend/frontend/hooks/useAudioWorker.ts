import { useRef, useEffect, useCallback } from 'react';

export interface AudioWorkerData {
  frequencyData: number[];
  rms?: number;
  peak?: number;
  sampleCount?: number;
}

export interface UseAudioWorkerOptions {
  onFrequencyData?: (data: number[]) => void;
  onAudioAnalysis?: (data: { rms: number; peak: number; sampleCount: number }) => void;
  onError?: (error: string) => void;
}

export function useAudioWorker(options: UseAudioWorkerOptions = {}) {
  const workerRef = useRef<Worker | null>(null);
  const isInitializedRef = useRef(false);

  const initializeWorker = useCallback(() => {
    if (workerRef.current || typeof Worker === 'undefined') return;

    try {
      // Create worker from inline script to avoid separate file issues
      const workerScript = `
        class AudioProcessorWorker {
          constructor() {
            this.audioContext = null;
            this.analyser = null;
            this.dataArray = null;
            this.animationId = null;
            this.isProcessing = false;
            
            self.onmessage = this.handleMessage.bind(this);
          }

          handleMessage(event) {
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
            }
          }

          initializeAudioContext(sampleRate = 44100) {
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
                data: { error: error.message || 'Failed to initialize audio context' }
              });
            }
          }

          startProcessing() {
            this.isProcessing = true;
            this.processLoop();
          }

          stopProcessing() {
            this.isProcessing = false;
            if (this.animationId) {
              cancelAnimationFrame(this.animationId);
              this.animationId = null;
            }
          }

          processLoop() {
            if (!this.isProcessing || !this.analyser || !this.dataArray) return;

            this.analyser.getByteFrequencyData(this.dataArray);
            
            self.postMessage({
              type: 'FREQUENCY_DATA',
              data: { frequencyData: Array.from(this.dataArray) }
            });

            this.animationId = requestAnimationFrame(() => this.processLoop());
          }

          processAudioData(audioData) {
            const rms = this.calculateRMS(audioData);
            const peak = this.calculatePeak(audioData);
            
            self.postMessage({
              type: 'AUDIO_ANALYSIS',
              data: { rms, peak, sampleCount: audioData.length }
            });
          }

          calculateRMS(audioData) {
            let sum = 0;
            for (let i = 0; i < audioData.length; i++) {
              sum += audioData[i] * audioData[i];
            }
            return Math.sqrt(sum / audioData.length);
          }

          calculatePeak(audioData) {
            let peak = 0;
            for (let i = 0; i < audioData.length; i++) {
              const abs = Math.abs(audioData[i]);
              if (abs > peak) peak = abs;
            }
            return peak;
          }

          cleanup() {
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

        new AudioProcessorWorker();
      `;

      const blob = new Blob([workerScript], { type: 'application/javascript' });
      const workerUrl = URL.createObjectURL(blob);
      
      workerRef.current = new Worker(workerUrl);
      
      workerRef.current.onmessage = (event) => {
        const { type, data } = event.data;
        
        switch (type) {
          case 'AUDIO_CONTEXT_INITIALIZED':
            isInitializedRef.current = true;
            break;
          case 'AUDIO_CONTEXT_ERROR':
            options.onError?.(data.error);
            break;
          case 'FREQUENCY_DATA':
            options.onFrequencyData?.(data.frequencyData);
            break;
          case 'AUDIO_ANALYSIS':
            options.onAudioAnalysis?.(data);
            break;
          case 'CLEANUP_COMPLETE':
            isInitializedRef.current = false;
            break;
        }
      };

      workerRef.current.onerror = (error) => {
        console.error('Audio worker error:', error);
        options.onError?.('Audio worker error occurred');
      };

      // Clean up blob URL
      URL.revokeObjectURL(workerUrl);
      
    } catch (error) {
      console.error('Failed to create audio worker:', error);
      options.onError?.('Failed to initialize audio processing');
    }
  }, [options]);

  const initializeAudioContext = useCallback((sampleRate: number = 44100) => {
    if (!workerRef.current) return;
    
    workerRef.current.postMessage({
      type: 'INIT_AUDIO_CONTEXT',
      data: { sampleRate }
    });
  }, []);

  const startProcessing = useCallback(() => {
    if (!workerRef.current || !isInitializedRef.current) return;
    
    workerRef.current.postMessage({
      type: 'START_PROCESSING'
    });
  }, []);

  const stopProcessing = useCallback(() => {
    if (!workerRef.current) return;
    
    workerRef.current.postMessage({
      type: 'STOP_PROCESSING'
    });
  }, []);

  const processAudioData = useCallback((audioData: Float32Array) => {
    if (!workerRef.current) return;
    
    workerRef.current.postMessage({
      type: 'PROCESS_AUDIO_DATA',
      data: { audioData }
    });
  }, []);

  const cleanup = useCallback(() => {
    if (!workerRef.current) return;
    
    workerRef.current.postMessage({
      type: 'CLEANUP'
    });
  }, []);

  const terminateWorker = useCallback(() => {
    if (workerRef.current) {
      workerRef.current.terminate();
      workerRef.current = null;
      isInitializedRef.current = false;
    }
  }, []);

  useEffect(() => {
    initializeWorker();
    
    return () => {
      cleanup();
      terminateWorker();
    };
  }, [initializeWorker, cleanup, terminateWorker]);

  return {
    initializeAudioContext,
    startProcessing,
    stopProcessing,
    processAudioData,
    cleanup,
    isInitialized: isInitializedRef.current,
  };
}
