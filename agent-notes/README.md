# MindBot Backend Documentation

This directory contains comprehensive documentation and notes for the M1NDB0T-STAWBERRY backend project.

## 📋 Documentation Index

### Core Documentation
- **[01-project-analysis.md](./01-project-analysis.md)** - Complete backend project analysis and requirements
- **[02-architecture-overview.md](./02-architecture-overview.md)** - Backend system architecture and component breakdown
- **[03-setup-guide.md](./03-setup-guide.md)** - Step-by-step backend development environment setup

### Configuration & APIs
- **[04-api-configuration.md](./04-api-configuration.md)** - API keys, rate limits, and provider configuration
- **[05-troubleshooting.md](./05-troubleshooting.md)** - Common backend issues and solutions

### Planning & Deployment
- **[06-feature-roadmap.md](./06-feature-roadmap.md)** - Backend development roadmap and feature prioritization
- **[07-deployment-guide.md](./07-deployment-guide.md)** - Production backend deployment strategies

## 🚀 Quick Start

1. **Read the Project Analysis** to understand backend goals and scope
2. **Follow the Setup Guide** to configure your development environment
3. **Reference API Configuration** for credential setup
4. **Use Troubleshooting Guide** when issues arise

## 🏗️ Backend Architecture

The MindBot backend is built with:
- **Python 3.11+** with LiveKit Agents framework
- **LiveKit** for real-time audio streaming
- **OpenAI** for LLM and TTS capabilities
- **Deepgram** for speech-to-text processing
- **Silero VAD** for voice activity detection

## 📝 Contributing to Documentation

When adding new backend features or making changes:

1. Update relevant documentation files
2. Add new troubleshooting entries for common issues
3. Update the feature roadmap progress
4. Document any new API configurations or dependencies

## 🔗 External Resources

- [LiveKit Documentation](https://docs.livekit.io/)
- [LiveKit Agents Framework](https://docs.livekit.io/agents)
- [OpenAI API Reference](https://platform.openai.com/docs/)
- [Deepgram API Docs](https://developers.deepgram.com/)

## 📊 Project Status

- **Phase**: 2 (Enhanced Functionality)
- **Status**: Backend Development
- **Last Updated**: Current
- **Next Milestone**: Enhanced agent personality and expanded function calling

## 🤝 Support

For backend-specific questions or issues:
1. Check the troubleshooting guide first
2. Search existing documentation
3. Consult external resources
4. Create detailed issue reports with logs and steps to reproduce

## 🚀 Available Agents

### Basic MindBot (`backend/basic-mindbot/`)
- Core voice AI agent with OpenAI integration
- Function calling capabilities (weather example)
- Real-time speech processing
- Metrics collection and monitoring

### RAG MindBot (`backend/llamaIndex-mindbot/`)
- Advanced agent with LlamaIndex integration
- Document knowledge base querying
- Vector search capabilities
- Retrieval-augmented generation

## 🛠️ Development Commands

```bash
# Start basic agent
cd backend/basic-mindbot
python basic-mindbot.py start

# Start RAG agent
cd backend/llamaIndex-mindbot
python quary_engine_mindbot.py start

# Install dependencies
pip install -r requirements.txt

# Run with debug logging
python basic-mindbot.py start --log-level DEBUG
```

---

*This documentation is maintained alongside the backend project and should be updated with any significant changes or additions.*