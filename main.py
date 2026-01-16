import os
from fastapi import FastAPI, Request, Depends, File, UploadFile 
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from database import engine, Base, get_db
from fastapi.middleware.cors import CORSMiddleware
from models import communication

# --- IMPORT ROUTERS (APIs) ---
from routers import dashboard, masters, students, fees, collection, results, auth, attendance, website, communication
from routers.exams import router as exams_router 
from routers import student_api
from routers import bulk_import
from routers import student_lifecycle

# --- IMPORT MODELS ---
from models.students import Student
from models.masters import ClassMaster, TransportMaster, SectionMaster, LedgerMaster
from models.transactions import FeeTransaction
from models.fees import FeeItem, FeePlan 
from models.paid_history import PaidMonth
from models.exams import Subject, ClassSubject, ExamType, ExamSchedule
from models.attendance import StudentAttendance 
from models.holidays import Holiday 
from models.website import WebsiteUpdate, StudentTopper 
from models.communication import MessageLog 

# --- CREATE DATABASE TABLES ---
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Digital School ERP")

# ==========================================
# ✅ SECURITY MIDDLEWARE (THE FIX IS HERE)
# ==========================================
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # In paths ko hamesha allow karna hai
    allowed_paths = ["/auth/login", "/api/v1/auth/login"]
    path = request.url.path

    # ✅ CHANGE: Maine yahan '/api/v1/website' add kar diya hai.
    # Ab Website ka data lene ke liye backend password nahi mangega.
    if path not in allowed_paths \
       and not path.startswith("/static") \
       and not path.startswith("/api/v1/student") \
       and not path.startswith("/api/v1/website"):  # 👈 YE LINE ZAROORI HAI
       
        token = request.cookies.get("user_token")
        
        # 🚨 LOCK: Agar token nahi hai YA token 'admin_access' nahi hai, toh bahar pheko
        if not token or token != "admin_access":
            return RedirectResponse(url="/auth/login")
    
    response = await call_next(request)
    return response

# ==========================================
# ✅ CORS MIDDLEWARE (Website Allowed)
# ==========================================
origins = [
    "http://localhost:3000",
    "https://vvic-erp.onrender.com",
    "https://vvicstudent.vercel.app",        # Student Portal
    "https://vidyavikas-psi.vercel.app",     # Main Website
    "https://vidyavikas-psi.vercel.app/"     # Safety Slash
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

# --- STATIC FILES & TEMPLATES ---
os.makedirs("static/uploads/website", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- REGISTER ROUTERS ---
app.include_router(dashboard.router)
app.include_router(masters.router)
app.include_router(students.router)
app.include_router(fees.router)
app.include_router(collection.router)
app.include_router(exams_router) 
app.include_router(results.router)
app.include_router(attendance.router) 
app.include_router(auth.router) 
app.include_router(website.router)
app.include_router(communication.router)
app.include_router(student_api.router)
app.include_router(bulk_import.router)
app.include_router(student_lifecycle.router)

# ===========================
#   WEB PAGES (Admin Panel)
# ===========================

@app.get("/", response_class=HTMLResponse)
def dashboard_ui(request: Request, db: Session = Depends(get_db)):
    student_count = db.query(Student).count()
    class_count = db.query(ClassMaster).count()
    route_count = db.query(TransportMaster).count()
    recent_students = db.query(Student).order_by(Student.id.desc()).limit(5).all()
    return templates.TemplateResponse("index.html", {
        "request": request, "total_students": student_count, 
        "total_classes": class_count, "total_routes": route_count, 
        "recent_students": recent_students
    })

@app.get("/admission", response_class=HTMLResponse)
def admission_page(request: Request):
    return templates.TemplateResponse("student_add.html", {"request": request})

@app.get("/students", response_class=HTMLResponse)
def student_list_page(request: Request):
    return templates.TemplateResponse("student_list.html", {"request": request})

@app.get("/print-admission", response_class=HTMLResponse)
def print_admission_page(request: Request):
    return templates.TemplateResponse("print_form.html", {"request": request})

@app.get("/fees/collect", response_class=HTMLResponse)
def fee_collect_page(request: Request):
    return templates.TemplateResponse("fee_collect.html", {"request": request})

@app.get("/fees/master", response_class=HTMLResponse)
def fee_master_page(request: Request):
    return templates.TemplateResponse("fee_master.html", {"request": request})

@app.get("/fees/schedule", response_class=HTMLResponse)
def fee_schedule_page(request: Request):
    return templates.TemplateResponse("fee_schedule.html", {"request": request})

@app.get("/masters/class", response_class=HTMLResponse)
def class_master_page(request: Request):
    return templates.TemplateResponse("master_class.html", {"request": request})

@app.get("/masters/section", response_class=HTMLResponse)
def section_master_page(request: Request):
    return templates.TemplateResponse("master_section.html", {"request": request})

@app.get("/masters/transport", response_class=HTMLResponse)
def transport_master_page(request: Request):
    return templates.TemplateResponse("master_transport.html", {"request": request})

@app.get("/masters/ledger", response_class=HTMLResponse)
def ledger_master_page(request: Request):
    return templates.TemplateResponse("master_ledger.html", {"request": request})

@app.get("/print/receipt", response_class=HTMLResponse)
def print_receipt_page(request: Request):
    return templates.TemplateResponse("print_receipt.html", {"request": request})

@app.get("/fees/history", response_class=HTMLResponse)
def fee_history_page(request: Request):
    return templates.TemplateResponse("fee_history.html", {"request": request})

@app.get("/exams/master", response_class=HTMLResponse)
def exam_master_page(request: Request):
    return templates.TemplateResponse("master_exams.html", {"request": request})

@app.get("/exams/schedule", response_class=HTMLResponse)
def exam_schedule_page(request: Request):
    return templates.TemplateResponse("exam_schedule.html", {"request": request})

@app.get("/exams/admit-card", response_class=HTMLResponse)
def admit_card_setup(request: Request):
    return templates.TemplateResponse("exam_admit_setup.html", {"request": request})

@app.get("/fees/id-cards-panel")
def id_card_panel(request: Request):
    return templates.TemplateResponse("id_card_panel.html", {"request": request})

@app.get("/results/manager", response_class=HTMLResponse)
def result_manager_page(request: Request):
    return templates.TemplateResponse("result_manager.html", {"request": request})

@app.get("/communication", response_class=HTMLResponse)
def communication_page(request: Request):
    return templates.TemplateResponse("communication_panel.html", {"request": request})