"""
Run this once to add missing columns/tables to your database.
Usage: python fix_db.py
"""
from database import engine
from sqlalchemy import text

with engine.connect() as conn:

    # 1. Add source_url to applications
    conn.execute(text("""
        ALTER TABLE applications
        ADD COLUMN IF NOT EXISTS source_url VARCHAR
    """))
    print("✅ source_url column added (or already exists)")

    # 2. Create password_reset_tokens table
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id         SERIAL PRIMARY KEY,
            user_id    INTEGER REFERENCES users(id) ON DELETE CASCADE,
            token      VARCHAR UNIQUE NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            used       BOOLEAN DEFAULT FALSE NOT NULL
        )
    """))
    print("✅ password_reset_tokens table created (or already exists)")

    conn.commit()

print("\n✅ All done! Restart uvicorn now.")