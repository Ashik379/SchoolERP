"""
Fee Management Models - Transaction-Based Ledger System
Created for robust fee tracking with audit trail
"""
from sqlalchemy import Column, Integer, String, Float, Date, Boolean, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from database import Base
import datetime


# 1. FEE HEAD MASTER - Master list of fee types
class FeeHeadMaster(Base):
    __tablename__ = "fee_head_masters"

    id = Column(Integer, primary_key=True, index=True)
    head_name = Column(String(100), nullable=False)  # e.g., "Tuition Fee", "Transport Fee"
    frequency = Column(String(20), default="Monthly")  # Monthly, One-time, Quarterly
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

    # Relationships
    class_val = relationship("ClassMaster")
    fee_head_val = relationship("FeeHeadMaster")


# 3. STUDENT FEE LEDGER - Transaction-based payment tracking (Core Table)
class StudentFeeLedger(Base):
    __tablename__ = "student_fee_ledgers"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    
    # Unique Receipt Number: REC-2025-0001
    receipt_no = Column(String(20), unique=True, nullable=False, index=True)
    
    # Transaction Details
    transaction_date = Column(Date, default=datetime.date.today)
    academic_year = Column(String(20), default="2025-2026")
    
    # Months Paid (JSON Array: ["Apr", "May", "Jun"])
    months_paid = Column(JSON, default=list)
    
    # Amount Details
    total_amount = Column(Float, default=0.0)      # Total fee due
    discount = Column(Float, default=0.0)           # Concession given
    fine = Column(Float, default=0.0)               # Late fee / Additional
    paid_amount = Column(Float, default=0.0)        # Final amount received
    
    # Payment Info
    payment_mode = Column(String(50))               # Cash, UPI, Cheque, Bank Transfer
    remarks = Column(String(500), nullable=True)
    
    # Payment Breakdown (JSON: {"Tuition Fee": 1200, "Transport Fee": 500})
    payment_breakdown = Column(JSON, default=dict)
    
    # Audit Trail
    created_by = Column(String(50), default="Admin")
    created_at = Column(Date, default=datetime.date.today)

    # Relationship
    student = relationship("models.students.Student")


# 4. RECEIPT COUNTER - For generating unique receipt numbers
class ReceiptCounter(Base):
    __tablename__ = "receipt_counters"

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False)  # e.g., 2025
    last_number = Column(Integer, default=0)  # Last used number for this year
