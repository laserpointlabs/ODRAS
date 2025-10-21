#!/usr/bin/env python3
"""
Add project_assumptions table to database for DAS Actions feature
"""

import sys
import psycopg2
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.config import Settings

def main():
    settings = Settings()
    
    print("🔧 Adding project_assumptions table for DAS Actions...")
    
    try:
        conn = psycopg2.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_database,
            user=settings.postgres_user,
            password=settings.postgres_password
        )
        
        cursor = conn.cursor()
        
        # Create project_assumptions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_assumptions (
                assumption_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                project_id UUID NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
                content TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                created_by UUID REFERENCES users(user_id),
                conversation_context TEXT,
                status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'validated', 'invalidated', 'archived')),
                notes TEXT
            );
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_assumptions_project ON project_assumptions(project_id);
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_assumptions_created_at ON project_assumptions(created_at);
        """)
        
        conn.commit()
        
        print("✅ project_assumptions table created successfully")
        print("✅ Indexes created successfully")
        
        # Verify table exists
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_name = 'project_assumptions'
        """)
        
        if cursor.fetchone()[0] == 1:
            print("✅ Table verification passed")
        else:
            print("❌ Table verification failed")
            return 1
        
        cursor.close()
        conn.close()
        
        print("\n🎉 DAS Actions database migration completed successfully!")
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
