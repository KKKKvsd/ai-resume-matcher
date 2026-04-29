from datetime import datetime
from pydantic import BaseModel, EmailStr,Field

class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)

class UserInfoResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    created_at: datetime

class UserRegisterResponse(BaseModel):
    code: int
    message: str
    data: UserInfoResponse

class TokenDataResponse(BaseModel):
    access_token: str
    token_type: str

class UserLoginResponse(BaseModel):
    code: int
    message: str
    data: TokenDataResponse

class UserMeResponse(BaseModel):
    code: int
    message: str
    data: UserInfoResponse