#!/usr/bin/env python3
"""
Main Voice Agent application class.
"""

# CRITICAL: Import cache setup FIRST before any other imports
from . import cache_setup

import asyncio
import signal
import sys
import os
from pathlib import Path
from typing import Optional
from loguru import logger

from .pipeline import VoiceAgentPipeline, create_pipeline_with_transport
from .transports.websocket_transport import VoiceAgentWebSocketTransport
from .config.settings import settings


class VoiceAgent:
    """
    Main Voice Agent application.
    """
    
    def __init__(self):
        """Initialize the voice agent."""
        self.pipeline = None
        self.transport = None
        self.running = False
        self.pipeline_task = None
        
        # Configure logging
        logger.remove()
        logger.add(
            sys.stderr,
            level="INFO",
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        )
        
    async def initialize(self):
        """Initialize the voice agent components."""
        logger.info("=" * 60)
        logger.info("🎙️ PRODUCTION VOICE AGENT")
        logger.info("=" * 60)
        logger.info("Components:")
        logger.info(f"  • STT: {settings.kyutai.stt_model}")
        logger.info(f"  • TTS: {settings.kyutai.tts_voice}")
        logger.info(f"  • LLM: {settings.ollama.model}")
        logger.info(f"  • Device: {settings.kyutai.device}")
        logger.info("=" * 60)
        
        # Create WebSocket transport
        logger.info("Initializing WebSocket transport...")
        self.transport = VoiceAgentWebSocketTransport(
            host=settings.server.websocket_host,
            port=settings.server.websocket_port,
            sample_rate=settings.audio.sample_rate_stt,
            enable_vad=True
        )
        
        # Create Pipecat transport
        pipecat_transport = self.transport.create_transport()
        
        # Create pipeline with transport
        logger.info("Creating voice agent pipeline...")
        self.pipeline = await create_pipeline_with_transport(pipecat_transport)
        
        # Set up callbacks
        self.transport.set_audio_callback(self.handle_audio_input)
        self.transport.set_text_callback(self.handle_text_input)
        self.transport.set_connect_callback(self.handle_client_connect)
        self.transport.set_disconnect_callback(self.handle_client_disconnect)
        
        logger.info("✅ Voice agent initialized successfully!")
        
    async def start(self):
        """Start the voice agent."""
        if self.running:
            logger.warning("Voice agent is already running")
            return
            
        self.running = True
        logger.info("Starting voice agent...")
        
        # Start WebSocket server
        await self.transport.start()
        
        # Start the pipeline
        await self.pipeline.start()
        
        # Send ready status
        await self.transport.send_status("ready", {
            "stt_model": settings.kyutai.stt_model,
            "tts_voice": settings.kyutai.tts_voice,
            "llm_model": settings.ollama.model
        })
        
        logger.info("🚀 Voice agent is running!")
        logger.info(f"🌐 WebSocket server: ws://{settings.server.websocket_host}:{settings.server.websocket_port}")
        logger.info("=" * 60)
        
    async def stop(self):
        """Stop the voice agent."""
        if not self.running:
            return
            
        logger.info("Stopping voice agent...")
        self.running = False
        
        # Send stopping status
        await self.transport.send_status("stopping")
        
        # Stop pipeline
        if self.pipeline:
            await self.pipeline.stop()
            
        # Stop transport
        if self.transport:
            await self.transport.stop()
            
        logger.info("✅ Voice agent stopped")
        
    async def handle_audio_input(self, audio_data: bytes, sample_rate: int):
        """Handle incoming audio from clients."""
        if not self.running:
            return
            
        # Process audio through pipeline
        await self.pipeline.process_audio(audio_data)
        
    async def handle_text_input(self, text: str):
        """Handle text input from clients."""
        logger.info(f"handle_text_input called with: {text}")
        logger.info(f"Voice agent running: {self.running}")
        
        if not self.running:
            logger.warning("Voice agent not running, ignoring text input")
            return
            
        logger.info(f"Processing text input: {text}")
        
        # Process text through pipeline
        result = await self.pipeline.process_text(text)
        logger.info(f"Pipeline process_text result: {result}")
        
    async def handle_client_connect(self, client_id: str):
        """Handle client connection."""
        logger.info(f"Client connected: {client_id}")
        
        # Send welcome message
        await self.transport.send_status("connected", {
            "client_id": client_id,
            "message": "Welcome to the Voice Agent!"
        })
        
    async def handle_client_disconnect(self, client_id: str):
        """Handle client disconnection."""
        logger.info(f"Client disconnected: {client_id}")
        
    async def run(self):
        """Run the voice agent using PipelineRunner."""
        from pipecat.pipeline.runner import PipelineRunner
        
        # Initialize
        await self.initialize()
        
        # Start the voice agent components (but not the pipeline task yet)
        if self.running:
            logger.warning("Voice agent is already running")
            return
            
        self.running = True
        logger.info("Starting voice agent...")
        
        # Start WebSocket server
        await self.transport.start()
        
        # Start the pipeline (creates the task but doesn't run it)
        await self.pipeline.start()
        
        # Send ready status
        await self.transport.send_status("ready", {
            "stt_model": settings.kyutai.stt_model,
            "tts_voice": settings.kyutai.tts_voice,
            "llm_model": settings.ollama.model
        })
        
        logger.info("🚀 Voice agent is running!")
        logger.info(f"🌐 WebSocket server: ws://{settings.server.websocket_host}:{settings.server.websocket_port}")
        logger.info("=" * 60)
        
        # Start the pipeline runner in the background
        runner = PipelineRunner(handle_sigint=False)  # Don't handle SIGINT here
        
        # Start the pipeline task in the background
        self.pipeline_runner_task = asyncio.create_task(runner.run(self.pipeline.task))
        
        # Keep the main coroutine running
        try:
            # Wait indefinitely while the server and pipeline run
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            # Clean up
            if hasattr(self, 'pipeline_runner_task'):
                self.pipeline_runner_task.cancel()
                try:
                    await self.pipeline_runner_task
                except asyncio.CancelledError:
                    pass


async def check_dependencies():
    """Check if required services are available."""
    import aiohttp
    
    logger.info("Checking dependencies...")
    
    # Check Ollama
    try:
        async with aiohttp.ClientSession() as session:
            # Remove /v1 from host for the tags endpoint
            base_host = settings.ollama.host.replace("/v1", "")
            async with session.get(f"{base_host}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    models = [m["name"] for m in data.get("models", [])]
                    if settings.ollama.model not in models:
                        logger.warning(f"Model {settings.ollama.model} not found in Ollama")
                        logger.info(f"Available models: {', '.join(models)}")
                        logger.info(f"Run: ollama pull {settings.ollama.model}")
                    else:
                        logger.info(f"✅ Ollama is running with {settings.ollama.model}")
                else:
                    logger.error(f"Ollama API returned status {response.status}")
                    return False
    except Exception as e:
        logger.error(f"❌ Ollama is not running at {base_host}")
        logger.info("Please start Ollama with: ollama serve")
        return False
        
    # Check CUDA if configured
    if settings.kyutai.device == "cuda":
        import torch
        if not torch.cuda.is_available():
            logger.warning("CUDA is not available, falling back to CPU")
            settings.kyutai.device = "cpu"
        else:
            logger.info(f"✅ CUDA is available: {torch.cuda.get_device_name(0)}")
            
    return True