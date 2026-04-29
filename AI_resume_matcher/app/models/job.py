from sqlalchemy import Column, BigInteger, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False)
    title = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    source = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())