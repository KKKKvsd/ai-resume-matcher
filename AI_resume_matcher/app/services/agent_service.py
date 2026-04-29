import json
from typing import Any, Callable, Literal

from pydantic import ValidationError

from app.core.logger import logger
from app.schemas.agent import AgentPlan, AgentToolCall, AgentTraceStep
from app.services.tools_service import (
    analyze_match_tool,
    deepsearch_tool,
    extract_keywords_tool,
    generate_interview_questions_tool,
    generate_learning_plan_tool,
    keyword_gap_analysis_tool,
    resume_rewrite_tool,
    retrieve_knowledge_tool,
    rewrite_suggestions_tool,
)
from app.utils.llm_client import call_llm, clean_llm_json_text


Intent = Literal[
    "match_analysis",
    "keyword_gap_analysis",
    "resume_rewrite",
    "interview_questions",
    "learning_plan",
    "deepsearch",
    "follow_up_qa",
]


MAX_AGENT_STEPS = 8


TOOL_SPECS: dict[str, str] = {
    "extract_job_keywords": "从岗位 JD 中提取标准化技能关键词。",
    "analyze_keyword_gap": "比较简历与岗位关键词，输出已匹配关键词和缺失关键词。",
    "retrieve_knowledge": "从本地知识库检索岗位技能、简历表达和面试准备相关资料。",
    "deepsearch": "将复杂问题拆成多个子查询，多轮检索知识库并聚合证据。",
    "run_match_analysis": "调用 LLM 进行简历与岗位匹配分析，输出分数、优势、不足和建议。",
    "rewrite_resume": "根据岗位要求、匹配结果和关键词缺口生成简历改写建议。",
    "generate_interview_questions": "根据关键词缺口生成高频面试问题和回答提示。",
    "generate_learning_plan": "根据关键词缺口生成学习补齐计划。",
    "generate_final_answer": "汇总所有工具执行结果，生成最终答复。",
}


def classify_user_intent(user_query: str) -> Intent:
    """
    规则兜底意图识别。
    LLM Planner 不可用时使用。
    """
    query = (user_query or "").lower()

    if any(keyword in query for keyword in ["deepsearch", "deep search", "深度检索", "深度调研", "调研"]):
        intent: Intent = "deepsearch"
    elif any(keyword in query for keyword in ["面试", "面试题", "interview"]):
        intent = "interview_questions"
    elif any(keyword in query for keyword in ["学习", "补充", "计划", "路线"]):
        intent = "learning_plan"
    elif any(keyword in query for keyword in ["改写", "润色", "重写", "优化项目描述", "改简历"]):
        intent = "resume_rewrite"
    elif any(keyword in query for keyword in ["关键词", "缺口", "缺失", "匹配点", "技能差距"]):
        intent = "keyword_gap_analysis"
    elif any(keyword in query for keyword in ["分析", "匹配", "适合", "岗位", "jd"]):
        intent = "match_analysis"
    else:
        intent = "follow_up_qa"

    logger.info(f"classify_user_intent -> {intent}")
    return intent


def _build_rule_based_plan(query: str) -> AgentPlan:
    """
    LLM Planner 不可用时的稳定计划。
    """
    intent = classify_user_intent(query)

    common_steps = [
        AgentToolCall(
            tool_name="extract_job_keywords",
            reason="提取岗位关键词，作为所有后续工具的共享上下文。",
            input={},
        ),
        AgentToolCall(
            tool_name="analyze_keyword_gap",
            reason="识别简历中已经覆盖和仍然缺失的关键词。",
            input={},
        ),
    ]

    if intent == "keyword_gap_analysis":
        steps = common_steps + [
            AgentToolCall(tool_name="generate_final_answer", reason="总结关键词差距。", input={})
        ]
        style = "diagnostic"

    elif intent == "resume_rewrite":
        steps = common_steps + [
            AgentToolCall(tool_name="retrieve_knowledge", reason="检索简历表达规则和岗位技能要求。", input={"top_k": 3}),
            AgentToolCall(tool_name="rewrite_resume", reason="基于缺口和知识库生成简历改写建议。", input={}),
            AgentToolCall(tool_name="generate_final_answer", reason="汇总改写建议。", input={}),
        ]
        style = "resume_bullets"

    elif intent == "interview_questions":
        steps = common_steps + [
            AgentToolCall(tool_name="retrieve_knowledge", reason="检索相关面试准备知识。", input={"top_k": 3}),
            AgentToolCall(tool_name="generate_interview_questions", reason="基于关键词缺口生成面试题。", input={}),
            AgentToolCall(tool_name="generate_final_answer", reason="汇总面试准备建议。", input={}),
        ]
        style = "interview"

    elif intent == "learning_plan":
        steps = common_steps + [
            AgentToolCall(tool_name="generate_learning_plan", reason="基于缺失关键词生成学习计划。", input={}),
            AgentToolCall(tool_name="generate_final_answer", reason="汇总学习计划。", input={}),
        ]
        style = "actionable"

    elif intent == "deepsearch":
        steps = common_steps + [
            AgentToolCall(tool_name="deepsearch", reason="执行多子问题检索并聚合证据。", input={"top_k": 3}),
            AgentToolCall(tool_name="generate_final_answer", reason="基于 DeepSearch 证据生成结论。", input={}),
        ]
        style = "diagnostic"

    elif intent == "match_analysis":
        steps = common_steps + [
            AgentToolCall(tool_name="retrieve_knowledge", reason="检索岗位相关知识作为 LLM 上下文。", input={"top_k": 3}),
            AgentToolCall(tool_name="run_match_analysis", reason="执行完整简历岗位匹配分析。", input={}),
            AgentToolCall(tool_name="generate_final_answer", reason="汇总匹配分数和优化建议。", input={}),
        ]
        style = "diagnostic"

    else:
        steps = common_steps + [
            AgentToolCall(tool_name="retrieve_knowledge", reason="检索可能相关的知识库内容。", input={"top_k": 3}),
            AgentToolCall(tool_name="generate_final_answer", reason="基于已有上下文回答用户追问。", input={}),
        ]
        style = "actionable"

    return AgentPlan(
        intent=intent,
        goal=f"回答用户问题：{query}",
        steps=steps[:MAX_AGENT_STEPS],
        final_response_style=style,
        requires_human_review=False,
    )


def _build_planner_prompt(query: str, resume_text: str, job_text: str, latest_suggestions: list[str]) -> str:
    tool_descriptions = "\n".join(
        f"- {name}: {description}" for name, description in TOOL_SPECS.items()
    )

    return f"""
你是一个生产级求职 Agent 的 Planner。你需要根据用户请求，选择工具并生成一个可执行计划。

可用工具：
{tool_descriptions}

限制：
1. 只能使用上面列出的 tool_name。
2. 最多生成 {MAX_AGENT_STEPS} 个步骤。
3. 必须先使用 extract_job_keywords，再使用 analyze_keyword_gap，除非用户请求完全无关。
4. 复杂调研类问题使用 deepsearch。
5. 最后必须使用 generate_final_answer。
6. 只返回合法 JSON，不要 Markdown，不要解释。

返回 JSON 格式：
{{
  "intent": "match_analysis|keyword_gap_analysis|resume_rewrite|interview_questions|learning_plan|deepsearch|follow_up_qa",
  "goal": "本次任务目标",
  "steps": [
    {{
      "tool_name": "extract_job_keywords",
      "reason": "为什么调用该工具",
      "input": {{}}
    }}
  ],
  "final_response_style": "actionable|interview|resume_bullets|diagnostic",
  "requires_human_review": false
}}

用户问题：
{query}

岗位 JD 摘要：
{job_text[:1800]}

简历摘要：
{resume_text[:1800]}

已有建议：
{json.dumps(latest_suggestions or [], ensure_ascii=False)}
""".strip()


def _request_llm_plan(query: str, resume_text: str, job_text: str, latest_suggestions: list[str]) -> tuple[AgentPlan, str]:
    """
    使用 LLM 生成计划；失败时回退规则计划。
    """
    prompt = _build_planner_prompt(
        query=query,
        resume_text=resume_text,
        job_text=job_text,
        latest_suggestions=latest_suggestions,
    )

    try:
        raw = call_llm(prompt, temperature=0)
        cleaned = clean_llm_json_text(raw)
        data = json.loads(cleaned)
        plan = AgentPlan.model_validate(data)
        return _sanitize_plan(plan), "llm_planner"
    except (json.JSONDecodeError, ValidationError, ValueError, Exception) as error:
        logger.warning(f"LLM planner failed, fallback to rule plan: {repr(error)}")
        return _build_rule_based_plan(query), "rule_fallback"


def _sanitize_plan(plan: AgentPlan) -> AgentPlan:
    """
    防止 LLM Planner 产生不存在的工具或危险步骤。
    """
    sanitized_steps: list[AgentToolCall] = []
    seen_final = False

    for step in plan.steps[:MAX_AGENT_STEPS]:
        if step.tool_name not in TOOL_SPECS:
            logger.warning(f"Drop unknown tool from plan: {step.tool_name}")
            continue

        if step.tool_name == "generate_final_answer":
            seen_final = True

        sanitized_steps.append(step)

    if not sanitized_steps:
        sanitized_steps = _build_rule_based_plan(plan.goal).steps

    tool_names = [step.tool_name for step in sanitized_steps]

    if "extract_job_keywords" not in tool_names and plan.intent != "follow_up_qa":
        sanitized_steps.insert(
            0,
            AgentToolCall(
                tool_name="extract_job_keywords",
                reason="补充基础步骤：提取岗位关键词。",
                input={},
            ),
        )

    tool_names = [step.tool_name for step in sanitized_steps]
    if "analyze_keyword_gap" not in tool_names and plan.intent != "follow_up_qa":
        insert_at = 1 if sanitized_steps and sanitized_steps[0].tool_name == "extract_job_keywords" else 0
        sanitized_steps.insert(
            insert_at,
            AgentToolCall(
                tool_name="analyze_keyword_gap",
                reason="补充基础步骤：识别关键词差距。",
                input={},
            ),
        )

    if not seen_final:
        sanitized_steps.append(
            AgentToolCall(
                tool_name="generate_final_answer",
                reason="汇总所有工具结果，生成最终回答。",
                input={},
            )
        )

    plan.steps = sanitized_steps[:MAX_AGENT_STEPS]
    return plan


def _safe_short_output(output: Any, max_chars: int = 2500) -> Any:
    """
    限制 trace 中输出体积，避免 API 返回过大。
    """
    try:
        text = json.dumps(output, ensure_ascii=False)
        if len(text) <= max_chars:
            return output
        return {
            "truncated": True,
            "preview": text[:max_chars],
        }
    except TypeError:
        text = str(output)
        if len(text) <= max_chars:
            return text
        return {"truncated": True, "preview": text[:max_chars]}


def _build_final_answer_fallback(query: str, state: dict[str, Any]) -> str:
    """
    LLM final synthesizer 不可用时的兜底答案。
    """
    gap = state.get("keyword_gap", {})
    matched = gap.get("matched_keywords", [])
    missing = gap.get("missing_keywords", [])

    parts = [f"针对你的问题：{query}"]

    if state.get("match_analysis"):
        analysis = state["match_analysis"]
        parts.append(f"匹配总结：{analysis.get('summary', '')}")
        if analysis.get("score") is not None:
            parts.append(f"匹配分数：{analysis.get('score')}")

    if matched:
        parts.append("已匹配能力：" + "、".join(matched[:8]) + "。")

    if missing:
        parts.append("建议优先补齐：" + "、".join(missing[:8]) + "。")

    if state.get("resume_rewrite"):
        parts.append("简历改写建议：\n" + str(state["resume_rewrite"]))

    if state.get("interview_questions"):
        questions = state["interview_questions"].get("questions", [])
        question_text = "\n".join(
            f"- {item.get('question', item)}" if isinstance(item, dict) else f"- {item}"
            for item in questions[:6]
        )
        parts.append("建议准备这些面试题：\n" + question_text)

    if state.get("learning_plan"):
        parts.append("学习计划：" + json.dumps(state["learning_plan"], ensure_ascii=False))

    if len(parts) == 1:
        parts.append("建议先完成一次岗位匹配分析，再基于关键词缺口进行简历改写和面试准备。")

    return "\n\n".join(part for part in parts if part)


def _synthesize_final_answer(query: str, plan: AgentPlan, state: dict[str, Any], trace: list[dict[str, Any]]) -> str:
    """
    用 LLM 汇总工具结果；失败时使用 deterministic fallback。
    """
    compact_state = {
        "job_keywords": state.get("job_keywords", []),
        "keyword_gap": state.get("keyword_gap", {}),
        "knowledge_chunks_count": len(state.get("knowledge", {}).get("chunks", [])) if isinstance(state.get("knowledge"), dict) else 0,
        "deepsearch": state.get("deepsearch", {}),
        "match_analysis": state.get("match_analysis", {}),
        "resume_rewrite": state.get("resume_rewrite", ""),
        "interview_questions": state.get("interview_questions", {}),
        "learning_plan": state.get("learning_plan", {}),
    }

    prompt = f"""
你是一个 AI 求职 Agent 的最终回答生成器。

请基于工具执行结果回答用户问题。

要求：
1. 回答要具体、可执行。
2. 不要编造工具结果中没有的经历、公司或指标。
3. 如果是简历改写，给出可以直接放进简历的 bullet。
4. 如果是面试准备，按“重点知识点 + 高频问题 + 准备建议”输出。
5. 如果是匹配分析，按“匹配结论 + 已匹配能力 + 缺口 + 下一步优化”输出。

用户问题：
{query}

Agent 计划：
{plan.model_dump_json()}

工具结果：
{json.dumps(compact_state, ensure_ascii=False, default=str)}

执行轨迹：
{json.dumps(trace, ensure_ascii=False, default=str)}
""".strip()

    try:
        return call_llm(prompt, temperature=0.2).strip()
    except Exception as error:
        logger.warning(f"Final answer synthesis failed, fallback used: {repr(error)}")
        return _build_final_answer_fallback(query=query, state=state)


def _execute_tool(
    step: AgentToolCall,
    state: dict[str, Any],
    resume_text: str,
    job_text: str,
    latest_suggestions: list[str],
) -> Any:
    """
    Tool executor.
    所有工具统一在这里调度，便于日志、权限控制、输入输出校验和后续监控。
    """
    tool_name = step.tool_name
    tool_input = step.input or {}

    if tool_name == "extract_job_keywords":
        output = extract_keywords_tool(job_text)
        state["job_keywords"] = output
        return output

    if tool_name == "analyze_keyword_gap":
        keywords = state.get("job_keywords") or extract_keywords_tool(job_text)
        state["job_keywords"] = keywords
        output = keyword_gap_analysis_tool(resume_text=resume_text, matched_keywords=keywords)
        state["keyword_gap"] = output
        return output

    if tool_name == "retrieve_knowledge":
        keywords = state.get("job_keywords") or extract_keywords_tool(job_text)
        top_k = int(tool_input.get("top_k", 3))
        output = retrieve_knowledge_tool(job_text=job_text, keywords=keywords, top_k=top_k)
        state["knowledge"] = output
        return output

    if tool_name == "deepsearch":
        keywords = state.get("job_keywords") or extract_keywords_tool(job_text)
        top_k = int(tool_input.get("top_k", 3))
        output = deepsearch_tool(
            job_text=job_text,
            resume_text=resume_text,
            keywords=keywords,
            top_k=top_k,
        )
        state["deepsearch"] = output
        return output

    if tool_name == "run_match_analysis":
        knowledge = state.get("knowledge")
        if not knowledge:
            keywords = state.get("job_keywords") or extract_keywords_tool(job_text)
            knowledge = retrieve_knowledge_tool(job_text=job_text, keywords=keywords, top_k=3)
            state["knowledge"] = knowledge

        output = analyze_match_tool(
            resume_text=resume_text,
            job_text=job_text,
            retrieved_context=knowledge.get("context", "") if isinstance(knowledge, dict) else "",
        )

        gap = state.get("keyword_gap", {})
        output["matched_keywords"] = gap.get("matched_keywords", output.get("matched_keywords", []))
        output["missing_keywords"] = gap.get("missing_keywords", output.get("missing_keywords", []))
        output["suggestions"] = rewrite_suggestions_tool(
            suggestions=output.get("suggestions", []),
            matched_keywords=output.get("matched_keywords", []),
            missing_keywords=output.get("missing_keywords", []),
        )
        state["match_analysis"] = output
        return output

    if tool_name == "rewrite_resume":
        gap = state.get("keyword_gap", {})
        suggestions = latest_suggestions[:]
        if state.get("match_analysis"):
            suggestions.extend(state["match_analysis"].get("suggestions", []))

        output = resume_rewrite_tool(
            resume_text=resume_text,
            job_text=job_text,
            suggestions=suggestions,
            missing_keywords=gap.get("missing_keywords", []),
        )
        state["resume_rewrite"] = output
        return output

    if tool_name == "generate_interview_questions":
        gap = state.get("keyword_gap", {})
        output = generate_interview_questions_tool(
            missing_keywords=gap.get("missing_keywords", []),
            matched_keywords=gap.get("matched_keywords", []),
        )
        state["interview_questions"] = output
        return output

    if tool_name == "generate_learning_plan":
        gap = state.get("keyword_gap", {})
        output = generate_learning_plan_tool(missing_keywords=gap.get("missing_keywords", []))
        state["learning_plan"] = output
        return output

    if tool_name == "generate_final_answer":
        # 由 _synthesize_final_answer 在主流程最后统一生成；这里返回占位，确保 trace 完整。
        return {"message": "Final answer will be synthesized after all tool calls."}

    raise ValueError(f"Unsupported tool: {tool_name}")


def _calculate_confidence(mode: str, trace: list[dict[str, Any]], state: dict[str, Any]) -> float:
    success_count = sum(1 for item in trace if item.get("status") == "success")
    total_count = max(len(trace), 1)
    base = success_count / total_count

    if mode == "llm_planner":
        base += 0.08

    if state.get("knowledge") or state.get("deepsearch"):
        base += 0.05

    if state.get("match_analysis"):
        base += 0.05

    return max(0.1, min(0.95, round(base, 2)))


def run_agent_pipeline(
    query: str,
    resume_text: str,
    job_text: str,
    latest_suggestions: list[str] | None = None,
) -> dict[str, Any]:
    """
    Production-style Agent Pipeline:
    1. LLM Planner 生成工具计划
    2. Plan Sanitizer 校验工具名、步骤数、必需步骤
    3. Tool Executor 执行工具并写入 working memory
    4. Final Synthesizer 汇总工具结果
    5. Trace / confidence / warnings 返回给前端，便于调试和展示
    """
    latest_suggestions = latest_suggestions or []
    warnings: list[str] = []
    state: dict[str, Any] = {
        "query": query,
        "latest_suggestions": latest_suggestions,
        "job_keywords": [],
        "keyword_gap": {},
        "knowledge": {},
        "deepsearch": {},
        "match_analysis": {},
        "resume_rewrite": "",
        "interview_questions": {},
        "learning_plan": {},
    }

    plan, mode = _request_llm_plan(
        query=query,
        resume_text=resume_text,
        job_text=job_text,
        latest_suggestions=latest_suggestions,
    )

    if mode == "rule_fallback":
        warnings.append("LLM Planner 不可用，已使用规则兜底计划。")

    trace: list[dict[str, Any]] = []

    for index, step in enumerate(plan.steps[:MAX_AGENT_STEPS], start=1):
        try:
            output = _execute_tool(
                step=step,
                state=state,
                resume_text=resume_text,
                job_text=job_text,
                latest_suggestions=latest_suggestions,
            )

            trace_step = AgentTraceStep(
                step_id=index,
                tool_name=step.tool_name,
                reason=step.reason,
                input=step.input,
                output=_safe_short_output(output),
                status="success",
                error=None,
            )

        except Exception as error:
            logger.error(f"Agent tool failed: tool={step.tool_name}, error={repr(error)}")
            warnings.append(f"工具 {step.tool_name} 执行失败：{repr(error)}")

            trace_step = AgentTraceStep(
                step_id=index,
                tool_name=step.tool_name,
                reason=step.reason,
                input=step.input,
                output=None,
                status="failed",
                error=repr(error),
            )

        trace.append(trace_step.model_dump())

    final_answer = _synthesize_final_answer(
        query=query,
        plan=plan,
        state=state,
        trace=trace,
    )

    result = {
        "job_keywords": state.get("job_keywords", []),
        "keyword_gap": state.get("keyword_gap", {}),
        "knowledge": _safe_short_output(state.get("knowledge", {})),
        "deepsearch": _safe_short_output(state.get("deepsearch", {})),
        "match_analysis": _safe_short_output(state.get("match_analysis", {})),
        "resume_rewrite": state.get("resume_rewrite", ""),
        "interview_questions": state.get("interview_questions", {}),
        "learning_plan": state.get("learning_plan", {}),
    }

    return {
        "intent": plan.intent,
        "final_answer": final_answer,
        "plan": plan.model_dump(),
        "steps": trace,
        "result": result,
        "confidence": _calculate_confidence(mode=mode, trace=trace, state=state),
        "mode": mode,
        "warnings": warnings,
    }
