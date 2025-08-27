import { useRef, useEffect, useCallback, useState } from 'react';
import { useAudioWorker } from './useAudioWorker';

export function useAudioVisualizer(stream: MediaStream | null, isActive: boolean) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameRef = useRef<number>();
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const [frequencyData, setFrequencyData] = useState<number[]>([]);
  const [audioStats, setAudioStats] = useState<{ rms: number; peak: number }>({ rms: 0, peak: 0 });

  const audioWorker = useAudioWorker({
    onFrequencyData: setFrequencyData,
    onAudioAnalysis: (data) => setAudioStats({ rms: data.rms, peak: data.peak }),
    onError: (error) => console.error('Audio worker error:', error),
  });

  const cleanupAudioContext = useCallback(() => {
    // Cancel animation frame
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = undefined;
    }

    // Disconnect and cleanup audio nodes
    if (sourceRef.current) {
      sourceRef.current.disconnect();
      sourceRef.current = null;
    }

    if (analyserRef.current) {
      analyserRef.current.disconnect();
      analyserRef.current = null;
    }

    // Close audio context
    if (audioContextRef.current) {
      if (audioContextRef.current.state !== 'closed') {
        audioContextRef.current.close().catch(console.error);
      }
      audioContextRef.current = null;
    }

    // Reset data
    setFrequencyData([]);
    setAudioStats({ rms: 0, peak: 0 });
  }, []);

  const initializeAudioContext = useCallback(async () => {
    if (!stream || !canvasRef.current) return;

    try {
      // Clean up existing context first
      cleanupAudioContext();

      // Create new audio context with optimal settings
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: 44100,
        latencyHint: 'interactive',
      });
      
      const audioContext = audioContextRef.current;

      // Resume context if suspended (required by some browsers)
      if (audioContext.state === 'suspended') {
        await audioContext.resume();
      }

      // Create analyser node with optimized settings
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256; // Good balance between resolution and performance
      analyser.smoothingTimeConstant = 0.8;
      analyser.minDecibels = -90;
      analyser.maxDecibels = -10;
      analyserRef.current = analyser;

      // Connect stream to analyser
      const source = audioContext.createMediaStreamSource(stream);
      source.connect(analyser);
      sourceRef.current = source;

      // Initialize worker with audio context
      audioWorker.initializeAudioContext(audioContext.sampleRate);

    } catch (error) {
      console.error('Error initializing audio context:', error);
      cleanupAudioContext();
    }
  }, [stream, cleanupAudioContext, audioWorker]);

  const drawWaveform = useCallback(() => {
    if (!canvasRef.current || !isActive) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas with fade effect for smoother animation
    ctx.fillStyle = 'rgba(0, 0, 0, 0.1)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    if (frequencyData.length === 0) {
      animationFrameRef.current = requestAnimationFrame(drawWaveform);
      return;
    }

    // Create dynamic gradient based on audio intensity
    const intensity = audioStats.peak;
    const gradient = ctx.createLinearGradient(0, 0, canvas.width, 0);
    
    if (intensity > 0.7) {
      gradient.addColorStop(0, '#ef4444'); // Red for high intensity
      gradient.addColorStop(0.5, '#f97316'); // Orange
      gradient.addColorStop(1, '#eab308'); // Yellow
    } else if (intensity > 0.4) {
      gradient.addColorStop(0, '#8b5cf6'); // Purple
      gradient.addColorStop(0.5, '#ec4899'); // Pink
      gradient.addColorStop(1, '#06b6d4'); // Cyan
    } else {
      gradient.addColorStop(0, '#6366f1'); // Indigo
      gradient.addColorStop(0.5, '#8b5cf6'); // Purple
      gradient.addColorStop(1, '#06b6d4'); // Cyan
    }

    // Draw frequency bars with improved visualization
    const barWidth = canvas.width / frequencyData.length;
    const maxBarHeight = canvas.height * 0.9;

    for (let i = 0; i < frequencyData.length; i++) {
      const barHeight = (frequencyData[i] / 255) * maxBarHeight;
      const x = i * barWidth;
      const y = canvas.height - barHeight;
      
      // Add glow effect for active bars
      if (barHeight > 5) {
        ctx.shadowColor = intensity > 0.5 ? '#ff6b6b' : '#8b5cf6';
        ctx.shadowBlur = 10;
      } else {
        ctx.shadowBlur = 0;
      }
      
      ctx.fillStyle = gradient;
      ctx.fillRect(x, y, barWidth - 1, barHeight);
      
      // Add highlight on top of bars
      if (barHeight > 10) {
        ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.fillRect(x, y, barWidth - 1, Math.min(3, barHeight * 0.1));
      }
    }

    // Reset shadow
    ctx.shadowBlur = 0;

    if (isActive) {
      animationFrameRef.current = requestAnimationFrame(drawWaveform);
    }
  }, [isActive, frequencyData, audioStats]);

  const drawIdleState = useCallback(() => {
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw subtle idle waveform
    const gradient = ctx.createLinearGradient(0, 0, canvas.width, 0);
    gradient.addColorStop(0, '#374151');
    gradient.addColorStop(0.5, '#4b5563');
    gradient.addColorStop(1, '#374151');

    const barCount = 32;
    const barWidth = canvas.width / barCount;
    const time = Date.now() * 0.001;

    for (let i = 0; i < barCount; i++) {
      // Create subtle animated idle pattern
      const barHeight = (Math.sin(time + i * 0.5) * 0.5 + 0.5) * 15 + 5;
      const x = i * barWidth;
      const y = canvas.height - barHeight;
      
      ctx.fillStyle = gradient;
      ctx.fillRect(x, y, barWidth - 1, barHeight);
    }
  }, []);

  // Handle active state changes
  useEffect(() => {
    if (isActive && stream) {
      initializeAudioContext().then(() => {
        audioWorker.startProcessing();
        drawWaveform();
      });
    } else {
      audioWorker.stopProcessing();
      
      // Draw idle state with animation
      const idleAnimation = () => {
        drawIdleState();
        if (!isActive) {
          requestAnimationFrame(idleAnimation);
        }
      };
      idleAnimation();
    }

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isActive, stream, initializeAudioContext, audioWorker, drawWaveform, drawIdleState]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanupAudioContext();
      audioWorker.cleanup();
    };
  }, [cleanupAudioContext, audioWorker]);

  return { 
    canvasRef, 
    audioStats,
    isProcessing: isActive && frequencyData.length > 0,
  };
}
