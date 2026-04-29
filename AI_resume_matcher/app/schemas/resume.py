from datetime import datetime
from pydantic import BaseModel

class ResumeInfoResponse(BaseModel):
    id: int
    file_name: str
    file_type: str
    file_path: str
    raw_text: str | None
    parsed_status: str
    created_at: datetime

class ResumeListItemResponse(BaseModel):
    id: int
    file_name: str
    file_type: str
    parsed_status: str
    created_at: datetime

class ResumeUploadResponse(BaseModel):
    code: int
    message: str
    data: ResumeInfoResponse

class ResumeListResponse(BaseModel):
    code: int
    message: str
    data: list[ResumeListItemResponse]

class ResumeDetailResponse(BaseModel):
    code: int
    message: str
    data: ResumeInfoResponse
    

