import React from 'react';
import { Play, Download, Trash2 } from 'lucide-react';

interface RecordingControlsProps {
  audioBlob: Blob | null;
  onClear: () => void;
  className?: string;
}

export default function RecordingControls({ audioBlob, onClear, className = '' }: RecordingControlsProps) {
  const playRecording = () => {
    if (!audioBlob) return;
    
    const audioUrl = URL.createObjectURL(audioBlob);
    const audio = new Audio(audioUrl);
    audio.play().catch(console.error);
    
    // Clean up URL after playing
    audio.addEventListener('ended', () => {
      URL.revokeObjectURL(audioUrl);
    });
  };

  const downloadRecording = () => {
    if (!audioBlob) return;
    
    const audioUrl = URL.createObjectURL(audioBlob);
    const link = document.createElement('a');
    link.href = audioUrl;
    link.download = `recording-${new Date().toISOString().slice(0, 19)}.webm`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(audioUrl);
  };

  if (!audioBlob) return null;

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <button
        onClick={playRecording}
        className="flex items-center justify-center w-10 h-10 rounded-full bg-green-600 hover:bg-green-700 transition-colors duration-200 shadow-lg hover:shadow-green-500/25"
        title="Play recording"
      >
        <Play className="w-4 h-4 text-white ml-0.5" />
      </button>
      
      <button
        onClick={downloadRecording}
        className="flex items-center justify-center w-10 h-10 rounded-full bg-blue-600 hover:bg-blue-700 transition-colors duration-200 shadow-lg hover:shadow-blue-500/25"
        title="Download recording"
      >
        <Download className="w-4 h-4 text-white" />
      </button>
      
      <button
        onClick={onClear}
        className="flex items-center justify-center w-10 h-10 rounded-full bg-red-600 hover:bg-red-700 transition-colors duration-200 shadow-lg hover:shadow-red-500/25"
        title="Delete recording"
      >
        <Trash2 className="w-4 h-4 text-white" />
      </button>
    </div>
  );
}
