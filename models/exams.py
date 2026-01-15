from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, Date, Time
from sqlalchemy.orm import relationship
from database import Base

# 1. SUBJECT MASTER (Hindi, English, Math...)
class Subject(Base):
    __tablename__ = "subjects"
    id = Column(Integer, primary_key=True, index=True)
    subject_name = Column(String(100), unique=True)
    subject_code = Column(String(20), nullable=True)
    subject_type = Column(String(20), default="Theory") # Theory/Practical

# 2. CLASS-SUBJECT MAPPING (Which subjects are in Class 10?)
class ClassSubject(Base):
    __tablename__ = "class_subjects"
    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"))
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    
    class_val = relationship("models.masters.ClassMaster")
    subject_val = relationship("Subject")

# 3. EXAM TYPE (Term 1, Annual, Unit Test)
class ExamType(Base):
    __tablename__ = "exam_types"
    id = Column(Integer, primary_key=True, index=True)
    exam_name = Column(String(100), unique=True) # e.g., "Half Yearly 2025"
    session = Column(String(20))

# 4. EXAM SCHEDULE (Updated with Marks)
class ExamSchedule(Base):
    __tablename__ = "exam_schedule"
    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exam_types.id"))
    class_id = Column(Integer, ForeignKey("classes.id"))
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    
    exam_date = Column(Date)
    start_time = Column(Time)
    end_time = Column(Time)
    
    # ✅ NEW FIELDS
    max_marks = Column(Integer, default=100)
    pass_marks = Column(Integer, default=33)

    exam_val = relationship("ExamType")
    class_val = relationship("models.masters.ClassMaster")
    subject_val = relationship("Subject")
# --- ✅ NEW: STUDENT MARKS TABLE ---
class StudentMark(Base):
    __tablename__ = "student_marks"
    
    id = Column(Integer, primary_key=True, index=True)
    
    student_id = Column(Integer, ForeignKey("students.id"))
    exam_id = Column(Integer, ForeignKey("exam_types.id"))
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    class_id = Column(Integer, ForeignKey("classes.id"))
    
    marks_obtained = Column(Float, default=0.0)
    max_marks = Column(Float, default=100.0) # Total marks for that subject
    is_absent = Column(Boolean, default=False)
    
    # Relationships
    student_val = relationship("models.students.Student")
    subject_val = relationship("Subject")
    exam_val = relationship("ExamType")