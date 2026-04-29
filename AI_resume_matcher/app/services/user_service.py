from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserRegisterRequest
from app.core.security import get_password_hash, verify_password

def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, user_in: UserRegisterRequest) -> User:
    hashed_password = get_password_hash(user_in.password)
    

    user = User(
        username=user_in.username,
        email=user_in.email,
        password_hash=hashed_password,
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user