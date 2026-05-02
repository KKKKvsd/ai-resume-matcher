"""
app/api/metrics.py

LLM 调用监控端点。

用途:
- 工程师快速看 LLM 调用健康度(成功率、延迟、错误分布)
- 部署后可挂到外部监控

不引入新依赖。如果 settings 里有 METRICS_TOKEN(可选环境变量),则需要 token 鉴权;
没设就开放给登录用户。
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.config import settings
from app.utils.llm_client import LLM_STATS


router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


def _verify_metrics_token(token: str | None = Query(default=None, alias="token")) -> None:
    """
    可选的 token 鉴权。
    settings 里设了 METRICS_TOKEN 才校验,未设时直接开放。
    """
    expected = getattr(settings, "METRICS_TOKEN", None)
    if not expected:
        return
    if token != expected:
        raise HTTPException(status_code=401, detail="Invalid metrics token")


@router.get("/llm")
def get_llm_metrics(
    _: None = Depends(_verify_metrics_token),
) -> dict:
    """
    返回 LLM 调用聚合统计快照。

    示例响应:
    {
        "code": 0,
        "message": "ok",
        "data": {
            "total_calls": 124,
            "total_success": 119,
            "total_failures": 5,
            "total_retries": 8,
            "success_rate": 0.96,
            "avg_latency_ms": 2350.4,
            "total_prompt_tokens": 18432,
            "total_completion_tokens": 4210,
            "by_profile": {"default": 80, "heavy": 30, "fast": 14},
            "by_error_type": {"APITimeoutError": 3, "RateLimitError": 2}
        }
    }

    说明:
    - 进程内统计,worker 重启会清零(适合短期观测)
    - 长期审计应该把 LLMCallMetrics 写入 DB,本步暂不做
    """
    snapshot = LLM_STATS.snapshot()
    return {
        "code": 0,
        "message": "ok",
        "data": snapshot,
    }