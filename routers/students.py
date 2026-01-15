from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, extract
from database import get_db
from models.students import Student
from models.masters import ClassMaster
from models.attendance import StudentAttendance
from models.holidays import Holiday
from typing import Optional
from datetime import date as dt_date
import shutil
import os
import random
import calendar
from models.exams import StudentMark, Subject, ExamType
from models.transactions import FeeTransaction 

templates = Jinja2Templates(directory="templates")
router = APIRouter(prefix="/students", tags=["Students"]) 

UPLOAD_DIR = "static/uploads/students"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ===============================
#  1. SPECIFIC ROUTES (UPAR RAKHEIN)
# ===============================

# --- Bulk ID Card Page Route (Moved to Top) ---
@router.get("/id_cards", response_class=HTMLResponse)
def id_card_print_page(request: Request, class_id: Optional[int] = None, id: Optional[int] = None):
    return templates.TemplateResponse("id_card_print.html", {"request": request})

# --- API Route to Fetch Data (JSON) ---
@router.get("/api/bulk-ids/{class_id}")
def get_bulk_id_data(class_id: int, db: Session = Depends(get_db)):
    students = db.query(Student).filter(Student.class_id == class_id, Student.status == True).options(joinedload(Student.class_val)).all()
    return students

# --- Filter API ---
@router.get("/api/filter")
def filter_students(class_id: str = "", search: str = "", db: Session = Depends(get_db)):
    query = db.query(Student).filter(Student.status == True).options(
        joinedload(Student.class_val),
        joinedload(Student.section_val)
    )

    if class_id and class_id != "all":
        query = query.filter(Student.class_id == int(class_id))

    if search:
        search_fmt = f"%{search}%"
        query = query.filter(
            or_(
                Student.student_name.ilike(search_fmt),
                Student.admission_no.ilike(search_fmt),
                Student.mobile_number.ilike(search_fmt)
            )
        )
    return query.all()

# ===============================
#  2. STUDENT CRUD OPERATIONS
# ===============================

# ADD STUDENT
@router.post("/")
async def add_student(
    student_name: str = Form(...),
    father_name: str = Form(...),
    mother_name: str = Form(...),
    class_id: int = Form(...),
    mobile_number: str = Form(...),
    gender: str = Form(...),
    
    section_id: Optional[int] = Form(None),
    roll_no: Optional[int] = Form(None),
    dob: Optional[dt_date] = Form(None),
    religion: Optional[str] = Form(None),
    caste: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    aadhaar_no: Optional[str] = Form(None),
    blood_group: Optional[str] = Form(None),
    father_occupation: Optional[str] = Form(None),
    mother_occupation: Optional[str] = Form(None),
    father_mobile: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    previous_school: Optional[str] = Form(None),
    transport_opted: bool = Form(False),
    pickup_point_id: Optional[int] = Form(None),
    
    # New Fields
    apaar_id: Optional[str] = Form(None),
    pan_no: Optional[str] = Form(None),
    father_aadhaar: Optional[str] = Form(None),
    mother_aadhaar: Optional[str] = Form(None),

    student_photo: Optional[UploadFile] = File(None),
    
    db: Session = Depends(get_db)
):
    admission_no = f"ADM-{random.randint(10000, 99999)}"

    # Save Photo
    photo_filename = None
    if student_photo:
        try:
            file_ext = student_photo.filename.split(".")[-1]
            photo_filename = f"{admission_no}.{file_ext}"
            file_path = os.path.join(UPLOAD_DIR, photo_filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(student_photo.file, buffer)
        except Exception as e:
            print(f"Error saving photo: {e}")

    new_student = Student(
        admission_no=admission_no,
        student_name=student_name,
        class_id=class_id,
        section_id=section_id,
        roll_no=roll_no,
        academic_session="2025-2026",
        status=True,
        father_name=father_name,
        mother_name=mother_name,
        mobile_number=mobile_number,
        dob=dob,
        gender=gender,
        religion=religion,
        caste=caste,
        category=category,
        aadhaar_no=aadhaar_no,
        blood_group=blood_group,
        father_occupation=father_occupation,
        mother_occupation=mother_occupation,
        father_mobile=father_mobile,
        address=address,
        city=city,
        previous_school=previous_school,
        transport_opted=transport_opted,
        pickup_point_id=pickup_point_id,
        student_photo=photo_filename,
        current_balance=0.0,

        # New Fields Mapping
        apaar_id=apaar_id,
        pan_no=pan_no,
        father_aadhaar=father_aadhaar,
        mother_aadhaar=mother_aadhaar
    )
    
    try:
        db.add(new_student)
        db.commit()
        db.refresh(new_student)
        return {"message": "Student Admitted Successfully", "id": new_student.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ===============================
#  3. DYNAMIC ID ROUTES (NICHE RAKHEIN)
# ===============================

# GET SINGLE STUDENT (Note: This catches anything like /students/123)
@router.get("/{id}")
def get_student_detail(id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == id).options(
        joinedload(Student.class_val),
        joinedload(Student.section_val)
    ).first()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    try:
        total_days = db.query(StudentAttendance).filter(StudentAttendance.student_id == id).count()
        present_days = db.query(StudentAttendance).filter(StudentAttendance.student_id == id, StudentAttendance.status == 'P').count()
        
        if total_days > 0:
            percent = round((present_days / total_days) * 100, 1)
        else:
            percent = 0
            
        student.attendance_percent = percent  
        
    except Exception as e:
        print(f"Attendance Error: {e}")
        student.attendance_percent = 0

    return student

# DELETE STUDENT
@router.delete("/{id}")
def delete_student(id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == id).first()
    if student:
        db.delete(student)
        db.commit()
    return {"message": "Deleted"}

# UPDATE PHOTO
@router.post("/{id}/update-photo")
async def update_student_photo(id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    if student.student_photo:
        old_path = os.path.join(UPLOAD_DIR, student.student_photo)
        if os.path.exists(old_path):
            os.remove(old_path)
    
    try:
        file_ext = file.filename.split(".")[-1]
        new_filename = f"{student.admission_no}.{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, new_filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        student.student_photo = new_filename
        db.commit()
        return {"message": "Photo Updated", "filename": new_filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# UPDATE STUDENT DETAILS
@router.post("/{id}/update")
async def update_student_details(
    id: int,
    student_name: str = Form(...),
    father_name: str = Form(...),
    mother_name: str = Form(...),
    mobile_number: str = Form(...),
    
    class_id: int = Form(...),
    section_id: Optional[int] = Form(None),
    roll_no: Optional[int] = Form(None),
    dob: Optional[dt_date] = Form(None),
    gender: str = Form(...),
    category: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    
    db: Session = Depends(get_db)
):
    student = db.query(Student).filter(Student.id == id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    student.student_name = student_name
    student.father_name = father_name
    student.mother_name = mother_name
    student.mobile_number = mobile_number
    student.class_id = class_id
    student.section_id = section_id
    student.roll_no = roll_no
    student.dob = dob
    student.gender = gender
    student.category = category
    student.address = address

    try:
        db.commit()
        db.refresh(student)
        return {"message": "Student Updated Successfully!"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# STUDENT PORTAL DASHBOARD (HTML)
@router.get("/portal/{id}")
def student_portal_dashboard(request: Request, id: int):
    return templates.TemplateResponse("student_dashboard.html", {"request": request})

# STUDENT ATTENDANCE HISTORY
@router.get("/attendance/{id}")
def student_attendance_history(request: Request, id: int, month: Optional[str] = None, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == id).first()
    if not student: raise HTTPException(status_code=404, detail="Student not found")

    if not month:
        today = dt_date.today()
        month = f"{today.year}-{today.month:02d}"

    year, month_num = map(int, month.split('-'))
    num_days = calendar.monthrange(year, month_num)[1]

    records = db.query(StudentAttendance).filter(
        StudentAttendance.student_id == id,
        extract('month', StudentAttendance.date) == month_num,
        extract('year', StudentAttendance.date) == year
    ).all()
    att_map = {r.date.day: r.status for r in records}

    holidays = db.query(Holiday).filter(
        extract('month', Holiday.date) == month_num,
        extract('year', Holiday.date) == year
    ).all()
    holiday_map = {h.date.day: h.name for h in holidays}

    days_data = []
    p_count, a_count, l_count = 0, 0, 0
    
    for d in range(1, num_days + 1):
        current_date = dt_date(year, month_num, d)
        status = att_map.get(d, "-")
        display_status = status
        css_class = "bg-light" 

        if d in holiday_map:
            display_status = holiday_map[d]
            css_class = "bg-warning text-dark"
        elif current_date.weekday() == 6:
            display_status = "Sunday"
            css_class = "bg-warning text-dark"
        
        elif status == 'P':
            p_count += 1
            css_class = "bg-success text-white"
            display_status = "Present"
        elif status == 'A':
            a_count += 1
            css_class = "bg-danger text-white"
            display_status = "Absent"
        elif status == 'L':
            l_count += 1
            css_class = "bg-info text-dark"
            display_status = "Late"

        days_data.append({
            "day": d,
            "date": current_date.strftime("%d-%b-%Y"),
            "status": display_status,
            "class": css_class
        })

    return templates.TemplateResponse("student_attendance_view.html", {
        "request": request, 
        "student": student, 
        "history": days_data,
        "summary": {"p": p_count, "a": a_count, "l": l_count},
        "current_month": month
    })

# STUDENT FEES HISTORY
@router.get("/fees/{id}")
def student_fees_history(request: Request, id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == id).first()
    if not student: 
        raise HTTPException(status_code=404, detail="Student not found")

    transactions = db.query(FeeTransaction).filter(
        FeeTransaction.student_id == id
    ).order_by(FeeTransaction.id.desc()).all()

    total_paid = sum(t.amount_paid for t in transactions)

    return templates.TemplateResponse("student_fees_view.html", {
        "request": request,
        "student": student,
        "fees": transactions,
        "total_paid": total_paid
    })

# EXAM RESULTS
@router.get("/results/{id}")
def student_results(request: Request, id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == id).first()
    if not student: 
        raise HTTPException(status_code=404, detail="Student not found")

    result_visible = True
    status_message = ""
    
    class_info = db.query(ClassMaster).filter(ClassMaster.id == student.class_id).first()
    
    if class_info and not class_info.is_result_published:
        result_visible = False
        status_message = "Results have not been published yet. Please check back later."
    elif student.is_result_withheld:
        result_visible = False
        reason = student.withhold_reason or "Please contact the school administration"
        status_message = f"Your result has been withheld. Reason: {reason}"

    results_data = {}
    if result_visible:
        marks_records = db.query(StudentMark).filter(StudentMark.student_id == id)\
            .options(joinedload(StudentMark.subject_val), joinedload(StudentMark.exam_val))\
            .all()

        for mark in marks_records:
            exam_name = mark.exam_val.exam_name if mark.exam_val else "Other"
            if exam_name not in results_data:
                results_data[exam_name] = []
            
            results_data[exam_name].append({
                "subject": mark.subject_val.subject_name if mark.subject_val else "Unknown",
                "obtained": mark.marks_obtained,
                "max": mark.max_marks,
                "status": "Absent" if mark.is_absent else ("Pass" if mark.marks_obtained >= 33 else "Fail")
            })

    return templates.TemplateResponse("student_results_view.html", {
        "request": request,
        "student": student,
        "results": results_data,
        "result_visible": result_visible,
        "status_message": status_message
    })

# STUDENT PROFILE VIEW
@router.get("/profile/{id}")
def student_profile_view(request: Request, id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == id).options(
        joinedload(Student.class_val),
        joinedload(Student.section_val),
        joinedload(Student.transport_val)
    ).first()
    
    if not student: 
        raise HTTPException(status_code=404, detail="Student not found")

    return templates.TemplateResponse("student_profile_view.html", {
        "request": request,
        "student": student
    })

# ===============================
#  4. RESULT WITHHOLD API
# ===============================

# Toggle Student Result Hold
@router.post("/hold/{student_id}")
def toggle_student_hold(student_id: int, hold: bool, reason: str = "", db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    student.is_result_withheld = hold
    if hold and reason:
        student.withhold_reason = reason
    elif not hold:
        student.withhold_reason = None
    
    db.commit()
    
    status = "withheld" if hold else "released"
    return {
        "message": f"Result {status} for {student.student_name}",
        "student_id": student_id,
        "is_withheld": hold,
        "reason": student.withhold_reason
    }

# Update Withhold Reason
@router.put("/hold/{student_id}/reason")
def update_withhold_reason(student_id: int, reason: str, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    student.withhold_reason = reason
    db.commit()
    
    return {
        "message": "Withhold reason updated",
        "student_id": student_id,
        "reason": reason
    }