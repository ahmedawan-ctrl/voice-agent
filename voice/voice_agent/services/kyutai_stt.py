"""
Kyutai STT Service for Pipecat
Adapted from delayed-streams-modeling repository
"""

# CRITICAL: Import cache setup FIRST before any HF-related imports
from .. import cache_setup

import asyncio
import os
import torch
import numpy as np
from pathlib import Path
from typing import AsyncGenerator, Optional, Dict, Any
from loguru import logger
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../delayed-streams-modeling'))

from pipecat.frames.frames import (
    AudioRawFrame,
    Frame,
    TranscriptionFrame,
    InterimTranscriptionFrame,
    StartFrame,
    EndFrame,
)
from pipecat.services.stt_service import STTService
from pipecat.transcriptions.language import Language

# Import from moshi package which includes Kyutai models
try:
    from moshi.models import loaders, MimiModel, LMModel, LMGen
    import sentencepiece
    MOSHI_AVAILABLE = True
except ImportError:
    MOSHI_AVAILABLE = False
    logger.warning("Moshi package not available, will use direct model loading")


class KyutaiSTTService(STTService):
    """
    STT Service implementation using Kyutai's delayed-streams-modeling.
    
    Features:
    - Streaming inference with low latency (0.5s delay for 1B model)
    - Word-level timestamps
    - Semantic VAD for voice activity detection
    - Support for both 1B and 2.6B models
    """
    
    def __init__(
        self,
        *,
        model_name: str = "kyutai/stt-1b-en_fr",
        device: str = None,
        sample_rate: int = 16000,
        chunk_size_ms: int = 100,
        use_semantic_vad: bool = True,
        cache_dir: str = ".hf_cache",
        **kwargs
    ):
        """
        Initialize Kyutai STT Service.
        
        Args:
            model_name: HuggingFace model repository (kyutai/stt-1b-en_fr or kyutai/stt-2.6b-en)
            device: Device to run the model on (cuda/cpu, auto-detected if None)
            sample_rate: Audio sample rate (16000 Hz recommended)
            chunk_size_ms: Size of audio chunks in milliseconds
            use_semantic_vad: Use semantic VAD for better voice detection
            cache_dir: Directory for caching downloaded models
        """
        super().__init__(sample_rate=sample_rate, **kwargs)
        
        self._model_name = model_name
        self._device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._chunk_size_ms = chunk_size_ms
        self._use_semantic_vad = use_semantic_vad
        self._cache_dir = cache_dir
        
        # Audio buffer for streaming
        self._audio_buffer = []
        self._chunk_size = int(sample_rate * chunk_size_ms / 1000)
        
        # Model state
        self._model = None
        self._processor = None
        self._context = None
        
        # Set up cache directory
        os.environ['HF_HOME'] = cache_dir
        os.environ['TRANSFORMERS_CACHE'] = cache_dir
        
        logger.info(f"Initializing Kyutai STT with model {model_name} on {self._device}")
        
    async def start(self, frame: StartFrame):
        """Load the model when pipeline starts."""
        await super().start(frame)
        await self._load_model()
        
    async def _load_model(self):
        """Load the STT model."""
        try:
            if not MOSHI_AVAILABLE:
                raise ImportError("Moshi package is required for Kyutai STT models")
            
            # Load Kyutai STT model using moshi loaders
            logger.info(f"Loading Kyutai STT model from {self._model_name}")
            
            # Set up HF cache environment - ensure absolute path
            cache_dir_abs = str(Path(self._cache_dir).absolute())
            os.environ['HF_HOME'] = cache_dir_abs
            os.environ['HF_HUB_CACHE'] = cache_dir_abs
            os.environ['TRANSFORMERS_CACHE'] = cache_dir_abs
            os.environ['HF_DATASETS_CACHE'] = cache_dir_abs
            os.environ['HUGGINGFACE_HUB_CACHE'] = cache_dir_abs
            logger.info(f"🗂️ STT cache directory: {cache_dir_abs}")
            
            # Load checkpoint info
            self._checkpoint_info = await asyncio.to_thread(
                loaders.CheckpointInfo.from_hf_repo,
                self._model_name
            )
            
            # Load Mimi (audio codec)
            self._mimi = await asyncio.to_thread(
                self._checkpoint_info.get_mimi,
                device=self._device
            )
            
            # Load text tokenizer
            self._text_tokenizer = await asyncio.to_thread(
                self._checkpoint_info.get_text_tokenizer
            )
            
            # Load language model
            self._lm = await asyncio.to_thread(
                self._checkpoint_info.get_moshi,
                device=self._device
            )
            
            # Create LM generator for streaming
            self._lm_gen = LMGen(self._lm, temp=0, temp_text=0, use_sampling=False)
            
            # Initialize streaming context
            self._init_streaming_context()
            
            logger.info(f"✅ STT model loaded: {self._model_name}")
            
        except Exception as e:
            logger.error(f"Failed to load STT model: {e}")
            raise
            
    def _init_streaming_context(self):
        """Initialize the streaming context for the model."""
        # Initialize streaming for both mimi and lm_gen
        batch_size = 1
        self._mimi.streaming_forever(batch_size)
        self._lm_gen.streaming_forever(batch_size)
        
        # Calculate frame size
        self._frame_size = int(self._mimi.sample_rate / self._mimi.frame_rate)
        
        # Initialize state
        self._first_frame = True
        self._processed_tokens = 0
            
    async def run_stt(self, audio: bytes) -> AsyncGenerator[Frame, None]:
        """
        Process audio and generate transcription frames.
        
        Args:
            audio: Raw audio bytes
            
        Yields:
            TranscriptionFrame or InterimTranscriptionFrame
        """
        if self._model is None:
            await self._load_model()
            
        # Convert bytes to numpy array
        audio_np = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
        
        # Add to buffer
        self._audio_buffer.extend(audio_np)
        
        # Process when we have enough data for a frame
        while len(self._audio_buffer) >= self._frame_size:
            chunk = np.array(self._audio_buffer[:self._frame_size])
            self._audio_buffer = self._audio_buffer[self._frame_size:]
            
            # Process chunk
            async for frame in self._process_chunk(chunk):
                yield frame
                
    async def _process_chunk(self, audio_chunk: np.ndarray) -> AsyncGenerator[Frame, None]:
        """Process a single audio chunk."""
        try:
            # Convert to tensor and ensure correct shape
            audio_tensor = torch.from_numpy(audio_chunk).to(self._device)
            if audio_tensor.dim() == 1:
                audio_tensor = audio_tensor.unsqueeze(0).unsqueeze(0)  # [batch, channels, samples]
            elif audio_tensor.dim() == 2:
                audio_tensor = audio_tensor.unsqueeze(0)  # [batch, channels, samples]
            
            with torch.no_grad():
                # Encode audio to codes using Mimi
                codes = await asyncio.to_thread(self._mimi.encode, audio_tensor)
                
                # Process codes through language model
                if self._first_frame:
                    # Ensure first slice is properly seen by transformer
                    tokens = await asyncio.to_thread(self._lm_gen.step, codes)
                    self._first_frame = False
                
                tokens = await asyncio.to_thread(self._lm_gen.step, codes)
                
                if tokens is not None:
                    # Decode tokens to text
                    text_parts = []
                    for token_id in tokens[0, 0].cpu().tolist():
                        if token_id not in [0, 3]:  # Skip special tokens
                            text_piece = self._text_tokenizer.id_to_piece(token_id)
                            text_piece = text_piece.replace("▁", " ")
                            text_parts.append(text_piece)
                    
                    if text_parts:
                        text = "".join(text_parts).strip()
                        if text:
                            yield TranscriptionFrame(
                                text=text,
                                user_id=self._user_id,
                                timestamp=None
                            )
                    
                    self._processed_tokens += 1
                        
        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}")

        
    async def stop(self, frame=None):
        """Clean up when stopping."""
        if frame:
            await super().stop(frame)
        else:
            await super().stop()
        
        # Process remaining buffer
        if hasattr(self, '_audio_buffer') and self._audio_buffer:
            remaining = np.array(self._audio_buffer)
            async for frame in self._process_chunk(remaining):
                yield frame
                
        # Clear model from memory
        if hasattr(self, '_mimi') and self._mimi is not None:
            del self._mimi
            self._mimi = None
            
        if hasattr(self, '_lm') and self._lm is not None:
            del self._lm
            self._lm = None
            
        if hasattr(self, '_lm_gen') and self._lm_gen is not None:
            del self._lm_gen
            self._lm_gen = None
            
        # Clear CUDA cache if using GPU
        if self._device == "cuda":
            torch.cuda.empty_cache()
            
        logger.info("Kyutai STT service stopped")


class KyutaiSTTServiceWithVAD(KyutaiSTTService):
    """
    Extended Kyutai STT with semantic VAD capabilities.
    
    The 1B model includes a semantic VAD that can detect when the user
    is actually speaking (vs background noise).
    """
    
    def __init__(self, vad_threshold: float = 0.5, **kwargs):
        """
        Initialize with VAD support.
        
        Args:
            vad_threshold: Threshold for voice activity detection (0.0-1.0)
        """
        super().__init__(use_semantic_vad=True, **kwargs)
        self._vad_threshold = vad_threshold
        self._is_speaking = False
        
    async def _process_chunk(self, audio_chunk: np.ndarray) -> AsyncGenerator[Frame, None]:
        """Process chunk with VAD."""
        # First check VAD if available
        if self._use_semantic_vad and hasattr(self._model, 'compute_vad'):
            audio_tensor = torch.from_numpy(audio_chunk).unsqueeze(0).to(self._device)
            
            with torch.no_grad():
                vad_score = await asyncio.to_thread(
                    self._model.compute_vad,
                    audio_tensor,
                    self._context
                )
                
            was_speaking = self._is_speaking
            self._is_speaking = vad_score > self._vad_threshold
            
            # Emit speaking state changes
            if not was_speaking and self._is_speaking:
                from pipecat.frames.frames import UserStartedSpeakingFrame
                yield UserStartedSpeakingFrame()
            elif was_speaking and not self._is_speaking:
                from pipecat.frames.frames import UserStoppedSpeakingFrame
                yield UserStoppedSpeakingFrame()
                
        # Process audio only if speaking
        if self._is_speaking or not self._use_semantic_vad:
            async for frame in super()._process_chunk(audio_chunk):
                yield frame
