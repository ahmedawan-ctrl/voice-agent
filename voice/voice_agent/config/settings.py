"""
Configuration settings for the voice agent
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class OllamaSettings:
    """Ollama LLM settings."""
    host: str = ""
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 500
    
    def __post_init__(self):
        self.host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "phi4-mini:latest")
        self.temperature = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("OLLAMA_MAX_TOKENS", "500"))


@dataclass
class KyutaiSettings:
    """Kyutai STT/TTS settings."""
    stt_model: str = ""
    tts_voice: str = ""
    tts_model_type: str = ""
    device: str = ""
    cache_dir: str = ""
    
    def __post_init__(self):
        self.stt_model = os.getenv("KYUTAI_STT_MODEL", "kyutai/stt-1b-en_fr")
        self.tts_voice = os.getenv("KYUTAI_TTS_VOICE", "moshika")
        self.tts_model_type = os.getenv("KYUTAI_TTS_MODEL_TYPE", "pytorch-bf16")
        self.device = os.getenv("KYUTAI_DEVICE", "cpu")
        
        # Ensure cache directory is absolute path in the voice directory
        cache_dir_env = os.getenv("HF_CACHE_DIR", ".hf_cache")
        if not os.path.isabs(cache_dir_env):
            # Make it relative to the voice directory (parent of voice_agent)
            voice_dir = Path(__file__).parent.parent.parent
            self.cache_dir = str((voice_dir / cache_dir_env).absolute())
        else:
            self.cache_dir = cache_dir_env


@dataclass
class AudioSettings:
    """Audio processing settings."""
    sample_rate_stt: int = 16000
    sample_rate_tts: int = 24000
    chunk_size_ms: int = 100
    vad_threshold: float = 0.5
    buffer_size_ms: int = 200
    
    def __post_init__(self):
        self.sample_rate_stt = int(os.getenv("SAMPLE_RATE_STT", "16000"))
        self.sample_rate_tts = int(os.getenv("SAMPLE_RATE_TTS", "24000"))
        self.chunk_size_ms = int(os.getenv("CHUNK_SIZE_MS", "100"))
        self.vad_threshold = float(os.getenv("VAD_THRESHOLD", "0.5"))
        self.buffer_size_ms = int(os.getenv("BUFFER_SIZE_MS", "200"))


@dataclass
class ServerSettings:
    """Server configuration."""
    websocket_host: str = ""
    websocket_port: int = 8765
    webrtc_host: str = ""
    webrtc_port: int = 8766
    max_connections: int = 10
    
    def __post_init__(self):
        self.websocket_host = os.getenv("WEBSOCKET_HOST", "0.0.0.0")
        self.websocket_port = int(os.getenv("WEBSOCKET_PORT", "8765"))
        self.webrtc_host = os.getenv("WEBRTC_HOST", "0.0.0.0")
        self.webrtc_port = int(os.getenv("WEBRTC_PORT", "8766"))
        self.max_connections = int(os.getenv("MAX_CONNECTIONS", "10"))


@dataclass
class Settings:
    """Main settings container."""
    ollama: OllamaSettings = field(default_factory=OllamaSettings)
    kyutai: KyutaiSettings = field(default_factory=KyutaiSettings)
    audio: AudioSettings = field(default_factory=AudioSettings)
    server: ServerSettings = field(default_factory=ServerSettings)
    enable_metrics: bool = True
    
    def __post_init__(self):
        self.enable_metrics = os.getenv("ENABLE_METRICS", "true").lower() == "true"
    
    def validate(self):
        """Validate settings."""
        # Create cache directory if it doesn't exist
        Path(self.kyutai.cache_dir).mkdir(parents=True, exist_ok=True)
        
        # Check device availability
        if self.kyutai.device == "cuda":
            import torch
            if not torch.cuda.is_available():
                self.kyutai.device = "cpu"
                print("CUDA not available, falling back to CPU")


# Global settings instance
settings = Settings()
