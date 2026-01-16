"""
Student Lifecycle Management Router
Handles: Bulk Promotions, Status Toggle (Active/Inactive), Safe Deletion
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from database import get_db
from models.students import Student
from models.masters import ClassMaster, SectionMaster
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/lifecycle", tags=["Student Lifecycle"])
templates = Jinja2Templates(directory="templates")

# ================================
#   PYDANTIC SCHEMAS
# ================================

class PromoteRequest(BaseModel):
    student_ids: List[int]
    target_class_id: int
    new_academic_session: str
    reset_roll_no: bool = False

class BulkDeleteRequest(BaseModel):
    student_ids: List[int]

class StatusToggleResponse(BaseModel):
    success: bool
    new_status: bool
    message: str

# ================================
#   HTML PAGE ROUTE
# ================================

@router.get("", response_class=HTMLResponse)
def lifecycle_dashboard(request: Request):
    """Student Lifecycle Management Dashboard"""
    return templates.TemplateResponse("student_lifecycle.html", {"request": request})

# ================================
#   API ENDPOINTS
# ================================

@router.get("/api/students")
def get_filtered_students(
    class_id: Optional[int] = None,
    section_id: Optional[int] = None,
    status_filter: str = "all",  # all, active, inactive
    search: str = "",
    db: Session = Depends(get_db)
):
    """Get filtered student list with status tabs"""
    # Eager load class and section to avoid N+1 queries
    query = db.query(Student).options(
        joinedload(Student.class_val),
        joinedload(Student.section_val)
    )
    
    # Status filter
    if status_filter == "active":
        query = query.filter(Student.status == True)
    elif status_filter == "inactive":
        query = query.filter(Student.status == False)
    
    # Class filter
    if class_id:
        query = query.filter(Student.class_id == class_id)
    
    # Section filter
    if section_id:
        query = query.filter(Student.section_id == section_id)
    
    # Search filter
    if search:
        search_fmt = f"%{search}%"
        query = query.filter(
            or_(
                Student.student_name.ilike(search_fmt),
                Student.admission_no.ilike(search_fmt),
                Student.father_name.ilike(search_fmt)
            )
        )
    
    students = query.order_by(Student.class_id, Student.roll_no).all()
    
    # Format response
    result = []
    for s in students:
        # ✅ PHOTO FETCHING LOGIC ADDED HERE
        # Agar photo NULL hai to empty string bhejenge taaki frontend error na de
        photo_url = s.student_photo if s.student_photo else ""

        result.append({
            "id": s.id,
            "admission_no": s.admission_no,
            "student_name": s.student_name,
            "father_name": s.father_name,
            "mobile_number": s.mobile_number,
            "roll_no": s.roll_no,
            "status": s.status,
            "academic_session": s.academic_session,
            "student_photo": photo_url,  # Cloudinary URL yahan aayega
            "class_id": s.class_id,
            "section_id": s.section_id,
            "class_name": s.class_val.class_name if s.class_val else "N/A",
            "section_name": s.section_val.section_name if s.section_val else ""
        })
    
    return result


@router.get("/api/classes")
def get_all_classes(db: Session = Depends(get_db)):
    """Get all classes for dropdown"""
    classes = db.query(ClassMaster).filter(ClassMaster.status == True).order_by(ClassMaster.id).all()
    return [{"id": c.id, "class_name": c.class_name} for c in classes]


@router.get("/api/sections/{class_id}")
def get_sections_by_class(class_id: int, db: Session = Depends(get_db)):
    """Get sections for a specific class"""
    sections = db.query(SectionMaster).filter(SectionMaster.class_id == class_id).all()
    return [{"id": s.id, "section_name": s.section_name} for s in sections]


@router.put("/api/toggle-status/{student_id}")
def toggle_student_status(student_id: int, db: Session = Depends(get_db)):
    """Toggle student status between Active and Inactive"""
    student = db.query(Student).filter(Student.id == student_id).first()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    student.status = not student.status
    db.commit()
    db.refresh(student)
    
    status_text = "Active" if student.status else "Inactive"
    return {
        "success": True,
        "new_status": student.status,
        "message": f"Student marked as {status_text}"
    }


@router.post("/api/promote")
def bulk_promote_students(request: PromoteRequest, db: Session = Depends(get_db)):
    """Bulk promote selected students to next class"""
    
    if not request.student_ids:
        raise HTTPException(status_code=400, detail="No students selected")
    
    target_class = db.query(ClassMaster).filter(ClassMaster.id == request.target_class_id).first()
    if not target_class:
        raise HTTPException(status_code=400, detail="Target class not found")
    
    # Get first section of target class
    first_section = db.query(SectionMaster).filter(
        SectionMaster.class_id == request.target_class_id
    ).first()
    
    if not first_section:
        raise HTTPException(
            status_code=400, 
            detail=f"No sections defined for {target_class.class_name}. Please create a section first."
        )
    
    students = db.query(Student).filter(Student.id.in_(request.student_ids)).all()
    
    if not students:
        raise HTTPException(status_code=400, detail="No valid students found")
    
    promoted_count = 0
    for student in students:
        if student.status:
            student.class_id = request.target_class_id
            student.academic_session = request.new_academic_session
            student.section_id = first_section.id 
            
            if request.reset_roll_no:
                student.roll_no = None
            
            promoted_count += 1
    
    db.commit()
    
    return {
        "success": True,
        "promoted_count": promoted_count,
        "message": f"Successfully promoted {promoted_count} students to {target_class.class_name}"
    }


@router.delete("/api/delete/{student_id}")
def safe_delete_student(student_id: int, db: Session = Depends(get_db)):
    """Delete student with safety check - only Inactive students can be deleted"""
    
    student = db.query(Student).filter(Student.id == student_id).first()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    if student.status == True:
        raise HTTPException(
            status_code=400, 
            detail="Active students cannot be deleted. Mark them as Inactive first."
        )
    
    student_name = student.student_name
    db.delete(student)
    db.commit()
    
    return {
        "success": True,
        "message": f"Student '{student_name}' has been deleted"
    }


@router.post("/api/bulk-delete")
def bulk_delete_inactive_students(request: BulkDeleteRequest, db: Session = Depends(get_db)):
    """Bulk delete selected Inactive students only"""
    
    if not request.student_ids:
        raise HTTPException(status_code=400, detail="No students selected")
    
    students = db.query(Student).filter(Student.id.in_(request.student_ids)).all()
    
    if not students:
        raise HTTPException(status_code=400, detail="No valid students found")
    
    active_students = [s for s in students if s.status == True]
    if active_students:
        active_names = ", ".join([s.student_name for s in active_students[:3]])
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete Active students: {active_names}. Mark them as Inactive first."
        )
    
    deleted_count = 0
    for student in students:
        db.delete(student)
        deleted_count += 1
    
    db.commit()
    
    return {
        "success": True,
        "deleted_count": deleted_count,
        "message": f"Successfully deleted {deleted_count} inactive students"
    }


@router.get("/api/stats")
def get_lifecycle_stats(db: Session = Depends(get_db)):
    """Get quick stats for the dashboard"""
    total = db.query(Student).count()
    active = db.query(Student).filter(Student.status == True).count()
    inactive = db.query(Student).filter(Student.status == False).count()
    
    return {
        "total": total,
        "active": active,
        "inactive": inactive
    }