from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.user import (
    UserRegisterRequest, 
    UserRegisterResponse, 
    UserLoginRequest, 
    UserLoginResponse,
    UserMeResponse,
)
from app.services.user_service import (
    get_user_by_email,
    get_user_by_username,
    create_user,
    authenticate_user,
    get_user_by_id,
)
from app.core.security import create_access_token, decode_access_token
from app.api.deps import get_current_user
from app.utils.response import success_response
from app.core.logger import logger

router = APIRouter(prefix="/api/v1/users", tags=["users"])
security = HTTPBearer()

@router.post("/register", response_model=UserRegisterResponse)
def register_user(user_in: UserRegisterRequest, db: Session = Depends(get_db)):
    logger.info(f"Register request received: email={user_in.email}, username={user_in.username}")

    existing_email = get_user_by_email(db, user_in.email)
    if existing_email:
        logger.warning(f"Register failed, email already exists: {user_in.email}")
        raise HTTPException(status_code=400, detail="Email already registered")

    existing_username = get_user_by_username(db, user_in.username)
    if existing_username:
        logger.warning(f"Register failed, username already exists: {user_in.username}")
        raise HTTPException(status_code=400, detail="Username already registered")

    user = create_user(db, user_in)
    logger.info(f"User registered successfully: user_id={user.id}, email={user.email}")

    return success_response(
        data={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "created_at": user.created_at,
        }
    )

@router.post("/login", response_model=UserLoginResponse)
def login_user(user_in: UserLoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, user_in.email, user_in.password)
    if not user:
        logger.warning(f"Login failed:  email={user_in.email}")
        raise HTTPException(status_code=400, detail="Invalid email or password")

    # Create access token
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email})
    
    logger.info(f"User login success: user_id={user.id}, email={user.email}")

    return success_response(
        data={
            "access_token": access_token,
            "token_type": "bearer",
        }
    )

@router.get("/me", response_model=UserMeResponse)
def get_current_user_info(current_user = Depends(get_current_user)):
    logger.info(f"Get current user info: user_id={current_user.id}")
    return success_response(
        data={
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "created_at": current_user.created_at,
        }
    )
    