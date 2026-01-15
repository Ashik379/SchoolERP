import os
from fastapi import FastAPI, Request, Depends, File, UploadFile 
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from database import engine, Base, get_db
from fastapi.middleware.cors import CORSMiddleware
from models import communication

# --- IMPORT ROUTERS (APIs) ---
from routers import dashboard, masters, students, fees, collection, results, auth, attendance, website, communication # ✅ Website added
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
from models.website import WebsiteUpdate, StudentTopper # ✅ Website models added
from models.communication import MessageLog #

# --- CREATE DATABASE TABLES ---
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Digital School ERP")

# ✅ CORS MIDDLEWARE (React connection ke liye sabse zaruri)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

# --- STATIC FILES & TEMPLATES ---
os.makedirs("static/uploads/website", exist_ok=True) # ✅ Website uploads folder
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
app.include_router(website.router) # ✅ Website router included
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

# 2. Admission Page
@app.get("/admission", response_class=HTMLResponse)
def admission_page(request: Request):
    return templates.TemplateResponse("student_add.html", {"request": request})

# 3. Student List Page
@app.get("/students", response_class=HTMLResponse)
def student_list_page(request: Request):
    return templates.TemplateResponse("student_list.html", {"request": request})

# 4. Print Admission Form
@app.get("/print-admission", response_class=HTMLResponse)
def print_admission_page(request: Request):
    return templates.TemplateResponse("print_form.html", {"request": request})

# 5. Fee Collection Page
@app.get("/fees/collect", response_class=HTMLResponse)
def fee_collect_page(request: Request):
    return templates.TemplateResponse("fee_collect.html", {"request": request})

# 6. Fee Settings - Fee Plan (Amount)
@app.get("/fees/master", response_class=HTMLResponse)
def fee_master_page(request: Request):
    return templates.TemplateResponse("fee_master.html", {"request": request})

# 7. Fee Settings - Fee Item + Schedule
@app.get("/fees/schedule", response_class=HTMLResponse)
def fee_schedule_page(request: Request):
    return templates.TemplateResponse("fee_schedule.html", {"request": request})

# --- MASTER RECORDS PAGES ---

# 8. Class Master
@app.get("/masters/class", response_class=HTMLResponse)
def class_master_page(request: Request):
    return templates.TemplateResponse("master_class.html", {"request": request})

# 9. Section Master
@app.get("/masters/section", response_class=HTMLResponse)
def section_master_page(request: Request):
    return templates.TemplateResponse("master_section.html", {"request": request})

# 10. Transport Master
@app.get("/masters/transport", response_class=HTMLResponse)
def transport_master_page(request: Request):
    return templates.TemplateResponse("master_transport.html", {"request": request})

# 11. Account Ledger
@app.get("/masters/ledger", response_class=HTMLResponse)
def ledger_master_page(request: Request):
    return templates.TemplateResponse("master_ledger.html", {"request": request})

# --- FEE RECEIPT PRINT ROUTE ---
@app.get("/print/receipt", response_class=HTMLResponse)
def print_receipt_page(request: Request):
    return templates.TemplateResponse("print_receipt.html", {"request": request})

# --- FEE HISTORY ROUTE ---
@app.get("/fees/history", response_class=HTMLResponse)
def fee_history_page(request: Request):
    return templates.TemplateResponse("fee_history.html", {"request": request})

# --- EXAM & SUBJECT MASTER PAGE ---
@app.get("/exams/master", response_class=HTMLResponse)
def exam_master_page(request: Request):
    return templates.TemplateResponse("master_exams.html", {"request": request})

# --- EXAM SCHEDULE PAGE ---
@app.get("/exams/schedule", response_class=HTMLResponse)
def exam_schedule_page(request: Request):
    return templates.TemplateResponse("exam_schedule.html", {"request": request})

# --- ADMIT CARD SETUP PAGE ---
@app.get("/exams/admit-card", response_class=HTMLResponse)
def admit_card_setup(request: Request):
    return templates.TemplateResponse("exam_admit_setup.html", {"request": request})

@app.get("/fees/id-cards-panel")
def id_card_panel(request: Request):
    return templates.TemplateResponse("id_card_panel.html", {"request": request})

# --- RESULT MANAGER PAGE ---
@app.get("/results/manager", response_class=HTMLResponse)
def result_manager_page(request: Request):
    return templates.TemplateResponse("result_manager.html", {"request": request})

@app.get("/communication", response_class=HTMLResponse)
def communication_page(request: Request):
    return templates.TemplateResponse("communication_panel.html", {"request": request})