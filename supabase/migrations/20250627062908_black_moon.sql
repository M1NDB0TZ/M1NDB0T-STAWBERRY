/*
  # MindBot Persona System Schema
  
  1. New Tables
    - `custom_personas`
      - `id` (uuid, primary key)
      - `user_id` (uuid, foreign key)
      - `slug` (text, unique)
      - `name` (text)
      - `config` (jsonb)
      - `system_prompt` (text)
      - `created_at` (timestamp)
      - `is_active` (boolean)
      - `usage_count` (integer)
      - `rating` (decimal)
    
    - `persona_sessions`
      - `id` (uuid, primary key)
      - `user_id` (uuid, foreign key)
      - `persona_slug` (text)
      - `session_id` (text)
      - `duration_minutes` (integer)
      - `cost_multiplier` (decimal)
      - `created_at` (timestamp)
    
    - `persona_ratings`
      - `id` (uuid, primary key)
      - `user_id` (uuid, foreign key)
      - `persona_slug` (text)
      - `rating` (integer)
      - `feedback` (text)
      - `created_at` (timestamp)
    
    - `user_subscriptions`
      - `id` (uuid, primary key)
      - `user_id` (uuid, foreign key)
      - `plan_id` (text)
      - `status` (text)
      - `current_period_start` (timestamp)
      - `current_period_end` (timestamp)
      - `cancel_at_period_end` (boolean)
      - `stripe_subscription_id` (text)
      - `created_at` (timestamp)
    
    - `ad_interactions`
      - `id` (uuid, primary key)
      - `user_id` (uuid, foreign key)
      - `ad_id` (text)
      - `ad_type` (text)
      - `view_duration` (integer)
      - `completed` (boolean)
      - `interacted` (boolean)
      - `revenue` (decimal)
      - `created_at` (timestamp)
  
  2. Security
    - Enable RLS on all tables
    - Add policies for user data access
    - Add admin policies for management
*/

-- Custom personas table
CREATE TABLE IF NOT EXISTS custom_personas (
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

-- Persona sessions table
CREATE TABLE IF NOT EXISTS persona_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    persona_slug TEXT NOT NULL,
    session_id TEXT NOT NULL,
    duration_minutes INTEGER,
    cost_multiplier DECIMAL DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Persona ratings table
CREATE TABLE IF NOT EXISTS persona_ratings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    persona_slug TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    feedback TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User subscriptions table
CREATE TABLE IF NOT EXISTS user_subscriptions (
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

-- Ad interactions table
CREATE TABLE IF NOT EXISTS ad_interactions (
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

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_custom_personas_user_id ON custom_personas(user_id);
CREATE INDEX IF NOT EXISTS idx_custom_personas_slug ON custom_personas(slug);
CREATE INDEX IF NOT EXISTS idx_persona_sessions_user_id ON persona_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_persona_sessions_persona_slug ON persona_sessions(persona_slug);
CREATE INDEX IF NOT EXISTS idx_persona_ratings_persona_slug ON persona_ratings(persona_slug);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user_id ON user_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_status ON user_subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_ad_interactions_user_id ON ad_interactions(user_id);
CREATE INDEX IF NOT EXISTS idx_ad_interactions_ad_type ON ad_interactions(ad_type);

-- Enable Row Level Security (RLS)
ALTER TABLE custom_personas ENABLE ROW LEVEL SECURITY;
ALTER TABLE persona_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE persona_ratings ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE ad_interactions ENABLE ROW LEVEL SECURITY;

-- RLS Policies for custom_personas table
CREATE POLICY "Users can read own custom personas" ON custom_personas
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "Users can create own custom personas" ON custom_personas
    FOR INSERT TO authenticated
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update own custom personas" ON custom_personas
    FOR UPDATE TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "Service role can manage custom personas" ON custom_personas
    FOR ALL TO service_role
    USING (true);

-- RLS Policies for persona_sessions table
CREATE POLICY "Users can read own persona sessions" ON persona_sessions
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "Service role can manage persona sessions" ON persona_sessions
    FOR ALL TO service_role
    USING (true);

-- RLS Policies for persona_ratings table
CREATE POLICY "Users can read own persona ratings" ON persona_ratings
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "Users can create own persona ratings" ON persona_ratings
    FOR INSERT TO authenticated
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Service role can manage persona ratings" ON persona_ratings
    FOR ALL TO service_role
    USING (true);

-- RLS Policies for user_subscriptions table
CREATE POLICY "Users can read own subscriptions" ON user_subscriptions
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "Service role can manage subscriptions" ON user_subscriptions
    FOR ALL TO service_role
    USING (true);

-- RLS Policies for ad_interactions table
CREATE POLICY "Users can read own ad interactions" ON ad_interactions
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "Users can create own ad interactions" ON ad_interactions
    FOR INSERT TO authenticated
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Service role can manage ad interactions" ON ad_interactions
    FOR ALL TO service_role
    USING (true);

-- Functions for persona analytics
CREATE OR REPLACE FUNCTION get_persona_analytics(user_uuid UUID)
RETURNS TABLE (
    total_sessions INTEGER,
    total_minutes INTEGER,
    favorite_persona TEXT,
    most_used_category TEXT,
    average_session_length DECIMAL
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH user_sessions AS (
        SELECT 
            ps.persona_slug,
            COUNT(*) as session_count,
            COALESCE(SUM(ps.duration_minutes), 0) as total_minutes,
            COALESCE(AVG(ps.duration_minutes), 0) as avg_duration
        FROM persona_sessions ps
        WHERE ps.user_id = user_uuid
        GROUP BY ps.persona_slug
    )
    SELECT 
        COALESCE(SUM(us.session_count), 0)::INTEGER as total_sessions,
        COALESCE(SUM(us.total_minutes), 0)::INTEGER as total_minutes,
        (SELECT persona_slug FROM user_sessions ORDER BY session_count DESC LIMIT 1) as favorite_persona,
        'general'::TEXT as most_used_category, -- Would need persona category mapping in production
        COALESCE(SUM(us.total_minutes) / NULLIF(SUM(us.session_count), 0), 0)::DECIMAL as average_session_length
    FROM user_sessions us;
END;
$$;

-- Function to get user subscription status
CREATE OR REPLACE FUNCTION get_user_subscription_tier(user_uuid UUID)
RETURNS TEXT
LANGUAGE plpgsql
AS $$
DECLARE
    subscription_status TEXT;
    subscription_plan TEXT;
BEGIN
    -- Check for active subscription
    SELECT status, plan_id
    INTO subscription_status, subscription_plan
    FROM user_subscriptions
    WHERE user_id = user_uuid
      AND status = 'active'
      AND current_period_end > NOW()
    ORDER BY current_period_end DESC
    LIMIT 1;
    
    -- Return tier based on subscription
    IF subscription_status = 'active' THEN
        IF subscription_plan LIKE 'premium%' THEN
            RETURN 'premium';
        ELSIF subscription_plan LIKE 'exclusive%' THEN
            RETURN 'exclusive';
        ELSE
            RETURN 'free';
        END IF;
    ELSE
        RETURN 'free';
    END IF;
END;
$$;

-- Function to check if user can create custom persona
CREATE OR REPLACE FUNCTION can_create_custom_persona(user_uuid UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    user_tier TEXT;
    current_count INTEGER;
    max_allowed INTEGER;
BEGIN
    -- Get user tier
    user_tier := get_user_subscription_tier(user_uuid);
    
    -- Set max allowed based on tier
    IF user_tier = 'premium' THEN
        max_allowed := 3;
    ELSIF user_tier = 'exclusive' THEN
        max_allowed := 999; -- Unlimited
    ELSE
        max_allowed := 0;
    END IF;
    
    -- Count current custom personas
    SELECT COUNT(*)
    INTO current_count
    FROM custom_personas
    WHERE user_id = user_uuid
      AND is_active = TRUE;
    
    -- Check if under limit
    RETURN current_count < max_allowed;
END;
$$;