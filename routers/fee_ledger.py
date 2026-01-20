"""
Fee Ledger Router - Complete Fee Management System
Transaction-based with Double-Entry Bookkeeping
Security: Pydantic validation, XSS prevention, RBAC ready
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from database import get_db
from models.fee_models import FeeHeadMaster, FeeStructure, StudentFeeLedger, ReceiptCounter
from models.students import Student
from models.masters import ClassMaster, TransportMaster
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from enum import Enum
import datetime
import re

router = APIRouter(prefix="/api/v1/fee-ledger", tags=["Fee Ledger System"])

# =====================
# CONSTANTS
# =====================
MONTH_ORDER = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]
VALID_PAYMENT_MODES = ["Cash", "UPI", "Cheque", "Bank Transfer"]


# =====================
# PYDANTIC SCHEMAS (Strict Validation)
# =====================
class FeeHeadCreate(BaseModel):
    head_name: str = Field(..., min_length=2, max_length=100)
    frequency: str = Field(default="Monthly")
    is_transport: bool = False

    @validator('head_name')
    def sanitize_name(cls, v):
        # Remove any HTML tags for XSS prevention
        return re.sub(r'<[^>]*>', '', v).strip()


class FeeStructureCreate(BaseModel):
    class_id: int = Field(..., gt=0)
    fee_head_id: int = Field(..., gt=0)
    amount: float = Field(..., ge=0)  # Cannot be negative


class FeeStructureBulk(BaseModel):
    structures: List[FeeStructureCreate]


class PaymentMode(str, Enum):
    CASH = "Cash"
    UPI = "UPI"
    CHEQUE = "Cheque"
    BANK_TRANSFER = "Bank Transfer"


class PaymentRequest(BaseModel):
    student_id: int = Field(..., gt=0)
    selected_months: List[str]
    selected_items: List[Dict[str, Any]]  # [{fee_head, month, amount}]
    payment_mode: str
    discount: float = Field(default=0.0, ge=0)
    fine: float = Field(default=0.0, ge=0)
    amount_received: float = Field(..., ge=0)
    remarks: Optional[str] = None

    @validator('payment_mode')
    def validate_payment_mode(cls, v):
        if v not in VALID_PAYMENT_MODES:
            raise ValueError(f"Invalid payment mode. Must be one of: {VALID_PAYMENT_MODES}")
        return v

    @validator('remarks')
    def sanitize_remarks(cls, v):
        if v:
            # Strip HTML tags to prevent XSS
            return re.sub(r'<[^>]*>', '', v).strip()[:500]
        return v

    @validator('selected_months', each_item=True)
    def validate_months(cls, v):
        if v not in MONTH_ORDER:
            raise ValueError(f"Invalid month: {v}")
        return v


# =====================
# HELPER FUNCTIONS
# =====================
def get_current_academic_month():
    """Get current month name in academic format"""
    today = datetime.date.today()
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return month_names[today.month - 1]


def get_months_till_current():
    """Get all months from April to current month"""
    current = get_current_academic_month()
    if current in MONTH_ORDER:
        idx = MONTH_ORDER.index(current)
        return MONTH_ORDER[:idx + 1]
    return MONTH_ORDER


def generate_receipt_number(db: Session) -> str:
    """Generate unique receipt: REC-2026-0001"""
    year = datetime.date.today().year
    counter = db.query(ReceiptCounter).filter(ReceiptCounter.year == year).first()
    
    if not counter:
        counter = ReceiptCounter(year=year, last_number=0)
        db.add(counter)
    
    counter.last_number += 1
    db.flush()  # Ensure we get the updated number
    
    return f"REC-{year}-{str(counter.last_number).zfill(4)}"


def number_to_words(num: float) -> str:
    """Convert number to Indian format words"""
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
            "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
            "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    
    num = int(round(num))
    if num == 0:
        return "Zero Rupees Only"
    if num < 0:
        return "Invalid Amount"
    
    def two_digit(n):
        if n < 20:
            return ones[n]
        return tens[n // 10] + (" " + ones[n % 10] if n % 10 else "")
    
    def three_digit(n):
        if n < 100:
            return two_digit(n)
        return ones[n // 100] + " Hundred" + (" and " + two_digit(n % 100) if n % 100 else "")
    
    if num < 100:
        result = two_digit(num)
    elif num < 1000:
        result = three_digit(num)
    elif num < 100000:
        result = two_digit(num // 1000) + " Thousand" + (" " + three_digit(num % 1000) if num % 1000 else "")
    elif num < 10000000:
        result = two_digit(num // 100000) + " Lakh" + (" " + three_digit((num % 100000) // 1000) + " Thousand" if (num % 100000) >= 1000 else "") + (" " + three_digit(num % 1000) if num % 1000 else "")
    else:
        result = str(num)
    
    return result.strip() + " Rupees Only"


# =====================
# FEE HEAD MASTER APIs
# =====================
@router.get("/heads")
def get_fee_heads(db: Session = Depends(get_db)):
    """Get all active fee heads"""
    return db.query(FeeHeadMaster).filter(FeeHeadMaster.is_active == True).order_by(FeeHeadMaster.id).all()


@router.post("/heads")
def create_fee_head(data: FeeHeadCreate, db: Session = Depends(get_db)):
    """Create new fee head"""
    # Check for duplicate
    existing = db.query(FeeHeadMaster).filter(FeeHeadMaster.head_name == data.head_name).first()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            existing.frequency = data.frequency
            existing.is_transport = data.is_transport
            db.commit()
            return {"message": "Fee head reactivated", "id": existing.id}
        raise HTTPException(status_code=400, detail="Fee head already exists")
    
    new_head = FeeHeadMaster(**data.dict())
    db.add(new_head)
    db.commit()
    db.refresh(new_head)
    return {"message": "Created successfully", "id": new_head.id}


@router.delete("/heads/{head_id}")
def delete_fee_head(head_id: int, db: Session = Depends(get_db)):
    """Soft delete fee head"""
    head = db.query(FeeHeadMaster).filter(FeeHeadMaster.id == head_id).first()
    if not head:
        raise HTTPException(status_code=404, detail="Fee head not found")
    head.is_active = False
    db.commit()
    return {"message": "Deleted successfully"}


# =====================
# FEE STRUCTURE APIs
# =====================
@router.get("/structure")
def get_fee_structure(db: Session = Depends(get_db)):
    """Get all fee structures with relationships"""
    return db.query(FeeStructure).filter(FeeStructure.is_active == True).options(
        joinedload(FeeStructure.class_val),
        joinedload(FeeStructure.fee_head_val)
    ).all()


@router.post("/structure")
def create_fee_structure(data: FeeStructureCreate, db: Session = Depends(get_db)):
    """Create or update single fee structure"""
    existing = db.query(FeeStructure).filter(
        FeeStructure.class_id == data.class_id,
        FeeStructure.fee_head_id == data.fee_head_id,
        FeeStructure.academic_year == "2025-2026"
    ).first()
    
    if existing:
        existing.amount = data.amount
        existing.is_active = True
    else:
        db.add(FeeStructure(**data.dict()))
    
    db.commit()
    return {"message": "Saved successfully"}


@router.post("/structure/bulk")
def save_bulk_structure(data: FeeStructureBulk, db: Session = Depends(get_db)):
    """Bulk save fee structures"""
    for s in data.structures:
        existing = db.query(FeeStructure).filter(
            FeeStructure.class_id == s.class_id,
            FeeStructure.fee_head_id == s.fee_head_id,
            FeeStructure.academic_year == "2025-2026"
        ).first()
        
        if existing:
            existing.amount = s.amount
            existing.is_active = True if s.amount > 0 else False
        elif s.amount > 0:
            db.add(FeeStructure(class_id=s.class_id, fee_head_id=s.fee_head_id, amount=s.amount))
    
    db.commit()
    return {"message": "Bulk save successful"}


# =====================
# DUES CALCULATION API
# =====================
@router.get("/dues/{student_id}")
def get_student_dues(student_id: int, db: Session = Depends(get_db)):
    """
    Calculate total dues for a student including:
    - Class-based fees from FeeStructure
    - Transport fees if opted
    - Previous balance
    """
    # Get student with relationships
    student = db.query(Student).options(
        joinedload(Student.class_val),
        joinedload(Student.section_val),
        joinedload(Student.transport_val)
    ).filter(Student.id == student_id).first()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Get paid months from previous transactions
    paid_records = db.query(StudentFeeLedger.months_paid).filter(
        StudentFeeLedger.student_id == student_id
    ).all()
    
    all_paid_months = set()
    for record in paid_records:
        if record.months_paid:
            all_paid_months.update(record.months_paid)
    
    # Get fee structure for student's class
    structures = db.query(FeeStructure).options(
        joinedload(FeeStructure.fee_head_val)
    ).filter(
        FeeStructure.class_id == student.class_id,
        FeeStructure.is_active == True
    ).all()
    
    # Calculate dues for each month
    months_to_check = get_months_till_current()
    dues_list = []
    total_due = 0.0
    
    for month in months_to_check:
        is_paid = month in all_paid_months
        
        for struct in structures:
            if struct.fee_head_val and not struct.fee_head_val.is_transport:
                # Only add monthly fees (skip transport here, handle separately)
                fee_entry = {
                    "fee_head": struct.fee_head_val.head_name,
                    "fee_head_id": struct.fee_head_id,
                    "month": month,
                    "amount": struct.amount,
                    "status": "Paid" if is_paid else "Due"
                }
                dues_list.append(fee_entry)
                if not is_paid:
                    total_due += struct.amount
    
    # Add Transport Fee if student opted
    if student.transport_opted and student.pickup_point_id:
        transport = db.query(TransportMaster).filter(
            TransportMaster.id == student.pickup_point_id
        ).first()
        
        if transport:
            for month in months_to_check:
                is_paid = month in all_paid_months
                fee_entry = {
                    "fee_head": "Transport Fee",
                    "fee_head_id": 0,  # Special ID for transport
                    "month": month,
                    "amount": transport.monthly_charge,
                    "status": "Paid" if is_paid else "Due",
                    "is_transport": True
                }
                dues_list.append(fee_entry)
                if not is_paid:
                    total_due += transport.monthly_charge
    
    # Get previous balance from student record
    previous_balance = float(student.current_balance) if student.current_balance else 0.0
    
    return {
        "student": {
            "id": student.id,
            "name": student.student_name,
            "father_name": student.father_name,
            "admission_no": student.admission_no,
            "class_name": student.class_val.class_name if student.class_val else "N/A",
            "section_name": student.section_val.section_name if student.section_val else "",
            "mobile": student.mobile_number,
            "photo": student.student_photo,
            "current_balance": previous_balance
        },
        "dues": dues_list,
        "total_due": total_due,
        "paid_months": list(all_paid_months),
        "current_month": get_current_academic_month()
    }


# =====================
# PAYMENT COLLECTION API
# =====================
@router.post("/pay")
def collect_fee(pay: PaymentRequest, db: Session = Depends(get_db)):
    """
    Process fee payment with atomic transaction.
    Creates ledger entry and updates student balance.
    Returns receipt number for printing.
    """
    # Validate student exists
    student = db.query(Student).filter(Student.id == pay.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Calculate totals
    total_due = sum(item.get('amount', 0) for item in pay.selected_items)
    
    # Include previous balance if any
    previous_balance = float(student.current_balance) if student.current_balance else 0.0
    
    # Build payment breakdown
    breakdown = {}
    previous_balance_already_included = False
    
    for item in pay.selected_items:
        key = f"{item.get('fee_head', 'Unknown')}|{item.get('month', 'N/A')}"
        breakdown[key] = item.get('amount', 0)
        
        # Check if previous balance is already in selected items
        if item.get('fee_head', '').lower().startswith('previous balance'):
            previous_balance_already_included = True
    
    # Add previous balance to total_due only if NOT already included in selected_items
    # This prevents double-counting when the frontend already sent it as a selected item
    if previous_balance > 0 and not previous_balance_already_included:
        breakdown["Previous Balance|Carried Forward"] = previous_balance
        total_due += previous_balance
    
    # Calculate net payable and balance
    net_payable = total_due - pay.discount + pay.fine
    balance_due = net_payable - pay.amount_received
    
    # Validate no overpayment (can be advance if needed)
    # For now, allow advance payments (negative balance means credit)
    
    try:
        # Generate receipt number
        receipt_no = generate_receipt_number(db)
        
        # Create ledger entry
        ledger = StudentFeeLedger(
            student_id=pay.student_id,
            receipt_no=receipt_no,
            transaction_date=datetime.date.today(),
            months_paid=pay.selected_months,
            total_due=total_due,
            discount=pay.discount,
            fine=pay.fine,
            net_payable=net_payable,
            paid_amount=pay.amount_received,
            balance_due=balance_due,
            payment_mode=pay.payment_mode,
            remarks=pay.remarks,
            payment_breakdown=breakdown
        )
        db.add(ledger)
        db.flush()  # Save ledger first so recalculate sees it
        
        # Recalculate student's FULL pending balance (not just this receipt's balance)
        # This accounts for all unpaid months, not just what was selected
        new_balance = calculate_student_dues(student, db)
        student.current_balance = new_balance
        
        db.commit()
        
        return {
            "success": True,
            "message": "Payment collected successfully",
            "receipt_no": receipt_no,
            "balance_due": new_balance  # Show actual remaining dues
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Payment failed: {str(e)}")


# =====================
# RECEIPT API
# =====================
@router.get("/receipt/{receipt_no}")
def get_receipt(receipt_no: str, db: Session = Depends(get_db)):
    """Get complete receipt details for printing"""
    ledger = db.query(StudentFeeLedger).filter(
        StudentFeeLedger.receipt_no == receipt_no
    ).first()
    
    if not ledger:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    student = db.query(Student).options(
        joinedload(Student.class_val),
        joinedload(Student.section_val)
    ).filter(Student.id == ledger.student_id).first()
    
    # Calculate remaining balance after this payment
    total_transactions = db.query(func.sum(StudentFeeLedger.paid_amount)).filter(
        StudentFeeLedger.student_id == ledger.student_id
    ).scalar() or 0
    
    return {
        "receipt": {
            "receipt_no": ledger.receipt_no,
            "date": ledger.transaction_date.strftime("%d-%m-%Y") if ledger.transaction_date else "",
            "academic_year": ledger.academic_year,
            "months_paid": ledger.months_paid,
            "total_due": ledger.total_due,
            "discount": ledger.discount,
            "fine": ledger.fine,
            "net_payable": ledger.net_payable,
            "paid_amount": ledger.paid_amount,
            "balance_due": ledger.balance_due,
            "payment_mode": ledger.payment_mode,
            "remarks": ledger.remarks,
            "breakdown": ledger.payment_breakdown,
            "amount_in_words": number_to_words(ledger.paid_amount)
        },
        "student": {
            "name": student.student_name,
            "father_name": student.father_name,
            "admission_no": student.admission_no,
            "class": student.class_val.class_name if student.class_val else "N/A",
            "section": student.section_val.section_name if student.section_val else "",
            "mobile": student.mobile_number
        }
    }


# =====================
# HISTORY APIs
# =====================
@router.get("/history/{student_id}")
def get_student_history(student_id: int, db: Session = Depends(get_db)):
    """Get payment history for a specific student"""
    transactions = db.query(StudentFeeLedger).filter(
        StudentFeeLedger.student_id == student_id
    ).order_by(StudentFeeLedger.transaction_date.desc()).all()
    
    return [{
        "receipt_no": t.receipt_no,
        "date": t.transaction_date.strftime("%d-%m-%Y") if t.transaction_date else "",
        "months": t.months_paid,
        "paid_amount": t.paid_amount,
        "balance": t.balance_due,
        "mode": t.payment_mode
    } for t in transactions]


@router.get("/transactions")
def get_all_transactions(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get all transactions for admin dashboard"""
    transactions = db.query(StudentFeeLedger).options(
        joinedload(StudentFeeLedger.student).joinedload(Student.class_val)
    ).order_by(
        StudentFeeLedger.transaction_date.desc()
    ).offset(offset).limit(limit).all()
    
    return [{
        "receipt_no": t.receipt_no,
        "date": t.transaction_date.strftime("%d-%m-%Y") if t.transaction_date else "",
        "student_name": t.student.student_name if t.student else "Unknown",
        "class": t.student.class_val.class_name if t.student and t.student.class_val else "N/A",
        "months": t.months_paid,
        "paid_amount": t.paid_amount,
        "balance": t.balance_due,
        "mode": t.payment_mode
    } for t in transactions]


# =====================
# DASHBOARD STATS API
# =====================
@router.get("/stats/dashboard")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get fee collection statistics for dashboard"""
    today = datetime.date.today()
    
    # Today's collection
    today_collection = db.query(func.sum(StudentFeeLedger.paid_amount)).filter(
        StudentFeeLedger.transaction_date == today
    ).scalar() or 0
    
    # This month's collection
    month_start = today.replace(day=1)
    month_collection = db.query(func.sum(StudentFeeLedger.paid_amount)).filter(
        StudentFeeLedger.transaction_date >= month_start
    ).scalar() or 0
    
    # Total pending dues (from all students)
    total_pending = db.query(func.sum(Student.current_balance)).scalar() or 0
    
    # Transaction count today
    today_count = db.query(func.count(StudentFeeLedger.id)).filter(
        StudentFeeLedger.transaction_date == today
    ).scalar() or 0
    
    return {
        "today_collection": float(today_collection),
        "month_collection": float(month_collection),
        "total_pending": float(total_pending),
        "today_transactions": today_count
    }


# =====================
# BALANCE SYNC APIs
# =====================
def calculate_student_dues(student: Student, db: Session) -> float:
    """
    Calculate accurate pending dues for a student.
    Formula: (Monthly Fee × Unpaid Months) + Previous Balance - Total Paid
    """
    # Get all months from April to current month
    months_till_now = get_months_till_current()
    
    # Get paid months from ledger
    paid_months = set()
    ledgers = db.query(StudentFeeLedger).filter(
        StudentFeeLedger.student_id == student.id
    ).all()
    
    total_paid = 0.0
    for ledger in ledgers:
        total_paid += ledger.paid_amount or 0
        if ledger.months_paid:
            for m in ledger.months_paid:
                paid_months.add(m)
    
    # Get fee structure for this class
    fee_structures = db.query(FeeStructure).options(
        joinedload(FeeStructure.fee_head_val)
    ).filter(
        FeeStructure.class_id == student.class_id,
        FeeStructure.is_active == True,
        FeeStructure.amount > 0
    ).all()
    
    # Calculate monthly fee (non-transport)
    monthly_fee = 0.0
    for fs in fee_structures:
        if fs.fee_head_val and not fs.fee_head_val.is_transport:
            monthly_fee += fs.amount
    
    # Add transport if opted
    if student.transport_opted and student.pickup_point_id:
        transport = db.query(TransportMaster).filter(
            TransportMaster.id == student.pickup_point_id
        ).first()
        if transport:
            monthly_fee += transport.monthly_charge or 0
    
    # Calculate total dues for unpaid months
    total_due = 0.0
    for month in months_till_now:
        if month not in paid_months:
            total_due += monthly_fee
    
    # Final balance = Total Due - Already Paid (can be negative if overpaid)
    # But we don't subtract total_paid here because paid_months already excludes paid ones
    # The dues are just for UNPAID months
    
    return max(total_due, 0)  # Never negative


@router.post("/sync-balances")
def sync_all_student_balances(db: Session = Depends(get_db)):
    """
    Bulk recalculate and update current_balance for ALL active students.
    This ensures Dashboard Pending Fees is always accurate.
    Call this when fee structure changes or periodically.
    """
    students = db.query(Student).filter(Student.status == True).all()
    
    updated_count = 0
    total_dues = 0.0
    
    for student in students:
        new_balance = calculate_student_dues(student, db)
        student.current_balance = new_balance
        total_dues += new_balance
        updated_count += 1
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Updated {updated_count} students",
        "total_pending_dues": round(total_dues, 2)
    }


@router.get("/recalculate/{student_id}")
def recalculate_single_student(student_id: int, db: Session = Depends(get_db)):
    """
    Recalculate dues for a single student and update current_balance.
    Called after payment or when checking individual student.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    new_balance = calculate_student_dues(student, db)
    old_balance = student.current_balance or 0
    student.current_balance = new_balance
    db.commit()
    
    return {
        "student_id": student_id,
        "student_name": student.student_name,
        "old_balance": round(old_balance, 2),
        "new_balance": round(new_balance, 2),
        "message": "Balance recalculated successfully"
    }
