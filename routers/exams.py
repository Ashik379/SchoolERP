from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from database import get_db
from models.exams import ExamType, ExamSchedule, Subject, ClassSubject
from models.students import Student
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/api/v1/exams", tags=["Exams"])
templates = Jinja2Templates(directory="templates")

# --- SCHEMAS ---
class SubjectSchema(BaseModel):
    subject_name: str
    subject_code: Optional[str] = None
    subject_type: str = "Theory"

class ExamTypeSchema(BaseModel):
    exam_name: str
    session: str

class MapSubjectSchema(BaseModel):
    class_id: int
    subject_ids: List[int]

class ScheduleItem(BaseModel):
    subject_id: int
    exam_date: str
    start_time: str
    end_time: str
    max_marks: int = 100
    pass_marks: int = 33

class ScheduleCreateSchema(BaseModel):
    class_id: int
    exam_name: str
    schedules: List[ScheduleItem]

# --- HELPER FUNCTION FOR ROBUST TIME PARSING ---
def parse_flexible_time(t_str: str):
    """Handles HH:MM, HH:MM:SS and cleans input"""
    t_str = t_str.strip()
    # Agar browser ne double seconds bhej diye (e.g., 09:00:00:00), usse fix karo
    if t_str.count(':') > 2:
        parts = t_str.split(':')
        t_str = f"{parts[0]}:{parts[1]}:{parts[2]}"
    
    # Format 1: HH:MM:SS
    try:
        return datetime.strptime(t_str, "%H:%M:%S").time()
    except ValueError:
        pass
    
    # Format 2: HH:MM (Seconds missing)
    try:
        return datetime.strptime(t_str, "%H:%M").time()
    except ValueError:
        raise ValueError(f"Unknown time format: {t_str}")

# ===========================
#        1. SUBJECT MASTER
# ===========================

@router.get("/subjects")
def get_all_subjects(db: Session = Depends(get_db)):
    return db.query(Subject).all()

@router.post("/subjects")
def add_subject(payload: SubjectSchema, db: Session = Depends(get_db)):
    existing = db.query(Subject).filter(Subject.subject_name == payload.subject_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Subject might already exist")
    new_sub = Subject(**payload.dict())
    db.add(new_sub)
    db.commit()
    db.refresh(new_sub)
    return new_sub

# ===========================
#        2. EXAM TYPES
# ===========================

@router.get("/types")
def get_exam_types(db: Session = Depends(get_db)):
    return db.query(ExamType).all()

@router.post("/types")
def add_exam_type(payload: ExamTypeSchema, db: Session = Depends(get_db)):
    existing = db.query(ExamType).filter(ExamType.exam_name == payload.exam_name).first()
    if existing:
        return existing
    new_exam = ExamType(exam_name=payload.exam_name, session=payload.session)
    db.add(new_exam)
    db.commit()
    db.refresh(new_exam)
    return new_exam

# ===========================
#    3. CLASS-SUBJECT MAPPING
# ===========================

@router.post("/map-subjects")
def map_subjects_to_class(payload: MapSubjectSchema, db: Session = Depends(get_db)):
    count = 0
    for sub_id in payload.subject_ids:
        exists = db.query(ClassSubject).filter(
            ClassSubject.class_id == payload.class_id, 
            ClassSubject.subject_id == sub_id
        ).first()
        if not exists:
            mapping = ClassSubject(class_id=payload.class_id, subject_id=sub_id)
            db.add(mapping)
            count += 1
    db.commit()
    return {"message": f"{count} Subjects Mapped Successfully"}

@router.get("/class-subjects/{class_id}")
def get_class_subjects(class_id: int, db: Session = Depends(get_db)):
    return db.query(ClassSubject).filter(ClassSubject.class_id == class_id).options(joinedload(ClassSubject.subject_val)).all()

# ===========================
#      4. EXAM SCHEDULE (FIXED)
# ===========================

@router.post("/save-schedule")
def save_exam_schedule(payload: ScheduleCreateSchema, db: Session = Depends(get_db)):
    # 1. Exam Type Check/Create
    exam = db.query(ExamType).filter(ExamType.exam_name == payload.exam_name).first()
    if not exam:
        exam = ExamType(exam_name=payload.exam_name, session="2025-2026")
        db.add(exam)
        db.commit()
        db.refresh(exam)
    
    # 2. Delete Old Schedule
    db.query(ExamSchedule).filter(
        ExamSchedule.class_id == payload.class_id,
        ExamSchedule.exam_id == exam.id
    ).delete()
    
    # 3. Add New Schedule (With Error Handling)
    for item in payload.schedules:
        try:
            date_obj = datetime.strptime(item.exam_date, "%Y-%m-%d").date()
            start_obj = parse_flexible_time(item.start_time) # ✅ Robust Parser Used
            end_obj = parse_flexible_time(item.end_time)     # ✅ Robust Parser Used
            
            new_sch = ExamSchedule(
                exam_id=exam.id,
                class_id=payload.class_id,
                subject_id=item.subject_id,
                exam_date=date_obj,
                start_time=start_obj,
                end_time=end_obj,
                max_marks=item.max_marks,
                pass_marks=item.pass_marks
            )
            db.add(new_sch)
        except ValueError as e:
            print(f"Format Error: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid Date/Time Format for Subject ID {item.subject_id}")
    
    try:
        db.commit()
        return {"message": "Schedule Saved Successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get-schedule")
def get_exam_schedule(class_id: int, exam_name: str, db: Session = Depends(get_db)):
    exam = db.query(ExamType).filter(ExamType.exam_name == exam_name).first()
    if not exam:
        return []
    
    # ✅ Joinedload added to show Subject Name instead of "Sub ID"
    schedules = db.query(ExamSchedule).filter(
        ExamSchedule.class_id == class_id,
        ExamSchedule.exam_id == exam.id
    ).options(joinedload(ExamSchedule.subject_val)).all()
    
    return schedules

# ===========================
#      5. ADMIT CARD PRINT
# ===========================

@router.get("/print-view", response_class=HTMLResponse)
def print_admit_cards(request: Request, class_id: int, exam_name: str, db: Session = Depends(get_db)):
    students = db.query(Student).filter(Student.class_id == class_id).all()
    
    exam = db.query(ExamType).filter(ExamType.exam_name == exam_name).first()
    schedule = []
    if exam:
        schedule = db.query(ExamSchedule).filter(
            ExamSchedule.class_id == class_id,
            ExamSchedule.exam_id == exam.id
        ).options(joinedload(ExamSchedule.subject_val)).all()
    
    return templates.TemplateResponse("print_admit_card.html", {
        "request": request,
        "students": students,
        "exam_name": exam_name,
        "schedule": schedule,
        "school_name": "DIGITAL PUBLIC SCHOOL",
        "session": "2025-26"
    })