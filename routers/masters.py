from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.masters import ClassMaster, SectionMaster, TransportMaster, LedgerMaster
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api/v1/masters", tags=["Master Records"])

# =======================
# 1. PYDANTIC SCHEMAS
# =======================
class ClassCreate(BaseModel):
    class_name: str

class SectionCreate(BaseModel):
    class_id: int
    section_name: str

class TransportCreate(BaseModel):
    pickup_point_name: str
    distance_km: float
    monthly_charge: float

class LedgerCreate(BaseModel):
    ledger_name: str
    under_group: str
    opening_balance: float
    balance_type: str

# =======================
# 2. CLASS APIs
# =======================
@router.get("/classes")
def list_classes(db: Session = Depends(get_db)):
    return db.query(ClassMaster).all()

@router.post("/classes")
def create_class(item: ClassCreate, db: Session = Depends(get_db)):
    existing = db.query(ClassMaster).filter(ClassMaster.class_name == item.class_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Class already exists")
    
    new_class = ClassMaster(class_name=item.class_name)
    db.add(new_class)
    db.commit()
    return {"message": "Class Created", "id": new_class.id}

# =======================
# 3. SECTION APIs (FIXED ✅)
# =======================

# Generic List (Saare sections ya filter query se)
@router.get("/sections")
def list_sections(class_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(SectionMaster)
    if class_id:
        query = query.filter(SectionMaster.class_id == class_id)
    return query.all()

# ✅ YAHAN GALTI THI - AB THEEK HAI
# Frontend maangta hai /sections/1, toh humne url se 'class' hata diya
@router.get("/sections/{class_id}")
def get_sections_by_class(class_id: int, db: Session = Depends(get_db)):
    # Ye wahi endpoint hai jo Edit Modal dhoond raha hai
    return db.query(SectionMaster).filter(SectionMaster.class_id == class_id).all()

@router.post("/sections")
def create_section(item: SectionCreate, db: Session = Depends(get_db)):
    cls = db.query(ClassMaster).filter(ClassMaster.id == item.class_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Class ID not found")
        
    new_section = SectionMaster(class_id=item.class_id, section_name=item.section_name)
    db.add(new_section)
    db.commit()
    return {"message": "Section Created"}

# =======================
# 4. TRANSPORT APIs
# =======================
@router.get("/transport")
def list_transport(db: Session = Depends(get_db)):
    return db.query(TransportMaster).all()

@router.post("/transport")
def create_pickup_point(item: TransportCreate, db: Session = Depends(get_db)):
    new_point = TransportMaster(
        pickup_point_name=item.pickup_point_name,
        distance_km=item.distance_km,
        monthly_charge=item.monthly_charge
    )
    db.add(new_point)
    db.commit()
    return {"message": "Pickup Point Added"}

# =======================
# 5. LEDGER APIs
# =======================
@router.get("/ledgers")
def get_ledgers(db: Session = Depends(get_db)):
    count = db.query(LedgerMaster).count()
    if count == 0:
        defaults = [
            {"name": "Admission Fee", "group": "Fee Received"},
            {"name": "Tie & Belt", "group": "Fee Received"},
            {"name": "I-Card", "group": "Fee Received"},
            {"name": "Diary Fee", "group": "Fee Received"},
            {"name": "Transport Fee", "group": "Fee Received"},
            {"name": "Exam Fee", "group": "Fee Received"},
            {"name": "Annual Function Fee", "group": "Fee Received"},
            {"name": "Board Fee", "group": "Fee Received"},
            {"name": "Book Fee", "group": "Fee Received"},
            {"name": "Cash Account", "group": "Cash"},
            {"name": "Bank Account", "group": "Bank"}
        ]
        for d in defaults:
            db.add(LedgerMaster(ledger_name=d["name"], under_group=d["group"], opening_balance=0.0, balance_type="Cr"))
        db.commit()
    
    return db.query(LedgerMaster).all()

@router.post("/ledgers")
def add_ledger(item: LedgerCreate, db: Session = Depends(get_db)):
    new_item = LedgerMaster(
        ledger_name=item.ledger_name,
        under_group=item.under_group,
        opening_balance=item.opening_balance,
        balance_type=item.balance_type
    )
    db.add(new_item)
    db.commit()
    return {"message": "Ledger Created"}