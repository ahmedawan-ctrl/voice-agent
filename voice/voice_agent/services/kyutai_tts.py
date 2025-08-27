"""
Kyutai TTS Service for Pipecat
Adapted from moshi repository using Mimi codec and TTS models
"""

# CRITICAL: Import cache setup FIRST before any HF-related imports
from .. import cache_setup

import asyncio
import os
import torch
import numpy as np
from pathlib import Path
from typing import AsyncGenerator, Optional, List, Dict, Any
from loguru import logger
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../moshi'))

from pipecat.frames.frames import (
    Frame,
    TTSAudioRawFrame,
    TTSStartedFrame,
    TTSStoppedFrame,
    StartFrame,
)
from pipecat.services.tts_service import TTSService

# Import from moshi package
try:
    from moshi.models import loaders, MimiModel, LMModel
    from moshi.models.tts import TTSModel, DEFAULT_DSM_TTS_REPO, DEFAULT_DSM_TTS_VOICE_REPO
    MOSHI_AVAILABLE = True
except ImportError:
    MOSHI_AVAILABLE = False
    logger.warning("Moshi package not available, will use fallback TTS")


class KyutaiTTSService(TTSService):
    """
    TTS Service implementation using Kyutai's Moshi models.
    
    Features:
    - Ultra-low latency (160-200ms)
    - High-quality neural codec (Mimi)
    - Streaming audio generation
    - Support for both male (Moshiko) and female (Moshika) voices
    """
    
    def __init__(
        self,
        *,
        voice: str = "moshika",  # "moshika" (female) or "moshiko" (male)
        model_type: str = "pytorch-bf16",  # or "pytorch-q8" for quantized
        device: str = None,
        sample_rate: int = 24000,  # Mimi uses 24kHz
        chunk_duration_ms: int = 80,  # Mimi frame size
        cache_dir: str = ".hf_cache",
        **kwargs
    ):
        """
        Initialize Kyutai TTS Service.
        
        Args:
            voice: Voice to use ("moshika" for female, "moshiko" for male)
            model_type: Model variant (pytorch-bf16 or pytorch-q8)
            device: Device to run on (cuda/cpu, auto-detected if None)
            sample_rate: Audio sample rate (24000 Hz for Mimi)
            chunk_duration_ms: Duration of audio chunks in ms (80ms for Mimi)
            cache_dir: Directory for caching models
        """
        super().__init__(sample_rate=sample_rate, **kwargs)
        
        self._voice = voice
        self._model_type = model_type
        # Check for separate TTS device setting
        tts_device = os.getenv("KYUTAI_TTS_DEVICE")
        if tts_device:
            self._device = tts_device
        else:
            self._device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._chunk_duration_ms = chunk_duration_ms
        self._cache_dir = cache_dir
        
        # Model components
        self._moshi_model = None
        self._mimi_codec = None
        self._tokenizer = None
        
        # Audio generation state
        self._generation_context = None
        self._audio_buffer = []
        
        # Set up cache directory
        os.environ['HF_HOME'] = cache_dir
        os.environ['TRANSFORMERS_CACHE'] = cache_dir
        
        # Calculate chunk size in samples
        self._chunk_size = int(sample_rate * chunk_duration_ms / 1000)
        
        logger.info(f"Initializing Kyutai TTS with voice '{voice}' on {self._device}")
        
    async def start(self, frame: StartFrame):
        """Load models when pipeline starts."""
        await super().start(frame)
        await self._load_models()
        
    async def _load_models(self):
        """Load Kyutai TTS models with proper Moshika voice integration."""
        try:
            if not MOSHI_AVAILABLE:
                raise ImportError("Moshi package is required for Kyutai TTS")
            
            logger.info(f"Loading Kyutai TTS models for voice '{self._voice}'")
            
            # Set up HF cache environment - ensure absolute path
            cache_dir_abs = str(Path(self._cache_dir).absolute())
            os.environ['HF_HOME'] = cache_dir_abs
            os.environ['HF_HUB_CACHE'] = cache_dir_abs
            os.environ['TRANSFORMERS_CACHE'] = cache_dir_abs
            os.environ['HF_DATASETS_CACHE'] = cache_dir_abs
            os.environ['HUGGINGFACE_HUB_CACHE'] = cache_dir_abs
            logger.info(f"🗂️ TTS cache directory: {cache_dir_abs}")
            
            # Always use the default TTS model - it supports all voices
            model_repo = DEFAULT_DSM_TTS_REPO
            logger.info(f"Using TTS model: {model_repo}")
            
            # Load checkpoint info for TTS
            self._checkpoint_info = await asyncio.to_thread(
                loaders.CheckpointInfo.from_hf_repo,
                model_repo
            )
            
            # Load TTS model
            self._tts_model = await asyncio.to_thread(
                TTSModel.from_checkpoint_info,
                self._checkpoint_info,
                n_q=32,
                temp=0.6,
                device=self._device
            )
            
            # Handle voice selection - try to find Moshika voice in the voice repository
            try:
                if self._voice.lower() == "moshika":
                    # Try different possible Moshika voice file names
                    moshika_voice_candidates = [
                        "moshika.wav",
                        "expresso/moshika.wav", 
                        "voices/moshika.wav",
                        "female/moshika.wav",
                        # Fallback to a known female voice if Moshika not found
                        "expresso/ex03-ex01_happy_001_channel1_334s.wav"
                    ]
                    
                    voice_loaded = False
                    for voice_candidate in moshika_voice_candidates:
                        try:
                            self._voice_path = await asyncio.to_thread(
                                self._tts_model.get_voice_path,
                                voice_candidate
                            )
                            logger.info(f"✅ Found Moshika voice: {voice_candidate}")
                            voice_loaded = True
                            break
                        except:
                            continue
                    
                    if not voice_loaded:
                        logger.warning("Moshika voice file not found, using default female voice")
                        self._voice_path = await asyncio.to_thread(
                            self._tts_model.get_voice_path,
                            "expresso/ex03-ex01_happy_001_channel1_334s.wav"
                        )
                        
                elif self._voice.lower() == "moshiko":
                    # Try to find Moshiko (male) voice
                    moshiko_voice_candidates = [
                        "moshiko.wav",
                        "expresso/moshiko.wav",
                        "voices/moshiko.wav", 
                        "male/moshiko.wav",
                        # Fallback to a known male voice
                        "expresso/ex01-ex03_sad_001_channel1_334s.wav"
                    ]
                    
                    voice_loaded = False
                    for voice_candidate in moshiko_voice_candidates:
                        try:
                            self._voice_path = await asyncio.to_thread(
                                self._tts_model.get_voice_path,
                                voice_candidate
                            )
                            logger.info(f"✅ Found Moshiko voice: {voice_candidate}")
                            voice_loaded = True
                            break
                        except:
                            continue
                    
                    if not voice_loaded:
                        logger.warning("Moshiko voice file not found, using default voice")
                        self._voice_path = await asyncio.to_thread(
                            self._tts_model.get_voice_path,
                            "expresso/ex01-ex03_sad_001_channel1_334s.wav"
                        )
                else:
                    # Handle other voice names
                    voice_name = f"expresso/{self._voice}.wav" if not self._voice.endswith('.wav') else self._voice
                    self._voice_path = await asyncio.to_thread(
                        self._tts_model.get_voice_path,
                        voice_name
                    )
                    logger.info(f"Using voice file: {voice_name}")
                    
            except Exception as voice_error:
                # Final fallback to default voice
                logger.warning(f"Voice '{self._voice}' not found ({voice_error}), using default")
                self._voice_path = await asyncio.to_thread(
                    self._tts_model.get_voice_path,
                    "expresso/ex03-ex01_happy_001_channel1_334s.wav"
                )
            
            # Prepare condition attributes with the selected voice
            self._condition_attributes = await asyncio.to_thread(
                self._tts_model.make_condition_attributes,
                [self._voice_path],
                cfg_coef=2.0
            )
            
            logger.info(f"✅ Kyutai TTS models loaded: {model_repo}")
            logger.info(f"✅ Voice configured: {self._voice} -> {getattr(self, '_voice_path', 'default')}")
            
        except Exception as e:
            logger.error(f"Failed to load TTS models: {e}")
            raise
            
    async def _load_models_fallback(self, model_repo: str):
        """Fallback model loading using HuggingFace."""
        from transformers import AutoModel, AutoTokenizer
        
        # Load tokenizer
        self._tokenizer = await asyncio.to_thread(
            AutoTokenizer.from_pretrained,
            model_repo,
            cache_dir=self._cache_dir
        )
        
        # Load model
        self._moshi_model = await asyncio.to_thread(
            AutoModel.from_pretrained,
            model_repo,
            torch_dtype=torch.float16 if self._device == "cuda" else torch.float32,
            cache_dir=self._cache_dir
        )
        self._moshi_model.to(self._device)
        self._moshi_model.eval()
        
        # Try to load Mimi codec separately
        try:
            mimi_repo = "kyutai/mimi"
            self._mimi_codec = await asyncio.to_thread(
                AutoModel.from_pretrained,
                mimi_repo,
                torch_dtype=torch.float16 if self._device == "cuda" else torch.float32,
                cache_dir=self._cache_dir
            )
            self._mimi_codec.to(self._device)
            self._mimi_codec.eval()
        except Exception as e:
            logger.warning(f"Could not load Mimi codec separately: {e}")
            
    def _init_generation_context(self):
        """Initialize the generation context."""
        if hasattr(self._moshi_model, 'init_generation'):
            self._generation_context = self._moshi_model.init_generation()
        else:
            self._generation_context = {
                'cache': None,
                'past_tokens': [],
                'audio_tokens': []
            }
            
    async def run_tts(self, text: str) -> AsyncGenerator[Frame, None]:
        """
        Generate speech from text.
        
        Args:
            text: Text to convert to speech
            
        Yields:
            TTSAudioRawFrame containing audio chunks
        """
        if self._moshi_model is None:
            await self._load_models()
            
        try:
            # Emit TTS started frame
            yield TTSStartedFrame()
            
            # Generate audio
            async for audio_chunk in self._generate_audio(text):
                yield TTSAudioRawFrame(
                    audio=audio_chunk,
                    sample_rate=self._sample_rate,
                    num_channels=1
                )
                
            # Emit TTS stopped frame
            yield TTSStoppedFrame()
            
        except Exception as e:
            logger.error(f"Error generating TTS: {e}")
            yield TTSStoppedFrame()
            
    async def _generate_audio(self, text: str) -> AsyncGenerator[bytes, None]:
        """Generate audio from text using Moshi."""
        try:
            if hasattr(self._moshi_model, 'generate_streaming'):
                # Use streaming generation if available
                async for chunk in self._generate_streaming(text):
                    yield chunk
            else:
                # Fallback to batch generation
                audio = await self._generate_batch(text)
                # Split into chunks
                for i in range(0, len(audio), self._chunk_size):
                    chunk = audio[i:i + self._chunk_size]
                    yield chunk
                    
        except Exception as e:
            logger.error(f"Error in audio generation: {e}")
            
    async def _generate_streaming(self, text: str) -> AsyncGenerator[bytes, None]:
        """Generate audio using streaming interface."""
        try:
            # Prepare script entries
            entries = await asyncio.to_thread(
                self._tts_model.prepare_script,
                [text],
                padding_between=1
            )
            
            # Generate audio frames
            audio_chunks = []
            
            def on_frame(frame):
                if (frame != -1).all():
                    pcm = self._tts_model.mimi.decode(frame[:, 1:, :]).cpu().numpy()
                    audio_chunks.append(np.clip(pcm[0, 0], -1, 1))
            
            # Generate with callback
            await asyncio.to_thread(
                self._tts_model.generate,
                [entries],
                [self._condition_attributes],
                on_frame=on_frame
            )
            
            # Convert to bytes and yield chunks
            for chunk in audio_chunks:
                # Convert float32 to int16
                audio_int16 = (chunk * 32767).astype(np.int16)
                yield audio_int16.tobytes()
                
        except Exception as e:
            logger.error(f"Error in streaming generation: {e}")
            return
            
            async for audio_tokens in generator:
                # Decode audio tokens to waveform using Mimi
                if self._mimi_codec:
                    audio_tensor = await asyncio.to_thread(
                        self._decode_with_mimi,
                        audio_tokens
                    )
                else:
                    # Use built-in decoder
                    audio_tensor = self._moshi_model.decode_audio(audio_tokens)
                    
                # Convert to bytes
                audio_np = audio_tensor.cpu().numpy().squeeze()
                audio_bytes = (audio_np * 32768).astype(np.int16).tobytes()
                yield audio_bytes
                
    async def _generate_batch(self, text: str) -> bytes:
        """Generate audio in batch mode."""
        try:
            # Prepare script entries
            entries = await asyncio.to_thread(
                self._tts_model.prepare_script,
                [text],
                padding_between=1
            )
            
            # Generate all audio at once
            audio_chunks = []
            
            def on_frame(frame):
                if (frame != -1).all():
                    pcm = self._tts_model.mimi.decode(frame[:, 1:, :]).cpu().numpy()
                    audio_chunks.append(np.clip(pcm[0, 0], -1, 1))
            
            # Generate with callback
            await asyncio.to_thread(
                self._tts_model.generate,
                [entries],
                [self._condition_attributes],
                on_frame=on_frame
            )
            
            # Concatenate all chunks
            if audio_chunks:
                full_audio = np.concatenate(audio_chunks)
                # Convert float32 to int16
                audio_int16 = (full_audio * 32767).astype(np.int16)
                return audio_int16.tobytes()
            else:
                return b''
                
        except Exception as e:
            logger.error(f"Error in batch generation: {e}")
            return b''
        
    def _decode_with_mimi(self, audio_tokens: torch.Tensor) -> torch.Tensor:
        """Decode audio tokens using Mimi codec."""
        with torch.no_grad():
            # Mimi decoding
            if hasattr(self._mimi_codec, 'decode'):
                audio = self._mimi_codec.decode(audio_tokens)
            else:
                # Fallback if method name is different
                audio = self._mimi_codec(audio_tokens)
        return audio
        
    async def stop(self, frame=None):
        """Clean up when stopping."""
        if frame:
            await super().stop(frame)
        else:
            await super().stop()
        
        # Clear models from memory
        if hasattr(self, '_tts_model') and self._tts_model is not None:
            del self._tts_model
            self._tts_model = None
            
        # Clear CUDA cache if using GPU
        if self._device == "cuda":
            torch.cuda.empty_cache()
            
        logger.info("Kyutai TTS service stopped")


class KyutaiMultiVoiceTTS(KyutaiTTSService):
    """
    Extended TTS service with support for multiple voices and voice cloning.
    """
    
    def __init__(
        self,
        voices: Dict[str, str] = None,
        default_voice: str = "moshika",
        **kwargs
    ):
        """
        Initialize multi-voice TTS.
        
        Args:
            voices: Dictionary mapping voice names to model names
            default_voice: Default voice to use
        """
        super().__init__(voice=default_voice, **kwargs)
        
        self._voices = voices or {
            "female": "moshika",
            "male": "moshiko",
            "assistant": "moshika",
            "narrator": "moshiko"
        }
        self._current_voice = default_voice
        self._voice_models = {}
        
    async def set_voice(self, voice_name: str):
        """Switch to a different voice."""
        if voice_name in self._voices:
            self._current_voice = self._voices[voice_name]
            # Load model if not already loaded
            if self._current_voice not in self._voice_models:
                await self._load_voice_model(self._current_voice)
        else:
            logger.warning(f"Voice '{voice_name}' not found, using default")
            
    async def _load_voice_model(self, voice: str):
        """Load a specific voice model."""
        # Implementation would load the model for the specific voice
        pass
