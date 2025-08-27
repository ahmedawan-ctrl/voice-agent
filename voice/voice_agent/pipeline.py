"""
Main Pipecat pipeline for the voice agent
Adapted from pipecat examples
"""

# CRITICAL: Import cache setup FIRST before any HF-related imports
from . import cache_setup

import asyncio
import uuid
from typing import List, Optional
from loguru import logger

# Import Pipecat components
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.services.ollama.llm import OLLamaLLMService
from pipecat.frames.frames import (
    Frame,
    SystemFrame,
    TextFrame,
    AudioRawFrame,
    StartFrame,
    EndFrame,
)
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection

# Import our custom services
from .services.kyutai_stt import KyutaiSTTServiceWithVAD
from .services.kyutai_tts import KyutaiTTSService
from .config.settings import settings


class VoiceAgentPipeline:
    """
    Main voice agent pipeline combining Kyutai STT/TTS with Ollama LLM.
    """
    
    def __init__(self, transport=None):
        """
        Initialize the voice agent pipeline.
        
        Args:
            transport: Transport layer (WebSocket, WebRTC, etc.)
        """
        self.transport = transport
        self.pipeline = None
        self.task = None
        self.runner = PipelineRunner()
        
        # Services
        self.stt_service = None
        self.llm_service = None
        self.tts_service = None
        self.context = None
        self.context_aggregator = None
        
        # Pipeline state
        self._running = False
        self._initialized = False
        
    async def initialize(self):
        """Initialize all services and build the pipeline."""
        logger.info("🚀 Initializing Voice Agent Pipeline...")
        
        # Validate settings
        settings.validate()
        
        # Initialize STT with semantic VAD
        logger.info("Loading Kyutai STT service...")
        self.stt_service = KyutaiSTTServiceWithVAD(
            model_name=settings.kyutai.stt_model,
            device=settings.kyutai.device,
            sample_rate=settings.audio.sample_rate_stt,
            chunk_size_ms=settings.audio.chunk_size_ms,
            vad_threshold=settings.audio.vad_threshold,
            cache_dir=settings.kyutai.cache_dir,
            audio_passthrough=True  # Don't pass audio through
        )
        
        # Initialize Ollama LLM
        logger.info("Loading Ollama LLM service...")
        self.llm_service = OLLamaLLMService(
            model=settings.ollama.model,
            base_url=settings.ollama.host,
            temperature=settings.ollama.temperature,
            max_tokens=settings.ollama.max_tokens,
        )
        
        # Initialize TTS
        logger.info("Loading Kyutai TTS service...")
        self.tts_service = KyutaiTTSService(
            voice=settings.kyutai.tts_voice,
            model_type=settings.kyutai.tts_model_type,
            device=settings.kyutai.device,
            sample_rate=settings.audio.sample_rate_tts,
            cache_dir=settings.kyutai.cache_dir,
        )
        
        # Initialize conversation context
        self.context = OpenAILLMContext(
            messages=[
                {
                    "role": "system",
                    "content": """You are a helpful AI voice assistant powered by advanced speech technology.
                    You provide clear, concise, and friendly responses.
                    Keep your responses brief and conversational, suitable for voice interaction.
                    If asked about your capabilities, mention that you use Kyutai's speech models
                    for understanding and generating speech, and Phi-4 Mini for intelligence."""
                }
            ]
        )
        
        # Build the pipeline
        await self._build_pipeline()
        self._initialized = True
        
        logger.info("✅ Voice Agent Pipeline initialized successfully!")
        
    async def _build_pipeline(self):
        """Build the processing pipeline."""
        # Create context aggregator for proper LLM message handling
        self.context_aggregator = self.llm_service.create_context_aggregator(self.context)
        
        processors = []
        
        # Add transport input if available
        if self.transport:
            processors.append(self.transport.input())
            
        # Add main processing chain
        processors.extend([
            self.stt_service,                        # Speech to text
            self.context_aggregator.user(),          # User message aggregator
            self.llm_service,                        # LLM processing
            self.tts_service,                        # Text to speech
            self.context_aggregator.assistant(),     # Assistant message aggregator (captures for context)
        ])
        
        # Add transport output if available
        if self.transport:
            processors.append(self.transport.output())
            
        # Create pipeline
        self.pipeline = Pipeline(processors)
        
    async def start(self):
        """Start the pipeline."""
        if not self._initialized:
            raise RuntimeError("Pipeline must be initialized before starting")
            
        if self._running:
            logger.warning("Pipeline is already running")
            return
            
        logger.info("Starting voice agent pipeline...")
        self._running = True
        
        try:
            # Create pipeline task with proper parameters
            self.task = PipelineTask(
                self.pipeline,
                params=PipelineParams(
                    allow_interruptions=True,
                    enable_metrics=settings.enable_metrics,
                    enable_usage_metrics=settings.enable_metrics,
                    send_initial_empty_metrics=False,
                )
            )
            
            # The pipeline task is created but not started yet
            # It will be started by the PipelineRunner in main.py
            logger.info("✅ Voice agent pipeline task created and ready")
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            self._running = False
            raise
        
    async def stop(self):
        """Stop the pipeline."""
        if not self._running:
            logger.warning("Pipeline is not running")
            return
            
        logger.info("Stopping voice agent pipeline...")
        self._running = False
        
        try:
            # Stop the pipeline task if it exists
            if hasattr(self, 'task') and self.task:
                await self.task.cancel()
                
        except Exception as e:
            logger.error(f"Error stopping pipeline: {e}")
            
        logger.info("✅ Voice agent pipeline stopped")
        
    async def process_text(self, text: str) -> bool:
        """Process text through the pipeline using proper Pipecat approach."""
        logger.info(f"process_text called with: {text}")
        logger.info(f"Pipeline running: {self._running}, Task exists: {self.task is not None}")
        
        if not self._running or not self.task:
            logger.warning("Pipeline is not running or task is None")
            return False
            
        try:
            logger.info(f"Processing text through pipeline: {text}")
            
            # Add user message to context
            self.context.add_message({"role": "user", "content": text})
            logger.info(f"Added message to context. Total messages: {len(self.context.get_messages())}")
            
            # Get context frame from the user aggregator to trigger LLM processing
            context_frame = self.context_aggregator.user().get_context_frame()
            
            logger.info("Created context frame for processing")
            
            await self.task.queue_frame(context_frame)
            logger.info("Context frame queued to pipeline successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error processing text: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    async def process_audio(self, audio_data: bytes):
        """
        Process audio input directly.
        
        Args:
            audio_data: Raw audio bytes
        """
        if not self._running or not self.task:
            logger.error("Pipeline is not running")
            return
            
        logger.info(f"Processing audio: {len(audio_data)} bytes")
        
        # Create audio frame and queue it to the pipeline task
        try:
            frame = AudioRawFrame(
                audio=audio_data,
                sample_rate=settings.audio.sample_rate_stt,
                num_channels=1
            )
            
            # Add missing attributes for compatibility with Pipecat observers
            frame.id = str(uuid.uuid4())
            frame.name = "AudioRawFrame"
            frame.pts = None
            frame.metadata = {}
            frame.transport_source = None
            frame.transport_destination = None
            
            await self.task.queue_frame(frame)
            logger.info("Audio frame queued successfully")
        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            import traceback
            traceback.print_exc()



class AudioResampler(FrameProcessor):
    """
    Processor to resample audio between different sample rates.
    Needed because STT uses 16kHz and TTS uses 24kHz.
    """
    
    def __init__(
        self,
        input_rate: int,
        output_rate: int,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.input_rate = input_rate
        self.output_rate = output_rate
        
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process and resample audio frames."""
        if isinstance(frame, AudioRawFrame):
            # Resample audio if needed
            if self.input_rate != self.output_rate:
                import scipy.signal
                import numpy as np
                
                # Convert bytes to numpy array
                audio_np = np.frombuffer(frame.audio, dtype=np.int16)
                
                # Resample
                num_samples = int(len(audio_np) * self.output_rate / self.input_rate)
                resampled = scipy.signal.resample(audio_np, num_samples)
                
                # Convert back to bytes
                frame.audio = resampled.astype(np.int16).tobytes()
                frame.sample_rate = self.output_rate
                
        await self.push_frame(frame, direction)


async def create_pipeline_with_transport(transport):
    """
    Create and initialize a pipeline with a specific transport.
    
    Args:
        transport: Transport instance (WebSocket, WebRTC, etc.)
        
    Returns:
        VoiceAgentPipeline instance
    """
    pipeline = VoiceAgentPipeline(transport)
    await pipeline.initialize()
    return pipeline
