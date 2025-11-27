#!/usr/bin/env python3
"""
VPS Database Schema Migration Script
Run this on your VPS to update the database schema to the latest version.

Usage:
    python run_migration.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import psycopg2

def run_migration():
    """Run the VPS schema update migration"""
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    print("=" * 60)
    print("VPS Database Schema Migration")
    print("=" * 60)
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("\n1. Updating jobs table status constraint...")
        try:
            cursor.execute("ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_status_check")
            cursor.execute("""
                ALTER TABLE jobs ADD CONSTRAINT jobs_status_check 
                CHECK (status IN ('pending', 'processing', 'awaiting_step8_review', 'awaiting_csv_review', 'pdf_ready', 'completed', 'failed', 'signed'))
            """)
            print("   ✓ Status constraint updated")
        except Exception as e:
            print(f"   ! Warning: {e}")
            conn.rollback()
        
        print("\n2. Adding payload column to jobs table...")
        try:
            cursor.execute("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'jobs' AND column_name = 'payload'
                    ) THEN
                        ALTER TABLE jobs ADD COLUMN payload JSONB;
                    END IF;
                END $$;
            """)
            conn.commit()
            print("   ✓ Payload column checked/added")
        except Exception as e:
            print(f"   ! Warning: {e}")
            conn.rollback()
        
        print("\n3. Adding folder_path column to jobs table...")
        try:
            cursor.execute("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'jobs' AND column_name = 'folder_path'
                    ) THEN
                        ALTER TABLE jobs ADD COLUMN folder_path TEXT;
                    END IF;
                END $$;
            """)
            conn.commit()
            print("   ✓ Folder path column checked/added")
        except Exception as e:
            print(f"   ! Warning: {e}")
            conn.rollback()
        
        print("\n4. Adding platform column to channels table...")
        try:
            cursor.execute("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'channels' AND column_name = 'platform'
                    ) THEN
                        ALTER TABLE channels ADD COLUMN platform VARCHAR(50) DEFAULT 'youtube';
                    END IF;
                END $$;
            """)
            conn.commit()
            print("   ✓ Platform column checked/added")
        except Exception as e:
            print(f"   ! Warning: {e}")
            conn.rollback()
        
        print("\n5. Adding metadata column to saved_rationale table...")
        try:
            cursor.execute("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'saved_rationale' AND column_name = 'metadata'
                    ) THEN
                        ALTER TABLE saved_rationale ADD COLUMN metadata JSONB;
                    END IF;
                END $$;
            """)
            conn.commit()
            print("   ✓ Metadata column checked/added")
        except Exception as e:
            print(f"   ! Warning: {e}")
            conn.rollback()
        
        print("\n6. Creating missing indexes...")
        indexes = [
            ("idx_jobs_user_id", "jobs", "user_id"),
            ("idx_jobs_status", "jobs", "status"),
            ("idx_jobs_tool_used", "jobs", "tool_used"),
            ("idx_job_steps_job_id", "job_steps", "job_id"),
            ("idx_job_steps_status", "job_steps", "status"),
            ("idx_saved_rationale_tool_used", "saved_rationale", "tool_used"),
            ("idx_saved_rationale_channel_id", "saved_rationale", "channel_id"),
        ]
        
        for idx_name, table, column in indexes:
            try:
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})")
                conn.commit()
            except Exception as e:
                conn.rollback()
        print("   ✓ Indexes checked/created")
        
        print("\n7. Verifying schema...")
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'jobs' ORDER BY ordinal_position
        """)
        columns = [row[0] for row in cursor.fetchall()]
        print(f"   Jobs columns: {', '.join(columns)}")
        
        cursor.execute("""
            SELECT pg_get_constraintdef(oid) 
            FROM pg_constraint 
            WHERE conrelid = 'jobs'::regclass AND contype = 'c' AND conname = 'jobs_status_check'
        """)
        constraint = cursor.fetchone()
        if constraint:
            print(f"   Status constraint: {constraint[0]}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✓ Migration completed successfully!")
        print("=" * 60)
        print("\nYou can now restart your application.")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
