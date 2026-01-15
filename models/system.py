from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from database import Base

class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    school_name = Column(String(255), nullable=False)
    school_address = Column(Text, nullable=True)
    school_logo_url = Column(String(255), nullable=True)
    school_phone = Column(String(20), nullable=True)
    
    # This is the most important field for the ERP logic
    current_session = Column(String(20), nullable=False, default="2025-2026")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())