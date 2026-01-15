from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

# 1. CLASS TABLE
class ClassMaster(Base):
    __tablename__ = "classes"
    id = Column(Integer, primary_key=True, index=True)
    class_name = Column(String(50), unique=True, index=True)
    status = Column(Boolean, default=True)
    is_result_published = Column(Boolean, default=False)  # Controls class-wide result visibility

# 2. SECTION TABLE
class SectionMaster(Base):
    __tablename__ = "sections"
    id = Column(Integer, primary_key=True, index=True)
    section_name = Column(String(10))
    class_id = Column(Integer, ForeignKey("classes.id"))
    class_val = relationship("ClassMaster")

# 3. TRANSPORT TABLE
class TransportMaster(Base):
    __tablename__ = "transport_points"
    id = Column(Integer, primary_key=True, index=True)
    pickup_point_name = Column(String(100))
    distance_km = Column(Float)
    monthly_charge = Column(Float)

# 4. FEE HEADS
class FeeHead(Base):
    __tablename__ = "fee_heads"
    id = Column(Integer, primary_key=True, index=True)
    fee_name = Column(String(100))
    fee_type = Column(String(20))

# 5. ACCOUNT LEDGER (Iska naam 'ledger_masters' hona chahiye)
class LedgerMaster(Base):
    __tablename__ = "ledger_masters"  # ✅ YE MATCH HONA CHAHIYE
    
    id = Column(Integer, primary_key=True, index=True)
    ledger_name = Column(String(100), nullable=False)
    under_group = Column(String(50), nullable=False)
    opening_balance = Column(Float, default=0.0)
    balance_type = Column(String(10), default="Dr")