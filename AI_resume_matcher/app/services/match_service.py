import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.logger import logger
from app.models.job import JobDescription
from app.models.match_result import MatchResult
from app.models.resume import Resume
from app.schemas.analysis import MatchAnalysisResult
from app.services.tools_service import (
    analyze_match_tool,
    extract_keywords_tool,
    retrieve_knowledge_tool,
    rewrite_suggestions_tool,
    keyword_gap_analysis_tool,
)


def dumps_json(value: Any) -> str:
    return json.dumps(value or [], ensure_ascii=False)


def loads_json_list(value: str | None) -> list:
    if not value:
        return []

    try:
        data = json.loads(value)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    return [line.strip() for line in value.split("\n") if line.strip()]


def get_resume_by_id(db: Session, resume_id: int) -> Resume | None:
    return db.query(Resume).filter(Resume.id == resume_id).first()


def get_job_by_id(db: Session, job_id: int) -> JobDescription | None:
    return db.query(JobDescription).filter(JobDescription.id == job_id).first()


def generate_mock_analysis(
    resume: Resume,
    job: JobDescription,
    error_message: str | None = None,
) -> dict:
    resume_text = resume.raw_text or ""
    job_text = job.content or ""

    job_keywords = extract_keywords_tool(job_text)
    gap_result = keyword_gap_analysis_tool(
        resume_text=resume_text,
        matched_keywords=job_keywords,
    )
    matched_keywords = gap_result["matched_keywords"]
    missing_keywords = gap_result["missing_keywords"]

    score = 60.0 + len(matched_keywords) * 5 - len(missing_keywords) * 2
    score = max(35.0, min(90.0, score))

    strengths: list[str] = []
    weaknesses: list[str] = []
    suggestions: list[str] = []

    if matched_keywords:
        strengths.append("简历中已体现部分岗位相关能力：" + "、".join(matched_keywords[:6]) + "。")
    else:
        strengths.append("简历具备一定软件开发基础，但岗位关键词覆盖还不够直接。")

    if missing_keywords:
        weaknesses.append("简历中对以下岗位关键词体现不足：" + "、".join(missing_keywords[:6]) + "。")
        suggestions.append("建议补充这些关键词对应的真实项目实践：" + "、".join(missing_keywords[:6]) + "。")
    else:
        weaknesses.append("当前未发现明显关键词缺口，但仍可增强项目结果和技术细节表达。")

    suggestions.append("建议将项目经历按照“业务场景 + 技术方案 + 个人职责 + 结果指标”的结构重写。")
    suggestions.append("建议突出 AI 应用开发、FastAPI、Prompt Engineering、RAG/Agent 和结构化输出能力。")

    result = MatchAnalysisResult(
        score=score,
        summary="该简历与岗位存在一定匹配度，建议针对岗位关键词进一步优化。",
        strengths=strengths,
        weaknesses=weaknesses,
        suggestions=suggestions,
        matched_keywords=matched_keywords,
        missing_keywords=missing_keywords,
        evidence=[],
        model_name="mock-analyzer-v1",
        status="fallback",
        analysis_mode="mock",
        error_message=error_message,
    )
    return result.model_dump()


def generate_analysis(resume: Resume, job: JobDescription) -> dict:
    resume_text = resume.raw_text or ""
    job_text = job.content or ""

    try:
        logger.info("Tool pipeline started")

        job_keywords = extract_keywords_tool(job_text)

        retrieved = retrieve_knowledge_tool(job_text=job_text, keywords=job_keywords, top_k=3)
        retrieved_context = retrieved.get("context", "")
        logger.info(f"RAG context length: {len(retrieved_context)}")

        llm_result = analyze_match_tool(
            resume_text=resume_text,
            job_text=job_text,
            retrieved_context=retrieved_context,
        )

        gap_result = keyword_gap_analysis_tool(
            resume_text=resume_text,
            matched_keywords=job_keywords,
        )
        matched_keywords = gap_result["matched_keywords"]
        missing_keywords = gap_result["missing_keywords"]

        llm_result["matched_keywords"] = matched_keywords
        llm_result["missing_keywords"] = missing_keywords
        llm_result["suggestions"] = rewrite_suggestions_tool(
            suggestions=llm_result.get("suggestions", []),
            matched_keywords=matched_keywords,
            missing_keywords=missing_keywords,
        )

        if retrieved.get("chunks"):
            llm_result["evidence"] = [
                {
                    "source": item.get("file_name", item.get("source", "knowledge")),
                    "content": item.get("content", ""),
                    "score": None,
                }
                for item in retrieved.get("chunks", [])
                if item.get("content")
            ]

        result = MatchAnalysisResult.model_validate(llm_result)
        logger.info("Tool pipeline finished successfully")
        return result.model_dump()

    except Exception as exc:
        logger.warning(f"Tool pipeline failed, fallback to mock: {repr(exc)}")
        return generate_mock_analysis(resume, job, error_message=repr(exc))


def create_match_result(
    db: Session,
    user_id: int,
    resume_id: int,
    job_id: int,
    analysis_result: dict,
) -> MatchResult:
    match_result = MatchResult(
        user_id=user_id,
        resume_id=resume_id,
        job_id=job_id,
        score=analysis_result.get("score"),
        summary=analysis_result.get("summary"),
        strengths=dumps_json(analysis_result.get("strengths")),
        weaknesses=dumps_json(analysis_result.get("weaknesses")),
        suggestions=dumps_json(analysis_result.get("suggestions")),
        matched_keywords=dumps_json(analysis_result.get("matched_keywords")),
        missing_keywords=dumps_json(analysis_result.get("missing_keywords")),
        evidence=dumps_json(analysis_result.get("evidence")),
        model_name=analysis_result.get("model_name"),
        analysis_mode=analysis_result.get("analysis_mode"),
        status=analysis_result.get("status", "success"),
        error_message=analysis_result.get("error_message"),
    )
    db.add(match_result)
    db.commit()
    db.refresh(match_result)
    return match_result


def get_match_result_by_user_id(db: Session, user_id: int) -> list[MatchResult]:
    return (
        db.query(MatchResult)
        .filter(MatchResult.user_id == user_id)
        .order_by(MatchResult.created_at.desc())
        .all()
    )


def get_match_result_by_id(db: Session, match_result_id: int) -> MatchResult | None:
    return db.query(MatchResult).filter(MatchResult.id == match_result_id).first()


def get_latest_match_result_by_user_id(db: Session, user_id: int) -> MatchResult | None:
    return (
        db.query(MatchResult)
        .filter(MatchResult.user_id == user_id)
        .order_by(MatchResult.created_at.desc())
        .first()
    )
