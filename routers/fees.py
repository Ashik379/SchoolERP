from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from database import get_db
from models.fees import FeeItem, FeePlan
from models.masters import LedgerMaster
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api/v1/fees", tags=["Fee Settings"])

# --- SCHEMAS ---
class FeeItemCreate(BaseModel):
    ledger_id: int
    frequency: str
    months: List[str]

class FeePlanCreate(BaseModel):
    class_id: int
    fee_item_id: int
    amount: float

# Output Schemas for UI
class LedgerSimpleOut(BaseModel):
    id: int
    ledger_name: str
    class Config:
        from_attributes = True

class FeeItemOut(BaseModel):
    id: int
    ledger_id: int
    frequency: str
    ledger_val: Optional[LedgerSimpleOut] = None
    class Config:
        from_attributes = True

class FeePlanOut(BaseModel):
    class_id: int
    fee_item_id: int
    amount: float
    class Config:
        from_attributes = True

# --- 1. FEE ITEMS (Schedule) ---
@router.get("/items", response_model=List[FeeItemOut])
def get_fee_items(db: Session = Depends(get_db)):
    return db.query(FeeItem).options(joinedload(FeeItem.ledger_val)).all()

@router.post("/items")
def create_fee_item(item: FeeItemCreate, db: Session = Depends(get_db)):
    existing = db.query(FeeItem).filter(FeeItem.ledger_id == item.ledger_id).first()
    if existing:
        db.delete(existing)
        db.commit()

    new_fee = FeeItem(
        ledger_id=item.ledger_id,
        frequency=item.frequency,
        apr="Apr" in item.months,
        may="May" in item.months,
        jun="Jun" in item.months,
        jul="Jul" in item.months,
        aug="Aug" in item.months,
        sep="Sep" in item.months,
        oct="Oct" in item.months,
        nov="Nov" in item.months,
        dec="Dec" in item.months,
        jan="Jan" in item.months,
        feb="Feb" in item.months,
        mar="Mar" in item.months
    )
    db.add(new_fee)
    db.commit()
    return {"message": "Saved"}

@router.delete("/items/{id}")
def delete_fee_item(id: int, db: Session = Depends(get_db)):
    item = db.query(FeeItem).filter(FeeItem.id == id).first()
    if item:
        db.delete(item)
        db.commit()
    return {"message": "Deleted"}

# --- 2. FEE PLAN (Amount) ---

# NEW: Get ALL Plans for Matrix View
@router.get("/plans/all", response_model=List[FeePlanOut])
def get_all_fee_plans(db: Session = Depends(get_db)):
    return db.query(FeePlan).all()

@router.post("/plans/bulk")
def save_bulk_plans(plans: List[FeePlanCreate], db: Session = Depends(get_db)):
    for p in plans:
        # Check if exists
        existing = db.query(FeePlan).filter(
            FeePlan.class_id == p.class_id, 
            FeePlan.fee_item_id == p.fee_item_id
        ).first()
        
        if existing:
            existing.amount = p.amount
        else:
            if p.amount > 0: # Only save if amount is > 0
                db.add(FeePlan(class_id=p.class_id, fee_item_id=p.fee_item_id, amount=p.amount))
    
    db.commit()
    return {"message": "Bulk Saved"}