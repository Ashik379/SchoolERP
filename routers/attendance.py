from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import extract
from database import get_db
from models.students import Student
from models.attendance import StudentAttendance 
from models.holidays import Holiday 
from pydantic import BaseModel
from typing import List
from datetime import datetime, date as dt_date # ✅ FIX: Renamed import
import calendar

router = APIRouter(prefix="/attendance", tags=["attendance"])
templates = Jinja2Templates(directory="templates")

# --- SCHEMAS ---
class AttendanceItem(BaseModel):
    student_id: int
    status: str 

class AttendanceSubmit(BaseModel):
    class_id: int
    date: str
    attendance: List[AttendanceItem]

class HolidaySubmit(BaseModel):
    date: str
    name: str

# 1. PAGES
@router.get("/entry")
def attendance_entry_page(request: Request):
    return templates.TemplateResponse("attendance_entry.html", {"request": request})

@router.get("/view")
def attendance_view_page(request: Request):
    return templates.TemplateResponse("attendance_view.html", {"request": request})

# 2. MARK HOLIDAY API
@router.post("/mark-holiday")
def mark_holiday(payload: HolidaySubmit, db: Session = Depends(get_db)):
    # Yahan datetime use ho raha hai, koi issue nahi
    date_obj = datetime.strptime(payload.date, "%Y-%m-%d").date()
    
    existing = db.query(Holiday).filter(Holiday.date == date_obj).first()
    if existing:
        existing.name = payload.name
    else:
        new_holiday = Holiday(date=date_obj, name=payload.name)
        db.add(new_holiday)
    try:
        db.commit()
        return {"message": "Holiday Marked Successfully!"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# 3. GET DATA & SAVE
@router.get("/get-data")
def get_attendance_data(class_id: int, date: str, db: Session = Depends(get_db)):
    # Note: Function argument 'date' is a string here
    date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    
    # Check Holiday (Manual + Auto Sunday)
    holiday = db.query(Holiday).filter(Holiday.date == date_obj).first()
    
    if holiday:
        holiday_info = holiday.name
    elif date_obj.weekday() == 6: # 6 = Sunday
        holiday_info = "Sunday"
    else:
        holiday_info = None

    students = db.query(Student).filter(Student.class_id == class_id, Student.status == True).all()
    existing = db.query(StudentAttendance).filter(StudentAttendance.class_id == class_id, StudentAttendance.date == date_obj).all()
    att_map = {rec.student_id: rec.status for rec in existing}

    data = []
    for s in students:
        data.append({
            "id": s.id,
            "name": s.student_name,
            "roll": s.roll_no,
            "adm_no": s.admission_no,
            "status": att_map.get(s.id, "P") 
        })
    return {"students": data, "holiday": holiday_info}

@router.post("/save")
def save_attendance(payload: AttendanceSubmit, db: Session = Depends(get_db)):
    date_obj = datetime.strptime(payload.date, "%Y-%m-%d").date()
    for item in payload.attendance:
        existing = db.query(StudentAttendance).filter(StudentAttendance.student_id == item.student_id, StudentAttendance.date == date_obj).first()
        if existing: existing.status = item.status
        else: db.add(StudentAttendance(student_id=item.student_id, class_id=payload.class_id, date=date_obj, status=item.status))
    try:
        db.commit()
        return {"message": "Attendance Saved!"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# 4. GET MONTHLY REGISTER (✅ AUTO SUNDAY FIXED)
@router.get("/get-register")
def get_monthly_register(class_id: int, month: str, db: Session = Depends(get_db)):
    year, month_num = map(int, month.split('-'))
    num_days = calendar.monthrange(year, month_num)[1]
    
    students = db.query(Student).filter(Student.class_id == class_id, Student.status == True).all()
    records = db.query(StudentAttendance).filter(
        StudentAttendance.class_id == class_id,
        extract('month', StudentAttendance.date) == month_num,
        extract('year', StudentAttendance.date) == year
    ).all()

    holidays = db.query(Holiday).filter(
        extract('month', Holiday.date) == month_num,
        extract('year', Holiday.date) == year
    ).all()
    holiday_map = {h.date.day: h.name for h in holidays}

    att_map = {}
    for r in records:
        if r.student_id not in att_map: att_map[r.student_id] = {}
        att_map[r.student_id][r.date.day] = r.status

    report = []
    for s in students:
        days_data = []
        p_count = 0
        working_days = 0 
        
        for d in range(1, num_days + 1):
            # ✅ FIX: Using 'dt_date' instead of 'date' to avoid conflict
            current_date_obj = dt_date(year, month_num, d)
            
            # 1. Manual Holiday
            if d in holiday_map:
                days_data.append(f"H:{holiday_map[d]}") 
            
            # 2. Auto Sunday
            elif current_date_obj.weekday() == 6: 
                days_data.append("H:Sunday")
            
            # 3. Normal Data
            else:
                status = att_map.get(s.id, {}).get(d, "-")
                days_data.append(status)
                if status != "-": 
                    working_days += 1
                    if status == 'P': p_count += 1
        
        if working_days > 0:
            perc = round((p_count / working_days) * 100, 1)
        else:
            perc = 0
            
        report.append({
            "name": s.student_name,
            "roll": s.roll_no,
            "days": days_data,
            "present": p_count,
            "absent": working_days - p_count,
            "perc": perc
        })
        
    return {"days": list(range(1, num_days + 1)), "report": report}