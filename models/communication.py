from sqlalchemy import Column, Integer, String, DateTime, Text
from database import Base
from datetime import datetime

class MessageLog(Base):
    __tablename__ = "communication_logs"

    id = Column(Integer, primary_key=True, index=True)
    target = Column(String, nullable=False) # "All Students" or "Class 10"
    message_type = Column(String, nullable=False) # "Holiday", "Notice", "Urgent"
    content = Column(Text, nullable=False) # Pura message jo bheja gaya
    sent_count = Column(Integer, default=0) # Kitne logo ko gaya
    sent_at = Column(DateTime, default=datetime.now)