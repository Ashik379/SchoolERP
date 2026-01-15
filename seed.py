from database import SessionLocal, engine, Base
from models.masters import ClassMaster, SectionMaster, TransportMaster, FeeHead
from models.students import Student
from models.fees import FeePlan, FeeReceiptConfig
from models.transactions import FeeTransaction

# --- MAGICAL LINE (Ye Tables bana degi agar missing hain) ---
Base.metadata.create_all(bind=engine)

# Database Connection
db = SessionLocal()

def seed_data():
    print("🌱 Seeding Master Data...")

    # 1. ADD CLASSES (Class 1 to Class 12)
    classes = ["Class 1", "Class 2", "Class 3", "Class 4", "Class 5", 
               "Class 6", "Class 7", "Class 8", "Class 9", "Class 10", 
               "Class 11", "Class 12"]
    
    class_objects = {} 
    
    for c_name in classes:
        exists = db.query(ClassMaster).filter_by(class_name=c_name).first()
        if not exists:
            new_class = ClassMaster(class_name=c_name)
            db.add(new_class)
            db.commit() 
            db.refresh(new_class)
            class_objects[c_name] = new_class.id
            print(f"✅ Added: {c_name}")
        else:
            class_objects[c_name] = exists.id
            print(f"ℹ️  Exists: {c_name}")

    # 2. ADD SECTIONS (A, B)
    sections = ["A", "B"]
    for c_name, c_id in class_objects.items():
        for sec in sections:
            exists = db.query(SectionMaster).filter_by(class_id=c_id, section_name=sec).first()
            if not exists:
                db.add(SectionMaster(class_id=c_id, section_name=sec))
                print(f"  └── Section {sec} added to {c_name}")
    db.commit()

    # 3. ADD TRANSPORT ROUTES
    routes = [
        {"name": "City Centre", "km": 5.0, "price": 1200},
        {"name": "Railway Station", "km": 8.5, "price": 1500},
        {"name": "Airport Road", "km": 12.0, "price": 2000},
        {"name": "Local Village", "km": 2.0, "price": 500}
    ]

    for r in routes:
        exists = db.query(TransportMaster).filter_by(pickup_point_name=r["name"]).first()
        if not exists:
            db.add(TransportMaster(
                pickup_point_name=r["name"], 
                distance_km=r["km"], 
                monthly_charge=r["price"]
            ))
            print(f"🚌 Added Route: {r['name']}")
    db.commit()

    # 4. ADD FEE HEADS
    heads = [
        {"name": "Admission Fee", "type": "one_time"},
        {"name": "Tuition Fee", "type": "monthly"},
        {"name": "Exam Fee", "type": "custom"},
        {"name": "Transport Fee", "type": "monthly"},
        {"name": "Annual Function", "type": "one_time"}
    ]

    for h in heads:
        exists = db.query(FeeHead).filter_by(fee_name=h["name"]).first()
        if not exists:
            db.add(FeeHead(fee_name=h["name"], fee_type=h["type"]))
            print(f"💰 Added Fee Head: {h['name']}")
    db.commit()

    print("\n🎉 All Data Seeded Successfully!")
    db.close()

if __name__ == "__main__":
    seed_data()