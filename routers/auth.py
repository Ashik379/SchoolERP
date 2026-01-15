from fastapi import APIRouter, Depends, HTTPException, Request, Form, responses, Response
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
def process_login(response: Response, data: LoginSchema, db: Session = Depends(get_db)):
    # --- ADMIN LOGIN LOGIC ---
    if data.role == "admin":
        if data.username == "admin" and data.password == "admin":
            # ✅ Login successful! Cookie set kar rahe hain (Middleware ke liye)
            response.set_cookie(key="user_token", value="admin_access", max_age=86400) # 24 Hours valid
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
            # ✅ Student ke liye bhi cookie set kar rahe hain
            response.set_cookie(key="user_token", value=f"student_{student.id}", max_age=86400)
            return {"status": "success", "redirect_url": f"/students/portal/{student.id}"}
        else:
            return {"status": "error", "detail": "Admission No ya Mobile No galat hai!"}
    
    return {"status": "error", "detail": "Role samajh nahi aaya"}

# 3. Logout Route (GET)
@router.get("/logout")
def logout():
    """
    User ko logout karke wapas login page par bhejta hai aur cookie delete karta hai.
    """
    response = responses.RedirectResponse(url="/auth/login", status_code=302)
    # ✅ Cookie delete kar di taaki login khatam ho jaye
    response.delete_cookie("user_token")
    return response