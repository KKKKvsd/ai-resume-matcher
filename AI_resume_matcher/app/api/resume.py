from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.schemas.resume import (
    ResumeUploadResponse,
    ResumeListResponse,
    ResumeDetailResponse,
)
from app.services.resume_service import (
    save_uploaded_resume,
    get_resume_by_user_id,
    get_resume_by_id,
)
from app.utils.response import success_response

router = APIRouter(prefix="/api/v1/resumes", tags=["resumes"])

@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume_api(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Invalid file")
    
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    file_content = await file.read()
    resume = save_uploaded_resume(
        db=db,
        user_id=current_user.id,
        file_name=file.filename,
        file_content=file_content,
        upload_dir=settings.UPLOAD_DIR,
    )
    return success_response(
        data={
            "id": resume.id,
            "file_name": resume.file_name,
            "file_type": resume.file_type,
            "file_path": resume.file_path,
            "raw_text": resume.raw_text,
            "parsed_status": resume.parsed_status,
            "created_at": resume.created_at,
        }
    )

@router.get("", response_model=ResumeListResponse)
def get_resume_list_api(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    resumes = get_resume_by_user_id(db, current_user.id)
    return success_response(
        data=[
            {
                "id": resume.id,
                "file_name": resume.file_name,
                "file_type": resume.file_type,
                "parsed_status": resume.parsed_status,
                "created_at": resume.created_at,
            }
            for resume in resumes
        ]
    )

@router.get("/{resume_id}", response_model=ResumeDetailResponse)
def get_resume_detail_api(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    resume = get_resume_by_id(db, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    if resume.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not permission to access this resume")
    
    return success_response(
        data={
            "id": resume.id,
            "file_name": resume.file_name,
            "file_type": resume.file_type,
            "file_path": resume.file_path,
            "raw_text": resume.raw_text,
            "parsed_status": resume.parsed_status,
            "created_at": resume.created_at,
        }
    )