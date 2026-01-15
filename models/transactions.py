from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
import datetime

class FeeTransaction(Base):
    __tablename__ = "fee_transactions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    
    # Payment Details
    total_amount = Column(Float, default=0.0)
    additional_fee = Column(Float, default=0.0)
    discount = Column(Float, default=0.0)
    net_payable = Column(Float, default=0.0)
    amount_paid = Column(Float, default=0.0)
    balance_amount = Column(Float, default=0.0)
    
    payment_date = Column(Date, default=datetime.date.today)
    payment_mode = Column(String(50))  # Cash, UPI
    remarks = Column(String(255), nullable=True)

    # Relationship
    student = relationship("models.students.Student")