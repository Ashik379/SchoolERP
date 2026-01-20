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
from routers import dashboard, masters, students, results, auth, attendance, website, communication
from routers.exams import router as exams_router 
from routers import student_api
from routers import bulk_import
from routers import student_lifecycle
from routers import fee_ledger  # Fee Ledger System (Unified)

# --- IMPORT MODELS ---
from models.students import Student
from models.masters import ClassMaster, TransportMaster, SectionMaster, LedgerMaster
from models.exams import Subject, ClassSubject, ExamType, ExamSchedule
from models.attendance import StudentAttendance 
from models.holidays import Holiday 
from models.website import WebsiteUpdate, StudentTopper 
from models.communication import MessageLog 
from models.fee_models import FeeHeadMaster, FeeStructure, StudentFeeLedger, ReceiptCounter
from sqlalchemy import text

# --- CREATE DATABASE TABLES ---
Base.metadata.create_all(bind=engine)

# --- AUTO MIGRATION: Add missing columns to existing tables ---
def run_migrations():
    """
    Auto-migration function to add missing columns to production database.
    This runs on every server start and safely adds columns if they don't exist.
    """
    from database import SessionLocal
    db = SessionLocal()
    
    try:
        # Check if we're using PostgreSQL (production) or SQLite (local)
        db_url = str(engine.url)
        is_postgres = 'postgresql' in db_url
        
        if is_postgres:
            # PostgreSQL migrations - Add missing columns to all fee-related tables
            migrations = [
                # fee_head_masters table
                "ALTER TABLE fee_head_masters ADD COLUMN IF NOT EXISTS is_transport BOOLEAN DEFAULT FALSE",
                "ALTER TABLE fee_head_masters ADD COLUMN IF NOT EXISTS frequency VARCHAR(20) DEFAULT 'Monthly'",
                "ALTER TABLE fee_head_masters ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
                "ALTER TABLE fee_head_masters ADD COLUMN IF NOT EXISTS created_at DATE",
                
                # fee_structures table
                "ALTER TABLE fee_structures ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
                "ALTER TABLE fee_structures ADD COLUMN IF NOT EXISTS academic_year VARCHAR(20) DEFAULT '2025-2026'",
                
                # student_fee_ledgers table
                "ALTER TABLE student_fee_ledgers ADD COLUMN IF NOT EXISTS total_due FLOAT DEFAULT 0.0",
                "ALTER TABLE student_fee_ledgers ADD COLUMN IF NOT EXISTS discount FLOAT DEFAULT 0.0",
                "ALTER TABLE student_fee_ledgers ADD COLUMN IF NOT EXISTS fine FLOAT DEFAULT 0.0",
                "ALTER TABLE student_fee_ledgers ADD COLUMN IF NOT EXISTS net_payable FLOAT DEFAULT 0.0",
                "ALTER TABLE student_fee_ledgers ADD COLUMN IF NOT EXISTS balance_due FLOAT DEFAULT 0.0",
                "ALTER TABLE student_fee_ledgers ADD COLUMN IF NOT EXISTS payment_breakdown JSON",
                "ALTER TABLE student_fee_ledgers ADD COLUMN IF NOT EXISTS created_by VARCHAR(50) DEFAULT 'Admin'",
                "ALTER TABLE student_fee_ledgers ADD COLUMN IF NOT EXISTS created_at DATE",
                "ALTER TABLE student_fee_ledgers ADD COLUMN IF NOT EXISTS months_paid JSON",
                "ALTER TABLE student_fee_ledgers ADD COLUMN IF NOT EXISTS academic_year VARCHAR(20) DEFAULT '2025-2026'",
                
                # Students table - result hold columns
                "ALTER TABLE students ADD COLUMN IF NOT EXISTS is_result_withheld BOOLEAN DEFAULT FALSE",
                "ALTER TABLE students ADD COLUMN IF NOT EXISTS withhold_reason VARCHAR(500)",
                "ALTER TABLE students ADD COLUMN IF NOT EXISTS current_balance FLOAT DEFAULT 0.0",
                
                # Classes table - result publish column
                "ALTER TABLE classes ADD COLUMN IF NOT EXISTS is_result_published BOOLEAN DEFAULT FALSE",
            ]
            
            for sql in migrations:
                try:
                    db.execute(text(sql))
                    db.commit()
                except Exception as e:
                    db.rollback()
                    # Column might already exist or other non-critical error
                    print(f"Migration note: {str(e)[:100]}")
            
            print("✅ Database migrations completed successfully!")
        else:
            print("ℹ️ SQLite detected - skipping PostgreSQL migrations")
            
    except Exception as e:
        print(f"⚠️ Migration error (non-critical): {str(e)[:200]}")
        db.rollback()
    finally:
        db.close()

# Run migrations on startup
run_migrations()

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
app.include_router(exams_router) 
app.include_router(results.router)
app.include_router(attendance.router) 
app.include_router(auth.router) 
app.include_router(website.router)
app.include_router(communication.router)
app.include_router(student_api.router)
app.include_router(bulk_import.router)
app.include_router(student_lifecycle.router)
app.include_router(fee_ledger.router)  # Fee Ledger System (Unified)

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

@app.get("/fees/setup", response_class=HTMLResponse)
def fee_setup_page(request: Request):
    return templates.TemplateResponse("fee_setup.html", {"request": request})

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