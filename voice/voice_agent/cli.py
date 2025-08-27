#!/usr/bin/env python3
"""
Command-line interface for the voice agent.
"""

# CRITICAL: Import cache setup FIRST before any other imports
from . import cache_setup

import asyncio
import argparse
import sys
import os
from pathlib import Path
from loguru import logger

from .main import VoiceAgent, check_dependencies


def create_parser():
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Production Voice Agent - Real-time AI voice assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  voice-agent                    # Start the voice agent with default settings
  voice-agent --host 0.0.0.0    # Listen on all interfaces
  voice-agent --port 8080       # Use custom port
  voice-agent --debug           # Enable debug logging
        """
    )
    
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="WebSocket server host (default: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="WebSocket server port (default: 8765)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    parser.add_argument(
        "--check-deps",
        action="store_true",
        help="Check dependencies and exit"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="Voice Agent 1.0.0"
    )
    
    return parser


async def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Configure logging level
    if args.debug:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    
    # Check dependencies only
    if args.check_deps:
        success = await check_dependencies()
        sys.exit(0 if success else 1)
    
    # Update settings if provided
    from .config.settings import settings
    if args.host:
        settings.server.websocket_host = args.host
    if args.port:
        settings.server.websocket_port = args.port
    
    # Check dependencies
    if not await check_dependencies():
        logger.error("Dependencies check failed. Please fix the issues and try again.")
        sys.exit(1)
        
    # Create and run voice agent
    agent = VoiceAgent()
    
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


def cli_main():
    """Synchronous CLI entry point."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown complete")


if __name__ == "__main__":
    cli_main()