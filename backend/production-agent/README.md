# MindBot Production Agent - Supabase & Stripe Integration

A production-ready voice AI agent following the Mem0 LiveKit pattern with comprehensive time tracking, payment processing, and user management via Supabase and Stripe.

## 🎯 Features

### 🎙️ Voice AI Capabilities
- **Real-time Voice Interaction**: Low-latency voice-to-voice conversations
- **Advanced Turn Detection**: Context-aware conversation management
- **Multiple AI Models**: OpenAI GPT-4.1-mini, Deepgram Nova-3, OpenAI TTS
- **Function Calling**: Extensible tool system for external actions

### 💳 Time Card System
- **Digital Time Cards**: Purchase pre-defined time blocks (1h, 5h, 10h, 25h, 50h)
- **Stripe Integration**: Secure payment processing with webhooks
- **Activation Codes**: Unique 12-character codes for time card activation
- **FIFO Usage**: First-expiring time is used first
- **Automatic Expiration**: 1-year validity period

### 👤 User Management
- **Supabase Authentication**: Secure user registration and login
- **Session Tracking**: Track voice sessions and usage analytics
- **User Context**: Personalized responses based on user history
- **Balance Management**: Real-time time balance tracking

### 📊 Analytics & Monitoring
- **Usage Analytics**: Session duration, frequency, and patterns
- **Payment Tracking**: Complete transaction history
- **Performance Metrics**: Response times, error rates, and quality scores
- **Admin Dashboard**: Comprehensive reporting and management

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Supabase account
- LiveKit Cloud account
- OpenAI API key
- Deepgram API key
- Stripe account

### 1. Environment Setup

```bash
cd backend/production-agent
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp env.example .env
# Edit .env with your actual credentials
```

Required environment variables:
```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# LiveKit
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
LIVEKIT_URL=wss://your-project.livekit.cloud

# AI Services
OPENAI_API_KEY=sk-your_openai_api_key
DEEPGRAM_API_KEY=your_deepgram_api_key

# Stripe
STRIPE_SECRET_KEY=sk_live_your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
```

### 3. Setup Supabase Database

1. Create a new Supabase project
2. Run the migration script: `backend/production-agent/supabase/migrations/001_initial_schema.sql`
3. Enable Row Level Security (RLS)
4. Configure authentication policies

### 4. Configure Stripe

1. Create webhook endpoint: `https://your-domain.com/webhooks/stripe`
2. Add events: `payment_intent.succeeded`, `payment_intent.payment_failed`
3. Copy webhook signing secret to environment

### 5. Launch the System

```bash
# Development mode (interactive)
./launch_script.sh dev

# Production mode (background services)
./launch_script.sh start

# Direct agent start
python production_mindbot.py start
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client Apps   │◄──►│   LiveKit        │◄──►│   Voice Agent   │
│                 │    │   Server         │    │   (Python)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Webhook       │◄──►│   Supabase       │◄──►│   Stripe        │
│   Server        │    │   Database       │    │   Payments      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 💰 Time Card Packages

| Package | Hours | Bonus | Price | Total Time | Description |
|---------|-------|-------|-------|------------|-------------|
| Starter | 1h | 0min | $9.99 | 1h | Perfect for trying out |
| Basic | 5h | 30min | $44.99 | 5.5h | Great for regular users |
| Premium | 10h | 2h | $79.99 | 12h | Best value option |
| Pro | 25h | 5h | $179.99 | 30h | For power users |
| Enterprise | 50h | 10h | $299.99 | 60h | Maximum value |

## 🛠️ Function Tools

The agent includes these function tools:

### `check_time_balance()`
Get current time balance and usage information

### `get_pricing_packages()`
List available time card packages with pricing

### `estimate_session_cost()`
Show current session cost and remaining time

### `start_purchase_process(package_id)`
Help user start the time card purchase process

### `get_session_summary()`
Provide summary of current session and usage

## 📊 Database Schema

### Core Tables

#### `users`
- User account information
- Authentication data
- Activity tracking

#### `time_cards`
- Digital time card records
- Activation codes and balances
- Expiration tracking

#### `voice_sessions`
- Voice conversation sessions
- Usage tracking and billing
- Quality metrics

#### `payment_history`
- Stripe payment records
- Transaction tracking
- Revenue analytics

#### `pricing_tiers`
- Time card package definitions
- Pricing and bonus structures
- Active/inactive management

### Key Functions

#### `get_user_time_balance(user_id)`
Calculate total remaining time across all active cards

#### `deduct_user_time(user_id, minutes)`
Deduct time using FIFO (first-expiring first) logic

#### `cleanup_expired_time_cards()`
Mark expired time cards as inactive

## 🔐 Security Features

### Row Level Security (RLS)
- Users can only access their own data
- Service role has full access for operations
- Public read access for pricing tiers

### Payment Security
- Stripe handles all payment processing
- Webhook signature verification
- No card data stored locally

### Authentication
- Supabase Auth integration
- JWT token validation
- Session management

## 📈 Analytics & Monitoring

### User Analytics
- Total conversation time used
- Session frequency and duration
- Payment history and spending
- Balance usage patterns

### System Metrics
- Agent response times
- Error rates and recovery
- Concurrent session handling
- Resource utilization

### Business Intelligence
- Revenue tracking and trends
- Package popularity analysis
- User retention metrics
- Support ticket correlation

## 🚀 Production Deployment

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Start both webhook server and voice agent
CMD ["./launch_script.sh", "start"]
```

### Environment Variables for Production

```env
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Use production keys
STRIPE_SECRET_KEY=sk_live_...
SUPABASE_URL=https://your-prod-project.supabase.co
LIVEKIT_URL=wss://your-prod-project.livekit.cloud

# Monitoring
PROMETHEUS_PORT=8080
HEALTH_CHECK_PORT=8090
```

### Health Checks

```bash
# Voice agent health
curl http://localhost:8090/health

# Webhook server health
curl http://localhost:8003/health

# Supabase connectivity
curl https://your-project.supabase.co/rest/v1/pricing_tiers
```

## 🔧 Development

### Running Tests

```bash
pip install pytest pytest-asyncio
pytest tests/ -v
```

### Debug Mode

```bash
# Start with debug logging
LOG_LEVEL=DEBUG python production_mindbot.py dev

# Monitor logs
tail -f logs/*.log
```

### Local Development

1. Use Stripe test keys
2. Use Supabase development project
3. Set `ENVIRONMENT=development`
4. Enable debug logging

## 📝 API Reference

### Webhook Endpoints

#### `POST /webhooks/stripe`
Handle Stripe webhook events for payment processing

#### `GET /pricing`
Get available pricing tiers

#### `POST /create-payment-intent`
Create Stripe payment intent for time card purchase

#### `GET /user/{user_id}/balance`
Get user's current time balance

#### `GET /user/{user_id}/analytics`
Get comprehensive user analytics

## 🆘 Troubleshooting

### Common Issues

#### Agent Not Starting
- Check environment variables
- Verify Supabase connectivity
- Validate LiveKit credentials
- Check Python version (3.11+)

#### Payment Processing Issues
- Verify Stripe webhook configuration
- Check webhook secret
- Monitor webhook server logs
- Test with Stripe CLI

#### Time Deduction Problems
- Check user balance in Supabase
- Verify session tracking
- Monitor database functions
- Check RLS policies

### Debug Commands

```bash
# Test Supabase connection
python -c "from supabase_client import supabase_client; print(supabase_client.supabase.table('users').select('count').execute())"

# Test Stripe connection
python -c "import stripe; stripe.api_key='sk_test_...'; print(stripe.Account.retrieve())"

# Check agent logs
tail -f logs/voice-agent.log

# Monitor webhook logs
tail -f logs/webhook-server.log
```

## 📞 Support

- **Technical Issues**: Check logs and error messages
- **Payment Problems**: Verify Stripe configuration
- **Database Issues**: Check Supabase dashboard
- **Voice Quality**: Monitor LiveKit metrics

## 🚀 Launch Checklist

- [ ] Environment variables configured
- [ ] Supabase database schema applied
- [ ] Stripe webhooks configured
- [ ] SSL certificates installed
- [ ] Health checks passing
- [ ] Monitoring alerts set up
- [ ] Backup procedures in place
- [ ] Load testing completed

This production agent provides a complete, scalable solution for voice AI with integrated payment processing and user management. It follows industry best practices for security, monitoring, and reliability.