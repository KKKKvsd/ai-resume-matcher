from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MatchAnalyzeRequest(BaseModel):
    resume_id: int = Field(..., gt=0)
    job_id: int = Field(..., gt=0)


class MatchResultInfoResponse(BaseModel):
    id: int
    resume_id: int
    job_id: int
    score: float | None
    summary: str | None

    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)

    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)

    model_name: str | None
    analysis_mode: str | None = None
    status: str
    error_message: str | None = None
    created_at: datetime


class MatchAnalyzeResponse(BaseModel):
    code: int
    message: str
    data: MatchResultInfoResponse | None


class MatchResultListItemResponse(BaseModel):
    id: int
    resume_id: int
    job_id: int
    score: float | None
    summary: str | None
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    model_name: str | None
    analysis_mode: str | None = None
    status: str
    created_at: datetime


class MatchResultListResponse(BaseModel):
    code: int
    message: str
    data: list[MatchResultListItemResponse]


class MatchResultDetailResponse(BaseModel):
    code: int
    message: str
    data: MatchResultInfoResponse | None


class MatchFollowUpRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)


class MatchFollowUpDataResponse(BaseModel):
    answer: str
    based_on_result_id: int


class MatchFollowUPResponse(BaseModel):
    code: int
    message: str
    data: MatchFollowUpDataResponse


class AgentTaskRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    session_id: str | None = Field(
        default=None,
        description="可选会话ID，同一会话的多轮追问应使用同一个session_id；不传则按无记忆模式处理。",
    )


class AgentTaskDataResponse(BaseModel):
    intent: str
    final_answer: str | None = None
    plan: dict[str, Any] = Field(default_factory=dict)
    steps: list[dict[str, Any]] = Field(default_factory=list)
    result: dict[str, Any] = Field(default_factory=dict)
    confidence: float | None = None
    mode: str | None = None
    warnings: list[str] = Field(default_factory=list)
    memory: dict[str, Any] | None = None


class AgentTaskResponse(BaseModel):
    code: int
    message: str
    data: AgentTaskDataResponse

class CreateSessionResponseData(BaseModel):
    session_id: str

class CreateSessionResponse(BaseModel):
    code: int
    message: str
    data: CreateSessionResponseData
