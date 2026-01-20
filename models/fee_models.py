"""
Fee Management Models - Transaction-Based Ledger System
Complete rebuild with double-entry bookkeeping and audit trail
"""
from sqlalchemy import Column, Integer, String, Float, Date, Boolean, ForeignKey, Text, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base
import datetime


# 1. FEE HEAD MASTER - Dynamic fee types (Tuition, Transport, Lab, etc.)
class FeeHeadMaster(Base):
    __tablename__ = "fee_head_masters"

    id = Column(Integer, primary_key=True, index=True)
    head_name = Column(String(100), nullable=False, unique=True)  # e.g., "Tuition Fee"
    frequency = Column(String(20), default="Monthly")  # Monthly, Quarterly, One-time, Annual
    is_transport = Column(Boolean, default=False)  # Flag for transport-based fee
    is_active = Column(Boolean, default=True)
    created_at = Column(Date, default=datetime.date.today)


# 2. FEE STRUCTURE - Class-wise fee mapping
class FeeStructure(Base):
    __tablename__ = "fee_structures"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    fee_head_id = Column(Integer, ForeignKey("fee_head_masters.id"), nullable=False)
    amount = Column(Float, default=0.0)
    academic_year = Column(String(20), default="2025-2026")
    is_active = Column(Boolean, default=True)

    # Unique constraint: One fee head per class per academic year
    __table_args__ = (
        UniqueConstraint('class_id', 'fee_head_id', 'academic_year', name='uq_class_feehead_year'),
    )

    # Relationships - added overlaps to prevent conflict with Student model
    class_val = relationship("ClassMaster", overlaps="class_val")
    fee_head_val = relationship("FeeHeadMaster")


# 3. STUDENT FEE LEDGER - Transaction-based payment tracking (CORE TABLE)
class StudentFeeLedger(Base):
    __tablename__ = "student_fee_ledgers"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    
    # Unique Receipt Number: REC-2026-0001
    receipt_no = Column(String(20), unique=True, nullable=False, index=True)
    
    # Transaction Details
    transaction_date = Column(Date, default=datetime.date.today)
    academic_year = Column(String(20), default="2025-2026")
    
    # Months Paid (JSON Array: ["Apr", "May", "Jun"])
    months_paid = Column(JSON, default=list)
    
    # Amount Details - Double Entry Bookkeeping
    total_due = Column(Float, default=0.0)          # Total fee due for selected items
    discount = Column(Float, default=0.0)            # Concession given
    fine = Column(Float, default=0.0)                # Late fee / Additional charges
    net_payable = Column(Float, default=0.0)         # total_due - discount + fine
    paid_amount = Column(Float, default=0.0)         # Actual amount received
    balance_due = Column(Float, default=0.0)         # Net Payable - Paid (carried forward)
    
    # Payment Info
    payment_mode = Column(String(50))                # Cash, UPI, Cheque, Bank Transfer
    remarks = Column(String(500), nullable=True)
    
    # Payment Breakdown (JSON: {"Tuition Fee|Apr": 1200, "Transport Fee|May": 500})
    payment_breakdown = Column(JSON, default=dict)
    
    # Audit Trail
    created_by = Column(String(50), default="Admin")
    created_at = Column(Date, default=datetime.date.today)

    # Relationship - added overlaps to prevent conflict
    student = relationship("Student", overlaps="class_val,section_val,transport_val")


# 4. RECEIPT COUNTER - For generating unique receipt numbers per year
class ReceiptCounter(Base):
    __tablename__ = "receipt_counters"

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False, unique=True)  # e.g., 2026
    last_number = Column(Integer, default=0)  # Last used receipt number for this year
