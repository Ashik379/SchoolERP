from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, Date
from sqlalchemy.orm import relationship
from database import Base
from models.masters import ClassMaster, LedgerMaster 

# 1. FEE SCHEDULE
class FeeItem(Base):
    __tablename__ = "fee_items_schedule"

    id = Column(Integer, primary_key=True, index=True)
    
    # ✅ FIX: Yahan 'ledger_masters.id' match karega models/masters.py se
    ledger_id = Column(Integer, ForeignKey("ledger_masters.id"), nullable=False)
    frequency = Column(String(50))  
    
    # Months
    apr = Column(Boolean, default=False)
    may = Column(Boolean, default=False)
    jun = Column(Boolean, default=False)
    jul = Column(Boolean, default=False)
    aug = Column(Boolean, default=False)
    sep = Column(Boolean, default=False)
    oct = Column(Boolean, default=False)
    nov = Column(Boolean, default=False)
    dec = Column(Boolean, default=False)
    jan = Column(Boolean, default=False)
    feb = Column(Boolean, default=False)
    mar = Column(Boolean, default=False)

    ledger_val = relationship("LedgerMaster")

# 2. FEE PLAN
class FeePlan(Base):
    __tablename__ = "fee_plans"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"))
    fee_item_id = Column(Integer, ForeignKey("fee_items_schedule.id"))
    amount = Column(Float, default=0.0)

    class_val = relationship("ClassMaster")
    fee_item_val = relationship("FeeItem")

# 3. RECEIPT CONFIG
class FeeReceiptConfig(Base):
    __tablename__ = "fee_receipt_config"
    id = Column(Integer, primary_key=True, index=True)
    school_name = Column(String(200))
    address = Column(String(500))

# 4. FEE COLLECTION
class FeeCollection(Base):
    __tablename__ = "fee_collections"

    id = Column(Integer, primary_key=True, index=True)
    receipt_no = Column(String, unique=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    date = Column(Date)
    total_amount = Column(Float)
    payment_mode = Column(String) 
    remarks = Column(String, nullable=True)

    student = relationship("models.students.Student")