from database import engine, Base
from models.transactions import FeeTransaction 
# Hum Transaction model ko import kar rahe hain taaki database isse pehchan sake

print("🛠 Creating Payment Transaction Table...")
Base.metadata.create_all(bind=engine)
print("✅ Success! Fee Transaction Table Created.")