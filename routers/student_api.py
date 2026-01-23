from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
from typing import List, Optional

try:
    from jose import JWTError, jwt
    JOSE_AVAILABLE = True
except ImportError:
    JOSE_AVAILABLE = False
    JWTError = Exception
    jwt = None
    print("python-jose not available - Student API JWT disabled")

from database import get_db
from models.students import Student
from models.results import Result
from models.attendance import StudentAttendance
from models.fee_models import StudentFeeLedger, FeeStructure
from pydantic import BaseModel

# --- CONFIGURATION ---
SECRET_KEY = "my_super_secret_key_change_this_later"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

router = APIRouter(prefix="/api/v1/student", tags=["Student App APIs"])
security = HTTPBearer()


# ===========================
#          SCHEMAS
# ===========================

class Token(BaseModel):
    access_token: str
    token_type: str

class StudentLogin(BaseModel):
    admission_no: str
    mobile_no: str

class DashboardStats(BaseModel):
    attendance: str
    fees_due: str
    result: str

class DashboardResponse(BaseModel):
    name: str
    admission_no: str
    class_details: str
    roll_no: Optional[str]
    photo: Optional[str]
    stats: DashboardStats

class ResultResponse(BaseModel):
    id: int
    exam_name: str
    subject: str
    marks_obtained: float
    total_marks: float
    grade: Optional[str]

    class Config:
        from_attributes = True

class AttendanceResponse(BaseModel):
    id: int
    date: str
    status: str

    class Config:
        from_attributes = True

class FeeResponse(BaseModel):
    id: int
    receipt_no: str
    transaction_date: str
    paid_amount: float
    payment_mode: str

    class Config:
        from_attributes = True


# ===========================
#     HELPER FUNCTIONS
# ===========================

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_student(
    credentials: HTTPAuthorizationCredentials = Depends(security), 
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        student_id: str = payload.get("sub")
        role: str = payload.get("role")
        
        if student_id is None or role != "student":
            raise HTTPException(status_code=401, detail="Unauthorized role")
            
    except JWTError:
        raise HTTPException(status_code=401, detail="Session expired, please login again")
    
    student = db.query(Student).filter(Student.id == int(student_id)).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Student record not found")
    return student


# ===========================
#        API ENDPOINTS
# ===========================

# 1. LOGIN API
@router.post("/login", response_model=Token)
def student_login(login_data: StudentLogin, db: Session = Depends(get_db)):
    student = db.query(Student).filter(
        Student.admission_no == login_data.admission_no.strip(),
        Student.mobile_number == login_data.mobile_no.strip()
    ).first()

    if not student:
        raise HTTPException(status_code=401, detail="Invalid Admission No or Mobile Number")

    access_token = create_access_token(data={"sub": str(student.id), "role": "student"})
    return {"access_token": access_token, "token_type": "bearer"}


# 2. DASHBOARD API (Main endpoint for frontend Dashboard.jsx)
@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """
    Get student dashboard with profile and aggregated stats.
    This is the main endpoint called when Dashboard loads.
    """
    # Build class details
    c_name = current_student.class_val.class_name if current_student.class_val else "N/A"
    sec = current_student.section_val.section_name if current_student.section_val else ""
    class_details = f"{c_name} - {sec}".strip(" -")
    
    # Calculate attendance percentage
    total_days = db.query(func.count(StudentAttendance.id)).filter(
        StudentAttendance.student_id == current_student.id
    ).scalar() or 0
    
    present_days = db.query(func.count(StudentAttendance.id)).filter(
        StudentAttendance.student_id == current_student.id,
        StudentAttendance.status == "Present"
    ).scalar() or 0
    
    attendance_pct = round((present_days / total_days * 100) if total_days > 0 else 0)
    
    # Calculate fees due (using current_balance from student)
    fees_due = float(current_student.current_balance or 0) + float(current_student.calculated_dues or 0)
    
    # Get latest result
    latest_result = db.query(Result).filter(
        Result.student_id == current_student.id
    ).order_by(Result.id.desc()).first()
    
    result_text = latest_result.grade if latest_result and hasattr(latest_result, 'grade') else "View"
    
    return DashboardResponse(
        name=current_student.student_name,
        admission_no=current_student.admission_no,
        class_details=class_details,
        roll_no=str(current_student.roll_no) if current_student.roll_no else None,
        photo=current_student.student_photo if current_student.student_photo else None,
        stats=DashboardStats(
            attendance=f"{attendance_pct}%",
            fees_due=f"₹ {int(fees_due)}" if fees_due > 0 else "₹ 0",
            result=result_text
        )
    )


# 3. PROFILE API
@router.get("/profile")
def read_profile(current_student: Student = Depends(get_current_student)):
    c_name = current_student.class_val.class_name if current_student.class_val else "N/A"
    sec = current_student.section_val.section_name if current_student.section_val else "N/A"
    
    return {
        "id": current_student.id,
        "name": current_student.student_name,
        "admission_no": current_student.admission_no,
        "class_details": f"{c_name} - {sec}",
        "mobile": current_student.mobile_number,
        "photo": current_student.student_photo if current_student.student_photo else ""
    }


# 4. RESULTS API
@router.get("/results", response_model=List[ResultResponse])
def read_results(
    current_student: Student = Depends(get_current_student), 
    db: Session = Depends(get_db)
):
    """Get all exam results for the student."""
    results = db.query(Result).filter(Result.student_id == current_student.id).all()
    
    return [
        ResultResponse(
            id=r.id,
            exam_name=r.exam_name if hasattr(r, 'exam_name') else "Exam",
            subject=r.subject if hasattr(r, 'subject') else "Subject",
            marks_obtained=float(r.marks_obtained) if hasattr(r, 'marks_obtained') else 0,
            total_marks=float(r.total_marks) if hasattr(r, 'total_marks') else 100,
            grade=r.grade if hasattr(r, 'grade') else None
        )
        for r in results
    ]


# 5. ATTENDANCE API
@router.get("/attendance", response_model=List[AttendanceResponse])
def get_attendance(
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """Get attendance log for the student (last 90 days)."""
    attendance = db.query(StudentAttendance).filter(
        StudentAttendance.student_id == current_student.id
    ).order_by(StudentAttendance.date.desc()).limit(90).all()
    
    return [
        AttendanceResponse(
            id=a.id,
            date=a.date.isoformat() if a.date else "",
            status=a.status if a.status else "Absent"
        )
        for a in attendance
    ]


# 6. FEES / PAYMENT HISTORY API
@router.get("/fees", response_model=List[FeeResponse])
def get_fee_history(
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """Get fee payment history for the student."""
    fees = db.query(StudentFeeLedger).filter(
        StudentFeeLedger.student_id == current_student.id
    ).order_by(StudentFeeLedger.transaction_date.desc()).all()
    
    return [
        FeeResponse(
            id=f.id,
            receipt_no=f.receipt_no or "",
            transaction_date=f.transaction_date.isoformat() if f.transaction_date else "",
            paid_amount=float(f.paid_amount or 0),
            payment_mode=f.payment_mode or "Cash"
        )
        for f in fees
    ]


# 7. TIMETABLE API (Placeholder - implement based on your timetable model)
@router.get("/timetable")
def get_timetable(
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """Get weekly timetable for the student's class."""
    # TODO: Implement when Timetable model is available
    # Return empty list for now
    return []


# 8. HOMEWORK API (Placeholder - implement based on your homework model)
@router.get("/homework")
def get_homework(
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """Get homework/assignments for the student's class."""
    # TODO: Implement when Homework model is available
    # Return empty list for now
    return []