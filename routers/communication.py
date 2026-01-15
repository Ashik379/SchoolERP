from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session
from database import get_db, engine
# Models
from models.communication import MessageLog 
from models.students import Student 
from models.masters import ClassMaster

# ✅ JABARDASTI TABLE BANANA (Force Create)
# Agar table nahi bani hogi, to ye line usse bana degi
MessageLog.__table__.create(bind=engine, checkfirst=True)

router = APIRouter(tags=["Communication"])

# --- 1. GET CLASSES FOR DROPDOWN ---
@router.get("/api/v1/communication/classes")
def get_classes_list(db: Session = Depends(get_db)):
    return db.query(ClassMaster).all()

# --- 2. SEND MESSAGE API (Bulletproof Logic) ---
@router.post("/api/v1/communication/send")
def send_message(
    target: str = Form(...),      
    msg_type: str = Form(...),    
    h_date: str = Form(None),
    h_reason: str = Form(None),
    h_reopen: str = Form(None),
    custom_text: str = Form(None),
    db: Session = Depends(get_db)
):
    try:
        # --- A. MESSAGE TEMPLATE ---
        final_message = ""
        if msg_type == "holiday":
            final_message = f"📢 HOLIDAY ALERT\n\nDear Parents,\nThe school will remain closed on {h_date} due to {h_reason}.\nClasses will resume from {h_reopen}.\n\n- Principal, Vidya Vikas"
        elif msg_type == "custom":
            final_message = f"📢 NOTICE\n\n{custom_text}\n\n- Vidya Vikas School"
        
        # --- B. FETCH STUDENTS (PYTHON FILTERING - 100% SAFE) ---
        # Pehle saare students le aao (Error se bachne ke liye)
        all_students = db.query(Student).all()
        target_students = []

        if target == "ALL":
            target_students = all_students
        else:
            # Python loop chala kar check karenge (Safe from Column Name errors)
            for stu in all_students:
                # Check karte hain ki student ki class match hoti hai kya
                # Hum alag alag tareeke try karenge taaki code fate nahi
                student_class_name = "Unknown"
                
                # Try 1: Agar student ke paas direct class name hai
                if hasattr(stu, 'student_class'):
                    student_class_name = str(stu.student_class)
                
                # Try 2: Agar relationship (class_val) hai (Jaisa Dashboard me tha)
                elif hasattr(stu, 'class_val') and stu.class_val:
                    student_class_name = str(stu.class_val.class_name)
                
                # Match check
                if student_class_name == target:
                    target_students.append(stu)

        if not target_students:
            return {"status": "error", "message": f"No students found in '{target}'"}

        # --- C. SIMULATE SENDING ---
        count = 0
        for stu in target_students:
            # Check mobile number safely
            mobile = getattr(stu, 'mobile_no', getattr(stu, 'mobile_number', None))
            if mobile:
                print(f"Sending SMS to {stu.student_name} ({mobile})")
                count += 1
        
        # --- D. SAVE LOG ---
        new_log = MessageLog(
            target=target,
            message_type=msg_type,
            content=final_message,
            sent_count=count
        )
        db.add(new_log)
        db.commit()

        return {"status": "success", "sent_to": count, "message": final_message}

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc() # Terminal me full error dikhayega
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")

# --- 3. HISTORY API ---
@router.get("/api/v1/communication/history")
def get_history(db: Session = Depends(get_db)):
    try:
        return db.query(MessageLog).order_by(MessageLog.id.desc()).all()
    except Exception:
        return []