from database import engine, Base
# Order bahut zaroori hai: Pehle Student, Fir PaidMonth
from models.students import Student
from models.paid_history import PaidMonth
from models.transactions import FeeTransaction

print("🚀 Starting Database Repair...")

# 1. Force Create Tables
try:
    print("🛠 Creating missing tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Success! Tables created.")
except Exception as e:
    print(f"❌ Error creating tables: {e}")

# 2. Check if PaidMonth works
from sqlalchemy.orm import sessionmaker
Session = sessionmaker(bind=engine)
db = Session()

try:
    count = db.query(PaidMonth).count()
    print(f"✅ PaidMonth Table is working. Records found: {count}")
except Exception as e:
    print(f"❌ PaidMonth Table ERROR: {e}")

print("🎉 Repair Complete. Now restart your server.")