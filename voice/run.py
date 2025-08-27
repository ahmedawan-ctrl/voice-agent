#!/usr/bin/env python3
"""
Production Voice Agent Entry Point

A real-time voice agent built with Pipecat AI framework.
Supports speech-to-text, text-to-speech, and LLM integration.
"""

import asyncio
import signal
import sys
from loguru import logger

from voice_agent.main import VoiceAgent, check_dependencies


async def main():
    """Main entry point."""
    # Check dependencies
    if not await check_dependencies():
        logger.error("Dependencies check failed. Please fix the issues and try again.")
        sys.exit(1)
        
    # Create and run voice agent
    agent = VoiceAgent()
    
    # Set up signal handlers
    def signal_handler(sig, frame):
        logger.info("Received interrupt signal, shutting down...")
        asyncio.create_task(agent.stop())
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the agent
    try:
        await agent.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise
    finally:
        await agent.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown complete")