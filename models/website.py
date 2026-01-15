from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime
from database import Base
from datetime import datetime

# Notice Board ke liye table
class WebsiteUpdate(Base):
    __tablename__ = "website_updates"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    category = Column(String, nullable=False) # 'notice' ya 'event'
    event_date = Column(Date, nullable=True)
    is_new = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

# ✅ Toppers ke liye table
class StudentTopper(Base):
    __tablename__ = "website_toppers"
    id = Column(Integer, primary_key=True, index=True)
    student_name = Column(String, nullable=False)
    class_name = Column(String, nullable=False) # e.g. "Class 10"
    percentage = Column(String, nullable=False)
    photo_path = Column(String, nullable=True) # Image ka filename
    rank = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.now)

# ✅ Gallery Table
class WebsiteGallery(Base):
    __tablename__ = "website_gallery"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String, nullable=True) # Photo ke baare mein (optional)
    category = Column(String, default="Events") # e.g., Campus, Sports, Annual Day
    image_path = Column(String, nullable=False) # Photo ka file naam
    created_at = Column(DateTime, default=datetime.now)