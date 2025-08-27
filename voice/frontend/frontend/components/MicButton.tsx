import React, { useState } from 'react';
import { Mic, MicOff, AlertCircle } from 'lucide-react';
import { useAudioRecorder } from '../hooks/useAudioRecorder';
import AudioWaveform from './AudioWaveform';
import RecordingControls from './RecordingControls';

export default function MicButton() {
  const [isHovered, setIsHovered] = useState(false);
  const {
    isRecording,
    isSupported,
    audioBlob,
    error,
    duration,
    toggleRecording,
    clearRecording,
    getAudioStream,
  } = useAudioRecorder();

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (!isSupported) {
    return (
      <div className="text-center">
        <div className="relative w-24 h-24 rounded-full bg-gray-600 shadow-2xl flex items-center justify-center mb-4">
          <AlertCircle className="w-8 h-8 text-gray-400" />
        </div>
        <p className="text-red-400 text-sm">Audio recording not supported</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-6">
      {/* Waveform Visualization */}
      <div className="w-64 h-16">
        <AudioWaveform 
          stream={getAudioStream()} 
          isActive={isRecording}
          className="w-full h-full"
        />
      </div>

      {/* Main Recording Button */}
      <div className="relative">
        {/* Ripple effect when recording */}
        {isRecording && (
          <div className="absolute inset-0 animate-ping">
            <div className="w-full h-full rounded-full border-2 border-red-400/50"></div>
          </div>
        )}
        
        {/* Hover ripple effect */}
        {isHovered && !isRecording && (
          <div className="absolute inset-0 animate-ping">
            <div className="w-full h-full rounded-full border-2 border-purple-400/50"></div>
          </div>
        )}
        
        {/* Main button */}
        <button
          onClick={toggleRecording}
          className={`relative w-24 h-24 rounded-full shadow-2xl transition-all duration-300 animate-float group ${
            isRecording
              ? 'bg-gradient-to-br from-red-600 to-red-700 shadow-red-500/50 hover:shadow-red-500/70'
              : 'bg-gradient-to-br from-purple-600 to-pink-600 shadow-purple-500/50 hover:shadow-purple-500/70'
          }`}
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
          disabled={!!error}
        >
          {/* Neon glow */}
          <div className={`absolute inset-0 rounded-full opacity-50 blur-md group-hover:opacity-70 transition-opacity duration-300 ${
            isRecording
              ? 'bg-gradient-to-br from-red-400 to-red-500'
              : 'bg-gradient-to-br from-purple-400 to-pink-400'
          }`}></div>
          
          {/* Button content */}
          <div className="relative z-10 flex items-center justify-center w-full h-full">
            {isRecording ? (
              <MicOff className="w-8 h-8 text-white group-hover:scale-110 transition-transform duration-300" />
            ) : (
              <Mic className="w-8 h-8 text-white group-hover:scale-110 transition-transform duration-300" />
            )}
          </div>
          
          {/* Inner glow */}
          <div className="absolute inset-2 rounded-full bg-gradient-to-br from-white/20 to-transparent opacity-30"></div>
          
          {/* Recording indicator */}
          {isRecording && (
            <div className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 rounded-full animate-pulse flex items-center justify-center">
              <div className="w-3 h-3 bg-white rounded-full"></div>
            </div>
          )}
        </button>
      </div>

      {/* Duration Display */}
      {isRecording && (
        <div className="text-center">
          <div className="text-2xl font-mono text-cyan-400 mb-1">
            {formatDuration(duration)}
          </div>
          <div className="text-xs text-gray-400">
            Recording duration
          </div>
        </div>
      )}

      {/* Status Text */}
      <div className="text-center min-h-[2rem]">
        {error && (
          <p className="text-red-400 text-sm max-w-xs">{error}</p>
        )}
        {isRecording && !error && (
          <p className="text-green-400 text-sm animate-pulse">Recording in progress...</p>
        )}
        {!isRecording && !error && audioBlob && (
          <p className="text-cyan-400 text-sm">Recording complete • {formatDuration(duration)}</p>
        )}
        {!isRecording && !error && !audioBlob && (
          <p className="text-gray-400 text-sm">Click to start recording</p>
        )}
      </div>

      {/* Recording Controls */}
      <RecordingControls 
        audioBlob={audioBlob}
        onClear={clearRecording}
        className="mt-2"
      />
    </div>
  );
}
