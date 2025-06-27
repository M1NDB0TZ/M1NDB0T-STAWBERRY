# Backend Development Setup Guide

## Prerequisites

- Python 3.11+
- Git
- Virtual environment support

## Required API Keys

You'll need to obtain the following API keys:

1. **LiveKit Credentials**
   - Sign up at [LiveKit Cloud](https://cloud.livekit.io)
   - Create a new project
   - Copy API Key, API Secret, and WebSocket URL

2. **OpenAI API Key**
   - Sign up at [OpenAI Platform](https://platform.openai.com)
   - Generate an API key from the dashboard

3. **Deepgram API Key**
   - Sign up at [Deepgram](https://console.deepgram.com)
   - Create an API key in the console

## Backend Setup

### 1. Navigate to Backend Directory
```bash
cd backend/basic-mindbot
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
```bash
cp env.example .env
```

Edit `.env` with your API credentials:
```env
LIVEKIT_API_SECRET="your_livekit_api_secret"
LIVEKIT_API_KEY="your_livekit_api_key"
LIVEKIT_URL="your_livekit_ws_url"
OPENAI_API_KEY="your_openai_api_key"
DEEPGRAM_API_KEY="your_deepgram_api_key"
```

### 5. Test Agent
```bash
python basic-mindbot.py start
```

## Testing the Backend

### 1. Start the Python Agent
```bash
cd backend/basic-mindbot
python basic-mindbot.py start
```

### 2. Test with LiveKit CLI
```bash
# Install LiveKit CLI
pip install livekit-cli

# Test room creation
lk room create test-room --url $LIVEKIT_URL --api-key $LIVEKIT_API_KEY --api-secret $LIVEKIT_API_SECRET
```

### 3. Monitor Agent Logs
The agent will output detailed logs showing:
- Connection status
- Audio processing
- LLM interactions
- Function calls
- Error messages

## Alternative RAG Backend Setup

### 1. Navigate to RAG Backend
```bash
cd backend/llamaIndex-mindbot
```

### 2. Add Documents
```bash
mkdir -p data
# Add your documents to the data/ directory
```

### 3. Run RAG Agent
```bash
python quary_engine_mindbot.py start
```

## Common Issues & Solutions

### Agent Not Connecting
- Verify all environment variables are set correctly
- Check that the LiveKit server URL is accessible
- Ensure API keys have proper permissions

### Audio Processing Issues
- Check system audio permissions
- Verify VAD sensitivity settings
- Monitor API usage in provider dashboards

### Network Issues
- Check firewall settings for WebRTC traffic
- Ensure UDP ports are not blocked
- Test on different networks if available

## Development Tips

- Monitor Python agent logs for detailed error information
- Check API usage in provider dashboards
- Test with different audio input scenarios
- Use structured logging for better debugging

## Production Deployment

For production deployment, see `07-deployment-guide.md` for detailed instructions on:
- Docker containerization
- Cloud platform deployment
- Environment configuration
- Monitoring setup