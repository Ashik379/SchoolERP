from fastapi import APIRouter, Depends, HTTPException, Form, Request, File, UploadFile # ✅ File aur UploadFile yahan hona chahiye
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from models.website import WebsiteUpdate, StudentTopper, WebsiteGallery 
from datetime import datetime
import shutil
import os
import random

# ✅ Change 1: Prefix hata diya taaki hum custom URL bana sakein
router = APIRouter(tags=["Website CMS"])

templates = Jinja2Templates(directory="templates")

# ===============================
#  1. ERP PAGE (HTML View)
# ===============================
# Ab iska URL simple hai: http://127.0.0.1:8000/website/manager
@router.get("/website/manager", response_class=HTMLResponse)
def website_manager_page(request: Request):
    return templates.TemplateResponse("website_admin.html", {"request": request})

# ===============================
#  2. PUBLIC API (For React Website)
# ===============================
# React yahan se data lega: http://127.0.0.1:8000/api/v1/website/updates
@router.get("/api/v1/website/updates")
def get_website_updates(db: Session = Depends(get_db)):
    # Sirf active notices dikhayenge, naye pehle aayenge
    updates = db.query(WebsiteUpdate).filter(WebsiteUpdate.is_active == True).order_by(WebsiteUpdate.id.desc()).all()
    
    # React ke liye sahi format banana
    formatted = []
    for item in updates:
        formatted.append({
            "id": item.id,
            "title": item.title,
            "date": item.event_date.strftime("%d %b %Y") if item.event_date else "",
            "isNew": item.is_new,
            "category": item.category
        })
    return formatted

# ===============================
#  3. ADMIN API (Save Data)
# ===============================
@router.post("/api/v1/website/add")
def add_update(
    title: str = Form(...),
    category: str = Form(...),
    event_date: str = Form(...),
    is_new: bool = Form(True),
    db: Session = Depends(get_db)
):
    try:
        # Date convert string -> object
        date_obj = datetime.strptime(event_date, "%Y-%m-%d").date()
        
        new_entry = WebsiteUpdate(
            title=title, 
            category=category, 
            event_date=date_obj, 
            is_new=is_new
        )
        
        db.add(new_entry)
        db.commit()
        return {"status": "success", "message": "Update Added Successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ===============================
#  4. DELETE API
# ===============================
@router.delete("/api/v1/website/delete/{id}")
def delete_update(id: int, db: Session = Depends(get_db)):
    item = db.query(WebsiteUpdate).filter(WebsiteUpdate.id == id).first()
    if item:
        db.delete(item)
        db.commit()
        return {"status": "deleted"}
    
    raise HTTPException(status_code=404, detail="Item not found")

# ===============================
#  5. TOPPERS GALLERY APIs
# ===============================

# --- Public API: Toppers List ---
@router.get("/api/v1/website/toppers")
def get_toppers(db: Session = Depends(get_db)):
    toppers = db.query(StudentTopper).order_by(StudentTopper.rank.asc()).all()
    
    data = []
    for t in toppers:
        # Photo ka full URL banana
        img_url = f"/static/uploads/website/{t.photo_path}" if t.photo_path else "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"
        
        data.append({
            "id": t.id,
            "student_name": t.student_name,
            "class_name": t.class_name,
            "percentage": t.percentage,
            "photo_url": img_url,
            "rank": t.rank
        })
    return data

# --- Admin API: Add Topper ---
@router.post("/api/v1/website/toppers/add")
async def add_topper(
    student_name: str = Form(...),
    class_name: str = Form(...),
    percentage: str = Form(...),
    rank: int = Form(...),
    photo: UploadFile = File(...), # ✅ Photo Upload Handle
    db: Session = Depends(get_db)
):
    # 1. Folder check karo
    UPLOAD_DIR = "static/uploads/website"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    # 2. File ka unique naam banao
    file_ext = photo.filename.split(".")[-1]
    unique_name = f"topper_{random.randint(1000,9999)}_{student_name.replace(' ', '')}.{file_ext}"
    file_path = f"{UPLOAD_DIR}/{unique_name}"
    
    # 3. File save karo
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(photo.file, buffer)
        
    # 4. Database mein entry
    new_topper = StudentTopper(
        student_name=student_name,
        class_name=class_name,
        percentage=percentage,
        rank=rank,
        photo_path=unique_name
    )
    db.add(new_topper)
    db.commit()
    
    return {"status": "success"}

# --- Admin API: Delete Topper ---
@router.delete("/api/v1/website/toppers/delete/{id}")
def delete_topper(id: int, db: Session = Depends(get_db)):
    topper = db.query(StudentTopper).filter(StudentTopper.id == id).first()
    if topper:
        # Photo bhi delete kar sakte hain (optional)
        try:
            os.remove(f"static/uploads/website/{topper.photo_path}")
        except:
            pass
            
        db.delete(topper)
        db.commit()
        return {"status": "deleted"}
    
    raise HTTPException(status_code=404, detail="Topper not found")

# ===============================
#  6. GALLERY APIs (New Section)
# ===============================

# --- Public API: Get All Photos ---
@router.get("/api/v1/website/gallery")
def get_gallery_images(db: Session = Depends(get_db)):
    images = db.query(WebsiteGallery).order_by(WebsiteGallery.id.desc()).all()
    
    data = []
    for img in images:
        full_url = f"/static/uploads/website/{img.image_path}"
        data.append({
            "id": img.id,
            "description": img.description,
            "category": img.category,
            "image_url": full_url
        })
    return data

# --- Admin API: Upload Photo ---
@router.post("/api/v1/website/gallery/add")
async def add_gallery_image(
    description: str = Form(""),
    category: str = Form("Events"),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 1. Folder ready karo
    UPLOAD_DIR = "static/uploads/website"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    # 2. File save karo
    file_ext = photo.filename.split(".")[-1]
    unique_name = f"gallery_{random.randint(10000,99999)}.{file_ext}"
    file_path = f"{UPLOAD_DIR}/{unique_name}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(photo.file, buffer)
        
    # 3. Database entry
    new_img = WebsiteGallery(
        description=description,
        category=category,
        image_path=unique_name
    )
    db.add(new_img)
    db.commit()
    
    return {"status": "success"}

# --- Admin API: Delete Photo ---
@router.delete("/api/v1/website/gallery/delete/{id}")
def delete_gallery_image(id: int, db: Session = Depends(get_db)):
    img = db.query(WebsiteGallery).filter(WebsiteGallery.id == id).first()
    if img:
        try:
            os.remove(f"static/uploads/website/{img.image_path}")
        except:
            pass
        db.delete(img)
        db.commit()
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Image not found")