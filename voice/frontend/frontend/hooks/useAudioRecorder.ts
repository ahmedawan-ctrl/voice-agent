import { useState, useRef, useCallback, useEffect } from 'react';

export interface AudioRecorderState {
  isRecording: boolean;
  isSupported: boolean;
  audioBlob: Blob | null;
  error: string | null;
  duration: number;
}

export function useAudioRecorder() {
  const [state, setState] = useState<AudioRecorderState>({
    isRecording: false,
    isSupported: typeof navigator !== 'undefined' && !!navigator.mediaDevices?.getUserMedia,
    audioBlob: null,
    error: null,
    duration: 0,
  });

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const startTimeRef = useRef<number>(0);
  const durationIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const cleanupTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Cleanup function to properly dispose of resources
  const cleanupResources = useCallback(() => {
    // Clear duration interval
    if (durationIntervalRef.current) {
      clearInterval(durationIntervalRef.current);
      durationIntervalRef.current = null;
    }

    // Clear cleanup timeout
    if (cleanupTimeoutRef.current) {
      clearTimeout(cleanupTimeoutRef.current);
      cleanupTimeoutRef.current = null;
    }

    // Stop and cleanup media recorder
    if (mediaRecorderRef.current) {
      if (mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      mediaRecorderRef.current = null;
    }

    // Stop all tracks in the stream
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => {
        track.stop();
        track.enabled = false;
      });
      streamRef.current = null;
    }

    // Clear chunks
    chunksRef.current = [];
  }, []);

  const startRecording = useCallback(async () => {
    if (!state.isSupported) {
      setState(prev => ({ ...prev, error: 'Audio recording is not supported in this browser' }));
      return;
    }

    try {
      // Clean up any existing resources first
      cleanupResources();

      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 44100,
          channelCount: 1,
        } 
      });
      
      streamRef.current = stream;
      chunksRef.current = [];

      // Determine the best MIME type
      let mimeType = 'audio/webm';
      if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
        mimeType = 'audio/webm;codecs=opus';
      } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
        mimeType = 'audio/mp4';
      } else if (MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')) {
        mimeType = 'audio/ogg;codecs=opus';
      }

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType,
        audioBitsPerSecond: 128000,
      });

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(chunksRef.current, { 
          type: mimeType 
        });
        
        setState(prev => ({ 
          ...prev, 
          audioBlob, 
          isRecording: false 
        }));

        // Schedule cleanup after a delay to allow for blob processing
        cleanupTimeoutRef.current = setTimeout(() => {
          cleanupResources();
        }, 1000);
      };

      mediaRecorder.onerror = (event) => {
        console.error('MediaRecorder error:', event);
        setState(prev => ({ 
          ...prev, 
          error: 'Recording failed', 
          isRecording: false 
        }));
        cleanupResources();
      };

      mediaRecorder.onstart = () => {
        startTimeRef.current = Date.now();
        
        // Update duration every 100ms
        durationIntervalRef.current = setInterval(() => {
          const elapsed = (Date.now() - startTimeRef.current) / 1000;
          setState(prev => ({ ...prev, duration: elapsed }));
        }, 100);
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start(100); // Collect data every 100ms for smoother processing

      setState(prev => ({ 
        ...prev, 
        isRecording: true, 
        error: null,
        audioBlob: null,
        duration: 0,
      }));

    } catch (error) {
      console.error('Error starting recording:', error);
      cleanupResources();
      
      let errorMessage = 'Failed to start recording';
      if (error instanceof Error) {
        if (error.name === 'NotAllowedError') {
          errorMessage = 'Microphone access denied. Please allow microphone access and try again.';
        } else if (error.name === 'NotFoundError') {
          errorMessage = 'No microphone found. Please connect a microphone and try again.';
        } else if (error.name === 'NotReadableError') {
          errorMessage = 'Microphone is already in use by another application.';
        } else {
          errorMessage = error.message;
        }
      }
      
      setState(prev => ({ 
        ...prev, 
        error: errorMessage,
        isRecording: false 
      }));
    }
  }, [state.isSupported, cleanupResources]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && state.isRecording) {
      mediaRecorderRef.current.stop();
      
      // Clear duration interval
      if (durationIntervalRef.current) {
        clearInterval(durationIntervalRef.current);
        durationIntervalRef.current = null;
      }
    }
  }, [state.isRecording]);

  const toggleRecording = useCallback(() => {
    if (state.isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  }, [state.isRecording, startRecording, stopRecording]);

  const clearRecording = useCallback(() => {
    setState(prev => ({ 
      ...prev, 
      audioBlob: null, 
      error: null,
      duration: 0,
    }));
    
    // Clean up resources when clearing
    cleanupResources();
  }, [cleanupResources]);

  const getAudioStream = useCallback(() => {
    return streamRef.current;
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanupResources();
    };
  }, [cleanupResources]);

  // Auto-stop recording after 10 minutes to prevent excessive memory usage
  useEffect(() => {
    if (state.isRecording && state.duration > 600) { // 10 minutes
      console.warn('Auto-stopping recording after 10 minutes');
      stopRecording();
    }
  }, [state.isRecording, state.duration, stopRecording]);

  return {
    ...state,
    startRecording,
    stopRecording,
    toggleRecording,
    clearRecording,
    getAudioStream,
  };
}
