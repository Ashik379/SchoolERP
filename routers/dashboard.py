from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from database import get_db
from models.students import Student
from models.attendance import StudentAttendance
from models.transactions import FeeTransaction
from models.fee_models import StudentFeeLedger  # ✅ NEW: Import StudentFeeLedger
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
    # ✅ FIX: Include BOTH old FeeTransaction AND new StudentFeeLedger
    today = date.today()
    try:
        # Old table collection
        old_collection = db.query(func.sum(FeeTransaction.amount_paid))\
            .filter(FeeTransaction.payment_date == today).scalar() or 0.0
        
        # New ledger collection
        new_collection = db.query(func.sum(StudentFeeLedger.paid_amount))\
            .filter(StudentFeeLedger.transaction_date == today).scalar() or 0.0
        
        todays_collection = old_collection + new_collection
    except:
        todays_collection = 0.0

    # ✅ PENDING FEES: Calculate total dues from FeePlan for all students
    try:
        from models.fees import FeePlan
        from models.paid_history import PaidMonth
        
        # Current month index (academic year: Apr=0 to Mar=11)
        month_map = {4: 0, 5: 1, 6: 2, 7: 3, 8: 4, 9: 5, 10: 6, 11: 7, 12: 8, 1: 9, 2: 10, 3: 11}
        current_month_idx = month_map.get(today.month, 0)
        months_in_year = current_month_idx + 1  # Number of months elapsed
        
        # Get total monthly fee per class from FeePlan
        fee_totals = db.query(
            FeePlan.class_id,
            func.sum(FeePlan.amount).label('monthly_total')
        ).filter(FeePlan.amount > 0).group_by(FeePlan.class_id).all()
        
        fee_by_class = {ft.class_id: ft.monthly_total for ft in fee_totals}
        
        # Get all active students with their class
        active_students = db.query(Student).filter(Student.status == True).all()
        
        total_due = 0.0
        for student in active_students:
            if student.class_id in fee_by_class:
                monthly_fee = fee_by_class[student.class_id]
                
                # Count paid months for this student
                paid_count = db.query(PaidMonth).filter(
                    PaidMonth.student_id == student.id
                ).count()
                
                # Also check new ledger
                ledger_months = db.query(StudentFeeLedger).filter(
                    StudentFeeLedger.student_id == student.id
                ).count()
                
                total_paid_months = paid_count + ledger_months
                unpaid_months = max(0, months_in_year - total_paid_months)
                
                total_due += (monthly_fee * unpaid_months)
            
            # Add transport dues if opted
            if student.transport_opted and student.pickup_point_id:
                transport = db.query(TransportMaster).filter(
                    TransportMaster.id == student.pickup_point_id
                ).first()
                if transport:
                    # Simple calculation: unpaid months * transport fee
                    paid_count = db.query(PaidMonth).filter(
                        PaidMonth.student_id == student.id
                    ).count()
                    unpaid = max(0, months_in_year - paid_count)
                    total_due += (transport.monthly_charge * unpaid)
        
        # Also add any outstanding balances
        balance_due = db.query(func.sum(Student.current_balance))\
            .filter(Student.status == True, Student.current_balance > 0).scalar() or 0.0
        total_due += balance_due
        
    except Exception as e:
        print(f"Dashboard dues error: {e}")
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