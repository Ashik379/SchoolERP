from fastapi import APIRouter, Depends, HTTPException, Request, Form, responses
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from models.students import Student
from pydantic import BaseModel

# ✅ Router setup with prefix
router = APIRouter(prefix="/auth", tags=["Authentication"])
templates = Jinja2Templates(directory="templates")

# ✅ Login Data Model
class LoginSchema(BaseModel):
    username: str
    password: str
    role: str

# 1. Login Page Route (GET)
@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# 2. Login Process Route (POST)
@router.post("/login")
def process_login(data: LoginSchema, db: Session = Depends(get_db)):
    # --- ADMIN LOGIN LOGIC ---
    if data.role == "admin":
        if data.username == "admin" and data.password == "admin":
            return {"status": "success", "redirect_url": "/"}
        else:
            return {"status": "error", "detail": "Galat Password Hai Bhai!"}

    # --- STUDENT LOGIN LOGIC ---
    elif data.role == "student":
        student = db.query(Student).filter(
            Student.admission_no == data.username,
            Student.mobile_number == data.password
        ).first()

        if student:
            return {"status": "success", "redirect_url": f"/students/portal/{student.id}"}
        else:
            return {"status": "error", "detail": "Admission No ya Mobile No galat hai!"}
    
    return {"status": "error", "detail": "Role samajh nahi aaya"}

# 3. Logout Route (GET) - ✅ FIXED Screenshot (416) Error
@router.get("/logout")
def logout(request: Request):
    """
    User ko logout karke wapas login page par bhejta hai.
    Agar aap Cookies ya JWT use kar rahe hain, toh unhe yahan delete karein.
    """
    response = responses.RedirectResponse(url="/auth/login", status_code=302)
    
    # Optional: Agar session cookie clear karni ho toh:
    # response.delete_cookie("access_token")
    
    return response