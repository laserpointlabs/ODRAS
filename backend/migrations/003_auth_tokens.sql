-- Migration: Add persistent authentication tokens table
-- This migration adds a table to store authentication tokens persistently
-- so they survive server restarts and don't require re-login on refresh

-- Create authentication tokens table
CREATE TABLE IF NOT EXISTS public.auth_tokens (
    token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_hash VARCHAR(64) UNIQUE NOT NULL, -- SHA-256 hash of the token for security
    user_id UUID NOT NULL REFERENCES public.users(user_id) ON DELETE CASCADE,
    username VARCHAR(255) NOT NULL,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '24 hours'),
    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_auth_tokens_token_hash ON public.auth_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_auth_tokens_user_id ON public.auth_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_tokens_expires_at ON public.auth_tokens(expires_at);
CREATE INDEX IF NOT EXISTS idx_auth_tokens_is_active ON public.auth_tokens(is_active);

-- Create a function to clean up expired tokens
CREATE OR REPLACE FUNCTION cleanup_expired_tokens()
RETURNS void AS $$
BEGIN
    DELETE FROM public.auth_tokens 
    WHERE expires_at < NOW() OR is_active = FALSE;
END;
$$ LANGUAGE plpgsql;

-- Create a function to update last_used_at when token is accessed
CREATE OR REPLACE FUNCTION update_token_last_used(token_hash_param VARCHAR(64))
RETURNS void AS $$
BEGIN
    UPDATE public.auth_tokens 
    SET last_used_at = NOW() 
    WHERE token_hash = token_hash_param AND is_active = TRUE;
END;
$$ LANGUAGE plpgsql;

-- Add comment
COMMENT ON TABLE public.auth_tokens IS 'Persistent storage for authentication tokens to survive server restarts';
COMMENT ON COLUMN public.auth_tokens.token_hash IS 'SHA-256 hash of the actual token for security';
COMMENT ON COLUMN public.auth_tokens.expires_at IS 'Token expiration time (default 24 hours)';
COMMENT ON COLUMN public.auth_tokens.last_used_at IS 'Last time this token was used for authentication';
