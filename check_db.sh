#!/bin/bash
# Script to check database tables without hanging

# Create SQL query
cat > temp_query.sql << EOF
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;
EOF

# Run query and capture output
PGPASSWORD=password psql -h localhost -U postgres -d odras -f temp_query.sql > db_output.txt 2>&1

# Show results
echo "=== Database Tables ==="
cat db_output.txt

# Clean up
rm -f temp_query.sql db_output.txt

echo "=== Done ==="
