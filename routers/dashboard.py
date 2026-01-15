from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from database import get_db
from models.students import Student
from models.attendance import StudentAttendance
from models.transactions import FeeTransaction
from models.masters import ClassMaster, TransportMaster 
from datetime import date

router = APIRouter(tags=["Dashboard"])
templates = Jinja2Templates(directory="templates")

@router.get("/") 
def dashboard_view(request: Request, db: Session = Depends(get_db)):
    # 1. Basic Counts
    total_students = db.query(Student).filter(Student.status == True).count()
    
    try: total_classes = db.query(ClassMaster).count()
    except: total_classes = 0
        
    try: total_routes = db.query(TransportMaster).count()
    except: total_routes = 0
    
    # 2. Financials
    # ✅ FIX: Today's Collection Logic Added
    today = date.today()
    try:
        todays_collection = db.query(func.sum(FeeTransaction.amount_paid))\
            .filter(FeeTransaction.payment_date == today).scalar()
        # Agar None hai (koi transaction nahi), toh 0.0 karein
        if todays_collection is None:
            todays_collection = 0.0
    except:
        todays_collection = 0.0

    try:
        total_due = db.query(func.sum(Student.current_balance))\
            .filter(Student.status == True).scalar()
        if total_due is None:
            total_due = 0.0
    except:
        total_due = 0.0

    # 3. Recent 5 Admissions
    recent_students = db.query(Student).filter(Student.status == True)\
        .options(joinedload(Student.class_val))\
        .order_by(Student.id.desc()).limit(5).all()

    # 4. Attendance Stats Logic
    try:
        att_counts = db.query(
            StudentAttendance.status, func.count(StudentAttendance.id)
        ).filter(StudentAttendance.date == today).group_by(StudentAttendance.status).all()
        
        stats_map = {status: count for status, count in att_counts}
        present = stats_map.get('P', 0)
        absent = stats_map.get('A', 0) + stats_map.get('L', 0) 
        
        # ✅ Logic: Jo bache hain wo "Unmarked" hain
        unmarked = total_students - (present + absent)
        if unmarked < 0: unmarked = 0
    except:
        # Agar koi error aaye toh sabko unmarked dikhao
        present, absent, unmarked = 0, 0, total_students

    return templates.TemplateResponse("dashboard_v2.html", {
        "request": request,
        "total_students": total_students,
        "total_classes": total_classes,
        "total_routes": total_routes,
        "todays_collection": todays_collection, # ✅ New Data
        "total_due": total_due,
        "recent_students": recent_students,
        "att_present": present,
        "att_absent": absent,
        "att_unmarked": unmarked
    })