import os
import uuid
from sqlalchemy.orm import Session

from app.models.resume import Resume
from app.utils.file_parser import extract_text_from_pdf
from app.core.logger import logger

def save_uploaded_resume(
    db: Session,
    user_id: int,
    file_name: str,
    file_content: bytes,
    upload_dir: str,
) -> Resume:
    # Ensure the upload directory exists
    os.makedirs(upload_dir, exist_ok=True)

    # Generate a unique file name to avoid conflicts
    ext = os.path.splitext(file_name)[1].lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(upload_dir, unique_name)

    logger.info(f"Saving resume file: {file_name} -> {file_path}")

    # Save the uploaded file to disk
    with open(file_path, "wb") as f:
        f.write(file_content)

    # Extract raw text from the PDF
    raw_text = None
    parsed_status = "pending"

    try:
        if ext == ".pdf":
            raw_text = extract_text_from_pdf(file_path)
            parsed_status = "success"
            logger.info(f"PDF parsed successfully: {file_name}")
        else:
            parsed_status = "failed"
            logger.warning(f"Unsupported file type: {file_name}")
    except Exception:
        parsed_status = "failed"
        logger.exception(f"PDF parsed failed: {file_name}")

    # Create a new Resume record in the database
    resume = Resume(
        user_id=user_id,
        file_name=file_name,
        file_type=ext.replace(".", ""),
        file_path=file_path,
        raw_text=raw_text,
        parsed_status=parsed_status,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    logger.info(f"Resume record created: id={resume.id}, user_id={user_id}")
    return resume

def get_resume_by_user_id(db: Session, user_id: int) -> list[Resume]:
    return (
        db.query(Resume)
        .filter(Resume.user_id == user_id)
        .order_by(Resume.created_at.desc())
        .all()
    )

def get_resume_by_id(db: Session, resume_id: int) -> Resume | None:
    return db.query(Resume).filter(Resume.id == resume_id).first()
