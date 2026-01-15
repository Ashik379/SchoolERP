from sqlalchemy import Column, Integer, String, Date
from database import Base

class Holiday(Base):
    __tablename__ = "holidays"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True) # Ek din ek hi chutti hogi
    name = Column(String) # Wajah: Sunday, Eid, Diwali etc.