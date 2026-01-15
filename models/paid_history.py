from sqlalchemy import Column, Integer, String, ForeignKey
from database import Base

class PaidMonth(Base):
    __tablename__ = "paid_months"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    month = Column(String(10))     # e.g., "Apr", "May"
    session = Column(String(20))   # e.g., "2025-26"