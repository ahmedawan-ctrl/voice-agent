# Voice Agent

A production-ready, real-time voice agent built with the Pipecat AI framework. This voice agent combines speech-to-text (STT), large language models (LLM), and text-to-speech (TTS) to create natural voice conversations.

## Features

- **Real-time Speech Processing**: Low-latency speech-to-text and text-to-speech
- **AI-Powered Conversations**: Integration with Ollama LLM for intelligent responses
- **WebSocket API**: Real-time bidirectional communication
- **Modular Architecture**: Clean, maintainable, and extensible codebase
- **Production Ready**: Comprehensive error handling, logging, and monitoring

## Components

- **STT**: Kyutai Speech-to-Text (1B parameter model)
- **TTS**: Kyutai Text-to-Speech with natural voice synthesis
- **LLM**: Ollama integration (supports Phi4-Mini and other models)
- **Transport**: WebSocket server for real-time communication
- **Pipeline**: Pipecat AI framework for audio/text processing

## Quick Start

### Prerequisites

1. **Python 3.8+** with pip
2. **Ollama** running locally
3. **CUDA** (optional, for GPU acceleration)

### Installation

1. Clone and setup:
```bash
cd voice-agent/voice
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. Install and start Ollama:
```bash
# Install Ollama (see https://ollama.ai)
ollama serve

# In another terminal, pull the model
ollama pull phi4:mini
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your settings
```

### Running the Voice Agent

#### Method 1: Using the CLI
```bash
# Start with default settings
python -m voice_agent.cli

# Custom host/port
python -m voice_agent.cli --host 0.0.0.0 --port 8080

# Debug mode
python -m voice_agent.cli --debug

# Check dependencies
python -m voice_agent.cli --check-deps
```

#### Method 2: Using the run script
```bash
python run.py
```

#### Method 3: Using the package
```python
from voice_agent import VoiceAgent
import asyncio

async def main():
    agent = VoiceAgent()
    await agent.run()

asyncio.run(main())
```

## API Usage

### WebSocket Connection

Connect to `ws://localhost:8765` and send/receive messages:

#### Text Input
```json
{
  "type": "text",
  "content": "Hello, how are you?"
}
```

#### Audio Input
Send raw audio bytes (16kHz, 16-bit, mono PCM)

#### Responses
- **Text responses**: JSON with `{"type": "text", "text": "response"}`
- **Audio responses**: Raw audio bytes (24kHz, 16-bit, mono PCM)

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
python tests/run_tests.py

# Run specific tests
python tests/test_text_only.py
python tests/test_comprehensive.py
```

## Project Structure

```
voice/
├── voice_agent/           # Main package
│   ├── __init__.py       # Package exports
│   ├── main.py           # VoiceAgent class
│   ├── cli.py            # Command-line interface
│   ├── pipeline.py       # Pipecat pipeline setup
│   ├── config/           # Configuration
│   │   ├── __init__.py
│   │   └── settings.py   # Settings management
│   ├── services/         # AI services
│   │   ├── __init__.py
│   │   ├── kyutai_stt.py # Speech-to-text
│   │   └── kyutai_tts.py # Text-to-speech
│   ├── transports/       # Communication
│   │   ├── __init__.py
│   │   └── websocket_transport.py
│   ├── processors/       # Audio/text processing
│   │   └── __init__.py
│   └── utils/            # Utilities
│       └── __init__.py
├── tests/                # Test suite
│   ├── __init__.py
│   ├── run_tests.py      # Test runner
│   ├── test_text_only.py # Text conversation tests
│   └── test_comprehensive.py # Full pipeline tests
├── .env                  # Environment configuration
├── requirements.txt      # Python dependencies
├── setup.py             # Package setup
├── run.py               # Simple entry point
└── README.md            # This file
```

## Configuration

Edit `.env` file or use environment variables:

```bash
# Ollama settings
OLLAMA_HOST=http://localhost:11434/v1
OLLAMA_MODEL=phi4:mini

# Kyutai settings
KYUTAI_STT_MODEL=kyutai/stt-1b-en_fr
KYUTAI_TTS_VOICE=moshika
KYUTAI_DEVICE=cuda  # or cpu

# Server settings
WEBSOCKET_HOST=0.0.0.0
WEBSOCKET_PORT=8765

# Audio settings
SAMPLE_RATE_STT=16000
SAMPLE_RATE_TTS=24000
```

## Development

### Adding New Features

1. **Services**: Add new AI services in `voice_agent/services/`
2. **Processors**: Add custom processors in `voice_agent/processors/`
3. **Transports**: Add new communication methods in `voice_agent/transports/`

### Testing

Always add tests for new features:

```bash
# Create test file
touch tests/test_new_feature.py

# Add to test runner
# Edit tests/run_tests.py
```

## Troubleshooting

### Common Issues

1. **Ollama not running**:
   ```bash
   ollama serve
   ```

2. **Model not found**:
   ```bash
   ollama pull phi4:mini
   ```

3. **CUDA issues**:
   ```bash
   # Check CUDA availability
   python -c "import torch; print(torch.cuda.is_available())"
   
   # Fallback to CPU
   export KYUTAI_DEVICE=cpu
   ```

4. **Port already in use**:
   ```bash
   python -m voice_agent.cli --port 8080
   ```

### Logs

Check logs for detailed error information:
- Console output shows real-time status
- Use `--debug` flag for verbose logging

## Performance

- **Latency**: ~200-500ms end-to-end (text input to audio output)
- **Memory**: ~2-4GB RAM (depending on models and device)
- **CPU**: Optimized for real-time processing
- **GPU**: CUDA acceleration supported for faster inference

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Support

For issues and questions:
- Check the troubleshooting section
- Review test files for usage examples
- Open an issue on GitHub