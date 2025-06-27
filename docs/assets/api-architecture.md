# MindBot API Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client Apps   │◄──►│   Auth Service   │◄──►│   User DB       │
│                 │    │   (Port 8000)    │    │   (Supabase)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        
         ▼                        ▼                        
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Time Service  │◄──►│   Stripe API     │    │   Time DB       │
│   (Port 8001)   │    │                  │    │   (Supabase)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                                              
         ▼                                              
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Persona API   │◄──►│   LiveKit        │◄──►│   Voice Agent   │
│   (Port 8004)   │    │   Server         │    │   Service       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                                              │
         ▼                                              ▼
┌─────────────────┐                          ┌─────────────────┐
│   Admin Panel   │                          │   OpenAI/       │
│   (Port 8002)   │                          │   Deepgram      │
└─────────────────┘                          └─────────────────┘
```

## API Service Architecture

| Service | Port | Purpose |
|---------|------|---------|
| Auth Service | 8000 | User authentication, JWT tokens, LiveKit tokens |
| Time Service | 8001 | Time card management, session tracking, billing |
| Admin Panel | 8002 | Analytics, monitoring, system management |
| Webhook Server | 8003 | Payment webhooks and external integrations |
| Persona API | 8004 | Persona management and creation |
| Monetization Service | 8005 | Subscriptions, ads, revenue optimization |

## Database Schema

The system uses Supabase with the following main tables:

- `users`: User accounts and authentication
- `time_cards`: Digital time cards for billing
- `voice_sessions`: Voice conversation sessions
- `payment_history`: Transaction records
- `pricing_tiers`: Time card package definitions
- `custom_personas`: User-created AI personas
- `persona_sessions`: Persona-specific usage tracking
- `persona_ratings`: User feedback on personas
- `user_subscriptions`: Subscription management
- `ad_interactions`: Ad viewing and rewards

## Authentication Flow

1. User registers/logs in → receives JWT token + LiveKit token
2. JWT token used for API access
3. LiveKit token used for voice sessions
4. User identity derived from JWT claims

## Integration Points

- **Stripe**: Payment processing and subscriptions
- **LiveKit**: Real-time voice communication
- **OpenAI**: LLM and text-to-speech
- **Deepgram**: Speech-to-text processing
- **Ad Networks**: For ad-supported tier