import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.schemas.match import (
    AgentTaskRequest,
    AgentTaskResponse,
    MatchAnalyzeRequest,
    MatchAnalyzeResponse,
    MatchFollowUPResponse,
    MatchFollowUpRequest,
    MatchResultDetailResponse,
    MatchResultListResponse,
)
from app.services.agent_service import run_agent_pipeline
from app.services.match_service import (
    create_match_result,
    generate_analysis,
    get_job_by_id,
    get_latest_match_result_by_user_id,
    get_match_result_by_id,
    get_match_result_by_user_id,
    get_resume_by_id,
)
from app.utils.llm_client import answer_followup_with_llm
from app.utils.response import success_response


router = APIRouter(prefix="/api/v1/match", tags=["match"])


def parse_list_field(value: str | None) -> list:
    """
    兼容新版 JSON 字符串和旧版换行字符串。
    """
    if not value:
        return []

    try:
        data = json.loads(value)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    return [line.strip() for line in value.split("\n") if line.strip()]


def result_to_detail_data(result) -> dict[str, Any]:
    return {
        "id": result.id,
        "resume_id": result.resume_id,
        "job_id": result.job_id,
        "score": float(result.score) if result.score is not None else None,
        "summary": result.summary,
        "strengths": parse_list_field(result.strengths),
        "weaknesses": parse_list_field(result.weaknesses),
        "suggestions": parse_list_field(result.suggestions),
        "matched_keywords": parse_list_field(result.matched_keywords),
        "missing_keywords": parse_list_field(result.missing_keywords),
        "evidence": parse_list_field(result.evidence),
        "model_name": result.model_name,
        "analysis_mode": result.analysis_mode,
        "status": result.status,
        "error_message": result.error_message,
        "created_at": result.created_at,
    }


def result_to_list_data(result) -> dict[str, Any]:
    return {
        "id": result.id,
        "resume_id": result.resume_id,
        "job_id": result.job_id,
        "score": float(result.score) if result.score is not None else None,
        "summary": result.summary,
        "matched_keywords": parse_list_field(result.matched_keywords),
        "missing_keywords": parse_list_field(result.missing_keywords),
        "model_name": result.model_name,
        "analysis_mode": result.analysis_mode,
        "status": result.status,
        "created_at": result.created_at,
    }


@router.post("/analyze", response_model=MatchAnalyzeResponse)
def analyze_match_api(
    request: MatchAnalyzeRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    resume = get_resume_by_id(db, request.resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    if resume.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="No permission to access this resume")

    job = get_job_by_id(db, request.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="No permission to access this job")

    analysis_result = generate_analysis(resume, job)

    result = create_match_result(
        db=db,
        user_id=current_user.id,
        resume_id=request.resume_id,
        job_id=request.job_id,
        analysis_result=analysis_result,
    )

    return success_response(data=result_to_detail_data(result))


@router.get("/results", response_model=MatchResultListResponse)
def get_match_result_list_api(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    results = get_match_result_by_user_id(db, current_user.id)
    return success_response(data=[result_to_list_data(result) for result in results])


@router.get("/results/{result_id}", response_model=MatchResultDetailResponse)
def get_match_result_detail_api(
    result_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = get_match_result_by_id(db, result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Match result not found")
    if result.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="No permission to access this match result")

    return success_response(data=result_to_detail_data(result))


@router.post("/follow-up", response_model=MatchFollowUPResponse)
def follow_up_match_result_api(
    request: MatchFollowUpRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    latest_result = get_latest_match_result_by_user_id(db, current_user.id)
    if not latest_result:
        raise HTTPException(status_code=404, detail="No analysis result found")

    resume = get_resume_by_id(db, latest_result.resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    job = get_job_by_id(db, latest_result.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    answer = answer_followup_with_llm(
        question=request.question,
        resume_text=resume.raw_text or "",
        job_text=job.content or "",
        summary=latest_result.summary or "",
        strengths=parse_list_field(latest_result.strengths),
        weaknesses=parse_list_field(latest_result.weaknesses),
        suggestions=parse_list_field(latest_result.suggestions),
    )

    return success_response(
        data={
            "answer": answer,
            "based_on_result_id": latest_result.id,
        }
    )


@router.post("/agent", response_model=AgentTaskResponse)
def run_match_agent_api(
    request: AgentTaskRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    latest_result = get_latest_match_result_by_user_id(db, current_user.id)
    if not latest_result:
        raise HTTPException(status_code=404, detail="No analysis result found")

    resume = get_resume_by_id(db, latest_result.resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    job = get_job_by_id(db, latest_result.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    agent_output = run_agent_pipeline(
        query=request.query,
        resume_text=resume.raw_text or "",
        job_text=job.content or "",
        latest_suggestions=parse_list_field(latest_result.suggestions),
    )

    return success_response(data=agent_output)
