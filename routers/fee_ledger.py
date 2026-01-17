"""
Fee Collection Router - Transaction-Based Ledger System
With auto-due detection and unique receipt generation
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from database import get_db
from models.students import Student
from models.masters import ClassMaster, TransportMaster
from models.fee_models import FeeHeadMaster, FeeStructure, StudentFeeLedger, ReceiptCounter
from models.paid_history import PaidMonth
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import datetime
import json

router = APIRouter(prefix="/api/v1/fee-ledger", tags=["Fee Ledger System"])

# =====================
# PYDANTIC SCHEMAS
# =====================

class FeeHeadCreate(BaseModel):
    head_name: str
    frequency: str = "Monthly"

class FeeStructureCreate(BaseModel):
    class_id: int
    fee_head_id: int
    amount: float

class DuesRequest(BaseModel):
    student_id: int
    months: List[str] = []  # Empty means current month only

class PaymentRequest(BaseModel):
    student_id: int
    selected_months: List[str]
    payment_mode: str
    discount: float = 0.0
    fine: float = 0.0
    amount_received: float
    remarks: Optional[str] = None
    items: List[dict] = []  # Fee breakdown items

# =====================
# HELPER FUNCTIONS
# =====================

MONTH_ORDER = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]

def get_current_academic_month():
    """Get current month in academic format (Apr-Mar)"""
    today = datetime.date.today()
    month_map = {
        4: "Apr", 5: "May", 6: "Jun", 7: "Jul", 8: "Aug", 9: "Sep",
        10: "Oct", 11: "Nov", 12: "Dec", 1: "Jan", 2: "Feb", 3: "Mar"
    }
    return month_map.get(today.month, "Apr")

def get_months_till_current():
    """Get all months from Apr to current month"""
    current = get_current_academic_month()
    current_idx = MONTH_ORDER.index(current)
    return MONTH_ORDER[:current_idx + 1]

def generate_receipt_number(db: Session) -> str:
    """Generate unique receipt number: REC-2025-0001"""
    current_year = datetime.date.today().year
    
    # Get or create counter for current year
    counter = db.query(ReceiptCounter).filter(ReceiptCounter.year == current_year).first()
    
    if not counter:
        counter = ReceiptCounter(year=current_year, last_number=0)
        db.add(counter)
    
    counter.last_number += 1
    db.flush()
    
    return f"REC-{current_year}-{str(counter.last_number).zfill(4)}"

def number_to_words(num):
    """Convert number to words (Indian format)"""
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
            "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
            "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    
    if num == 0:
        return "Zero"
    
    if num < 0:
        return "Minus " + number_to_words(-num)
    
    result = ""
    
    if num >= 10000000:  # Crore
        result += number_to_words(num // 10000000) + " Crore "
        num %= 10000000
    
    if num >= 100000:  # Lakh
        result += number_to_words(num // 100000) + " Lakh "
        num %= 100000
    
    if num >= 1000:  # Thousand
        result += number_to_words(num // 1000) + " Thousand "
        num %= 1000
    
    if num >= 100:  # Hundred
        result += ones[num // 100] + " Hundred "
        num %= 100
    
    if num >= 20:
        result += tens[num // 10] + " "
        num %= 10
    
    if num > 0:
        result += ones[num] + " "
    
    return result.strip() + " Only"


# =====================
# FEE HEAD MASTER APIs
# =====================

@router.get("/heads")
def get_fee_heads(db: Session = Depends(get_db)):
    """Get all active fee heads"""
    return db.query(FeeHeadMaster).filter(FeeHeadMaster.is_active == True).all()

@router.post("/heads")
def create_fee_head(data: FeeHeadCreate, db: Session = Depends(get_db)):
    """Create new fee head"""
    new_head = FeeHeadMaster(head_name=data.head_name, frequency=data.frequency)
    db.add(new_head)
    db.commit()
    return {"message": "Fee Head Created", "id": new_head.id}

@router.delete("/heads/{head_id}")
def delete_fee_head(head_id: int, db: Session = Depends(get_db)):
    """Soft delete fee head"""
    head = db.query(FeeHeadMaster).filter(FeeHeadMaster.id == head_id).first()
    if head:
        head.is_active = False
        db.commit()
    return {"message": "Deleted"}


# =====================
# FEE STRUCTURE APIs
# =====================

@router.get("/structure")
def get_fee_structure(db: Session = Depends(get_db)):
    """Get all fee structures with relationships"""
    return db.query(FeeStructure).options(
        joinedload(FeeStructure.class_val),
        joinedload(FeeStructure.fee_head_val)
    ).filter(FeeStructure.is_active == True).all()

@router.post("/structure")
def create_fee_structure(data: FeeStructureCreate, db: Session = Depends(get_db)):
    """Create or update fee structure"""
    existing = db.query(FeeStructure).filter(
        FeeStructure.class_id == data.class_id,
        FeeStructure.fee_head_id == data.fee_head_id
    ).first()
    
    if existing:
        existing.amount = data.amount
    else:
        db.add(FeeStructure(
            class_id=data.class_id,
            fee_head_id=data.fee_head_id,
            amount=data.amount
        ))
    
    db.commit()
    return {"message": "Saved"}

@router.post("/structure/bulk")
def save_bulk_structure(structures: List[FeeStructureCreate], db: Session = Depends(get_db)):
    """Bulk save fee structures"""
    for s in structures:
        existing = db.query(FeeStructure).filter(
            FeeStructure.class_id == s.class_id,
            FeeStructure.fee_head_id == s.fee_head_id
        ).first()
        
        if existing:
            existing.amount = s.amount
        elif s.amount > 0:
            db.add(FeeStructure(
                class_id=s.class_id,
                fee_head_id=s.fee_head_id,
                amount=s.amount
            ))
    
    db.commit()
    return {"message": "Bulk Saved"}


# =====================
# DUES CALCULATION API
# =====================

@router.get("/dues/{student_id}")
def get_student_dues(student_id: int, db: Session = Depends(get_db)):
    """
    Calculate total dues for a student
    - Uses FeePlan table (existing Fee Plan admin UI)
    - Automatically includes current month if not paid
    - Shows all unpaid months from Apr to current
    """
    from models.fees import FeePlan, FeeItem
    from models.masters import LedgerMaster
    
    student = db.query(Student).options(
        joinedload(Student.class_val),
        joinedload(Student.section_val),
        joinedload(Student.transport_val)
    ).filter(Student.id == student_id).first()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Get months till current
    months_till_now = get_months_till_current()
    
    # Get already paid months from NEW ledger
    paid_ledgers = db.query(StudentFeeLedger).filter(
        StudentFeeLedger.student_id == student_id
    ).all()
    
    paid_months = []
    for ledger in paid_ledgers:
        if ledger.months_paid:
            paid_months.extend(ledger.months_paid)
    
    # Also check OLD paid_months table
    old_paid = db.query(PaidMonth).filter(PaidMonth.student_id == student_id).all()
    for p in old_paid:
        if p.month not in paid_months:
            paid_months.append(p.month)
    
    # ✅ FIX: Get fee plans from OLD FeePlan table (this is where admin creates data)
    fee_plans = db.query(FeePlan).options(
        joinedload(FeePlan.fee_item_val)
    ).filter(
        FeePlan.class_id == student.class_id,
        FeePlan.amount > 0
    ).all()
    
    dues_list = []
    total_due = 0.0
    
    # Month mapping for FeeItem boolean columns
    month_col_map = {
        "Apr": "apr", "May": "may", "Jun": "jun", "Jul": "jul",
        "Aug": "aug", "Sep": "sep", "Oct": "oct", "Nov": "nov",
        "Dec": "dec", "Jan": "jan", "Feb": "feb", "Mar": "mar"
    }
    
    for month in months_till_now:
        is_paid = month in paid_months
        col_name = month_col_map.get(month, "apr")
        
        for fp in fee_plans:
            # Check if this fee is applicable for this month
            fee_item = fp.fee_item_val
            if fee_item:
                # Get fee name from LedgerMaster
                ledger = db.query(LedgerMaster).filter(LedgerMaster.id == fee_item.ledger_id).first()
                fee_name = ledger.ledger_name if ledger else "School Fee"
                
                # Check if this month is marked for this fee item
                is_applicable = getattr(fee_item, col_name, True)  # Default True if column missing
                
                if is_applicable and fp.amount > 0:
                    dues_list.append({
                        "fee_head": fee_name,
                        "fee_head_id": fp.id,
                        "month": month,
                        "amount": fp.amount,
                        "status": "Paid" if is_paid else "Due"
                    })
                    if not is_paid:
                        total_due += fp.amount
        
        # Add transport fee if opted
        if student.transport_opted and student.pickup_point_id:
            transport = db.query(TransportMaster).filter(
                TransportMaster.id == student.pickup_point_id
            ).first()
            if transport:
                dues_list.append({
                    "fee_head": "Transport Fee",
                    "fee_head_id": 0,
                    "month": month,
                    "amount": transport.monthly_charge,
                    "status": "Paid" if is_paid else "Due"
                })
                if not is_paid:
                    total_due += transport.monthly_charge
    
    return {
        "student": {
            "id": student.id,
            "name": student.student_name,
            "father_name": student.father_name,
            "class_name": student.class_val.class_name if student.class_val else "-",
            "section_name": student.section_val.section_name if student.section_val else "",
            "admission_no": student.admission_no,
            "mobile": student.mobile_number,
            "photo": student.student_photo,
            "current_balance": student.current_balance or 0
        },
        "dues": dues_list,
        "total_due": total_due,
        "paid_months": paid_months,
        "current_month": get_current_academic_month()
    }


@router.post("/dues/calculate")
def calculate_selected_dues(req: DuesRequest, db: Session = Depends(get_db)):
    """Calculate dues for specific selected months"""
    student = db.query(Student).filter(Student.id == req.student_id).first()
    if not student:
        return {"dues": [], "total": 0}
    
    # Get paid months
    paid_ledgers = db.query(StudentFeeLedger).filter(
        StudentFeeLedger.student_id == req.student_id
    ).all()
    
    paid_months = []
    for ledger in paid_ledgers:
        if ledger.months_paid:
            paid_months.extend(ledger.months_paid)
    
    old_paid = db.query(PaidMonth).filter(PaidMonth.student_id == req.student_id).all()
    for p in old_paid:
        if p.month not in paid_months:
            paid_months.append(p.month)
    
    # Get fee structure
    fee_structures = db.query(FeeStructure).options(
        joinedload(FeeStructure.fee_head_val)
    ).filter(
        FeeStructure.class_id == student.class_id,
        FeeStructure.is_active == True
    ).all()
    
    dues_list = []
    total = 0.0
    
    months_to_check = req.months if req.months else [get_current_academic_month()]
    
    for month in months_to_check:
        is_paid = month in paid_months
        
        for fs in fee_structures:
            if fs.amount > 0:
                dues_list.append({
                    "fee_head": fs.fee_head_val.head_name if fs.fee_head_val else "Unknown",
                    "month": month,
                    "amount": fs.amount,
                    "status": "Paid" if is_paid else "Due"
                })
                if not is_paid:
                    total += fs.amount
        
        if student.transport_opted and student.pickup_point_id:
            transport = db.query(TransportMaster).filter(
                TransportMaster.id == student.pickup_point_id
            ).first()
            if transport:
                dues_list.append({
                    "fee_head": "Transport Fee",
                    "month": month,
                    "amount": transport.monthly_charge,
                    "status": "Paid" if is_paid else "Due"
                })
                if not is_paid:
                    total += transport.monthly_charge
    
    return {
        "dues": dues_list,
        "total": total,
        "old_balance": student.current_balance or 0
    }


# =====================
# PAYMENT COLLECTION API
# =====================

@router.post("/collect")
def collect_fee(pay: PaymentRequest, db: Session = Depends(get_db)):
    """
    Process fee collection and generate receipt
    """
    student = db.query(Student).filter(Student.id == pay.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Generate unique receipt number
    receipt_no = generate_receipt_number(db)
    
    # Calculate totals
    item_total = sum(item.get("amount", 0) for item in pay.items)
    net_amount = item_total + pay.fine - pay.discount
    
    # Build payment breakdown JSON
    breakdown = {}
    for item in pay.items:
        head = item.get("head", "Fee")
        month = item.get("month", "")
        key = f"{head} ({month})" if month else head
        breakdown[key] = item.get("amount", 0)
    
    # Create ledger entry
    ledger = StudentFeeLedger(
        student_id=pay.student_id,
        receipt_no=receipt_no,
        transaction_date=datetime.date.today(),
        months_paid=pay.selected_months,
        total_amount=item_total,
        discount=pay.discount,
        fine=pay.fine,
        paid_amount=pay.amount_received,
        payment_mode=pay.payment_mode,
        remarks=pay.remarks,
        payment_breakdown=breakdown
    )
    db.add(ledger)
    
    # Update old paid_months table for backward compatibility
    for month in pay.selected_months:
        exists = db.query(PaidMonth).filter(
            PaidMonth.student_id == pay.student_id,
            PaidMonth.month == month
        ).first()
        if not exists:
            db.add(PaidMonth(student_id=pay.student_id, month=month, session="2025-26"))
    
    # Update student balance
    balance = net_amount - pay.amount_received
    student.current_balance = (student.current_balance or 0) + balance
    
    db.commit()
    
    return {
        "message": "Payment Successful",
        "receipt_no": receipt_no,
        "ledger_id": ledger.id
    }


# =====================
# RECEIPT API
# =====================

@router.get("/receipt/{receipt_no}")
def get_receipt(receipt_no: str, db: Session = Depends(get_db)):
    """Get receipt details for printing"""
    ledger = db.query(StudentFeeLedger).filter(
        StudentFeeLedger.receipt_no == receipt_no
    ).first()
    
    if not ledger:
        # Try to find by ID (backward compatibility)
        try:
            ledger_id = int(receipt_no)
            ledger = db.query(StudentFeeLedger).filter(
                StudentFeeLedger.id == ledger_id
            ).first()
        except:
            pass
    
    if not ledger:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    student = db.query(Student).options(
        joinedload(Student.class_val),
        joinedload(Student.section_val)
    ).filter(Student.id == ledger.student_id).first()
    
    # Build items list from breakdown
    items = []
    if ledger.payment_breakdown:
        idx = 1
        for key, amount in ledger.payment_breakdown.items():
            items.append({
                "sno": idx,
                "head": key,
                "amount": amount
            })
            idx += 1
    
    return {
        "receipt_no": ledger.receipt_no,
        "date": str(ledger.transaction_date),
        "student": {
            "name": student.student_name if student else "-",
            "father_name": student.father_name if student else "-",
            "admission_no": student.admission_no if student else "-",
            "class_name": student.class_val.class_name if student and student.class_val else "-",
            "section_name": student.section_val.section_name if student and student.section_val else ""
        },
        "months": ledger.months_paid,
        "items": items,
        "total_amount": ledger.total_amount,
        "discount": ledger.discount,
        "fine": ledger.fine,
        "paid_amount": ledger.paid_amount,
        "payment_mode": ledger.payment_mode,
        "amount_in_words": number_to_words(int(ledger.paid_amount))
    }


# =====================
# HISTORY APIs
# =====================

@router.get("/history/{student_id}")
def get_student_history(student_id: int, db: Session = Depends(get_db)):
    """Get payment history for a student"""
    ledgers = db.query(StudentFeeLedger).filter(
        StudentFeeLedger.student_id == student_id
    ).order_by(StudentFeeLedger.id.desc()).all()
    
    return [
        {
            "id": l.id,
            "receipt_no": l.receipt_no,
            "date": str(l.transaction_date),
            "months": l.months_paid,
            "paid_amount": l.paid_amount,
            "payment_mode": l.payment_mode
        }
        for l in ledgers
    ]

@router.get("/all-transactions")
def get_all_transactions(db: Session = Depends(get_db)):
    """Get all transactions for admin view"""
    ledgers = db.query(StudentFeeLedger).order_by(StudentFeeLedger.id.desc()).limit(100).all()
    
    result = []
    for l in ledgers:
        # Fetch student with class info
        student = db.query(Student).options(
            joinedload(Student.class_val)
        ).filter(Student.id == l.student_id).first()
        
        result.append({
            "id": l.id,
            "receipt_no": l.receipt_no,
            "date": str(l.transaction_date),
            "student_name": student.student_name if student else "-",
            "admission_no": student.admission_no if student else "-",
            "class_name": student.class_val.class_name if student and student.class_val else "-",
            "months": l.months_paid,
            "paid_amount": l.paid_amount,
            "payment_mode": l.payment_mode
        })
    
    return result

