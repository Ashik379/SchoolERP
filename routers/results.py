from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from database import get_db
from models.students import Student
from models.exams import ExamType, ExamSchedule, StudentMark, ClassSubject
from models.masters import ClassMaster 
# Note: ClassSection hata diya hai kyunki wo error de raha tha

from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/results", tags=["Results"])
templates = Jinja2Templates(directory="templates")

# ===========================
#      SCHEMAS (MODELS)
# ===========================
class MarkEntrySchema(BaseModel):
    student_id: int
    subject_id: int
    marks: float
    is_absent: bool = False

class MarksSubmitSchema(BaseModel):
    class_id: int
    exam_id: int
    data: List[MarkEntrySchema]

# ===========================
#   PART 1: MARKS ENTRY SYSTEM
# ===========================

# 1. PAGE UI: Marks Entry
@router.get("/entry")
def marks_entry_page(request: Request):
    return templates.TemplateResponse("marks_entry.html", {"request": request})

# 2. API: Get Data for Grid (Subjects from Date Sheet + Students)
@router.get("/get-entry-data")
def get_entry_data(class_id: int, exam_id: int, db: Session = Depends(get_db)):
    # Fetch Subjects & Max Marks from Date Sheet (ExamSchedule)
    schedules = db.query(ExamSchedule).filter(
        ExamSchedule.class_id == class_id,
        ExamSchedule.exam_id == exam_id
    ).options(joinedload(ExamSchedule.subject_val)).all()

    # If no date sheet created, return empty
    if not schedules:
        return {"subjects": [], "students": [], "saved_marks": {}}

    sub_list = []
    for sch in schedules:
        sub_list.append({
            "id": sch.subject_id, 
            "name": sch.subject_val.subject_name,
            "max_marks": sch.max_marks 
        })
    
    # Fetch Students
    students = db.query(Student).filter(Student.class_id == class_id, Student.status == True).all()
    
    # Fetch Existing Marks
    existing_marks = db.query(StudentMark).filter(
        StudentMark.class_id == class_id,
        StudentMark.exam_id == exam_id
    ).all()
    
    marks_map = {}
    for m in existing_marks:
        key = f"{m.student_id}_{m.subject_id}"
        marks_map[key] = m.marks_obtained

    std_list = [{"id": s.id, "name": s.student_name, "roll": s.roll_no, "adm_no": s.admission_no} for s in students]

    return {
        "subjects": sub_list,
        "students": std_list,
        "saved_marks": marks_map
    }

# 3. API: Save Marks
@router.post("/save")
def save_marks(payload: MarksSubmitSchema, db: Session = Depends(get_db)):
    count = 0
    for item in payload.data:
        existing = db.query(StudentMark).filter(
            StudentMark.student_id == item.student_id,
            StudentMark.exam_id == payload.exam_id,
            StudentMark.subject_id == item.subject_id
        ).first()

        if existing:
            existing.marks_obtained = item.marks
            existing.is_absent = item.is_absent
        else:
            new_mark = StudentMark(
                student_id=item.student_id,
                exam_id=payload.exam_id,
                subject_id=item.subject_id,
                class_id=payload.class_id,
                marks_obtained=item.marks,
                is_absent=item.is_absent
            )
            db.add(new_mark)
        count += 1
    
    try:
        db.commit()
        return {"message": "Marks Saved Successfully!", "updated_count": count}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ===========================
#   RESULT PUBLICATION CONTROL
# ===========================

# API: Toggle Class Result Publication
@router.post("/publish/{class_id}")
def toggle_class_publication(class_id: int, publish: bool, db: Session = Depends(get_db)):
    """
    Toggle result publication status for a specific class
    """
    class_obj = db.query(ClassMaster).filter(ClassMaster.id == class_id).first()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")
    
    class_obj.is_result_published = publish
    db.commit()
    
    status = "published" if publish else "unpublished"
    return {
        "message": f"Results {status} for {class_obj.class_name}",
        "class_id": class_id,
        "is_published": publish
    }

# API: Bulk Publish All Classes
@router.post("/publish-all")
def publish_all_results(db: Session = Depends(get_db)):
    """
    Publish results for all classes at once
    """
    classes = db.query(ClassMaster).all()
    count = 0
    
    for cls in classes:
        cls.is_result_published = True
        count += 1
    
    db.commit()
    return {
        "message": f"Results published for all {count} classes",
        "count": count
    }

# API: Get Publication Status for All Classes
@router.get("/publication-status")
def get_publication_status(db: Session = Depends(get_db)):
    """
    Get list of all classes with their publication status
    """
    classes = db.query(ClassMaster).all()
    
    result = []
    for cls in classes:
        student_count = db.query(Student).filter(
            Student.class_id == cls.id,
            Student.status == True
        ).count()
        
        result.append({
            "class_id": cls.id,
            "class_name": cls.class_name,
            "is_published": cls.is_result_published,
            "student_count": student_count
        })
    
    return result



# ===========================
#   PART 2: PRINT SYSTEM
# ===========================

# Helper Function: Generate Report Logic
def generate_student_report(db: Session, student_id: int):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student: return None

    class_info = db.query(ClassMaster).filter(ClassMaster.id == student.class_id).first()
    
    # ✅ VISIBILITY CHECK
    is_visible = True
    withhold_message = ""
    
    if class_info and not class_info.is_result_published:
        is_visible = False
        withhold_message = "Results have not been published yet. Please check back later."
    elif student.is_result_withheld:
        is_visible = False
        reason = student.withhold_reason or "Please contact the school administration"
        withhold_message = f"Your result has been withheld. Reason: {reason}"
    
    exams = db.query(ExamType).all()
    
    class_subjects = db.query(ClassSubject).filter(
        ClassSubject.class_id == student.class_id
    ).options(joinedload(ClassSubject.subject_val)).all()

    marks_data = db.query(StudentMark).filter(StudentMark.student_id == student_id).all()

    report_card = []
    grand_total_obt = 0
    grand_total_max = 0

    for cs in class_subjects:
        sub_id = cs.subject_id
        sub_name = cs.subject_val.subject_name
        
        row_data = {"subject": sub_name, "marks": {}, "total_obt": 0, "total_max": 0}
        
        for exam in exams:
            mark_entry = next((m for m in marks_data if m.subject_id == sub_id and m.exam_id == exam.id), None)
            
            schedule = db.query(ExamSchedule).filter(
                ExamSchedule.class_id == student.class_id,
                ExamSchedule.exam_id == exam.id,
                ExamSchedule.subject_id == sub_id
            ).first()

            max_mm = schedule.max_marks if schedule else 100
            obt_mm = mark_entry.marks_obtained if mark_entry else 0
            
            row_data["marks"][exam.id] = {
                "obtained": obt_mm if mark_entry else "-",
                "max": max_mm
            }

            if mark_entry:
                row_data["total_obt"] += obt_mm
                row_data["total_max"] += max_mm

        try:
            perc = (row_data["total_obt"] / row_data["total_max"]) * 100 if row_data["total_max"] > 0 else 0
            row_data["grade"] = calculate_grade(perc)
        except: row_data["grade"] = "-"

        grand_total_obt += row_data["total_obt"]
        grand_total_max += row_data["total_max"]
        report_card.append(row_data)

    final_percentage = (grand_total_obt / grand_total_max * 100) if grand_total_max > 0 else 0
    final_grade = calculate_grade(final_percentage)

    return {
        "student": student,
        "class_name": class_info.class_name if class_info else "",
        "report_data": report_card,
        "grand_total": grand_total_obt,
        "max_total": grand_total_max,
        "percentage": round(final_percentage, 2),
        "final_grade": final_grade,
        "result_visible": is_visible,  # ✅ NEW
        "withhold_message": withhold_message  # ✅ NEW
    }

def calculate_grade(percentage):
    if percentage >= 91: return "A1"
    elif percentage >= 81: return "A2"
    elif percentage >= 71: return "B1"
    elif percentage >= 61: return "B2"
    elif percentage >= 51: return "C1"
    elif percentage >= 41: return "C2"
    elif percentage >= 33: return "D"
    else: return "E"

# 4. PAGE: Print Selection UI
@router.get("/print-selection")
def print_selection_page(request: Request):
    return templates.TemplateResponse("print_selection.html", {"request": request})

# 5. API: Get Students List for Selection
@router.get("/get-class-students/{class_id}")
def get_class_students_list(class_id: int, db: Session = Depends(get_db)):
    students = db.query(Student).filter(Student.class_id == class_id, Student.status == True).all()
    return students

# 6. PAGE: Single Print
@router.get("/print/{student_id}", response_class=HTMLResponse)
def print_single_result(request: Request, student_id: int, db: Session = Depends(get_db)):
    data = generate_student_report(db, student_id)
    if not data: raise HTTPException(status_code=404, detail="Student not found")
    
    exams = db.query(ExamType).all()
    return templates.TemplateResponse("print_result.html", {
        "request": request,
        "exams": exams,
        **data
    })

# 7. PAGE: Bulk Print
@router.get("/print-bulk/{class_id}", response_class=HTMLResponse)
def print_bulk_results(request: Request, class_id: int, db: Session = Depends(get_db)):
    # ✅ STRICT CHECK: Verify class is published before allowing bulk print
    class_info = db.query(ClassMaster).filter(ClassMaster.id == class_id).first()
    
    if not class_info:
        raise HTTPException(status_code=404, detail="Class not found")
    
    # If class is not published, return error or redirect
    if not class_info.is_result_published:
        return templates.TemplateResponse("error_page.html", {
            "request": request,
            "error_title": "Results Not Published",
            "error_message": f"Results for {class_info.class_name} have not been published yet. Please contact the administration."
        })
    
    students = db.query(Student).filter(Student.class_id == class_id, Student.status == True).all()
    
    all_reports = []
    exams = db.query(ExamType).all()
    
    # ✅ FIXED: Generate report for each student with visibility check
    for std in students:
        data = generate_student_report(db, std.id)
        if data:
            all_reports.append(data)
            
    return templates.TemplateResponse("print_bulk.html", {
        "request": request,
        "exams": exams,
        "all_reports": all_reports,
        "class_name": class_info.class_name
    })