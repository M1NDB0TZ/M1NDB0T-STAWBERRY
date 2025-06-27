# MindBotz Time Tracking Service

A comprehensive time tracking and payment system for MindBotz that enables users to purchase, manage, and track digital time cards for AI conversation sessions.

## 🎯 Features

### 💳 Time Card System
- **Digital Time Cards**: Purchase pre-defined time blocks (1h, 5h, 10h, 25h, 50h)
- **Activation Codes**: Unique 12-character codes for time card activation
- **Stacking**: Add multiple time cards to build up balance
- **Expiration**: 1-year validity period for unused time
- **FIFO Usage**: First-expiring time is used first

### 💰 Stripe Integration
- **Secure Payments**: Full Stripe payment processing integration
- **Multiple Packages**: 5 different time card packages with bonus minutes
- **Payment History**: Complete transaction tracking and history
- **Webhook Support**: Automatic card activation on payment success
- **Saved Payment Methods**: Optional payment method storage for repeat purchases

### ⏱️ Real-Time Tracking
- **Session Tracking**: Track time usage during voice AI sessions
- **Minute-by-Minute Billing**: Accurate time deduction based on actual usage
- **Balance Monitoring**: Real-time balance checking and low balance alerts
- **Session History**: Complete history of all time sessions

### 🔔 Notification System
- **Low Balance Alerts**: Automatic notifications when time is running low
- **Email Notifications**: Email alerts for important events
- **In-App Notifications**: Real-time in-app notification support

## 🚀 Quick Start

### 1. Setup Environment

```bash
cd backend/time-service
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Stripe

1. Create a Stripe account at [stripe.com](https://stripe.com)
2. Get your API keys from the Stripe dashboard
3. Set up a webhook endpoint for payment confirmations

### 3. Configure Environment Variables

```bash
cp env.example .env
# Edit .env with your credentials
```

Required environment variables:
```env
STRIPE_SECRET_KEY="sk_test_..."
STRIPE_PUBLISHABLE_KEY="pk_test_..."  
STRIPE_WEBHOOK_SECRET="whsec_..."
JWT_SECRET="your-super-secret-jwt-key"
```

### 4. Start the Service

```bash
python time_server.py
```

The service will start on `http://localhost:8001`

## 📋 API Reference

### Time Card Management

#### Get Pricing Tiers
```http
GET /time/pricing
```

**Response:**
```json
{
  "pricing_tiers": [
    {
      "id": "starter_1h",
      "name": "Starter Pack",
      "hours": 1,
      "price_cents": 999,
      "price_display": "$9.99",
      "bonus_minutes": 0,
      "total_minutes": 60,
      "description": "Perfect for trying out MindBotz"
    }
  ]
}
```

#### Purchase Time Card
```http
POST /time/purchase
Authorization: Bearer jwt_token
Content-Type: application/json

{
  "package_id": "basic_5h",
  "payment_method_id": "pm_card_visa",
  "save_payment_method": false
}
```

#### Activate Time Card
```http
POST /time/activate  
Authorization: Bearer jwt_token
Content-Type: application/json

{
  "activation_code": "ABCD-EFGH-IJKL"
}
```

#### Check Time Balance
```http
GET /time/balance
Authorization: Bearer jwt_token
```

### Session Tracking

#### Start Time Session
```http
POST /time/session/start
Authorization: Bearer jwt_token
Content-Type: application/json

{
  "session_id": "session_123",
  "room_name": "voice_room_456"
}
```

#### End Time Session
```http
POST /time/session/end
Authorization: Bearer jwt_token
Content-Type: application/json

{
  "session_id": "session_123", 
  "duration_seconds": 1800
}
```

#### Get Session History
```http
GET /time/sessions?limit=50
Authorization: Bearer jwt_token
```

## 🗄️ Database Schema

### Time Cards Table
```sql
CREATE TABLE time_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    activation_code TEXT UNIQUE NOT NULL,
    total_minutes INTEGER NOT NULL,
    remaining_minutes INTEGER NOT NULL,
    activated_at TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending',
    stripe_payment_intent_id TEXT
);
```

### Time Sessions Table
```sql
CREATE TABLE time_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_id TEXT NOT NULL,
    room_name TEXT NOT NULL,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    duration_seconds INTEGER,
    cost_minutes INTEGER,
    status TEXT DEFAULT 'active'
);
```

### Payment History Table
```sql
CREATE TABLE payment_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    stripe_payment_intent_id TEXT UNIQUE NOT NULL,
    amount_cents INTEGER NOT NULL,
    currency TEXT DEFAULT 'usd',
    status TEXT NOT NULL,
    time_card_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 💳 Pricing Packages

| Package | Hours | Bonus | Price | Total Minutes | Description |
|---------|-------|-------|-------|---------------|-------------|
| Starter | 1h | 0min | $9.99 | 60 | Perfect for trying out |
| Basic | 5h | 30min | $44.99 | 330 | Great for regular users |
| Premium | 10h | 2h | $79.99 | 720 | Best value option |
| Pro | 25h | 5h | $179.99 | 1800 | For power users |
| Enterprise | 50h | 10h | $299.99 | 3600 | Maximum value |

## 🔗 Integration with MindBot Agent

### Time-Aware Agent

The `time_aware_mindbot.py` agent automatically:

1. **Checks Balance**: Greets users with their remaining time
2. **Tracks Sessions**: Starts/stops time tracking automatically
3. **Provides Alerts**: Warns users when time is running low
4. **Offers Packages**: Suggests time card purchases when needed

### Function Tools

The time-aware agent includes these function tools:
- `check_time_balance()`: Get current balance information
- `get_time_packages()`: List available time card packages
- `estimate_session_cost()`: Show current session cost and remaining time

### Example Integration

```python
# In your agent's on_enter method
async def on_enter(self):
    await self.start_time_tracking()
    balance = await self.get_user_balance()
    
    if balance['total_minutes'] < 30:
        await self.session.say(
            f"Hi! You have {balance['total_minutes']} minutes remaining. "
            "Consider purchasing more time cards to continue our conversations!"
        )
```

## 🛡️ Security Features

### Payment Security
- **Stripe Integration**: Industry-standard payment processing
- **Webhook Verification**: Cryptographically signed webhook validation
- **No Card Storage**: Payment methods securely stored by Stripe only
- **JWT Authentication**: Secure API access with JWT tokens

### Time Tracking Security
- **User Isolation**: Users can only access their own time data
- **Balance Validation**: Server-side balance validation prevents manipulation
- **Session Tracking**: Secure session ID generation and validation
- **Audit Trail**: Complete audit trail of all time usage

## 🚀 Production Deployment

### Environment Configuration
```env
# Production Stripe keys
STRIPE_SECRET_KEY="sk_live_..."
STRIPE_PUBLISHABLE_KEY="pk_live_..."
STRIPE_WEBHOOK_SECRET="whsec_..."

# Secure JWT secret
JWT_SECRET="your-super-secure-production-jwt-secret-256-bits"

# Production database
DATABASE_PATH="/app/data/mindbot_time_tracking.db"
```

### Docker Deployment
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8001

CMD ["python", "time_server.py"]
```

### Monitoring & Alerts
- Set up Stripe dashboard monitoring for payments
- Monitor database size and performance
- Set up alerts for high error rates or failed payments
- Track user balance distributions and usage patterns

## 📊 Analytics & Reporting

The service provides rich analytics data:
- **Revenue Tracking**: Daily, weekly, monthly revenue reports
- **Usage Patterns**: Peak usage times and session patterns
- **Package Popularity**: Which packages sell best
- **User Behavior**: Session duration and frequency analysis
- **Balance Analytics**: Average balances and low-balance patterns

## 🤝 Integration with Admin Dashboard

The admin dashboard provides:
- Real-time revenue and usage analytics
- User balance monitoring and management
- Pricing tier management and updates
- Payment issue resolution and refund processing
- System health monitoring and alerts

## 📝 Testing

### Test Purchase Flow
```bash
# Test with Stripe test cards
curl -X POST http://localhost:8001/time/purchase \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "package_id": "starter_1h",
    "payment_method_id": "pm_card_visa"
  }'
```

### Test Session Tracking
```bash
# Start session
curl -X POST http://localhost:8001/time/session/start \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_session_123",
    "room_name": "test_room"
  }'

# End session
curl -X POST http://localhost:8001/time/session/end \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_session_123",
    "duration_seconds": 300
  }'
```

This time tracking service provides a complete foundation for monetizing your MindBot voice AI platform with a user-friendly time card system that scales from individual users to enterprise customers.