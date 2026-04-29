from sqlalchemy import Column, BigInteger, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=False)
    raw_text = Column(Text, nullable=True)
    parsed_status = Column(String(20), nullable=False, default='pending')
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())