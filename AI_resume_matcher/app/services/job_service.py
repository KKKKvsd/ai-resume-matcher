from sqlalchemy.orm import Session
from app.models.job import JobDescription
from app.schemas.job import JobCreateRequest

def create_job(db: Session,user_id: int, job_in: JobCreateRequest) -> JobDescription:
    job = JobDescription(
        user_id=user_id,
        title=job_in.title,
        company_name=job_in.company_name,
        content=job_in.content,
        source=job_in.source,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job

def get_job_by_user_id(db: Session, user_id: int) -> list[JobDescription]:
    return (
        db.query(JobDescription)
        .filter(JobDescription.user_id == user_id)
        .order_by(JobDescription.created_at.desc())
        .all()
            )

def get_job_by_id(db: Session, job_id: int) -> JobDescription | None:
    return db.query(JobDescription).filter(JobDescription.id == job_id).first()