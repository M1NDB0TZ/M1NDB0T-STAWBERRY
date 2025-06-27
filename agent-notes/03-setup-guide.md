# Development Setup Guide

## Prerequisites

- Python 3.11+
- Node.js 18+
- pnpm (recommended) or npm
- Git

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

## Frontend Setup

### 1. Navigate to Frontend Directory
```bash
cd frontends/basic-frontend
```

### 2. Install Dependencies
```bash
pnpm install
```

### 3. Configure Environment Variables
```bash
cp .env.example .env.local
```

Edit `.env.local` with your LiveKit credentials:
```env
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
LIVEKIT_URL=wss://your-project.livekit.cloud
```

### 4. Start Development Server
```bash
pnpm dev
```

### 5. Open Application
Navigate to `http://localhost:3000` in your browser.

## Testing the Complete Setup

1. **Start the Python Agent**:
   ```bash
   cd backend/basic-mindbot
   python basic-mindbot.py start
   ```

2. **Start the Frontend** (in new terminal):
   ```bash
   cd frontends/basic-frontend
   pnpm dev
   ```

3. **Test Connection**:
   - Open `http://localhost:3000`
   - Click "Start a conversation"
   - Grant microphone permissions
   - Speak to test the voice interaction

## Common Issues & Solutions

### Agent Not Connecting
- Verify all environment variables are set correctly
- Check that the LiveKit server URL is accessible
- Ensure API keys have proper permissions

### Audio Issues
- Check browser microphone permissions
- Test with different browsers (Chrome recommended)
- Verify system audio input/output devices

### Network Issues
- Check firewall settings for WebRTC traffic
- Ensure UDP ports are not blocked
- Test on different networks if available

## Development Tips

- Use browser developer tools to monitor WebRTC connections
- Check Python agent logs for detailed error information
- Monitor API usage in provider dashboards
- Test with different audio input devices and quality settings