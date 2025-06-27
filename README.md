# M1NDB0T-STAWBERRY Backend

A sophisticated conversational AI voice assistant backend built using LiveKit Agents framework. MindBot is designed to provide seamless voice-to-voice interaction with advanced AI capabilities.

## 🎯 Project Overview

MindBot is a self-aware AI personality that helps humans through natural voice conversations. The backend handles real-time audio processing, speech recognition, language model interactions, and speech synthesis.

### Key Features

- **Real-time Voice Processing**: Low-latency voice-to-voice interactions
- **Advanced AI Integration**: OpenAI LLM and TTS, Deepgram STT
- **Function Calling**: Extensible tool system for external actions
- **RAG Capabilities**: LlamaIndex integration for knowledge base queries
- **Metrics & Monitoring**: Comprehensive usage tracking and performance monitoring
- **Production Ready**: Robust error handling and scalable architecture

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client Apps   │◄──►│   LiveKit        │◄──►│   Backend       │
│   (Any SDK)     │    │   Server         │    │   (Python)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

The backend consists of:
- **AI Agent**: Core conversation handling and personality
- **Speech Pipeline**: STT (Deepgram) → LLM (OpenAI) → TTS (OpenAI)
- **Function Tools**: Extensible system for external integrations
- **Metrics Collection**: Performance and usage analytics

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- LiveKit Cloud account or self-hosted LiveKit server
- OpenAI API key
- Deepgram API key

### Setup

1. **Clone and navigate to backend**:
   ```bash
   cd backend/basic-mindbot
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   ```bash
   cp env.example .env
   # Edit .env with your API credentials
   ```

5. **Start the agent**:
   ```bash
   python basic-mindbot.py start
   ```

## 🔧 Available Backends

### Basic MindBot (`backend/basic-mindbot/`)
Core voice AI agent with:
- OpenAI GPT-4.1-mini for conversations
- Deepgram Nova-3 for speech recognition  
- OpenAI Fable voice for speech synthesis
- Function calling (weather lookup example)
- Comprehensive metrics collection

### RAG MindBot (`backend/llamaIndex-mindbot/`)
Advanced agent with knowledge base capabilities:
- LlamaIndex integration for document queries
- Vector search capabilities
- Retrieval-augmented generation
- Custom knowledge base from your documents

## 📚 Documentation

Comprehensive documentation is available in the `agent-notes/` directory:

- **[Setup Guide](agent-notes/03-setup-guide.md)**: Detailed installation and configuration
- **[Architecture Overview](agent-notes/02-architecture-overview.md)**: System design and components
- **[API Configuration](agent-notes/04-api-configuration.md)**: API keys and provider setup
- **[Troubleshooting](agent-notes/05-troubleshooting.md)**: Common issues and solutions
- **[Deployment Guide](agent-notes/07-deployment-guide.md)**: Production deployment strategies
- **[Feature Roadmap](agent-notes/06-feature-roadmap.md)**: Development plans and priorities

## 🛠️ Development

### Environment Variables

```env
LIVEKIT_API_SECRET="your_livekit_api_secret"
LIVEKIT_API_KEY="your_livekit_api_key" 
LIVEKIT_URL="wss://your-project.livekit.cloud"
OPENAI_API_KEY="your_openai_api_key"
DEEPGRAM_API_KEY="your_deepgram_api_key"
```

### Running with Debug Logging

```bash
python basic-mindbot.py start --log-level DEBUG
```

### Testing Connectivity

```bash
# Test LiveKit connection
lk room list --url $LIVEKIT_URL --api-key $LIVEKIT_API_KEY --api-secret $LIVEKIT_API_SECRET

# Test room creation
lk room create test-room --url $LIVEKIT_URL --api-key $LIVEKIT_API_KEY --api-secret $LIVEKIT_API_SECRET
```

## 🚀 Deployment

### Railway (Recommended)
```bash
npm install -g @railway/cli
railway login
railway init
railway up
```

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "basic-mindbot.py", "start"]
```

### Environment-Specific Configs
- **Development**: Local LiveKit server, debug logging
- **Staging**: LiveKit Cloud, info logging, rate limiting
- **Production**: LiveKit Cloud, warn logging, security headers

## 📊 Monitoring

The backend includes comprehensive monitoring:
- **Usage Metrics**: Session duration, API calls, response times
- **Performance Metrics**: CPU, memory, latency tracking
- **Error Tracking**: Structured logging and error reporting
- **Health Checks**: API endpoints for service monitoring

## 🤝 Contributing

1. Follow the setup guide to configure your development environment
2. Check the troubleshooting guide for common issues
3. Update documentation when adding new features
4. Include tests for new functionality

## 📋 Current Status

- **Phase**: 2 (Enhanced Functionality)
- **Status**: Active Development
- **Next Milestone**: Enhanced agent personality and expanded function calling

## 🆘 Support

- Check the [troubleshooting guide](agent-notes/05-troubleshooting.md)
- Review [LiveKit documentation](https://docs.livekit.io)
- Join the [LiveKit Discord](https://discord.gg/livekit)

## 📄 License

This project is part of the M1NDB0T-STAWBERRY suite focused on building production-ready voice AI backends.