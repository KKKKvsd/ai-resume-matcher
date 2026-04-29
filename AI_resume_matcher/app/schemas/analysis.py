from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class EvidenceChunk(BaseModel):
    source: str = Field(default="knowledge")
    content: str = Field(..., min_length=1)
    score: float | None = None


class MatchAnalysisResult(BaseModel):
    score: float = Field(..., ge=0, le=100)
    summary: str = Field(..., min_length=1)

    strengths: list[str] = Field(default_factory=list, max_length=6)
    weaknesses: list[str] = Field(default_factory=list, max_length=6)
    suggestions: list[str] = Field(default_factory=list, max_length=8)

    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    evidence: list[EvidenceChunk] = Field(default_factory=list)

    model_name: str = "unknown"
    status: Literal["success", "fallback"] = "success"
    analysis_mode: Literal["llm", "mock", "repair"] = "llm"
    error_message: str | None = None

    @field_validator(
        "strengths",
        "weaknesses",
        "suggestions",
        "matched_keywords",
        "missing_keywords",
        mode="before",
    )
    @classmethod
    def normalize_list(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return []
            return [line.strip() for line in value.splitlines() if line.strip()] or [value]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return [str(value).strip()]

    @field_validator("summary", mode="before")
    @classmethod
    def normalize_summary(cls, value):
        value = str(value or "").strip()
        return value or "该简历与岗位存在一定匹配度，建议结合岗位要求进一步优化。"

    @model_validator(mode="after")
    def fill_required_business_defaults(self):
        if not self.strengths:
            self.strengths = ["具备一定项目和技术基础，但优势表述仍可进一步增强。"]
        if not self.weaknesses:
            self.weaknesses = ["当前未发现明显硬性短板，但仍可增强岗位针对性。"]
        if not self.suggestions:
            self.suggestions = ["建议根据岗位关键词继续优化简历内容。"]
        return self
