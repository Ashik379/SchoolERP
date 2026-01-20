from fastapi import APIRouter, Depends, HTTPException, Form, Request, File, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from models.website import WebsiteUpdate, StudentTopper, WebsiteGallery 
from datetime import datetime
import os
import shutil

# Cloudinary Import (Optional)
try:
    import cloudinary
    import cloudinary.uploader
    cloudinary.config( 
        cloud_name = "dwe5az2ec",
        api_key = "862764192254549",
        api_secret = "wkAdLdjkNg4Xsb88MzAfcAcPcE4"
    )
    CLOUDINARY_AVAILABLE = True
except ImportError:
    CLOUDINARY_AVAILABLE = False
    print("Cloudinary not available in website module")

router = APIRouter(tags=["Website CMS"])
templates = Jinja2Templates(directory="templates")

# ===============================
#   1. ERP PAGE (HTML View)
# ===============================
@router.get("/website/manager", response_class=HTMLResponse)
def website_manager_page(request: Request):
    return templates.TemplateResponse("website_admin.html", {"request": request})

# ===============================
#   2. PUBLIC API (For React Website)
# ===============================
@router.get("/api/v1/website/updates")
def get_website_updates(db: Session = Depends(get_db)):
    updates = db.query(WebsiteUpdate).filter(WebsiteUpdate.is_active == True).order_by(WebsiteUpdate.id.desc()).all()
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
#   3. ADMIN API (Save Notices) - Isme image nahi hai, ye same rahega
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
        date_obj = datetime.strptime(event_date, "%Y-%m-%d").date()
        new_entry = WebsiteUpdate(title=title, category=category, event_date=date_obj, is_new=is_new)
        db.add(new_entry)
        db.commit()
        return {"status": "success", "message": "Update Added Successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/v1/website/delete/{id}")
def delete_update(id: int, db: Session = Depends(get_db)):
    item = db.query(WebsiteUpdate).filter(WebsiteUpdate.id == id).first()
    if item:
        db.delete(item)
        db.commit()
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Item not found")

# ===============================
#   4. TOPPERS API (CLOUD UPLOAD FIX) ☁️
# ===============================

@router.get("/api/v1/website/toppers")
def get_toppers(db: Session = Depends(get_db)):
    toppers = db.query(StudentTopper).order_by(StudentTopper.rank.asc()).all()
    data = []
    for t in toppers:
        # Ab hum seedha Cloudinary ka URL bhejenge
        data.append({
            "id": t.id,
            "student_name": t.student_name,
            "class_name": t.class_name,
            "percentage": t.percentage,
            "photo_url": t.photo_path, # Cloudinary URL yahan store hoga
            "rank": t.rank
        })
    return data

@router.post("/api/v1/website/toppers/add")
async def add_topper(
    student_name: str = Form(...),
    class_name: str = Form(...),
    percentage: str = Form(...),
    rank: int = Form(...),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # ✅ Cloudinary Upload Logic
    try:
        # File ko read karo aur upload karo
        result = cloudinary.uploader.upload(photo.file, folder="vvic_toppers")
        image_url = result.get("secure_url") # Ye hamesha chalne wala link hai
        
        new_topper = StudentTopper(
            student_name=student_name,
            class_name=class_name,
            percentage=percentage,
            rank=rank,
            photo_path=image_url # Database mein ab URL jayega, file name nahi
        )
        db.add(new_topper)
        db.commit()
        return {"status": "success", "url": image_url}
        
    except Exception as e:
        print("Upload Error:", e)
        raise HTTPException(status_code=500, detail="Image upload failed")

@router.delete("/api/v1/website/toppers/delete/{id}")
def delete_topper(id: int, db: Session = Depends(get_db)):
    topper = db.query(StudentTopper).filter(StudentTopper.id == id).first()
    if topper:
        # Cloudinary se delete karna optional hai, abhi bas DB se hatate hain
        db.delete(topper)
        db.commit()
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Topper not found")

# ===============================
#   5. GALLERY API (CLOUD UPLOAD FIX) ☁️
# ===============================

@router.get("/api/v1/website/gallery")
def get_gallery_images(db: Session = Depends(get_db)):
    images = db.query(WebsiteGallery).order_by(WebsiteGallery.id.desc()).all()
    data = []
    for img in images:
        data.append({
            "id": img.id,
            "description": img.description,
            "category": img.category,
            "image_url": img.image_path # Cloudinary URL
        })
    return data

@router.post("/api/v1/website/gallery/add")
async def add_gallery_image(
    description: str = Form(""),
    category: str = Form("Events"),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # ✅ Cloudinary Upload Logic
    try:
        result = cloudinary.uploader.upload(photo.file, folder="vvic_gallery")
        image_url = result.get("secure_url")
        
        new_img = WebsiteGallery(
            description=description,
            category=category,
            image_path=image_url # Database mein URL save karo
        )
        db.add(new_img)
        db.commit()
        return {"status": "success", "url": image_url}

    except Exception as e:
        print("Gallery Upload Error:", e)
        raise HTTPException(status_code=500, detail="Gallery upload failed")

@router.delete("/api/v1/website/gallery/delete/{id}")
def delete_gallery_image(id: int, db: Session = Depends(get_db)):
    img = db.query(WebsiteGallery).filter(WebsiteGallery.id == id).first()
    if img:
        db.delete(img)
        db.commit()
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Image not found")