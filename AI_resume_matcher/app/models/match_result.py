from sqlalchemy import Column, BigInteger, String, DateTime, Text, ForeignKey, Numeric
from sqlalchemy.sql import func
from app.core.database import Base


class MatchResult(Base):
    __tablename__ = "match_results"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    resume_id = Column(BigInteger, ForeignKey("resumes.id"), nullable=False)
    job_id = Column(BigInteger, ForeignKey("job_descriptions.id"), nullable=False)

    score = Column(Numeric(5, 2), nullable=True)
    summary = Column(Text, nullable=True)
    strengths = Column(Text, nullable=True)
    weaknesses = Column(Text, nullable=True)
    suggestions = Column(Text, nullable=True)

    matched_keywords = Column(Text, nullable=True)
    missing_keywords = Column(Text, nullable=True)
    evidence = Column(Text, nullable=True)

    model_name = Column(String(100), nullable=True)
    analysis_mode = Column(String(30), nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())