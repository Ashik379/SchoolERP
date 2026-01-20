from sqlalchemy import Column, Integer, String, Date, Boolean, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    admission_no = Column(String(50), unique=True, index=True)
    student_name = Column(String(100))
    
    # --- ACADEMIC INFO ---
    class_id = Column(Integer, ForeignKey("classes.id"))
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=True)
    
    # New Columns
    roll_no = Column(Integer, nullable=True)
    academic_session = Column(String(20), default="2025-2026")

    # --- PARENTS INFO ---
    father_name = Column(String(100))
    mother_name = Column(String(100))
    father_mobile = Column(String(15), nullable=True)
    mobile_number = Column(String(15))
    father_occupation = Column(String(100), nullable=True)
    mother_occupation = Column(String(100), nullable=True)

    # --- PERSONAL INFO ---
    dob = Column(Date, nullable=True)
    gender = Column(String(10))
    category = Column(String(20), nullable=True)
    religion = Column(String(50), nullable=True)
    caste = Column(String(50), nullable=True)
    aadhaar_no = Column(String(20), nullable=True)
    blood_group = Column(String(5), nullable=True)

    apaar_id = Column(String(50), nullable=True)     # ✅ NEW
    pan_no = Column(String(20), nullable=True)       # ✅ NEW
    father_aadhaar = Column(String(20), nullable=True) # ✅ NEW
    mother_aadhaar = Column(String(20), nullable=True) # ✅ NEW
    
    # --- ADDRESS & CONTACT ---
    address = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    previous_school = Column(String(200), nullable=True)
    
    # --- TRANSPORT & OTHERS ---
    transport_opted = Column(Boolean, default=False)
    
    # ✅ FIX: Yahan 'transport' ki jagah 'transport_points' kar diya hai
    pickup_point_id = Column(Integer, ForeignKey("transport_points.id"), nullable=True) 
    
    student_photo = Column(String(255), nullable=True)
    
    status = Column(Boolean, default=True)
    current_balance = Column(Float, default=0.0)  # Partial payment remainder (carried forward)
    calculated_dues = Column(Float, default=0.0)  # Monthly fees for unpaid months
     # ✅ RESULT WITHHOLD CONTROL
    is_result_withheld = Column(Boolean, default=False)
    withhold_reason = Column(String(255), nullable=True)

    # --- RELATIONSHIPS ---
    class_val = relationship("models.masters.ClassMaster")
    section_val = relationship("models.masters.SectionMaster")
    transport_val = relationship("models.masters.TransportMaster")