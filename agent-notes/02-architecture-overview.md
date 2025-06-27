# Architecture Overview

## System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│                 │    │                  │    │                 │
│   Frontend      │◄──►│   LiveKit        │◄──►│   Backend       │
│   (Next.js)     │    │   Server         │    │   (Python)      │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│                 │    │                  │    │                 │
│ - React UI      │    │ - WebRTC SFU     │    │ - AI Agent      │
│ - Voice I/O     │    │ - Room Mgmt      │    │ - OpenAI LLM    │
│ - Transcription │    │ - Media Routing  │    │ - Deepgram STT  │
│ - Visualizer    │    │ - Authentication │    │ - Function Tools│
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Component Breakdown

### Frontend Components
- **App Router (Next.js 14)**: Main application routing and page management
- **Voice Assistant UI**: Real-time voice interaction interface
- **Transcription View**: Live conversation display
- **Audio Visualizer**: Visual feedback for audio activity
- **Connection Manager**: LiveKit room connection handling

### Backend Components
- **Agent Session**: Main orchestrator for voice AI interactions
- **LLM Pipeline**: OpenAI integration for natural language processing
- **STT Pipeline**: Deepgram integration for speech recognition
- **TTS Pipeline**: OpenAI integration for speech synthesis
- **VAD System**: Silero voice activity detection
- **Function Tools**: Extensible tool system for external actions

### LiveKit Infrastructure
- **WebRTC SFU**: Selective Forwarding Unit for real-time media
- **Room Management**: Session and participant handling
- **Authentication**: JWT token-based access control
- **Media Routing**: Audio/video stream distribution

## Data Flow

1. **User Speech** → Frontend captures audio
2. **Audio Stream** → Sent to LiveKit server
3. **Media Routing** → LiveKit forwards to Python agent
4. **Speech-to-Text** → Deepgram processes audio
5. **LLM Processing** → OpenAI generates response
6. **Function Calling** → Tools executed if needed
7. **Text-to-Speech** → OpenAI synthesizes audio
8. **Audio Response** → Sent back through LiveKit
9. **Frontend Playback** → User hears agent response

## Security Architecture

- **JWT Authentication**: Token-based access control
- **API Key Management**: Secure credential handling
- **HTTPS/WSS**: Encrypted connections
- **CORS Configuration**: Cross-origin request protection
- **Environment Variables**: Sensitive data isolation