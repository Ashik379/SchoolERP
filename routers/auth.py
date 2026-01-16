from fastapi import APIRouter, Depends, Request, responses, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from pydantic import BaseModel

# ✅ Router setup
router = APIRouter(prefix="/auth", tags=["Authentication"])
templates = Jinja2Templates(directory="templates")

# ✅ Login Data Model (Role abhi bhi rakha hai taaki frontend crash na ho, par check sirf admin hoga)
class LoginSchema(BaseModel):
    username: str
    password: str
    role: str

# 1. Login Page Route (GET)
@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# 2. Login Process Route (POST) - AB SIRF ADMIN KE LIYE
@router.post("/login")
def process_login(response: Response, data: LoginSchema, db: Session = Depends(get_db)):
    
    # 🚨 SECURITY LOCK: Sirf admin role aur sahi credentials allow honge
    if data.role == "admin" and data.username == "admin" and data.password == "admin":
        # ✅ Login successful!
        response.set_cookie(key="user_token", value="admin_access", max_age=86400) 
        return {"status": "success", "redirect_url": "/"}
    
    # Baki sab ke liye seedha error
    return {"status": "error", "detail": "Unauthorized: Access only for Admin!"}

# 3. Logout Route (GET)
@router.get("/logout")
def logout():
    response = responses.RedirectResponse(url="/auth/login", status_code=302)
    # ✅ Cookie delete kar di
    response.delete_cookie("user_token")
    return response