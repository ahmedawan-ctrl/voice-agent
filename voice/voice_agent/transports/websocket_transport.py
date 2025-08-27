"""
WebSocket Transport for Voice Agent
Handles real-time bidirectional communication
"""

import asyncio
import json
import websockets
from typing import Optional, Callable, Dict, Any
from loguru import logger

from pipecat.transports.base_transport import BaseTransport
from pipecat.frames.frames import AudioRawFrame, TextFrame, StartFrame, EndFrame
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection


class VoiceAgentWebSocketTransport:
    """
    WebSocket server for handling voice agent connections.
    """
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        sample_rate: int = 16000,
        enable_vad: bool = True
    ):
        """
        Initialize WebSocket transport.
        
        Args:
            host: Host to bind to
            port: Port to listen on
            sample_rate: Audio sample rate
            enable_vad: Enable voice activity detection
        """
        self.host = host
        self.port = port
        self.sample_rate = sample_rate
        self.enable_vad = enable_vad
        
        # WebSocket server
        self.server = None
        self.clients = {}
        
        # Callbacks
        self._audio_callback = None
        self._text_callback = None
        self._connect_callback = None
        self._disconnect_callback = None
        
    def set_audio_callback(self, callback: Callable):
        """Set callback for audio data."""
        self._audio_callback = callback
        
    def set_text_callback(self, callback: Callable):
        """Set callback for text data."""
        self._text_callback = callback
        
    def set_connect_callback(self, callback: Callable):
        """Set callback for client connections."""
        self._connect_callback = callback
        
    def set_disconnect_callback(self, callback: Callable):
        """Set callback for client disconnections."""
        self._disconnect_callback = callback
        
    async def handle_client(self, websocket):
        """Handle a client connection."""
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        self.clients[client_id] = websocket
        
        logger.info(f"🔗 NEW CLIENT CONNECTED: {client_id}")
        print(f"🔗 NEW CLIENT CONNECTED: {client_id}")  # Force print to console
        
        # Notify connection
        if self._connect_callback:
            logger.info(f"🔗 Calling connect callback for {client_id}")
            await self._connect_callback(client_id)
            
        try:
            async for message in websocket:
                await self.process_message(client_id, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
        finally:
            if client_id in self.clients:
                del self.clients[client_id]
            if self._disconnect_callback:
                await self._disconnect_callback(client_id)
                
    async def process_message(self, client_id: str, message):
        """Process incoming message from client."""
        try:
            # Try to parse as JSON first
            try:
                if isinstance(message, bytes):
                    message_str = message.decode('utf-8')
                else:
                    message_str = message
                    
                data = json.loads(message_str)
                msg_type = data.get("type")
                
                if msg_type == "text":
                    # Text input
                    text_content = data.get("data", data.get("text", data.get("content", "")))
                    logger.info(f"📝 RECEIVED TEXT from {client_id}: {text_content}")
                    print(f"📝 RECEIVED TEXT from {client_id}: {text_content}")  # Force print to console
                    if self._text_callback:
                        logger.info(f"📝 Calling text callback with: {text_content}")
                        await self._text_callback(text_content)
                elif msg_type == "audio":
                    # Audio input
                    audio_hex = data.get("data", "")
                    if audio_hex:
                        try:
                            audio_bytes = bytes.fromhex(audio_hex)
                            sample_rate = data.get("sample_rate", self.sample_rate)
                            logger.info(f"Received audio from {client_id}: {len(audio_bytes)} bytes")
                            if self._audio_callback:
                                await self._audio_callback(audio_bytes, sample_rate)
                        except ValueError as e:
                            logger.error(f"Invalid audio hex data: {e}")
                elif msg_type == "audio_config":
                    # Audio configuration
                    logger.info(f"Audio config from {client_id}: {data}")
                else:
                    logger.warning(f"Unknown message type: {msg_type}")
                    
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Assume it's raw audio data
                if self._audio_callback:
                    await self._audio_callback(message, self.sample_rate)
                    
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            
    async def send_audio(self, audio_data: bytes, sample_rate: int = None):
        """Send audio to all connected clients."""
        if not self.clients:
            return
            
        # Wrap audio data in JSON message
        message = json.dumps({
            "type": "audio",
            "data": audio_data.hex(),  # Convert bytes to hex string
            "sample_rate": sample_rate or self.sample_rate,
            "channels": 1,
            "format": "raw"
        })
        
        # Create a copy of clients to avoid dictionary changed size during iteration
        clients_copy = dict(self.clients)
        disconnected = []
        
        # Send to all clients
        for client_id, websocket in clients_copy.items():
            try:
                await websocket.send(message)
            except:
                disconnected.append(client_id)
                
        # Remove disconnected clients
        for client_id in disconnected:
            if client_id in self.clients:
                del self.clients[client_id]
            
    async def send_text(self, text: str):
        """Send text to all connected clients."""
        message = json.dumps({"type": "text", "data": text})
        await self.send_message(message)
        
    async def send_status(self, status: str, details: Dict[str, Any] = None):
        """Send status update to all clients."""
        message = json.dumps({
            "type": "status",
            "status": status,
            "details": details or {}
        })
        await self.send_message(message)
        
    async def send_message(self, message: str):
        """Send message to all connected clients."""
        if not self.clients:
            return
            
        # Create a copy of clients to avoid dictionary changed size during iteration
        clients_copy = dict(self.clients)
        disconnected = []
        
        for client_id, websocket in clients_copy.items():
            try:
                await websocket.send(message)
            except:
                disconnected.append(client_id)
                
        # Remove disconnected clients
        for client_id in disconnected:
            if client_id in self.clients:
                del self.clients[client_id]
            
    async def start(self):
        """Start the WebSocket server."""
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        self.server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port,
            max_size=10 * 1024 * 1024  # 10MB max message size
        )
        
    async def stop(self):
        """Stop the WebSocket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("WebSocket server stopped")
            
    def create_transport(self) -> 'MockPipecatTransport':
        """
        Create a Pipecat transport wrapper.
        This allows integration with Pipecat pipeline.
        """
        return MockPipecatTransport(self)


class MockPipecatTransport(FrameProcessor):
    """Mock transport for testing without full Pipecat integration."""
    
    def __init__(self, ws_transport, name: str = "MockPipecatTransport"):
        super().__init__(name=name)
        self.ws_transport = ws_transport
        
    def input(self):
        """Return input processor."""
        return MockInputProcessor(self)
        
    def output(self):
        """Return output processor."""
        return MockOutputProcessor(self)
        
    async def process_frame(self, frame, direction):
        """Process frames (mock implementation)."""
        # First, let the parent class handle the frame (this sets internal __started flag)
        await super().process_frame(frame, direction)
        
        # Then handle our custom logic
        if isinstance(frame, (StartFrame, EndFrame)):
            # Pass lifecycle frames to all connected processors
            await self.push_frame(frame, direction)
        else:
            # Handle other frames normally
            await self.push_frame(frame, direction)


class MockInputProcessor(FrameProcessor):
    """Mock input processor for the transport."""
    
    def __init__(self, transport, name: str = "MockInputProcessor"):
        super().__init__(name=name)
        self.transport = transport
        self._started = False
        
    async def process_frame(self, frame, direction):
        """Process frames (mock implementation)."""
        # First, let the parent class handle the frame (this sets internal __started flag)
        await super().process_frame(frame, direction)
        
        # Then handle our custom logic
        if isinstance(frame, StartFrame):
            # Mark ourselves as started and pass along the frame
            self._started = True
            await self.push_frame(frame, direction)
        elif isinstance(frame, EndFrame):
            # Pass along end frames
            self._started = False
            await self.push_frame(frame, direction)
        else:
            # Only process data frames if we have been started
            if self._started:
                await self.push_frame(frame, direction)
            else:
                # Ignore frames received before StartFrame
                pass


class MockOutputProcessor(FrameProcessor):
    """Mock output processor for the transport."""
    
    def __init__(self, transport, name: str = "MockOutputProcessor"):
        super().__init__(name=name)
        self.transport = transport
        
    async def process_frame(self, frame, direction):
        """Process frames (mock implementation)."""
        # First, let the parent class handle the frame (this sets internal __started flag)
        await super().process_frame(frame, direction)
        
        # Debug: Log all frames being processed
        logger.info(f"🔍 MockOutputProcessor processing frame: {type(frame).__name__}")
        print(f"🔍 MockOutputProcessor processing frame: {type(frame).__name__}")
        
        # Then handle our custom logic
        if isinstance(frame, StartFrame):
            # Pass along the frame
            await self.push_frame(frame, direction)
        elif isinstance(frame, EndFrame):
            # Pass along end frames
            await self.push_frame(frame, direction)
        elif isinstance(frame, AudioRawFrame):
            # Handle output audio frames - send to clients
            logger.info(f"MockOutputProcessor: Sending audio frame: {len(frame.audio)} bytes")
            await self.transport.ws_transport.send_audio(frame.audio)
            await self.push_frame(frame, direction)
        elif isinstance(frame, TextFrame):
            # Handle output text frames - send to clients
            logger.info(f"🎯 MockOutputProcessor: Sending text frame: {frame.text}")
            print(f"🎯 MockOutputProcessor: Sending text frame: {frame.text}")
            await self.transport.ws_transport.send_text(frame.text)
            await self.push_frame(frame, direction)
        else:
            # Handle other frames
            logger.debug(f"MockOutputProcessor: Processing frame: {type(frame).__name__}")
            await self.push_frame(frame, direction)


class WebSocketClient:
    """
    WebSocket client for connecting to voice agent server.
    """
    
    def __init__(self, url: str):
        """
        Initialize WebSocket client.
        
        Args:
            url: WebSocket server URL (e.g., ws://localhost:8765)
        """
        self.url = url
        self.websocket = None
        self.connected = False
        
        # Callbacks
        self._audio_callback = None
        self._text_callback = None
        self._status_callback = None
        
    def set_audio_callback(self, callback: Callable):
        """Set callback for received audio data."""
        self._audio_callback = callback
        
    def set_text_callback(self, callback: Callable):
        """Set callback for received text data."""
        self._text_callback = callback
        
    def set_status_callback(self, callback: Callable):
        """Set callback for status updates."""
        self._status_callback = callback
        
    async def connect(self):
        """Connect to the WebSocket server."""
        try:
            self.websocket = await websockets.connect(self.url)
            self.connected = True
            logger.info(f"Connected to {self.url}")
        except Exception as e:
            logger.error(f"Failed to connect to {self.url}: {e}")
            raise
            
    async def disconnect(self):
        """Disconnect from the WebSocket server."""
        if self.websocket and not self.websocket.closed:
            await self.websocket.close()
            self.connected = False
            logger.info("Disconnected from server")
            
    async def send_audio(self, audio_data: bytes, sample_rate: int = None):
        """Send audio data to server."""
        if self.websocket and self.connected:
            await self.websocket.send(audio_data)
            
    async def send_text(self, text: str):
        """Send text message to server."""
        if self.websocket and self.connected:
            message = json.dumps({"type": "text", "text": text})
            await self.websocket.send(message)
            
    async def send_audio_config(self, config: Dict[str, Any]):
        """Send audio configuration to server."""
        if self.websocket and self.connected:
            message = json.dumps({"type": "audio_config", **config})
            await self.websocket.send(message)
            
    async def receive_messages(self):
        """Receive and process messages from server."""
        if not self.websocket or not self.connected:
            return
            
        try:
            async for message in self.websocket:
                await self.process_received_message(message)
        except websockets.exceptions.ConnectionClosed:
            logger.info("Server connection closed")
            self.connected = False
        except Exception as e:
            logger.error(f"Error receiving messages: {e}")
            
    async def process_received_message(self, message):
        """Process received message from server."""
        try:
            # Try to parse as JSON first
            try:
                data = json.loads(message)
                msg_type = data.get("type")
                
                if msg_type == "text" and self._text_callback:
                    await self._text_callback(data.get("text", ""))
                elif msg_type == "status" and self._status_callback:
                    await self._status_callback(data.get("status"), data.get("data"))
                else:
                    logger.debug(f"Received message: {data}")
                    
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Assume it's raw audio data
                if self._audio_callback:
                    await self._audio_callback(message)
                    
        except Exception as e:
            logger.error(f"Error processing received message: {e}")
            
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self.connected and self.websocket and not self.websocket.closed
