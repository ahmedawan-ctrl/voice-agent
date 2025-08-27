import React from 'react';
import { useAudioVisualizer } from '../hooks/useAudioVisualizer';

interface AudioWaveformProps {
  stream: MediaStream | null;
  isActive: boolean;
  className?: string;
}

export default function AudioWaveform({ stream, isActive, className = '' }: AudioWaveformProps) {
  const { canvasRef, audioStats, isProcessing } = useAudioVisualizer(stream, isActive);

  return (
    <div className={`relative ${className}`}>
      <canvas
        ref={canvasRef}
        width={200}
        height={60}
        className="w-full h-full rounded-lg bg-black/20 backdrop-blur-sm border border-white/10"
      />
      
      {/* Activity indicator overlay */}
      {isActive && (
        <div className="absolute inset-0 rounded-lg bg-gradient-to-r from-purple-500/10 to-pink-500/10 animate-pulse" />
      )}
      
      {/* Audio level indicators */}
      {isProcessing && (
        <div className="absolute top-1 right-1 flex gap-1">
          {/* RMS level indicator */}
          <div 
            className="w-1 h-4 bg-green-400 rounded-full transition-all duration-100"
            style={{ 
              height: `${Math.max(4, audioStats.rms * 16)}px`,
              opacity: audioStats.rms > 0.1 ? 1 : 0.3 
            }}
          />
          {/* Peak level indicator */}
          <div 
            className="w-1 h-4 bg-red-400 rounded-full transition-all duration-50"
            style={{ 
              height: `${Math.max(4, audioStats.peak * 16)}px`,
              opacity: audioStats.peak > 0.1 ? 1 : 0.3 
            }}
          />
        </div>
      )}
      
      {/* Status text */}
      <div className="absolute bottom-1 left-1 text-xs text-white/60">
        {isActive ? (isProcessing ? 'Processing' : 'Listening') : 'Idle'}
      </div>
    </div>
  );
}
