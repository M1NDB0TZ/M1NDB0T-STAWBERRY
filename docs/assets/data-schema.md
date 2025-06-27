# MindBot Data Schema

## Core Database Tables

### Users Table

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE
);
```

### Time Cards Table

```sql
CREATE TABLE time_cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    activation_code TEXT UNIQUE NOT NULL,
    total_minutes INTEGER NOT NULL,
    remaining_minutes INTEGER NOT NULL,
    activated_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'expired', 'used', 'refunded')),
    stripe_payment_intent_id TEXT
);
```

### Voice Sessions Table

```sql
CREATE TABLE voice_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL,
    room_name TEXT NOT NULL,
    start_time TIMESTAMPTZ DEFAULT NOW(),
    end_time TIMESTAMPTZ,
    duration_seconds INTEGER,
    cost_minutes INTEGER,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'error', 'cancelled')),
    agent_type TEXT DEFAULT 'production',
    quality_rating INTEGER CHECK (quality_rating BETWEEN 1 AND 5)
);
```

### Payment History Table

```sql
CREATE TABLE payment_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    stripe_payment_intent_id TEXT UNIQUE NOT NULL,
    amount_cents INTEGER NOT NULL,
    currency TEXT DEFAULT 'usd',
    status TEXT NOT NULL,
    time_card_id UUID REFERENCES time_cards(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB
);
```

### Pricing Tiers Table

```sql
CREATE TABLE pricing_tiers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    hours INTEGER NOT NULL,
    price_cents INTEGER NOT NULL,
    bonus_minutes INTEGER DEFAULT 0,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Persona System Tables

### Custom Personas Table

```sql
CREATE TABLE custom_personas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    config JSONB NOT NULL,
    system_prompt TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    usage_count INTEGER DEFAULT 0,
    rating DECIMAL DEFAULT 0.0
);
```

### Persona Sessions Table

```sql
CREATE TABLE persona_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    persona_slug TEXT NOT NULL,
    session_id TEXT NOT NULL,
    duration_minutes INTEGER,
    cost_multiplier DECIMAL DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Persona Ratings Table

```sql
CREATE TABLE persona_ratings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    persona_slug TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    feedback TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Subscription & Ad Tables

### User Subscriptions Table

```sql
CREATE TABLE user_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'canceled', 'past_due', 'trialing', 'incomplete')),
    current_period_start TIMESTAMPTZ NOT NULL,
    current_period_end TIMESTAMPTZ NOT NULL,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    stripe_subscription_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Ad Interactions Table

```sql
CREATE TABLE ad_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ad_id TEXT NOT NULL,
    ad_type TEXT NOT NULL,
    view_duration INTEGER NOT NULL,
    completed BOOLEAN DEFAULT FALSE,
    interacted BOOLEAN DEFAULT FALSE,
    revenue DECIMAL DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Key Data Objects

### PersonaConfig

```typescript
interface PersonaConfig {
  // Core Identity
  name: string;
  slug: string;  
  summary: string;
  category: string;
  access_level: string;
  
  // Personality & Behavior
  persona: string;
  purpose: string;
  system_prompt: string;
  
  // Voice Configuration
  voice: {
    tts: string;
    style: string;
  };
  
  // Capabilities
  tools: string[];
  custom_tools: any[];
  
  // Safety & Compliance
  safety: string;
  content_filters: string[];
  age_restriction: number | null;
  
  // Metadata
  created_by: string;
  created_at: string;
  version: string;
  is_active: boolean;
  usage_count: number;
  rating: number;
  
  // Revenue Optimization
  base_cost_multiplier: number;
  session_time_limit: number | null;
  daily_usage_limit: number | null;
  ad_supported: boolean;
  premium_features: string[];
  
  // Customization
  user_customizable_fields: string[];
}
```

### TimeCard

```typescript
interface TimeCard {
  id: string;
  user_id: string;
  activation_code: string;
  total_minutes: number;
  remaining_minutes: number;
  activated_at: string | null;
  expires_at: string | null;
  created_at: string;
  status: 'pending' | 'active' | 'expired' | 'used' | 'refunded';
  stripe_payment_intent_id: string | null;
}
```

### VoiceSession

```typescript
interface VoiceSession {
  id: string;
  user_id: string;
  session_id: string;
  room_name: string;
  start_time: string;
  end_time: string | null;
  duration_seconds: number | null;
  cost_minutes: number | null;
  status: 'active' | 'completed' | 'error' | 'cancelled';
  agent_type: string;
  quality_rating: number | null;
}
```

### Subscription

```typescript
interface Subscription {
  id: string;
  user_id: string;
  plan_id: string;
  status: 'active' | 'canceled' | 'past_due' | 'trialing' | 'incomplete';
  current_period_start: string;
  current_period_end: string;
  cancel_at_period_end: boolean;
  stripe_subscription_id: string | null;
  created_at: string;
}
```

### PricingTier

```typescript
interface PricingTier {
  id: string;
  name: string;
  hours: number;
  price_cents: number;
  bonus_minutes: number;
  description: string;
  active: boolean;
  created_at: string;
}
```

### User

```typescript
interface User {
  id: string;
  email: string;
  full_name: string;
  created_at: string;
  last_login: string | null;
  is_active: boolean;
  email_verified: boolean;
}
```