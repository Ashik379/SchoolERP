from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
from jose import JWTError, jwt
from database import get_db
from models.students import Student
from models.results import Result
from pydantic import BaseModel

# --- CONFIGURATION ---
SECRET_KEY = "my_super_secret_key_change_this_later"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

router = APIRouter(prefix="/api/v1/student", tags=["Student App APIs"])
security = HTTPBearer()

# --- SCHEMAS ---
class Token(BaseModel):
    access_token: str
    token_type: str

class StudentLogin(BaseModel):
    admission_no: str
    mobile_no: str

# --- HELPER FUNCTIONS ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_student(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        student_id: str = payload.get("sub")
        role: str = payload.get("role")
        
        # 🚨 Role Check: Taaki Admin ka token yahan kaam na kare
        if student_id is None or role != "student":
            raise HTTPException(status_code=401, detail="Unauthorized role")
            
    except JWTError:
        raise HTTPException(status_code=401, detail="Session expired, please login again")
    
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Student record not found")
    return student

# ===========================
#        API ENDPOINTS
# ===========================

# 1. LOGIN API
@router.post("/login", response_model=Token)
def student_login(login_data: StudentLogin, db: Session = Depends(get_db)):
    # .strip() use kiya hai taaki extra space se login fail na ho
    student = db.query(Student).filter(
        Student.admission_no == login_data.admission_no.strip(),
        Student.mobile_number == login_data.mobile_no.strip()
    ).first()

    if not student:
        raise HTTPException(status_code=401, detail="Galat Admission No ya Mobile Number")

    access_token = create_access_token(data={"sub": str(student.id), "role": "student"})
    return {"access_token": access_token, "token_type": "bearer"}

# 2. PROFILE API (Crash-Proof Version)
@router.get("/profile")
def read_profile(current_student: Student = Depends(get_current_student)):
    # 🛠️ Safe Fetching with Relationships
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

# 3. RESULT API
@router.get("/results")
def read_results(current_student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    # Row-Level Security: Student sirf apna hi result dekh payega
    results = db.query(Result).filter(Result.student_id == current_student.id).all()
    return results