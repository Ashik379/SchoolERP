from sqlalchemy import Column, Integer, String, ForeignKey, Float, Date
from sqlalchemy.orm import relationship
from database import Base

class Result(Base):
    __tablename__ = "results"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    exam_name = Column(String)       # Example: "Half Yearly", "Annual"
    subject = Column(String)         # Example: "Maths", "Science"
    marks_obtained = Column(Float)   # Example: 85.5
    total_marks = Column(Float)      # Example: 100.0
    grade = Column(String)           # Example: "A+"
    remarks = Column(String, nullable=True)
    date_declared = Column(Date, nullable=True)

    # Student se connection (Optional, agar Student model mein back_populates nahi hai to ye line hata bhi sakte ho)
    student = relationship("Student")