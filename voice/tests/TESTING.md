# 🧪 Voice Agent Testing

Simple guide for testing the voice agent.

## 🚀 Quick Start

1. **Start server:**
   ```bash
   cd ..
   python -m voice_agent.cli
   ```

2. **Run all tests:**
   ```bash
   python run_tests.py
   ```

## 📁 Test Files

- **`test_voice_agent.py`** - Comprehensive automated tests
- **`test_interactive.py`** - Interactive manual testing  
- **`run_tests.py`** - Runs all tests
- **`client.py`** - Test client with multiple modes

## 🧪 Testing Options

### Automated Testing
```bash
python run_tests.py                    # Run all tests
python test_voice_agent.py             # Comprehensive test suite
python test_interactive.py --mode quick # Quick automated test
```

### Manual Testing
```bash
python client.py --mode simple         # Simple connectivity test
python client.py --mode interactive    # Chat with AI
python client.py --mode debug          # Debug connection
```

### Interactive Testing
```bash
python test_interactive.py --mode conversation  # Manual chat mode
python test_interactive.py --mode stress       # Stress testing
```

## ✅ Expected Results

**All tests pass:**
```
🎉 ALL TESTS PASSED - VOICE AGENT IS PRODUCTION READY!
```

**Simple client test:**
```
✅ Voice agent is working!
   Responses: 3
   Text: ✅
   Audio: ✅
```

## 🔧 Troubleshooting

**Server not running:**
```bash
python -m voice_agent.cli  # Start server first
```

**Tests fail:**
- Check Ollama is running: `ollama serve`
- Verify model available: `ollama list`
- Check server logs for errors

## 📊 Test Coverage

- ✅ Server connectivity
- ✅ Text → Audio pipeline  
- ✅ Audio → Audio pipeline
- ✅ Moshika voice integration
- ✅ Multiple clients
- ✅ Always-on behavior

That's it! Simple and effective testing. 🚀