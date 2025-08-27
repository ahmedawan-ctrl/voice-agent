#!/usr/bin/env python3
"""
Interactive Voice Agent Test Client
Provides manual testing capabilities for real-time interaction with the voice agent.
"""

import asyncio
import json
import websockets
import numpy as np
import sys
from pathlib import Path
from loguru import logger
import argparse

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

class InteractiveVoiceClient:
    """Interactive client for manual testing of the voice agent."""
    
    def __init__(self, host="localhost", port=8765):
        self.host = host
        self.port = port
        self.uri = f"ws://{host}:{port}"
        self.websocket = None
        self.running = False
        
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
            welcome = await self.websocket.recv()
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
            logger.info("Disconnected from voice agent")
    
    async def listen_for_responses(self):
        """Listen for responses from the voice agent."""
        try:
            while self.running:
                response = await self.websocket.recv()
                await self.handle_response(response)
        except websockets.exceptions.ConnectionClosed:
            logger.info("Connection closed by server")
        except Exception as e:
            if self.running:  # Only log if we're still supposed to be running
                logger.error(f"Error listening for responses: {e}")
    
    async def handle_response(self, response: str):
        """Handle response from the voice agent."""
        try:
            data = json.loads(response)
            msg_type = data.get("type", "unknown")
            
            if msg_type == "text":
                text = data.get("text", "") or data.get("data", "")
                logger.info(f"🤖 AI: {text}")
                
            elif msg_type == "audio":
                audio_hex = data.get("data", "") or data.get("audio", "")
                if audio_hex:
                    audio_bytes = len(bytes.fromhex(audio_hex))
                    logger.info(f"🔊 Audio received: {audio_bytes} bytes")
                    
            elif msg_type == "status":
                status = data.get("status", "")
                logger.info(f"📊 Status: {status}")
                
            else:
                logger.info(f"📥 Response: {data}")
                
        except json.JSONDecodeError:
            logger.info(f"📥 Raw response: {response}")
    
    async def send_text(self, text: str):
        """Send text message to the voice agent."""
        message = {
            "type": "text",
            "text": text
        }
        
        await self.websocket.send(json.dumps(message))
        logger.info(f"📤 You: {text}")
    
    async def send_audio_file(self, audio_file: str):
        """Send audio file to the voice agent."""
        try:
            import wave
            
            with wave.open(audio_file, 'rb') as wf:
                logger.info(f"📁 Audio file info:")
                logger.info(f"   Channels: {wf.getnchannels()}")
                logger.info(f"   Sample rate: {wf.getframerate()}")
                logger.info(f"   Duration: {wf.getnframes() / wf.getframerate():.2f}s")
                
                # Read all audio data
                audio_data = wf.readframes(wf.getnframes())
                
                message = {
                    "type": "audio",
                    "data": audio_data.hex(),
                    "sample_rate": wf.getframerate(),
                    "channels": wf.getnchannels()
                }
                
                await self.websocket.send(json.dumps(message))
                logger.info(f"📤 Sent audio file: {len(audio_data)} bytes")
                
        except Exception as e:
            logger.error(f"Error sending audio file: {e}")
    
    def generate_test_audio(self, duration=2.0, frequency=440, message="test tone") -> bytes:
        """Generate test audio signal."""
        sample_rate = 16000
        samples = int(sample_rate * duration)
        t = np.linspace(0, duration, samples, False)
        
        if message == "test tone":
            # Simple sine wave
            audio = np.sin(2 * np.pi * frequency * t) * 0.3
        elif message == "speech-like":
            # More complex signal that might resemble speech
            audio = (np.sin(2 * np.pi * frequency * t) * 
                    np.sin(2 * np.pi * 5 * t) * 
                    np.random.normal(1, 0.1, len(t)) * 0.2)
        else:
            # White noise
            audio = np.random.normal(0, 0.1, samples)
        
        return (audio * 32767).astype(np.int16).tobytes()
    
    async def send_test_audio(self, audio_type="test tone"):
        """Send generated test audio."""
        audio_data = self.generate_test_audio(duration=1.0, message=audio_type)
        
        message = {
            "type": "audio",
            "data": audio_data.hex(),
            "sample_rate": 16000
        }
        
        await self.websocket.send(json.dumps(message))
        logger.info(f"📤 Sent {audio_type}: {len(audio_data)} bytes")
    
    async def conversation_mode(self):
        """Interactive conversation mode."""
        logger.info("=" * 50)
        logger.info("💬 CONVERSATION MODE")
        logger.info("Commands:")
        logger.info("  - Type messages to chat with AI")
        logger.info("  - '/audio <file>' - Send audio file")
        logger.info("  - '/test-audio' - Send test tone")
        logger.info("  - '/speech-audio' - Send speech-like signal")
        logger.info("  - '/noise-audio' - Send noise signal")
        logger.info("  - '/quit' - Exit")
        logger.info("=" * 50)
        
        self.running = True
        
        # Start listening for responses
        listen_task = asyncio.create_task(self.listen_for_responses())
        
        try:
            while self.running:
                try:
                    # Get user input
                    user_input = await asyncio.get_event_loop().run_in_executor(
                        None, input, "You: "
                    )
                    
                    if user_input.lower() in ['/quit', '/exit', '/q']:
                        break
                    elif user_input.startswith('/audio '):
                        audio_file = user_input[7:].strip()
                        if Path(audio_file).exists():
                            await self.send_audio_file(audio_file)
                        else:
                            logger.error(f"Audio file not found: {audio_file}")
                    elif user_input == '/test-audio':
                        await self.send_test_audio("test tone")
                    elif user_input == '/speech-audio':
                        await self.send_test_audio("speech-like")
                    elif user_input == '/noise-audio':
                        await self.send_test_audio("noise")
                    elif user_input.strip():
                        await self.send_text(user_input)
                        
                except KeyboardInterrupt:
                    break
                except EOFError:
                    break
                    
        finally:
            self.running = False
            listen_task.cancel()
            try:
                await listen_task
            except asyncio.CancelledError:
                pass
    
    async def quick_test_mode(self):
        """Quick automated test mode."""
        logger.info("=" * 50)
        logger.info("⚡ QUICK TEST MODE")
        logger.info("=" * 50)
        
        self.running = True
        
        # Start listening for responses
        listen_task = asyncio.create_task(self.listen_for_responses())
        
        try:
            # Test 1: Simple greeting
            logger.info("\n🧪 Test 1: Simple greeting")
            await self.send_text("Hello! Can you hear me?")
            await asyncio.sleep(3)
            
            # Test 2: Request specific response
            logger.info("\n🧪 Test 2: Specific response request")
            await self.send_text("Please say exactly 'Testing successful' so I know you're working.")
            await asyncio.sleep(5)
            
            # Test 3: Moshika voice test
            logger.info("\n🧪 Test 3: Moshika voice test")
            await self.send_text("Speak with your beautiful Moshika voice!")
            await asyncio.sleep(5)
            
            # Test 4: Audio input test
            logger.info("\n🧪 Test 4: Audio input test")
            await self.send_test_audio("test tone")
            await asyncio.sleep(3)
            
            logger.info("\n✅ Quick test completed!")
            
        finally:
            self.running = False
            listen_task.cancel()
            try:
                await listen_task
            except asyncio.CancelledError:
                pass
    
    async def stress_test_mode(self):
        """Stress test mode with multiple rapid requests."""
        logger.info("=" * 50)
        logger.info("💪 STRESS TEST MODE")
        logger.info("=" * 50)
        
        self.running = True
        
        # Start listening for responses
        listen_task = asyncio.create_task(self.listen_for_responses())
        
        try:
            # Send multiple rapid text messages
            logger.info("🔥 Sending rapid text messages...")
            for i in range(5):
                await self.send_text(f"Rapid message {i+1}")
                await asyncio.sleep(0.5)
            
            await asyncio.sleep(2)
            
            # Send multiple audio signals
            logger.info("🔥 Sending rapid audio signals...")
            for i in range(3):
                await self.send_test_audio("test tone")
                await asyncio.sleep(1)
            
            await asyncio.sleep(3)
            
            logger.info("✅ Stress test completed!")
            
        finally:
            self.running = False
            listen_task.cancel()
            try:
                await listen_task
            except asyncio.CancelledError:
                pass


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Interactive Voice Agent Test Client")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=8765, help="Server port")
    parser.add_argument("--mode", choices=["conversation", "quick", "stress"], 
                       default="conversation", help="Test mode")
    
    args = parser.parse_args()
    
    client = InteractiveVoiceClient(args.host, args.port)
    
    try:
        # Connect to server
        if not await client.connect():
            logger.error("Failed to connect to voice agent")
            return 1
        
        # Run selected mode
        if args.mode == "conversation":
            await client.conversation_mode()
        elif args.mode == "quick":
            await client.quick_test_mode()
        elif args.mode == "stress":
            await client.stress_test_mode()
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1
    finally:
        await client.disconnect()


if __name__ == "__main__":
    exit_code = asyncio.run(main())