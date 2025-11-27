-- VPS Database Schema Update Script
-- Run this on your VPS PostgreSQL database to update the schema

-- 1. Update jobs table status CHECK constraint to include new statuses
-- First drop the old constraint, then add the new one
DO $$ 
BEGIN
    -- Drop old constraint if exists
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE table_name = 'jobs' AND constraint_type = 'CHECK'
    ) THEN
        ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_status_check;
    END IF;
    
    -- Add new constraint with all status values
    ALTER TABLE jobs ADD CONSTRAINT jobs_status_check 
        CHECK (status IN ('pending', 'processing', 'awaiting_step8_review', 'awaiting_csv_review', 'pdf_ready', 'completed', 'failed', 'signed'));
EXCEPTION
    WHEN others THEN
        RAISE NOTICE 'Could not update jobs_status_check constraint: %', SQLERRM;
END $$;

-- 2. Add payload column to jobs table if not exists
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'jobs' AND column_name = 'payload'
    ) THEN
        ALTER TABLE jobs ADD COLUMN payload JSONB;
        RAISE NOTICE 'Added payload column to jobs table';
    END IF;
END $$;

-- 3. Add folder_path column to jobs table if not exists
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'jobs' AND column_name = 'folder_path'
    ) THEN
        ALTER TABLE jobs ADD COLUMN folder_path TEXT;
        RAISE NOTICE 'Added folder_path column to jobs table';
    END IF;
END $$;

-- 4. Add platform column to channels table if not exists
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'channels' AND column_name = 'platform'
    ) THEN
        ALTER TABLE channels ADD COLUMN platform VARCHAR(50) DEFAULT 'youtube';
        RAISE NOTICE 'Added platform column to channels table';
    END IF;
END $$;

-- 5. Add metadata column to saved_rationale table if not exists
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'saved_rationale' AND column_name = 'metadata'
    ) THEN
        ALTER TABLE saved_rationale ADD COLUMN metadata JSONB;
        RAISE NOTICE 'Added metadata column to saved_rationale table';
    END IF;
END $$;

-- 6. Create missing indexes
CREATE INDEX IF NOT EXISTS idx_jobs_user_id ON jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_tool_used ON jobs(tool_used);
CREATE INDEX IF NOT EXISTS idx_job_steps_job_id ON job_steps(job_id);
CREATE INDEX IF NOT EXISTS idx_job_steps_status ON job_steps(status);
CREATE INDEX IF NOT EXISTS idx_saved_rationale_tool_used ON saved_rationale(tool_used);
CREATE INDEX IF NOT EXISTS idx_saved_rationale_channel_id ON saved_rationale(channel_id);

-- 7. Verify the schema update
SELECT 'Schema update completed successfully!' as status;

-- Show current jobs status constraint
SELECT conname, pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conrelid = 'jobs'::regclass AND contype = 'c';
