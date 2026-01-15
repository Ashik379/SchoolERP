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

# ✅ SECURITY MIDDLEWARE (Added for Login Check)
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # In paths ko bina login ke allow karna hai
    allowed_paths = ["/auth/login", "/api/v1/auth/login"]
    path = request.url.path

    # Agar user logged in nahi hai aur protected page access kar raha hai
    if path not in allowed_paths and not path.startswith("/static"):
        token = request.cookies.get("user_token")
        if not token:
            return RedirectResponse(url="/auth/login")
    
    response = await call_next(request)
    return response

# ✅ CORS MIDDLEWARE
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
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

# ===========================
#   WEB PAGES (HTML ROUTES)
# ===========================

# 1. Dashboard
@app.get("/", response_class=HTMLResponse)
def dashboard_ui(request: Request, db: Session = Depends(get_db)):
    student_count = db.query(Student).count()
    class_count = db.query(ClassMaster).count()
    route_count = db.query(TransportMaster).count()
    recent_students = db.query(Student).order_by(Student.id.desc()).limit(5).all()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "total_students": student_count,
        "total_classes": class_count,
        "total_routes": route_count,
        "recent_students": recent_students
    })

# admission page, student list, etc... (Baqi saare routes niche same hain)
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