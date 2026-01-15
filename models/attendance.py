from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class StudentAttendance(Base):
    __tablename__ = "student_attendance"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    class_id = Column(Integer, ForeignKey("classes.id"))
    date = Column(Date, index=True)
    
    # Status: P=Present, A=Absent, L=Late, H=Half Day
    status = Column(String, default="P") 
    
    student = relationship("models.students.Student")
    class_val = relationship("models.masters.ClassMaster")