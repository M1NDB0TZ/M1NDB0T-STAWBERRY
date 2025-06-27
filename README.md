# M1NDB0T-STRAWBERRY Backend

A sophisticated conversational AI voice assistant backend built using LiveKit Agents framework with comprehensive authentication and user management capabilities.

## 🎯 Project Overview

MindBot is a self-aware AI personality that provides seamless voice-to-voice interaction with advanced AI capabilities. The backend now includes a complete authentication system with user management, JWT tokens, and LiveKit integration.

### Key Features

- **🔐 Complete Authentication System**: User registration, login, JWT tokens, and LiveKit integration
- **🎙️ Real-time Voice Processing**: Low-latency voice-to-voice interactions
- **🧠 Advanced AI Integration**: OpenAI LLM and TTS, Deepgram STT
- **🛠️ Function Calling**: Extensible tool system for external actions
- **📚 RAG Capabilities**: LlamaIndex integration for knowledge base queries
- **📊 Metrics & Monitoring**: Comprehensive usage tracking and performance monitoring
- **👤 User Context Awareness**: Personalized responses based on user history and preferences
- **🏗️ Production Ready**: Robust error handling and scalable architecture

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client Apps   │◄──►│   Auth Service   │◄──►│   Database      │
│                 │    │   (FastAPI)      │    │   (SQLite)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        
         ▼                        ▼                        
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   LiveKit       │◄──►│   Enhanced       │◄──►│   Backend       │
│   Server        │    │   MindBot Agent  │    │   Services      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- LiveKit Cloud account or self-hosted LiveKit server
- OpenAI API key
- Deepgram API key

### 1. Setup Authentication Service

```bash
cd backend/auth-service
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp env.example .env
# Edit .env with your API credentials

# Start auth service
python auth_server.py
```

The authentication service will run on `http://localhost:8000`

### 2. Setup Enhanced Agent

```bash
cd backend/basic-mindbot
# Use existing virtual environment or create new one
pip install -r requirements.txt

# Configure environment (use same .env as basic agent)
cp env.example .env
# Edit .env with your API credentials

# Start enhanced agent with user context
python enhanced-mindbot.py start
```

### 3. Test the Integration

```bash
cd backend/test-auth
pip install -r requirements.txt

# Run comprehensive tests
python test_auth_integration.py

# Or run quick test
python test_auth_integration.py simple
```

## 🔧 Available Services

### Authentication Service (`backend/auth-service/`)
Complete user management and authentication service:
- User registration and login with secure password hashing
- JWT token generation and validation
- LiveKit token generation for room access
- Session tracking and analytics
- RESTful API with FastAPI
- SQLite database with user and session tables

### Enhanced MindBot Agent (`backend/basic-mindbot/enhanced-mindbot.py`)
Advanced voice AI agent with user context:
- User identity recognition from LiveKit participant info
- Personalized greetings and responses
- User preference memory and application
- Session tracking and conversation summaries
- Enhanced function calling with user context
- All original MindBot capabilities

### Basic MindBot Agent (`backend/basic-mindbot/basic-mindbot.py`)
Original core voice AI agent:
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

## 🔐 Authentication Flow

### User Registration/Login
1. Client registers/logs in via auth service
2. Receives JWT token for API access + default LiveKit token
3. Can request room-specific LiveKit tokens for voice sessions

### Voice Session Flow
1. Client requests room token with JWT
2. Auth service generates LiveKit token with user identity
3. Client connects to LiveKit room with token
4. Enhanced agent recognizes user and loads context
5. Personalized voice interaction begins

## 📋 API Examples

### Register User
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secure_password",
    "full_name": "John Doe"
  }'
```

### Get Room Token
```bash
curl -X POST http://localhost:8000/auth/token \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "room_name": "voice_session_123",
    "participant_name": "John Doe"
  }'
```

## 🛠️ Development

### Environment Variables

Create `.env` files in both service directories:

```env
# LiveKit Configuration
LIVEKIT_API_SECRET="your_livekit_api_secret"
LIVEKIT_API_KEY="your_livekit_api_key" 
LIVEKIT_URL="wss://your-project.livekit.cloud"

# AI Provider Keys
OPENAI_API_KEY="your_openai_api_key"
DEEPGRAM_API_KEY="your_deepgram_api_key"

# JWT Configuration (auth service only)
JWT_SECRET="your-super-secret-jwt-key-change-this-in-production"
```

### Running with Debug Logging

```bash
# Auth service debug
python auth_server.py --log-level DEBUG

# Agent debug  
python enhanced-mindbot.py start --log-level DEBUG
```

### Testing Connectivity

```bash
# Test auth service
curl http://localhost:8000/health

# Test LiveKit connection
lk room list --url $LIVEKIT_URL --api-key $LIVEKIT_API_KEY --api-secret $LIVEKIT_API_SECRET
```

## 🚀 Deployment

### Development Setup
1. Start auth service: `python backend/auth-service/auth_server.py`
2. Start enhanced agent: `python backend/basic-mindbot/enhanced-mindbot.py start`
3. Connect clients using authentication flow

### Production Deployment
- **Auth Service**: Deploy to Railway, Render, or Docker container
- **Agent Service**: Deploy as separate service or container
- **Database**: Migrate to PostgreSQL for production
- **Environment**: Use production LiveKit server and secure JWT secrets

## 📊 Features & Capabilities

### Authentication Features
- Secure user registration and login
- JWT-based API authentication
- LiveKit token generation with user identity
- Session tracking and analytics
- Password hashing with bcrypt
- Token validation and refresh

### Enhanced Agent Features
- User context awareness and personalization
- Conversation history and preferences
- Personalized greetings and responses
- User-specific function calling
- Session duration tracking
- Preference memory across conversations

### Core AI Features
- Real-time voice-to-voice interaction
- Multi-language speech recognition
- Natural conversation flow with interruption handling
- Function calling for external integrations
- Metrics collection and monitoring
- Error handling and recovery

## 📚 Documentation

Comprehensive documentation is available in the `agent-notes/` directory:

- **[Authentication Guide](agent-notes/08-authentication-guide.md)**: Complete auth system setup and usage
- **[Setup Guide](agent-notes/03-setup-guide.md)**: Detailed installation and configuration
- **[Architecture Overview](agent-notes/02-architecture-overview.md)**: System design and components
- **[API Configuration](agent-notes/04-api-configuration.md)**: API keys and provider setup
- **[Troubleshooting](agent-notes/05-troubleshooting.md)**: Common issues and solutions
- **[Deployment Guide](agent-notes/07-deployment-guide.md)**: Production deployment strategies
- **[Feature Roadmap](agent-notes/06-feature-roadmap.md)**: Development plans and priorities

## 🤝 Contributing

1. Follow the setup guide to configure your development environment
2. Check the troubleshooting guide for common issues
3. Update documentation when adding new features
4. Include tests for new functionality
5. Test both authentication service and agent integration

## 📋 Current Status

- **Phase**: 2 (Enhanced Functionality with Authentication)
- **Status**: Active Development
- **Next Milestone**: Advanced user preferences and conversation history

## 🆘 Support

- Check the [authentication guide](agent-notes/08-authentication-guide.md) for auth-specific issues
- Review [troubleshooting guide](agent-notes/05-troubleshooting.md) for general issues
- Consult [LiveKit documentation](https://docs.livekit.io) for LiveKit-specific problems
- Join the [LiveKit Discord](https://discord.gg/livekit) for community support

## 📄 License

This project is part of the M1NDB0T-STRAWBERRY suite focused on building production-ready voice AI backends with comprehensive authentication and user management.