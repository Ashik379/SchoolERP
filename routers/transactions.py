from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models.students import Student
from models.fees import FeePlan, FeeReceiptConfig
from models.transactions import FeeTransaction
from models.system import SystemSetting
from pydantic import BaseModel
from typing import List, Optional
from datetime import date

router = APIRouter(prefix="/api/v1/collection", tags=["Fee Collection"])

# --- Schemas ---
class PaymentRequest(BaseModel):
    student_id: int
    amount_paid: float
    payment_mode: str  # CASH, UPI, BANK
    remarks: Optional[str] = None

class DueResponse(BaseModel):
    student_name: str
    class_name: str
    total_fee_assigned: float
    total_paid_so_far: float
    current_balance: float

# --- HELPER: Generate Receipt No (REC-2025-1001) ---
def get_next_receipt_no(db: Session, session: str):
    config = db.query(FeeReceiptConfig).filter_by(academic_session=session).first()
    if not config:
        # Auto-create config if missing
        config = FeeReceiptConfig(academic_session=session, starting_no=1001, current_receipt_no=1001)
        db.add(config)
        db.commit()
    
    # Generate String
    rec_no = f"{config.receipt_prefix}-{session.split('-')[0]}-{config.current_receipt_no}"
    
    # Increment counter
    config.current_receipt_no += 1
    db.commit()
    
    return rec_no

# --- API 1: CHECK DUES (Kitna paisa baaki hai?) ---
@router.get("/dues/{student_id}", response_model=DueResponse)
def check_student_dues(student_id: int, db: Session = Depends(get_db)):
    # 1. Get Student
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    current_session = student.academic_session

    # 2. Calculate TOTAL Fee assigned to his Class
    # (Sum of all Fee Plans for Class 10)
    total_assigned = db.query(func.sum(FeePlan.amount))\
        .filter(FeePlan.class_id == student.class_id, FeePlan.academic_session == current_session)\
        .scalar() or 0.0

    # 3. Add Transport Fee if opted
    if student.transport_opted and student.pickup_point_id:
        # Assuming 12 months for simple calculation logic
        # In real world, we check "Transport Fee" head specifically
        # For this demo, we will keep it simple based on Module 2
        transport = student.transport_val
        if transport:
            total_assigned += (transport.monthly_charge * 12)

    # 4. Calculate TOTAL Paid so far
    total_paid = db.query(func.sum(FeeTransaction.amount_paid))\
        .filter(FeeTransaction.student_id == student_id, FeeTransaction.academic_session == current_session)\
        .scalar() or 0.0

    return {
        "student_name": student.student_name,
        "class_name": f"{student.class_val.class_name} - {student.section_val.section_name}",
        "total_fee_assigned": total_assigned,
        "total_paid_so_far": total_paid,
        "current_balance": total_assigned - total_paid
    }

# --- API 2: PAY FEES (Paisa Jama Karo) ---
@router.post("/pay")
def submit_payment(payment: PaymentRequest, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == payment.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # 1. Generate Receipt No
    new_receipt = get_next_receipt_no(db, student.academic_session)

    # 2. Save Transaction
    transaction = FeeTransaction(
        receipt_no=new_receipt,
        student_id=payment.student_id,
        academic_session=student.academic_session,
        amount_paid=payment.amount_paid,
        payment_mode=payment.payment_mode,
        remarks=payment.remarks
    )
    
    db.add(transaction)
    db.commit()
    
    return {
        "status": "Success",
        "receipt_no": new_receipt,
        "amount_paid": payment.amount_paid,
        "balance_remaining": "Check Dues API"
    }

# --- API 3: TRANSACTION HISTORY ---
@router.get("/history/{student_id}")
def payment_history(student_id: int, db: Session = Depends(get_db)):
    return db.query(FeeTransaction).filter(FeeTransaction.student_id == student_id).all()