from sqlalchemy import Column, BigInteger, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime,nullable=True, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, server_default=func.now(), onupdate=func.now())