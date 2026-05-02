"""
tests/eval/schema.py

Eval 框架的统一数据结构。

设计目标：
1. 一份 schema 同时覆盖三类评测：关键词抽取 / 匹配分析 / RAG 检索。
2. 每个样本独立可序列化为 JSONL 一行。
3. 评测结果可对比（baseline vs current），便于追踪 prompt 迭代。
"""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


EvalKind = Literal["keyword_extraction", "match_analysis", "rag_retrieval"]


class EvalSample(BaseModel):
    """单个评测样本。"""
    sample_id: str = Field(..., description="样本唯一标识。")
    kind: EvalKind = Field(..., description="评测类型。")
    notes: str = Field(default="", description="样本备注。")

    inputs: dict[str, Any] = Field(default_factory=dict)
    expected: dict[str, Any] = Field(default_factory=dict)


class SampleResult(BaseModel):
    """跑完一个样本的结果。"""
    sample_id: str
    kind: EvalKind

    actual_output: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, float] = Field(default_factory=dict)
    passed: bool = False
    failure_reasons: list[str] = Field(default_factory=list)

    latency_ms: Optional[float] = None
    error: Optional[str] = None


class EvalReport(BaseModel):
    """一次评测运行的完整报告。"""
    eval_kind: EvalKind
    run_id: str = Field(default_factory=lambda: datetime.utcnow().strftime("%Y%m%d_%H%M%S"))
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    label: str = Field(default="")
    sample_count: int = 0

    sample_results: list[SampleResult] = Field(default_factory=list)
    aggregated_metrics: dict[str, float] = Field(default_factory=dict)
    pass_rate: float = 0.0
    avg_latency_ms: Optional[float] = None
    error_count: int = 0

    def summary(self) -> str:
        lines = [
            f"=== Eval Report [{self.eval_kind}] {self.label or self.run_id} ===",
            f"Samples: {self.sample_count} | Passed: {int(self.pass_rate * self.sample_count)} "
            f"({self.pass_rate * 100:.1f}%) | Errors: {self.error_count}",
        ]
        if self.avg_latency_ms is not None:
            lines.append(f"Avg latency: {self.avg_latency_ms:.0f}ms")
        if self.aggregated_metrics:
            metric_str = " | ".join(
                f"{k}={v:.3f}" for k, v in self.aggregated_metrics.items()
            )
            lines.append(f"Metrics: {metric_str}")
        return "\n".join(lines)