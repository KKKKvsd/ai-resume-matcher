from datetime import datetime
from pydantic import BaseModel,Field

class JobCreateRequest(BaseModel):
    title: str = Field(...,min_length=1, max_length=255)
    company_name: str | None = Field(None, max_length=255)
    content: str = Field(..., min_length=1)
    source: str | None = Field(None, max_length=50)

class JobInfoResponse(BaseModel):
    id: int
    title: str
    company_name: str | None
    content: str
    source: str | None
    created_at: datetime

class JobListItemResponse(BaseModel):
    id: int
    title: str
    company_name: str | None
    source: str | None
    created_at: datetime

class JobCreateResponse(BaseModel):
    code: int
    message: str
    data: JobInfoResponse

class JobListResponse(BaseModel):
    code: int
    message: str
    data: list[JobListItemResponse]

class JobDetailResponse(BaseModel):
    code: int
    message: str
    data: JobInfoResponse