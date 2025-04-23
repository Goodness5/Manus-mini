import os
import requests
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get Supabase credentials from environment
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not found in .env file")
    sys.exit(1)

# SQL to create agent_runs table - extracted from migration file
sql = """
-- Create agent_runs table if it doesn't exist
CREATE TABLE IF NOT EXISTS agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'running',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    responses JSONB NOT NULL DEFAULT '[]'::jsonb,
    error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Create trigger for updated_at if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_agent_runs_updated_at') THEN
        CREATE TRIGGER update_agent_runs_updated_at
            BEFORE UPDATE ON agent_runs
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END
$$;

-- Create indexes if they don't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_agent_runs_thread_id') THEN
        CREATE INDEX idx_agent_runs_thread_id ON agent_runs(thread_id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_agent_runs_status') THEN
        CREATE INDEX idx_agent_runs_status ON agent_runs(status);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_agent_runs_created_at') THEN
        CREATE INDEX idx_agent_runs_created_at ON agent_runs(created_at);
    END IF;
END
$$;

-- Enable Row Level Security
ALTER TABLE agent_runs ENABLE ROW LEVEL SECURITY;

-- Create policies if they don't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE polname = 'agent_run_select_policy') THEN
        CREATE POLICY agent_run_select_policy ON agent_runs
            FOR SELECT
            USING (
                EXISTS (
                    SELECT 1 FROM threads
                    LEFT JOIN projects ON threads.project_id = projects.project_id
                    WHERE threads.thread_id = agent_runs.thread_id
                    AND (
                        projects.is_public = TRUE OR
                        basejump.has_role_on_account(threads.account_id) = true OR 
                        basejump.has_role_on_account(projects.account_id) = true
                    )
                )
            );
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE polname = 'agent_run_insert_policy') THEN
        CREATE POLICY agent_run_insert_policy ON agent_runs
            FOR INSERT
            WITH CHECK (
                EXISTS (
                    SELECT 1 FROM threads
                    LEFT JOIN projects ON threads.project_id = projects.project_id
                    WHERE threads.thread_id = agent_runs.thread_id
                    AND (
                        basejump.has_role_on_account(threads.account_id) = true OR 
                        basejump.has_role_on_account(projects.account_id) = true
                    )
                )
            );
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE polname = 'agent_run_update_policy') THEN
        CREATE POLICY agent_run_update_policy ON agent_runs
            FOR UPDATE
            USING (
                EXISTS (
                    SELECT 1 FROM threads
                    LEFT JOIN projects ON threads.project_id = projects.project_id
                    WHERE threads.thread_id = agent_runs.thread_id
                    AND (
                        basejump.has_role_on_account(threads.account_id) = true OR 
                        basejump.has_role_on_account(projects.account_id) = true
                    )
                )
            );
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE polname = 'agent_run_delete_policy') THEN
        CREATE POLICY agent_run_delete_policy ON agent_runs
            FOR DELETE
            USING (
                EXISTS (
                    SELECT 1 FROM threads
                    LEFT JOIN projects ON threads.project_id = projects.project_id
                    WHERE threads.thread_id = agent_runs.thread_id
                    AND (
                        basejump.has_role_on_account(threads.account_id) = true OR 
                        basejump.has_role_on_account(projects.account_id) = true
                    )
                )
            );
    END IF;
END
$$;
"""

print("Installing required Python package: supabase")
os.system("pip install supabase")

print("Creating agent_runs table using Supabase Python client")
from supabase import create_client

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

try:
    # Use the Supabase client to execute raw SQL
    result = supabase.table("agent_runs").select("count(*)").execute()
    print("Table exists check:", result)
    
    # Try to create the table
    print("Attempting to create the table...")
    
    # We need to use PostgreSQL functions to execute our SQL
    # First, check if all required tables are already created
    response = supabase.rpc(
        "test_db_connection", 
        {}
    ).execute()
    
    print("The table might already exist or PostgreSQL functions are not available")
    print("Let's try to select from the table to verify if it exists:")
    
    try:
        result = supabase.table("agent_runs").select("*").limit(1).execute()
        print("Table exists! Rows:", len(result.data))
    except Exception as table_error:
        print("Error confirming table existence:", str(table_error))
        
        # Try more basic approach
        print("\nTrying another approach...")
        print("Please go to the Supabase Dashboard and run the following SQL in the SQL Editor:")
        print("\n" + sql + "\n")
        print("After running the SQL, restart your application.")
        
except Exception as e:
    print("Error:", str(e))
    
    # Fallback to showing manual instructions
    print("\nManual approach required:")
    print("Please go to the Supabase Dashboard and run the following SQL in the SQL Editor:")
    print("\n" + sql + "\n")
    print("After running the SQL, restart your application.") 