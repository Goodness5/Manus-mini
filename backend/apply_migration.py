import psycopg2
import os
from pathlib import Path

# Database connection string
conn_string = "postgresql://postgres.vjicnhhemyscenfgcyeq:manus123#@aws-0-us-east-2.pooler.supabase.com:5432/postgres"

# Path to your migrations folder
migrations_path = Path("supabase/migrations")

def run_migrations():
    try:
        print("Connecting to database...")
        # Connect to the database
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()
        print("Database connection established successfully")
        
        # Get all migration files sorted by name
        print(f"Scanning migrations folder: {migrations_path}")
        migration_files = sorted(migrations_path.glob("*.sql"))
        print(f"Found {len(migration_files)} migration files")
        
        for migration_file in migration_files:
            print(f"\nProcessing migration: {migration_file.name}")
            print("-" * 50)
            
            # Read the SQL file
            with open(migration_file, 'r') as f:
                sql = f.read()
                print(f"Migration content:\n{sql}\n")
                print("-" * 50)
            
            # Execute the SQL
            print("Executing migration...")
            cursor.execute(sql)
            conn.commit()
            print(f"Migration {migration_file.name} completed successfully")
            
        print("\nAll migrations completed successfully")
        
    except Exception as e:
        print(f"\nError running migrations: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            cursor.close()
            conn.close()
            print("Database connection closed")

if __name__ == "__main__":
    run_migrations()