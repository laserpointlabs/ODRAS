-- Migration script to add proper authentication fields to users table
-- Run this to upgrade from the current allowlist system to proper password authentication

-- Add password and authentication fields to users table
ALTER TABLE public.users
ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255),
ADD COLUMN IF NOT EXISTS salt VARCHAR(255),
ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Update existing users to be active
UPDATE public.users
SET is_active = TRUE, updated_at = NOW()
WHERE is_active IS NULL;

-- Create index for username lookups (if not exists)
CREATE INDEX IF NOT EXISTS idx_users_username ON public.users(username);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON public.users(is_active);

-- Add constraint to ensure password_hash and salt are set for active users
-- (We'll handle this in the application layer for now)

-- Create a function to update the updated_at timestamp for users
CREATE OR REPLACE FUNCTION update_users_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for users table
DROP TRIGGER IF EXISTS update_users_updated_at ON public.users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION update_users_updated_at();

-- Note: Existing users will need to have passwords set through the admin interface
-- or password reset functionality

