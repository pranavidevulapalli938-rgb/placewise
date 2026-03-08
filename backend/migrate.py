"""
Run this script once to:
1. Add missing 'created_at' column to notes table
2. Delete fake Gmail entries (Leetcode, Eu, Naukri)
"""
from database import SessionLocal, engine
from sqlalchemy import text

db = SessionLocal()

try:
    # Step 1: Add created_at column if it doesn't exist
    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='notes' AND column_name='created_at'
        """))
        exists = result.fetchone()

        if not exists:
            conn.execute(text("""
                ALTER TABLE notes
                ADD COLUMN created_at TIMESTAMP WITH TIME ZONE
                DEFAULT NOW()
            """))
            conn.commit()
            print("✅ Added 'created_at' column to notes table")
        else:
            print("✅ 'created_at' column already exists")

    # Step 2: Delete fake Gmail entries using raw SQL (avoids ORM cascade issue)
    with engine.connect() as conn:
        # First delete related notes and status history
        result = conn.execute(text("""
            SELECT id FROM applications WHERE role = '(via Gmail)'
        """))
        fake_ids = [row[0] for row in result.fetchall()]

        if fake_ids:
            for app_id in fake_ids:
                conn.execute(text(f"DELETE FROM notes WHERE application_id = {app_id}"))
                conn.execute(text(f"DELETE FROM application_status_history WHERE application_id = {app_id}"))
                conn.execute(text(f"DELETE FROM applications WHERE id = {app_id}"))
                print(f"✅ Deleted fake application ID {app_id}")
            conn.commit()
            print(f"✅ Deleted {len(fake_ids)} fake Gmail entries")
        else:
            print("✅ No fake Gmail entries found")

    print("\n✅ Migration complete! Restart FastAPI and sync Gmail again.")

except Exception as e:
    print(f"❌ Error: {e}")
    db.rollback()
finally:
    db.close()


# Step 3: Add applied_date column if missing
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name='applications' AND column_name='applied_date'
    """))
    if not result.fetchone():
        conn.execute(text("ALTER TABLE applications ADD COLUMN applied_date TIMESTAMPTZ DEFAULT NOW()"))
        conn.commit()
        print("✅ Added applied_date to applications")
    else:
        print("✅ applied_date already exists")

# Step 4: Add gmail_message_id column if missing
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name='applications' AND column_name='gmail_message_id'
    """))
    if not result.fetchone():
        conn.execute(text("ALTER TABLE applications ADD COLUMN gmail_message_id VARCHAR"))
        conn.commit()
        print("✅ Added gmail_message_id to applications")
    else:
        print("✅ gmail_message_id already exists")