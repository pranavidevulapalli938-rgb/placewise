from database import SessionLocal
from models import User

db = SessionLocal()

users = db.query(User).all()

if not users:
    print("❌ No users found in the database.")
else:
    print(f"✅ Found {len(users)} user(s):\n")
    for u in users:
        print(f"  ID: {u.id}  |  Email: {u.email}")

db.close()