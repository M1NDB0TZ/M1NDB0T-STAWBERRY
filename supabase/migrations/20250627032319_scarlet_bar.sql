/*
  # MindBot Initial Database Schema
  
  1. New Tables
    - `users`
      - `id` (uuid, primary key)
      - `email` (text, unique)
      - `full_name` (text)
      - `password_hash` (text)
      - `created_at` (timestamp)
      - `last_login` (timestamp)
      - `is_active` (boolean)
      - `email_verified` (boolean)
    
    - `time_cards`
      - `id` (uuid, primary key)
      - `user_id` (uuid, foreign key)
      - `activation_code` (text, unique)
      - `total_minutes` (integer)
      - `remaining_minutes` (integer)
      - `activated_at` (timestamp)
      - `expires_at` (timestamp)
      - `created_at` (timestamp)
      - `status` (text)
      - `stripe_payment_intent_id` (text)
    
    - `voice_sessions`
      - `id` (uuid, primary key)
      - `user_id` (uuid, foreign key)
      - `session_id` (text)
      - `room_name` (text)
      - `start_time` (timestamp)
      - `end_time` (timestamp)
      - `duration_seconds` (integer)
      - `cost_minutes` (integer)
      - `status` (text)
      - `agent_type` (text)
      - `quality_rating` (integer)
    
    - `payment_history`
      - `id` (uuid, primary key)
      - `user_id` (uuid, foreign key)
      - `stripe_payment_intent_id` (text, unique)
      - `amount_cents` (integer)
      - `currency` (text)
      - `status` (text)
      - `time_card_id` (uuid, foreign key)
      - `created_at` (timestamp)
      - `metadata` (jsonb)
    
    - `pricing_tiers`
      - `id` (text, primary key)
      - `name` (text)
      - `hours` (integer)
      - `price_cents` (integer)
      - `bonus_minutes` (integer)
      - `description` (text)
      - `active` (boolean)
      - `created_at` (timestamp)
  
  2. Security
    - Enable RLS on all tables
    - Add policies for user data access
    - Add admin policies for management
*/

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE
);

-- Time cards table
CREATE TABLE IF NOT EXISTS time_cards (
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

-- Voice sessions table
CREATE TABLE IF NOT EXISTS voice_sessions (
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

-- Payment history table
CREATE TABLE IF NOT EXISTS payment_history (
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

-- Pricing tiers table
CREATE TABLE IF NOT EXISTS pricing_tiers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    hours INTEGER NOT NULL,
    price_cents INTEGER NOT NULL,
    bonus_minutes INTEGER DEFAULT 0,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default pricing tiers
INSERT INTO pricing_tiers (id, name, hours, price_cents, bonus_minutes, description) VALUES
('starter_1h', 'Starter Pack', 1, 999, 0, 'Perfect for trying out MindBot - 1 hour of AI conversation time'),
('basic_5h', 'Basic Pack', 5, 4499, 30, 'Great for regular users - 5 hours + 30 bonus minutes'),
('premium_10h', 'Premium Pack', 10, 7999, 120, 'Best value - 10 hours + 2 bonus hours'),
('pro_25h', 'Pro Pack', 25, 17999, 300, 'For power users - 25 hours + 5 bonus hours'),
('enterprise_50h', 'Enterprise Pack', 50, 29999, 600, 'Maximum value - 50 hours + 10 bonus hours')
ON CONFLICT (id) DO NOTHING;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_time_cards_user_id ON time_cards(user_id);
CREATE INDEX IF NOT EXISTS idx_time_cards_status ON time_cards(status);
CREATE INDEX IF NOT EXISTS idx_time_cards_expires_at ON time_cards(expires_at);
CREATE INDEX IF NOT EXISTS idx_voice_sessions_user_id ON voice_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_voice_sessions_session_id ON voice_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_voice_sessions_status ON voice_sessions(status);
CREATE INDEX IF NOT EXISTS idx_payment_history_user_id ON payment_history(user_id);
CREATE INDEX IF NOT EXISTS idx_payment_history_status ON payment_history(status);

-- Enable Row Level Security (RLS)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE time_cards ENABLE ROW LEVEL SECURITY;
ALTER TABLE voice_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE pricing_tiers ENABLE ROW LEVEL SECURITY;

-- RLS Policies for users table
CREATE POLICY "Users can read own data" ON users
    FOR SELECT TO authenticated
    USING (auth.uid() = id);

CREATE POLICY "Users can update own data" ON users
    FOR UPDATE TO authenticated
    USING (auth.uid() = id);

-- RLS Policies for time_cards table
CREATE POLICY "Users can read own time cards" ON time_cards
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "Service role can manage time cards" ON time_cards
    FOR ALL TO service_role
    USING (true);

-- RLS Policies for voice_sessions table
CREATE POLICY "Users can read own sessions" ON voice_sessions
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "Service role can manage sessions" ON voice_sessions
    FOR ALL TO service_role
    USING (true);

-- RLS Policies for payment_history table
CREATE POLICY "Users can read own payment history" ON payment_history
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "Service role can manage payments" ON payment_history
    FOR ALL TO service_role
    USING (true);

-- RLS Policies for pricing_tiers table (public read)
CREATE POLICY "Everyone can read active pricing tiers" ON pricing_tiers
    FOR SELECT TO anon, authenticated
    USING (active = true);

CREATE POLICY "Service role can manage pricing tiers" ON pricing_tiers
    FOR ALL TO service_role
    USING (true);

-- Functions for time balance calculation
CREATE OR REPLACE FUNCTION get_user_time_balance(user_uuid UUID)
RETURNS TABLE (
    total_minutes INTEGER,
    total_hours DECIMAL,
    active_cards INTEGER,
    next_expiration TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COALESCE(SUM(remaining_minutes), 0)::INTEGER as total_minutes,
        ROUND(COALESCE(SUM(remaining_minutes), 0)::DECIMAL / 60, 1) as total_hours,
        COUNT(*)::INTEGER as active_cards,
        MIN(expires_at) as next_expiration
    FROM time_cards 
    WHERE user_id = user_uuid 
      AND status = 'active' 
      AND remaining_minutes > 0
      AND (expires_at IS NULL OR expires_at > NOW());
END;
$$;

-- Function to deduct time from cards (FIFO)
CREATE OR REPLACE FUNCTION deduct_user_time(user_uuid UUID, minutes_to_deduct INTEGER)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    card_record RECORD;
    remaining_to_deduct INTEGER := minutes_to_deduct;
    deduction_amount INTEGER;
BEGIN
    -- Get active cards ordered by expiration date (FIFO)
    FOR card_record IN 
        SELECT id, remaining_minutes
        FROM time_cards 
        WHERE user_id = user_uuid 
          AND status = 'active' 
          AND remaining_minutes > 0
          AND (expires_at IS NULL OR expires_at > NOW())
        ORDER BY expires_at ASC NULLS LAST, created_at ASC
    LOOP
        EXIT WHEN remaining_to_deduct <= 0;
        
        deduction_amount := LEAST(card_record.remaining_minutes, remaining_to_deduct);
        
        UPDATE time_cards 
        SET 
            remaining_minutes = remaining_minutes - deduction_amount,
            status = CASE 
                WHEN remaining_minutes - deduction_amount <= 0 THEN 'used'
                ELSE 'active'
            END
        WHERE id = card_record.id;
        
        remaining_to_deduct := remaining_to_deduct - deduction_amount;
    END LOOP;
    
    -- Return true if all time was successfully deducted
    RETURN remaining_to_deduct = 0;
END;
$$;

-- Function to cleanup expired time cards
CREATE OR REPLACE FUNCTION cleanup_expired_time_cards()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE time_cards 
    SET status = 'expired'
    WHERE status = 'active' 
      AND expires_at IS NOT NULL 
      AND expires_at < NOW();
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END;
$$;

-- Create a scheduled job to cleanup expired cards (if pg_cron is available)
-- SELECT cron.schedule('cleanup-expired-cards', '0 1 * * *', 'SELECT cleanup_expired_time_cards();');