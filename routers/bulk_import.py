"""
Student Bulk Import Router
Allows administrators to upload Excel files containing student records
and import them into the database with smart lookups and validation.
"""

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from database import get_db
from models.students import Student
from models.masters import ClassMaster, SectionMaster, TransportMaster
from typing import List, Dict, Any, Optional
from datetime import datetime
import random
import io

# Import pandas and openpyxl for Excel processing
import pandas as pd

router = APIRouter(prefix="/bulk-import", tags=["Bulk Import"])

# ==========================================
#   LOOKUP FUNCTIONS (Name → ID)
# ==========================================

def lookup_class_id(class_name: str, db: Session) -> Optional[int]:
    """Look up class ID by class name (case-insensitive)"""
    if not class_name or pd.isna(class_name):
        return None
    class_name = str(class_name).strip()
    class_obj = db.query(ClassMaster).filter(
        ClassMaster.class_name.ilike(class_name)
    ).first()
    return class_obj.id if class_obj else None


def lookup_section_id(section_name: str, class_id: int, db: Session) -> Optional[int]:
    """Look up section ID by section name and class ID"""
    if not section_name or pd.isna(section_name) or not class_id:
        return None
    section_name = str(section_name).strip()
    section_obj = db.query(SectionMaster).filter(
        SectionMaster.section_name.ilike(section_name),
        SectionMaster.class_id == class_id
    ).first()
    return section_obj.id if section_obj else None


def lookup_transport_id(transport_name: str, db: Session) -> Optional[int]:
    """Look up transport ID by pickup point name"""
    if not transport_name or pd.isna(transport_name):
        return None
    transport_name = str(transport_name).strip()
    transport_obj = db.query(TransportMaster).filter(
        TransportMaster.pickup_point_name.ilike(transport_name)
    ).first()
    return transport_obj.id if transport_obj else None


def generate_unique_admission_no(db: Session) -> str:
    """Generate a unique admission number"""
    while True:
        admission_no = f"ADM-{random.randint(10000, 99999)}"
        existing = db.query(Student).filter(Student.admission_no == admission_no).first()
        if not existing:
            return admission_no


def safe_str(value) -> Optional[str]:
    """Safely convert value to string, handling NaN and None"""
    if value is None or pd.isna(value):
        return None
    return str(value).strip() if str(value).strip() else None


def safe_int(value) -> Optional[int]:
    """Safely convert value to integer"""
    if value is None or pd.isna(value):
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def parse_date(value) -> Optional[datetime]:
    """Parse date from various formats"""
    if value is None or pd.isna(value):
        return None
    
    # If already a datetime object
    if isinstance(value, datetime):
        return value.date()
    
    if isinstance(value, pd.Timestamp):
        return value.date()
    
    # Try common date formats
    date_formats = [
        "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d",
        "%d-%b-%Y", "%d %b %Y", "%Y-%m-%d %H:%M:%S"
    ]
    
    value_str = str(value).strip()
    for fmt in date_formats:
        try:
            return datetime.strptime(value_str, fmt).date()
        except ValueError:
            continue
    return None


# ==========================================
#   MAIN BULK IMPORT ENDPOINT
# ==========================================

@router.post("/students")
async def bulk_import_students(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Bulk import students from an Excel file.
    
    Expected columns: student_name, class_name, section_name, roll_no, academic_year,
    gender, dob, category, religion, caste, father_name, mother_name, father_mobile,
    mobile_number, father_occupation, mother_occupation, aadhaar_no, blood_group,
    apaar_id, pan_no, father_aadhaar, mother_aadhaar, address, city, previous_school,
    transport_route, student_photo
    """
    
    # Validate file type
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400, 
            detail="Invalid file format. Please upload an Excel file (.xlsx or .xls)"
        )
    
    try:
        # Read file content
        contents = await file.read()
        
        # Determine engine based on file extension
        # openpyxl = .xlsx (new format), xlrd = .xls (old format)
        if file.filename.endswith('.xlsx'):
            engine = 'openpyxl'
        else:
            engine = None  # Let pandas auto-detect for .xls
        
        # Parse Excel using pandas
        try:
            df = pd.read_excel(io.BytesIO(contents), engine=engine)
        except Exception:
            # Fallback: try without specifying engine
            df = pd.read_excel(io.BytesIO(contents))
        
        # Strip whitespace from column names
        df.columns = df.columns.str.strip().str.lower()
        
    except Exception as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Error reading Excel file: {str(e)}"
        )
    
    # Track results
    errors: List[Dict[str, Any]] = []
    students_to_add: List[Student] = []
    total_rows = len(df)
    
    # Required fields
    required_fields = ['student_name', 'class_name', 'father_name', 'mother_name', 'mobile_number', 'gender']
    
    # Pre-fetch all classes, sections, and transport points for faster lookup
    all_classes = {c.class_name.lower(): c.id for c in db.query(ClassMaster).all()}
    all_sections = {}
    for s in db.query(SectionMaster).all():
        key = (s.section_name.lower() if s.section_name else "", s.class_id)
        all_sections[key] = s.id
    all_transport = {t.pickup_point_name.lower(): t.id for t in db.query(TransportMaster).all()}
    
    # Process each row
    for idx, row in df.iterrows():
        row_num = idx + 2  # Excel row number (1-indexed + header)
        row_errors = []
        
        # Skip completely empty rows
        if row.isna().all():
            continue
        
        # Check required fields
        for field in required_fields:
            if field not in df.columns:
                row_errors.append(f"Missing column '{field}' in Excel")
            elif pd.isna(row.get(field)) or str(row.get(field, '')).strip() == '':
                row_errors.append(f"Missing required field '{field}'")
        
        if row_errors:
            errors.append({"row": row_num, "error": "; ".join(row_errors)})
            continue
        
        # Lookup class_id
        class_name = safe_str(row.get('class_name', ''))
        class_id = all_classes.get(class_name.lower()) if class_name else None
        
        if not class_id:
            errors.append({"row": row_num, "error": f"Class '{class_name}' not found in database"})
            continue
        
        # Lookup section_id (optional, but must match class_id if provided)
        section_name = safe_str(row.get('section_name', ''))
        section_id = None
        if section_name:
            # Section lookup MUST match both section_name AND class_id
            section_key = (section_name.lower(), class_id)
            section_id = all_sections.get(section_key)
            if not section_id:
                # Error: Section not found for this specific class
                errors.append({
                    "row": row_num, 
                    "error": f"Section '{section_name}' not found for class '{class_name}'"
                })
                continue
        
        # Lookup transport_id (OPTIONAL - empty values are allowed)
        transport_name = safe_str(row.get('transport_route', ''))
        transport_id = None
        transport_opted = False
        
        # Only lookup transport if a value is provided
        if transport_name:
            transport_id = all_transport.get(transport_name.lower())
            if transport_id:
                transport_opted = True
            else:
                # Transport name provided but not found - this IS an error
                errors.append({
                    "row": row_num, 
                    "error": f"Transport route '{transport_name}' not found in database"
                })
                continue
        # If transport_name is empty/None, transport_id stays None (student added without transport)
        
        # Parse date of birth
        dob = parse_date(row.get('dob'))
        
        # Generate unique admission number (ignore any Excel value)
        admission_no = generate_unique_admission_no(db)
        
        # Create student object
        try:
            student = Student(
                admission_no=admission_no,
                student_name=safe_str(row.get('student_name')),
                class_id=class_id,
                section_id=section_id,
                roll_no=safe_int(row.get('roll_no')),
                academic_session=safe_str(row.get('academic_year')) or "2025-2026",
                status=True,
                
                # Parents Info
                father_name=safe_str(row.get('father_name')),
                mother_name=safe_str(row.get('mother_name')),
                father_mobile=safe_str(row.get('father_mobile')),
                mobile_number=safe_str(row.get('mobile_number')),
                father_occupation=safe_str(row.get('father_occupation')),
                mother_occupation=safe_str(row.get('mother_occupation')),
                
                # Personal Info
                dob=dob,
                gender=safe_str(row.get('gender')),
                category=safe_str(row.get('category')),
                religion=safe_str(row.get('religion')),
                caste=safe_str(row.get('caste')),
                aadhaar_no=safe_str(row.get('aadhaar_no')),
                blood_group=safe_str(row.get('blood_group')),
                
                # New Fields
                apaar_id=safe_str(row.get('apaar_id')),
                pan_no=safe_str(row.get('pan_no')),
                father_aadhaar=safe_str(row.get('father_aadhaar')),
                mother_aadhaar=safe_str(row.get('mother_aadhaar')),
                
                # Address & Contact
                address=safe_str(row.get('address')),
                city=safe_str(row.get('city')),
                previous_school=safe_str(row.get('previous_school')),
                
                # Transport
                transport_opted=transport_opted,
                pickup_point_id=transport_id,
                
                # Photo URL
                student_photo=safe_str(row.get('student_photo')),
                
                # Defaults
                current_balance=0.0,
                is_result_withheld=False,
                withhold_reason=None
            )
            students_to_add.append(student)
            
        except Exception as e:
            errors.append({"row": row_num, "error": f"Error creating student record: {str(e)}"})
            continue
    
    # Bulk insert with transaction
    imported_count = 0
    if students_to_add:
        try:
            db.add_all(students_to_add)
            db.commit()
            imported_count = len(students_to_add)
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Database integrity error. No students were imported. Error: {str(e)}"
            )
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Database error. No students were imported. Error: {str(e)}"
            )
    
    return {
        "success": True,
        "total_rows": total_rows,
        "imported_count": imported_count,
        "error_count": len(errors),
        "errors": errors
    }


# ==========================================
#   SAMPLE TEMPLATE DOWNLOAD
# ==========================================

@router.get("/template")
async def get_sample_template():
    """
    Returns the expected column names for the Excel template.
    Administrators should use this to create their upload files.
    """
    return {
        "required_columns": [
            "student_name",
            "class_name",
            "father_name", 
            "mother_name",
            "mobile_number",
            "gender"
        ],
        "optional_columns": [
            "section_name",
            "roll_no",
            "academic_year",
            "dob",
            "category",
            "religion",
            "caste",
            "father_mobile",
            "father_occupation",
            "mother_occupation",
            "aadhaar_no",
            "blood_group",
            "apaar_id",
            "pan_no",
            "father_aadhaar",
            "mother_aadhaar",
            "address",
            "city",
            "previous_school",
            "transport_route",
            "student_photo"
        ],
        "notes": [
            "class_name should match exactly with class names in the database",
            "section_name should match exactly with section names in the database",
            "transport_route should match pickup point names in the database",
            "admission_no column will be ignored - system generates unique IDs automatically",
            "dob should be in format: YYYY-MM-DD or DD-MM-YYYY or DD/MM/YYYY",
            "student_photo should be a valid image URL"
        ]
    }
