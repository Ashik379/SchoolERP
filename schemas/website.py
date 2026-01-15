from pydantic import BaseModel
from datetime import date
from typing import Optional

# 1. Website par data bhejne ke liye (Response Model)
class WebsiteUpdateSchema(BaseModel):
    id: int
    title: str
    date: str  # Backend isse "15 Jan 2026" bana kar bhejega
    isNew: bool
    category: str

    class Config:
        from_attributes = True # Purane version mein 'orm_mode = True' tha

# 2. ERP Admin se naya notice save karne ke liye
class WebsiteCreateSchema(BaseModel):
    title: str
    category: str  # 'notice' ya 'event'
    event_date: date
    is_new: Optional[bool] = True
class TopperSchema(BaseModel):
    id: int
    student_name: str
    class_name: str
    percentage: str
    photo_url: str
    rank: int
    class Config: from_attributes = True