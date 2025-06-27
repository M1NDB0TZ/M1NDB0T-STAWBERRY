# 📘 MindBot API Integration Guide

This comprehensive guide documents all API endpoints, data structures, and integration patterns needed to build a frontend for the MindBot voice AI platform with time-based billing, personas, and monetization features.

## 📋 Table of Contents

1. [Authentication](#authentication)
2. [Time Card System](#time-card-system)
3. [Voice Sessions](#voice-sessions)
4. [Persona System](#persona-system)
5. [Monetization](#monetization)
6. [User Management](#user-management)
7. [Analytics](#analytics)
8. [Webhooks](#webhooks)
9. [Frontend Integration Examples](#frontend-integration-examples)

## Authentication

### Register User

Register a new user account with the system.

```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password",
  "full_name": "John Doe"
}
```

**Response**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "livekit_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "livekit_url": "wss://your-project.livekit.cloud"
}
```

### Login User

Authenticate an existing user.

```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password"
}
```

**Response**: Same as register.

### Get Room Token

Generate a LiveKit token for a specific room. Used for voice sessions.

```http
POST /auth/token
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "room_name": "voice_session_123",
  "participant_name": "John Doe"
}
```

**Response**:
```json
{
  "livekit_token": "eyJhbGciOiJIUzI1NiIs...",
  "livekit_url": "wss://your-project.livekit.cloud",
  "room_name": "voice_session_123",
  "session_id": 42
}
```

### Get Current User

Get information about the current authenticated user.

```http
GET /auth/me
Authorization: Bearer {access_token}
```

**Response**:
```json
{
  "id": "user_id",
  "email": "user@example.com",
  "full_name": "John Doe",
  "created_at": "2025-06-25T14:30:00.000Z",
  "last_login": "2025-06-27T09:15:00.000Z"
}
```

## Time Card System

### Get Pricing Tiers

Get available time card pricing packages.

```http
GET /time/pricing
```

**Response**:
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
      "description": "Perfect for trying out MindBot"
    },
    {
      "id": "basic_5h",
      "name": "Basic Pack",
      "hours": 5,
      "price_cents": 4499,
      "price_display": "$44.99",
      "bonus_minutes": 30,
      "total_minutes": 330,
      "description": "Great for regular users"
    }
    // Additional packages...
  ]
}
```

### Purchase Time Card

Create a payment intent for a time card purchase.

```http
POST /time/purchase
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "package_id": "basic_5h",
  "payment_method_id": "pm_card_visa",
  "save_payment_method": false
}
```

**Response**:
```json
{
  "payment_intent_id": "pi_3OxRbp2eZvKYlo2C1eQYwMqB",
  "client_secret": "pi_3OxRbp2eZvKYlo2C1eQYwMqB_secret_hISrTu37uLECnbKFmIXgUvGWb",
  "time_card_id": "tcrd_123456",
  "activation_code": "ABCD-EFGH-IJKL",
  "package": {
    "name": "Basic Pack",
    "hours": 5,
    "bonus_minutes": 30,
    "total_minutes": 330
  }
}
```

### Activate Time Card

Activate a time card with an activation code.

```http
POST /time/activate
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "activation_code": "ABCD-EFGH-IJKL"
}
```

**Response**:
```json
{
  "message": "Time card activated successfully",
  "time_card": {
    "id": "tcrd_123456",
    "total_minutes": 330,
    "remaining_minutes": 330,
    "expires_at": "2026-06-27T00:00:00.000Z"
  }
}
```

### Get Time Balance

Get user's current time balance and time card information.

```http
GET /time/balance
Authorization: Bearer {access_token}
```

**Response**:
```json
{
  "balance": {
    "total_minutes": 330,
    "total_hours": 5.5,
    "active_cards": 1,
    "next_expiration": "2026-06-27T00:00:00.000Z"
  },
  "time_cards": [
    {
      "id": "tcrd_123456",
      "activation_code": "ABCD-EFGH-IJKL",
      "total_minutes": 330,
      "remaining_minutes": 330,
      "status": "active",
      "activated_at": "2025-06-27T10:30:00.000Z",
      "expires_at": "2026-06-27T10:30:00.000Z",
      "created_at": "2025-06-27T10:25:00.000Z"
    }
  ]
}
```

## Voice Sessions

### Start Time Session

Start tracking time for a voice session.

```http
POST /time/session/start
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "session_id": "session_123456",
  "room_name": "voice_room_abc"
}
```

**Response**:
```json
{
  "session_id": "session_123456",
  "start_time": "2025-06-27T15:00:00.000Z",
  "remaining_balance_minutes": 330
}
```

### End Time Session

End time tracking for a voice session.

```http
POST /time/session/end
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "session_id": "session_123456",
  "duration_seconds": 900
}
```

**Response**:
```json
{
  "session_id": "session_123456",
  "duration_seconds": 900,
  "cost_minutes": 15,
  "status": "completed",
  "remaining_balance": {
    "total_minutes": 315,
    "total_hours": 5.25,
    "active_cards": 1
  }
}
```

### Get Session History

Get history of user's time sessions.

```http
GET /time/sessions?limit=50
Authorization: Bearer {access_token}
```

**Response**:
```json
{
  "sessions": [
    {
      "id": "sess_123456",
      "session_id": "session_123456",
      "room_name": "voice_room_abc",
      "start_time": "2025-06-27T15:00:00.000Z",
      "end_time": "2025-06-27T15:15:00.000Z",
      "duration_seconds": 900,
      "cost_minutes": 15,
      "status": "completed"
    }
    // Additional sessions...
  ]
}
```

## Persona System

### Get Available Personas

Get list of available personas for user.

```http
GET /personas?user_tier=premium&category=education&ad_supported=true&sort_by=rating&limit=20
```

**Response**:
```json
{
  "personas": [
    {
      "slug": "professor-oak-tutor",
      "name": "Professor Oak",
      "summary": "Patient academic tutor who breaks down complex subjects into digestible lessons with encouraging guidance.",
      "category": "education",
      "access_level": "free",
      "rating": 4.9,
      "cost_multiplier": 0.8,
      "session_limit": 90,
      "age_restriction": null,
      "ad_supported": true,
      "premium_features": ["homework_checker", "study_plan_generator", "progress_tracking"],
      "estimated_cost_per_hour": 8.0
    },
    // Additional personas...
  ]
}
```

### Get Persona Details

Get detailed information about a specific persona.

```http
GET /personas/professor-oak-tutor
```

**Response**:
```json
{
  "slug": "professor-oak-tutor",
  "name": "Professor Oak",
  "summary": "Patient academic tutor who breaks down complex subjects into digestible lessons with encouraging guidance.",
  "persona": "Wise, patient, encouraging, uses analogies and real-world examples, celebrates small wins.",
  "purpose": "Help students understand difficult concepts, provide homework guidance, and build confidence in learning.",
  "category": "education",
  "access_level": "free",
  "voice": {"tts": "onyx", "style": "warm professorial tone"},
  "tools": ["check_time_balance", "create_quiz", "explain_concept", "suggest_resources"],
  "safety": "Encourage academic integrity, never do homework for students, focus on teaching understanding.",
  "age_restriction": null,
  "rating": 4.9,
  "usage_count": 10452,
  "cost_multiplier": 0.8,
  "session_limit": 90,
  "daily_limit": null,
  "ad_supported": true,
  "premium_features": ["homework_checker", "study_plan_generator", "progress_tracking"],
  "user_customizable_fields": ["subject_focus", "difficulty_level"],
  "created_at": "2025-06-01T00:00:00.000Z"
}
```

### Create Custom Persona

Create a custom persona from user specifications.

```http
POST /personas/custom
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "My Custom Tutor",
  "summary": "Specialized math tutor for calculus",
  "persona": "Patient, encouraging, uses visual examples",
  "purpose": "Help students learn calculus concepts",
  "category": "education"
}
```

**Response**:
```json
{
  "slug": "my-custom-tutor-a1b2c3",
  "name": "My Custom Tutor",
  "message": "Custom persona created successfully!",
  "system_prompt_preview": "You are My Custom Tutor, a specialized mathematics tutor focused on calculus. Your teaching approach is patient and encouraging...",
  "cost_multiplier": 1.2,
  "estimated_hourly_cost": 12.0
}
```

### Start Persona Session

Start a voice session with a specific persona.

```http
POST /personas/professor-oak-tutor/session
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "room_name": "optional_custom_room",
  "enable_ads": true,
  "quality_preference": "standard"
}
```

**Response**:
```json
{
  "session_started": true,
  "room_name": "persona_professor-oak-tutor_a1b2c3d4",
  "livekit_token": "eyJhbGciOiJIUzI1NiIs...",
  "livekit_url": "wss://mindbot.livekit.cloud",
  "persona": {
    "name": "Professor Oak",
    "slug": "professor-oak-tutor",
    "summary": "Patient academic tutor who breaks down complex subjects",
    "cost_multiplier": 0.8,
    "voice": {"tts": "onyx", "style": "warm professorial tone"},
    "ad_supported": true
  },
  "session_id": "persona_professor-oak-tutor_1624553699",
  "time_balance": {
    "total_minutes": 315,
    "total_hours": 5.25,
    "active_cards": 1
  },
  "estimated_cost_per_minute": 0.8,
  "ads_enabled": true,
  "cost_savings": 0.4,
  "premium_features_available": []
}
```

### Get Persona Categories

Get available persona categories with descriptions.

```http
GET /categories
```

**Response**:
```json
{
  "categories": [
    {
      "value": "entertainment",
      "label": "Entertainment",
      "description": "Fun, engaging personas for entertainment and leisure",
      "icon": "🎉",
      "popular_personas": ["sizzle", "pixel"]
    },
    {
      "value": "education",
      "label": "Education",
      "description": "Learning-focused personas for tutoring and skill development",
      "icon": "📚",
      "popular_personas": ["professor_oak"]
    }
    // Additional categories...
  ]
}
```

### Rate Persona

Rate a persona after a session.

```http
POST /personas/professor-oak-tutor/rate?rating=5&feedback=Great%20tutor!
Authorization: Bearer {access_token}
```

**Response**:
```json
{
  "message": "Thank you for your feedback!",
  "rating_recorded": 5,
  "persona": "Professor Oak"
}
```

## Monetization

### Get Subscription Plans

Get available subscription plans.

```http
GET /plans
```

**Response**:
```json
{
  "plans": [
    {
      "id": "premium_monthly",
      "name": "Premium Monthly",
      "price": 19.99,
      "price_display": "$19.99/month",
      "currency": "usd",
      "interval": "month",
      "features": [
        "Access to all personas",
        "Ad-free experience",
        "Premium voice quality",
        "Create up to 3 custom personas",
        "Priority support"
      ]
    },
    {
      "id": "premium_yearly",
      "name": "Premium Yearly",
      "price": 199.99,
      "price_display": "$199.99/year",
      "currency": "usd",
      "interval": "year",
      "features": [
        "Access to all personas",
        "Ad-free experience",
        "Premium voice quality",
        "Create up to 3 custom personas",
        "Priority support",
        "2 months free compared to monthly"
      ]
    }
    // Additional plans...
  ]
}
```

### Create Subscription

Create a new subscription.

```http
POST /subscriptions
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "plan_id": "premium_monthly",
  "payment_method_id": "pm_card_visa",
  "coupon_code": "WELCOME25"
}
```

**Response**:
```json
{
  "subscription_id": "sub_12345",
  "client_secret": "sub_client_secret_12345",
  "plan": "Premium Monthly",
  "amount": 19.99,
  "currency": "usd",
  "interval": "month"
}
```

### Get Current Subscription

Get user's current subscription.

```http
GET /subscriptions/current
Authorization: Bearer {access_token}
```

**Response**:
```json
{
  "status": "active",
  "plan": "premium_monthly",
  "plan_name": "Premium Monthly",
  "current_period_end": "2025-07-27T15:00:00.000Z",
  "cancel_at_period_end": false,
  "amount": 19.99,
  "currency": "usd",
  "features": [
    "Access to all personas",
    "Ad-free experience",
    "Premium voice quality",
    "Create up to 3 custom personas",
    "Priority support"
  ]
}
```

### Cancel Subscription

Cancel subscription at period end.

```http
POST /subscriptions/cancel
Authorization: Bearer {access_token}
```

**Response**:
```json
{
  "cancelled": true,
  "message": "Your subscription will be cancelled at the end of the current billing period."
}
```

### Get Ad Configuration

Get ad configuration for the current user.

```http
GET /ads/config
Authorization: Bearer {access_token}
```

**Response**:
```json
{
  "ads_enabled": true,
  "ad_frequency": 3,
  "ad_types": ["banner", "video", "sponsored_message"],
  "reward_options": {
    "watch_ad_for_time": {
      "ad_length": 30,
      "time_reward": 5
    },
    "watch_ad_for_discount": {
      "ad_length": 15,
      "discount_percent": 50
    }
  }
}
```

### Record Ad View

Record when user views an ad for cost reduction.

```http
POST /ads/viewed
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "ad_id": "video_ad_123",
  "persona_slug": "professor-oak-tutor",
  "view_duration": 30
}
```

**Response**:
```json
{
  "reward_earned": true,
  "cost_reduction_percentage": 50,
  "next_session_discount": 0.5,
  "message": "Thanks for watching! Your next interaction is 50% off."
}
```

### Validate Coupon Code

Validate a coupon code.

```http
GET /coupons/validate/WELCOME25?amount=4499
Authorization: Bearer {access_token}
```

**Response**:
```json
{
  "valid": true,
  "percent_off": 25,
  "description": "25% off for new users",
  "valid_until": "2025-12-31",
  "message": "Coupon applied: 25% off!"
}
```

## User Management

### Get User Analytics

Get comprehensive user analytics.

```http
GET /user/analytics
Authorization: Bearer {access_token}
```

**Response**:
```json
{
  "user_id": "user_123",
  "email": "user@example.com",
  "full_name": "John Doe",
  "created_at": "2025-06-01T00:00:00.000Z",
  "last_login": "2025-06-27T09:15:00.000Z",
  "balance": {
    "total_minutes": 315,
    "total_hours": 5.25,
    "active_cards": 1,
    "next_expiration": "2026-06-27T00:00:00.000Z"
  },
  "usage": {
    "total_sessions": 15,
    "completed_sessions": 15,
    "total_minutes_used": 135,
    "total_hours_used": 2.25
  },
  "payments": {
    "total_spent_cents": 4499,
    "total_spent_display": "$44.99",
    "transaction_count": 1
  }
}
```

### Get User Subscription

Get user's subscription details and usage.

```http
GET /user/subscription
Authorization: Bearer {access_token}
```

**Response**:
```json
{
  "tier": "free",
  "features": [
    "Basic personas",
    "Ad-supported sessions",
    "Standard voice quality"
  ],
  "usage": {
    "sessions_this_month": 23,
    "minutes_used": 145,
    "personas_accessed": 5
  },
  "upgrade_benefits": {
    "premium": [
      "Remove all ads",
      "Access to premium personas",
      "Custom persona creation",
      "Priority support",
      "Advanced analytics"
    ],
    "premium_price": "$19.99/month"
  }
}
```

### Upgrade Subscription

Upgrade user's subscription tier.

```http
POST /user/upgrade?tier=premium
Authorization: Bearer {access_token}
```

**Response**:
```json
{
  "upgrade_initiated": true,
  "target_tier": "premium",
  "message": "Upgrade process initiated. You'll be redirected to payment.",
  "payment_url": "/payment/subscribe?tier=premium&user=user_123"
}
```

## Analytics

### Get Persona Analytics

Get persona usage analytics and insights.

```http
GET /analytics/personas
Authorization: Bearer {access_token}
```

**Response**:
```json
{
  "user_usage": {
    "total_sessions": 47,
    "total_minutes": 312,
    "favorite_persona": "professor_oak",
    "most_used_category": "education",
    "average_session_length": 6.6,
    "cost_savings_from_ads": 12.50
  },
  "persona_recommendations": [
    {
      "slug": "zen-master",
      "name": "Zen Master",
      "reason": "Based on your wellness interests"
    },
    {
      "slug": "code-wizard",
      "name": "Code Wizard", 
      "reason": "Trending in your technical category"
    }
  ],
  "popular_personas": [
    {"slug": "mindbot", "name": "MindBot", "usage_percent": 32.1},
    {"slug": "professor_oak", "name": "Professor Oak", "usage_percent": 28.5},
    {"slug": "zen_master", "name": "Zen Master", "usage_percent": 15.3},
    {"slug": "sizzle", "name": "SizzleBot", "usage_percent": 12.7}
  ],
  "category_usage": {
    "education": 45.2,
    "general": 25.1,
    "wellness": 18.7,
    "entertainment": 11.0
  }
}
```

## Webhooks

### Stripe Webhook

Endpoint for Stripe webhook events.

```http
POST /webhooks/stripe
Stripe-Signature: {stripe_signature}

// Stripe webhook payload
```

**Response**:
```json
{
  "status": "received"
}
```

## Frontend Integration Examples

### User Registration and Login

```javascript
// Registration
async function registerUser(email, password, fullName) {
  try {
    const response = await fetch('/auth/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        email,
        password,
        full_name: fullName
      })
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || 'Registration failed');
    }
    
    // Store tokens
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('livekit_token', data.livekit_token);
    localStorage.setItem('livekit_url', data.livekit_url);
    
    return data;
  } catch (error) {
    console.error('Registration error:', error);
    throw error;
  }
}

// Login
async function loginUser(email, password) {
  try {
    const response = await fetch('/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        email,
        password
      })
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || 'Login failed');
    }
    
    // Store tokens
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('livekit_token', data.livekit_token);
    localStorage.setItem('livekit_url', data.livekit_url);
    
    return data;
  } catch (error) {
    console.error('Login error:', error);
    throw error;
  }
}
```

### Time Card Purchase with Stripe

```javascript
// Purchase time card
async function purchaseTimeCard(packageId) {
  try {
    // Initialize Stripe
    const stripe = Stripe('pk_live_your_publishable_key');
    
    // 1. Create payment intent
    const response = await fetch('/time-cards/purchase', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      },
      body: JSON.stringify({
        package_id: packageId,
        save_payment_method: true
      })
    });
    
    const paymentData = await response.json();
    
    if (!response.ok) {
      throw new Error(paymentData.detail || 'Payment creation failed');
    }
    
    // 2. Handle card payment
    const result = await stripe.confirmCardPayment(paymentData.client_secret, {
      payment_method: {
        card: elements.getElement(CardElement),
        billing_details: {
          name: 'John Doe',
          email: 'user@example.com'
        }
      }
    });
    
    if (result.error) {
      throw new Error(result.error.message);
    }
    
    // 3. Payment succeeded
    return {
      success: true,
      package: paymentData.package,
      timeCard: paymentData.time_card
    };
  } catch (error) {
    console.error('Purchase error:', error);
    throw error;
  }
}
```

### Starting a Voice Session with a Persona

```javascript
// Start persona session and connect to LiveKit
async function startPersonaSession(personaSlug, enableAds = true) {
  try {
    // 1. Request session and token
    const response = await fetch(`/personas/${personaSlug}/session`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      },
      body: JSON.stringify({
        enable_ads: enableAds,
        quality_preference: 'standard'
      })
    });
    
    const sessionData = await response.json();
    
    if (!response.ok) {
      throw new Error(sessionData.detail || 'Failed to start session');
    }
    
    // 2. Connect to LiveKit
    const room = new LivekitRoom();
    await room.connect(sessionData.livekit_url, sessionData.livekit_token);
    
    // 3. Set up audio/video tracks
    await room.localParticipant.enableMicrophone();
    
    // 4. Set up UI with persona info
    updateUIWithPersona(sessionData.persona);
    
    // 5. Show balance and cost info
    updateBalanceDisplay(sessionData.time_balance);
    updateCostInfo(sessionData.estimated_cost_per_minute);
    
    // 6. Handle ad display if enabled
    if (sessionData.ads_enabled) {
      setupAdDisplay(sessionData.cost_savings);
    }
    
    return {
      room,
      sessionId: sessionData.session_id,
      persona: sessionData.persona
    };
  } catch (error) {
    console.error('Session start error:', error);
    throw error;
  }
}
```

### Checking Time Balance

```javascript
// Get user's time balance
async function getUserTimeBalance() {
  try {
    const response = await fetch('/time/balance', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      }
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || 'Failed to get balance');
    }
    
    // Update UI with balance info
    updateBalanceDisplay(data.balance);
    
    // Show time cards
    renderTimeCards(data.time_cards);
    
    return data;
  } catch (error) {
    console.error('Balance check error:', error);
    throw error;
  }
}
```

### Managing Subscription

```javascript
// Subscribe to a premium plan
async function subscribeToPlan(planId) {
  try {
    // Initialize Stripe
    const stripe = Stripe('pk_live_your_publishable_key');
    
    // 1. Create subscription
    const response = await fetch('/subscriptions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      },
      body: JSON.stringify({
        plan_id: planId,
        payment_method_id: 'pm_card_visa' // From Stripe Elements
      })
    });
    
    const subscriptionData = await response.json();
    
    if (!response.ok) {
      throw new Error(subscriptionData.detail || 'Subscription failed');
    }
    
    // 2. Complete subscription payment
    const result = await stripe.confirmCardPayment(subscriptionData.client_secret);
    
    if (result.error) {
      throw new Error(result.error.message);
    }
    
    // 3. Subscription succeeded
    updateSubscriptionStatus(subscriptionData.plan);
    
    return {
      success: true,
      subscription: subscriptionData
    };
  } catch (error) {
    console.error('Subscription error:', error);
    throw error;
  }
}

// Get current subscription
async function getCurrentSubscription() {
  try {
    const response = await fetch('/subscriptions/current', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      }
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || 'Failed to get subscription');
    }
    
    updateSubscriptionDisplay(data);
    
    return data;
  } catch (error) {
    console.error('Get subscription error:', error);
    return null; // User might not have a subscription
  }
}
```

### Handling Ads

```javascript
// Show ad to earn rewards
async function showAdForReward(adType) {
  try {
    // 1. Display ad (implementation depends on ad network)
    const adResult = await displayAd(adType);
    
    // 2. Report ad view to backend
    const response = await fetch('/ads/viewed', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      },
      body: JSON.stringify({
        ad_id: adResult.adId,
        persona_slug: currentPersona.slug,
        view_duration: adResult.viewDuration
      })
    });
    
    const rewardData = await response.json();
    
    if (!response.ok) {
      throw new Error(rewardData.detail || 'Failed to record ad view');
    }
    
    // 3. Apply rewards
    if (rewardData.reward_earned) {
      if (rewardData.cost_reduction_percentage) {
        applyCostReduction(rewardData.cost_reduction_percentage);
      }
      
      if (rewardData.time_reward) {
        addFreeTime(rewardData.time_reward);
      }
      
      showRewardMessage(rewardData.message);
    }
    
    return rewardData;
  } catch (error) {
    console.error('Ad reward error:', error);
    throw error;
  }
}
```

### Creating a Custom Persona

```javascript
// Create a custom persona
async function createCustomPersona(personaData) {
  try {
    const response = await fetch('/personas/custom', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      },
      body: JSON.stringify({
        name: personaData.name,
        summary: personaData.summary,
        persona: personaData.personality,
        purpose: personaData.purpose,
        category: personaData.category
      })
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || 'Failed to create persona');
    }
    
    // Show success and add to persona list
    addPersonaToList(data);
    
    return data;
  } catch (error) {
    console.error('Custom persona creation error:', error);
    throw error;
  }
}
```

## LiveKit Integration

### Connecting to a Voice Session

```javascript
// Connect to LiveKit for voice session
async function connectToVoiceSession(livekitUrl, livekitToken, roomName) {
  try {
    // 1. Import LiveKit Room
    const { Room } = await import('livekit-client');
    
    // 2. Create and connect to room
    const room = new Room({
      adaptiveStream: true,
      dynacast: true,
      audioEnabled: true,
      videoEnabled: false
    });
    
    // 3. Set up event listeners
    room.on('connectionStateChanged', (state) => {
      console.log('Connection state:', state);
      updateConnectionStatus(state);
    });
    
    room.on('participantConnected', (participant) => {
      console.log('Participant connected:', participant.identity);
      updateParticipantStatus(participant, 'connected');
    });
    
    room.on('participantDisconnected', (participant) => {
      console.log('Participant disconnected:', participant.identity);
      updateParticipantStatus(participant, 'disconnected');
    });
    
    // 4. Connect to room
    await room.connect(livekitUrl, livekitToken);
    console.log('Connected to room:', roomName);
    
    // 5. Enable audio
    await room.localParticipant.enableMicrophone();
    
    return room;
  } catch (error) {
    console.error('LiveKit connection error:', error);
    throw error;
  }
}

// Handle audio from remote participants
function handleRemoteAudio(room) {
  room.on('trackSubscribed', (track, publication, participant) => {
    if (track.kind === 'audio') {
      // Create audio element for remote participant
      const audioElement = new Audio();
      audioElement.srcObject = new MediaStream([track.mediaStreamTrack]);
      audioElement.play();
      
      // Store reference to clean up later
      audioElements[participant.identity] = audioElement;
    }
  });
  
  room.on('trackUnsubscribed', (track, publication, participant) => {
    if (track.kind === 'audio' && audioElements[participant.identity]) {
      audioElements[participant.identity].srcObject = null;
      delete audioElements[participant.identity];
    }
  });
}
```

## Webhook Implementation

### Stripe Webhook Handler

```javascript
// Server-side implementation (Node.js example)
const express = require('express');
const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);
const app = express();

app.post('/webhooks/stripe', express.raw({type: 'application/json'}), async (req, res) => {
  const signature = req.headers['stripe-signature'];
  
  try {
    // Verify webhook signature
    const event = stripe.webhooks.constructEvent(
      req.body,
      signature,
      process.env.STRIPE_WEBHOOK_SECRET
    );
    
    // Handle specific events
    switch (event.type) {
      case 'payment_intent.succeeded':
        await handlePaymentSuccess(event.data.object);
        break;
      case 'payment_intent.payment_failed':
        await handlePaymentFailure(event.data.object);
        break;
      case 'customer.subscription.created':
        await handleSubscriptionCreated(event.data.object);
        break;
      case 'customer.subscription.updated':
        await handleSubscriptionUpdated(event.data.object);
        break;
      case 'customer.subscription.deleted':
        await handleSubscriptionDeleted(event.data.object);
        break;
      default:
        console.log(`Unhandled event type: ${event.type}`);
    }
    
    res.json({received: true});
  } catch (err) {
    console.error(`Webhook error: ${err.message}`);
    res.status(400).send(`Webhook Error: ${err.message}`);
  }
});

async function handlePaymentSuccess(paymentIntent) {
  // Activate time card or process subscription
  const userId = paymentIntent.metadata.user_id;
  
  if (paymentIntent.metadata.mindbot_service === 'time_card_purchase') {
    // Activate time card logic
    console.log(`Activating time card for user ${userId}`);
    
    // Update database
    // Send confirmation email
  }
}
```