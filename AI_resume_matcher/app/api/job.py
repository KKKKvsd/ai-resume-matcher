from fastapi import Depends, HTTPException, APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.schemas.job import (
    JobCreateRequest,
    JobCreateResponse,
    JobListResponse,
    JobDetailResponse,
)
from app.services.job_service import create_job, get_job_by_user_id, get_job_by_id
from app.utils.response import success_response

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])

@router.post("", response_model=JobCreateResponse)
def create_job_api(
    job_in: JobCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    job = create_job(db, current_user.id, job_in)
    return success_response(
        data={
            "id": job.id,
            "title": job.title,
            "company_name": job.company_name,
            "content": job.content,
            "source": job.source,
            "created_at": job.created_at,
        }
    )

@router.get("", response_model=JobListResponse)
def get_job_list_api(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    jobs = get_job_by_user_id(db, current_user.id)
    return success_response(
        data=[
            {
                "id": job.id,
                "title": job.title,
                "company_name": job.company_name,
                "content": job.content,
                "source": job.source,
                "created_at": job.created_at,
            }
            for job in jobs
        ]
    )

@router.get("/{job_id}", response_model=JobDetailResponse)
def get_job_detail_api(
    job_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    job = get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not permission to access this job")

    return success_response(
        data={
            "id": job.id,
            "title": job.title,
            "company_name": job.company_name,
            "content": job.content,
            "source": job.source,
            "created_at": job.created_at,
        }
    )