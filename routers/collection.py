from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from database import get_db
from models.students import Student
from models.fees import FeeItem, FeePlan
from models.transactions import FeeTransaction
from models.paid_history import PaidMonth
from models.masters import TransportMaster
from pydantic import BaseModel
from typing import List, Optional
import datetime
import json # ✅ Added for item tracking

router = APIRouter(prefix="/api/v1/collection", tags=["Fee Collection"])

class DuesRequest(BaseModel):
    student_id: int
    months: List[str]

class FullPaymentRequest(BaseModel):
    student_id: int
    total_amount: float
    additional_fee: float = 0
    discount: float = 0
    net_payable: float
    paid_amount: float
    balance: float
    payment_mode: str
    remarks: Optional[str] = None
    paid_months_list: List[str] = []
    items: List[dict] = [] # ✅ Frontend se ab items ki list aayegi

@router.post("/get-dues")
def calculate_dues(req: DuesRequest, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == req.student_id).first()
    if not student: return {"dues": [], "old_balance": 0}
    old_bal = float(student.current_balance) if student.current_balance else 0.0
    paid_records = db.query(PaidMonth).filter(PaidMonth.student_id == req.student_id).all()
    already_paid_months = [r.month for r in paid_records]
    dues_list = []
    for month in req.months:
        month_key = month.lower()
        is_already_paid = month in already_paid_months
        scheduled_items = db.query(FeeItem).all()
        for item in scheduled_items:
            if hasattr(item, month_key) and getattr(item, month_key):
                plan = db.query(FeePlan).filter(FeePlan.class_id == student.class_id, FeePlan.fee_item_id == item.id).first()
                if plan and plan.amount > 0:
                    dues_list.append({
                        "fee_head": item.ledger_val.ledger_name if item.ledger_val else "Unknown",
                        "month": month,
                        "amount": plan.amount,
                        "status": "Paid" if is_already_paid else "Due"
                    })
        if student.transport_opted and student.pickup_point_id:
            t_point = db.query(TransportMaster).filter(TransportMaster.id == student.pickup_point_id).first()
            if t_point:
                dues_list.append({
                    "fee_head": "Transport Fee",
                    "month": month,
                    "amount": t_point.monthly_charge,
                    "status": "Paid" if is_already_paid else "Due"
                })
    return {"dues": dues_list, "old_balance": old_bal}

@router.post("/pay-full")
def submit_full_payment(pay: FullPaymentRequest, db: Session = Depends(get_db)):
    # ✅ Sabse important: Pay kiye gaye items ko Remarks mein JSON bana kar save karna
    items_data = json.dumps(pay.items)
    final_remark = f"RECEIPT_DATA:{items_data} | {pay.remarks or ''}"
    
    new_txn = FeeTransaction(
        student_id=pay.student_id,
        total_amount=pay.total_amount,
        additional_fee=pay.additional_fee,
        discount=pay.discount,
        net_payable=pay.net_payable,
        amount_paid=pay.paid_amount,
        balance_amount=pay.balance,
        payment_date=datetime.date.today(),
        payment_mode=pay.payment_mode,
        remarks=final_remark
    )
    db.add(new_txn)
    for m in pay.paid_months_list:
        exists = db.query(PaidMonth).filter(PaidMonth.student_id==pay.student_id, PaidMonth.month==m).first()
        if not exists: db.add(PaidMonth(student_id=pay.student_id, month=m, session="2025-26"))
    student = db.query(Student).filter(Student.id == pay.student_id).first()
    if student: student.current_balance = pay.balance
    db.commit()
    return {"message": "Success", "receipt_no": new_txn.id}

# routers/collection.py

# routers/collection.py

@router.get("/receipt/{txn_id}")
def get_receipt(txn_id: int, db: Session = Depends(get_db)):
    txn = db.query(FeeTransaction).filter(FeeTransaction.id == txn_id).first()
    if not txn: raise HTTPException(status_code=404, detail="Not Found")
    
    student = db.query(Student).filter(Student.id == txn.student_id).options(joinedload(Student.class_val)).first()
    
    # ✅ 1. Months Formatting: Sirf mahino ke naam (e.g., Feb, Mar)
    display_months = "Current Session"
    if txn.remarks and "[" in txn.remarks and "]" in txn.remarks:
        try:
            display_months = txn.remarks.split("]")[0].replace("[", "")
        except: pass

    # ✅ 2. Breakup Extraction: Table ke items
    breakup_list = []
    if txn.remarks and "RECEIPT_DATA:" in txn.remarks:
        try:
            json_str = txn.remarks.split("RECEIPT_DATA:")[1].split(" | ")[0]
            breakup_list = json.loads(json_str)
        except: pass
    
    # ✅ 3. Previous Due Logic: Agar extra amount pay kiya hai
    if txn.amount_paid > txn.net_payable:
        prev_paid = txn.amount_paid - txn.net_payable
        breakup_list.append({"head": "Previous Outstanding Due", "month": "Prev", "amount": prev_paid})

    return {
        "txn": txn, 
        "student": student, 
        "breakup": breakup_list, 
        "formatted_months": display_months
    }

# ✅ 4. History API (Fixed Error loading data)
@router.get("/history")
def get_transaction_history(db: Session = Depends(get_db)):
    try:
        return db.query(FeeTransaction).order_by(FeeTransaction.id.desc()).options(
            joinedload(FeeTransaction.student).joinedload(Student.class_val)
        ).all()
    except Exception as e:
        return []