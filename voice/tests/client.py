#!/usr/bin/env python3
"""
Voice Agent Test Client
Consolidated client for testing all voice agent functionality.
"""

import asyncio
import json
import sys
import websockets
import argparse
from pathlib import Path
from loguru import logger

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

class VoiceAgentClient:
    """Consolidated WebSocket client for the Voice Agent."""
    
    def __init__(self, host="localhost", port=8765):
        self.host = host
        self.port = port
        self.uri = f"ws://{host}:{port}"
        self.websocket = None
        
        # Configure logging
        logger.remove()
        logger.add(
            sys.stderr,
            level="INFO",
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> - <level>{message}</level>"
        )
    
    async def connect(self) -> bool:
        """Connect to the voice agent."""
        try:
            logger.info(f"Connecting to {self.uri}...")
            self.websocket = await asyncio.wait_for(websockets.connect(self.uri), timeout=10.0)
            
            # Wait for welcome message
            welcome = await asyncio.wait_for(self.websocket.recv(), timeout=5.0)
            welcome_data = json.loads(welcome)
            logger.info(f"✅ Connected! {welcome_data.get('data', {}).get('message', '')}")
            return True
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from the voice agent."""
        if self.websocket:
            await self.websocket.close()
            logger.info("Disconnected")
    
    async def send_text(self, text: str):
        """Send text message to the voice agent."""
        message = {"type": "text", "text": text}
        await self.websocket.send(json.dumps(message))
        logger.info(f"📤 Sent: {text}")
    
    async def listen_for_responses(self, max_responses=10, timeout=15.0):
        """Listen for responses from the voice agent."""
        responses = []
        
        for i in range(max_responses):
            try:
                response = await asyncio.wait_for(self.websocket.recv(), timeout=timeout)
                data = json.loads(response)
                responses.append(data)
                
                msg_type = data.get("type", "unknown")
                if msg_type == "text":
                    text = data.get("text", "") or data.get("data", "")
                    logger.info(f"📥 AI: {text}")
                elif msg_type == "audio":
                    audio_hex = data.get("data", "")
                    if audio_hex:
                        audio_bytes = len(bytes.fromhex(audio_hex))
                        logger.info(f"🔊 Audio: {audio_bytes} bytes")
                elif msg_type == "status":
                    logger.info(f"📊 Status: {data.get('status')}")
                else:
                    logger.info(f"📥 Response: {data}")
                    
            except asyncio.TimeoutError:
                # Continue trying if we haven't received any responses yet
                if len(responses) > 0:
                    break
                if i == 0:
                    logger.warning("Waiting for response...")
                continue
            except json.JSONDecodeError:
                logger.warning(f"Non-JSON response: {response}")
        
        return responses


async def simple_test(host="localhost", port=8765):
    """Simple connectivity and functionality test."""
    logger.info("🧪 SIMPLE VOICE AGENT TEST")
    logger.info("=" * 40)
    
    client = VoiceAgentClient(host, port)
    
    try:
        # Test connection
        if not await client.connect():
            return False
        
        # Test text message
        await client.send_text("Hello! Please respond so I know you're working.")
        responses = await client.listen_for_responses(max_responses=20, timeout=5.0)
        
        # Evaluate results
        has_text = any(r.get("type") == "text" for r in responses)
        has_audio = any(r.get("type") == "audio" for r in responses)
        
        logger.info(f"\n📊 Results:")
        logger.info(f"   Responses: {len(responses)}")
        logger.info(f"   Text: {'✅' if has_text else '❌'}")
        logger.info(f"   Audio: {'✅' if has_audio else '❌'}")
        
        success = len(responses) > 0
        if success:
            logger.info("✅ Voice agent is working!")
        else:
            logger.error("❌ No responses received")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False
    finally:
        await client.disconnect()


async def interactive_mode(host="localhost", port=8765):
    """Interactive chat mode."""
    logger.info("💬 INTERACTIVE CHAT MODE")
    logger.info("Type messages to chat with AI")
    logger.info("Type 'quit' to exit")
    logger.info("=" * 40)
    
    client = VoiceAgentClient(host, port)
    
    try:
        if not await client.connect():
            return
        
        while True:
            try:
                # Get user input
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, input, "You: "
                )
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                
                if user_input.strip():
                    await client.send_text(user_input)
                    await client.listen_for_responses(max_responses=3, timeout=8.0)
                    
            except KeyboardInterrupt:
                break
            except EOFError:
                break
                
    except Exception as e:
        logger.error(f"Error in interactive mode: {e}")
    finally:
        await client.disconnect()


async def debug_connection(host="localhost", port=8765):
    """Debug basic WebSocket connection."""
    logger.info("🔧 DEBUG CONNECTION TEST")
    logger.info("=" * 40)
    
    uri = f"ws://{host}:{port}"
    
    try:
        logger.info(f"Attempting to connect to {uri}...")
        websocket = await asyncio.wait_for(websockets.connect(uri), timeout=5.0)
        async with websocket:
            logger.info("✅ Connection successful!")
            
            # Send simple message
            message = {"type": "text", "text": "Debug test"}
            logger.info(f"Sending: {message}")
            await websocket.send(json.dumps(message))
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                logger.info(f"Received: {response}")
                return True
            except asyncio.TimeoutError:
                logger.info("No response within 5 seconds (this may be normal)")
                return True  # Connection worked even if no response
                
    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")
        logger.info("💡 Make sure the voice agent server is running:")
        logger.info("   python -m voice_agent.cli")
        return False


async def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(description="Voice Agent Test Client")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=8765, help="Server port")
    parser.add_argument("--mode", choices=["simple", "interactive", "debug"], 
                       default="simple", help="Test mode")
    
    args = parser.parse_args()
    
    try:
        if args.mode == "simple":
            success = await simple_test(args.host, args.port)
            sys.exit(0 if success else 1)
        elif args.mode == "interactive":
            await interactive_mode(args.host, args.port)
        elif args.mode == "debug":
            success = await debug_connection(args.host, args.port)
            sys.exit(0 if success else 1)
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())