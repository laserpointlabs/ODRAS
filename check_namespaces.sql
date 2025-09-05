-- Check if namespace tables exist and have data
\dt namespace*

-- Check namespace_registry table specifically
SELECT COUNT(*) as namespace_count FROM namespace_registry;

-- Show table structure if it exists
\d namespace_registry

