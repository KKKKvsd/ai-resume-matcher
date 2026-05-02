"""
tests/eval/runner.py

Eval runner: 加载数据集 → 跑评测 → 聚合报告。
"""

import json
import time
import traceback
from pathlib import Path
from typing import Callable, Optional

from tests.eval.metrics import (
    absolute_error,
    aggregate_mean,
    hit_rate,
    mean_absolute_error,
    mrr_at_k,
    must_not_include_violations,
    precision_recall_f1,
)
from tests.eval.schema import EvalReport, EvalSample, SampleResult


def load_dataset(path: str | Path) -> list[EvalSample]:
    """从 JSONL 文件加载评测数据集。"""
    samples: list[EvalSample] = []
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Dataset not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                data = json.loads(line)
                samples.append(EvalSample.model_validate(data))
            except (json.JSONDecodeError, Exception) as e:
                raise ValueError(f"Invalid sample at line {line_num}: {repr(e)}")

    return samples


def save_report(report: EvalReport, output_dir: str | Path = "tests/eval/reports") -> Path:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    label = report.label or "unlabeled"
    file_path = out_dir / f"{report.eval_kind}_{label}_{report.run_id}.json"
    file_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return file_path


# ===========================================================================
# 单样本评测器
# ===========================================================================
def evaluate_keyword_extraction(sample: EvalSample, extracted: list[str]) -> SampleResult:
    must_include = sample.expected.get("must_include", []) or []
    must_not_include = sample.expected.get("must_not_include", []) or []

    prf = precision_recall_f1(predicted=extracted, expected=must_include)
    violations = must_not_include_violations(extracted, must_not_include)

    metrics = {
        "precision": prf["precision"],
        "recall": prf["recall"],
        "f1": prf["f1"],
        "violations": float(violations),
    }

    failure_reasons: list[str] = []
    if prf["f1"] < 0.7:
        failure_reasons.append(f"F1 too low: {prf['f1']:.3f} < 0.7")
    if violations > 0:
        failure_reasons.append(f"{violations} forbidden keywords leaked")

    return SampleResult(
        sample_id=sample.sample_id,
        kind=sample.kind,
        actual_output={"extracted_keywords": extracted},
        metrics=metrics,
        passed=len(failure_reasons) == 0,
        failure_reasons=failure_reasons,
    )


def evaluate_match_analysis(sample: EvalSample, analysis: dict) -> SampleResult:
    score_min = float(sample.expected.get("score_min", 0))
    score_max = float(sample.expected.get("score_max", 100))
    required_strengths = sample.expected.get("required_strengths", []) or []
    required_weaknesses = sample.expected.get("required_weaknesses", []) or []

    metrics: dict[str, float] = {}
    failure_reasons: list[str] = []

    score = analysis.get("score")
    if score is None or not isinstance(score, (int, float)):
        metrics["parsed_ok"] = 0.0
        metrics["score_error"] = float(score_max - score_min)
        failure_reasons.append("Score field missing or non-numeric")
    else:
        metrics["parsed_ok"] = 1.0
        metrics["score_error"] = absolute_error(float(score), score_min, score_max)
        if metrics["score_error"] > 15:
            failure_reasons.append(f"Score deviation too large: {metrics['score_error']:.1f}")

    if required_strengths:
        strengths_text = " ".join(analysis.get("strengths", []) or []).lower()
        hits = sum(1 for s in required_strengths if s.lower() in strengths_text)
        metrics["strengths_recall"] = hits / len(required_strengths)
        if metrics["strengths_recall"] < 0.5:
            failure_reasons.append(f"Strengths recall too low: {metrics['strengths_recall']:.2f}")
    else:
        metrics["strengths_recall"] = 1.0

    if required_weaknesses:
        weak_text = " ".join(analysis.get("weaknesses", []) or []).lower()
        hits = sum(1 for w in required_weaknesses if w.lower() in weak_text)
        metrics["weaknesses_recall"] = hits / len(required_weaknesses)
        if metrics["weaknesses_recall"] < 0.5:
            failure_reasons.append(f"Weaknesses recall too low: {metrics['weaknesses_recall']:.2f}")
    else:
        metrics["weaknesses_recall"] = 1.0

    return SampleResult(
        sample_id=sample.sample_id,
        kind=sample.kind,
        actual_output={"analysis": analysis},
        metrics=metrics,
        passed=len(failure_reasons) == 0,
        failure_reasons=failure_reasons,
    )


def evaluate_rag_retrieval(sample: EvalSample, retrieved_chunks: list[dict]) -> SampleResult:
    must_retrieve_keywords = sample.expected.get("must_retrieve_keywords", []) or []
    contents = [c.get("content", "") for c in retrieved_chunks]

    metrics = {
        "hit_rate": hit_rate(contents, must_retrieve_keywords),
        "mrr_at_5": mrr_at_k(contents, must_retrieve_keywords, k=5),
        "retrieved_count": float(len(contents)),
    }

    failure_reasons: list[str] = []
    if metrics["hit_rate"] < 0.5:
        failure_reasons.append(f"Hit rate too low: {metrics['hit_rate']:.2f}")
    if metrics["mrr_at_5"] == 0 and must_retrieve_keywords:
        failure_reasons.append("No relevant chunk in top-5")

    return SampleResult(
        sample_id=sample.sample_id,
        kind=sample.kind,
        actual_output={"chunks": retrieved_chunks},
        metrics=metrics,
        passed=len(failure_reasons) == 0,
        failure_reasons=failure_reasons,
    )


# ===========================================================================
# 主入口
# ===========================================================================
def run_eval(
    samples: list[EvalSample],
    test_function: Callable,
    eval_kind: str,
    label: str = "",
    sample_evaluator: Optional[Callable] = None,
) -> EvalReport:
    if sample_evaluator is None:
        sample_evaluator = {
            "keyword_extraction": _default_keyword_evaluator,
            "match_analysis": _default_match_evaluator,
            "rag_retrieval": _default_rag_evaluator,
        }.get(eval_kind)
        if sample_evaluator is None:
            raise ValueError(f"Unknown eval_kind: {eval_kind}")

    sample_results: list[SampleResult] = []
    error_count = 0
    latencies: list[float] = []

    for sample in samples:
        if sample.kind != eval_kind:
            continue

        start = time.perf_counter()
        try:
            output = test_function(sample.inputs)
            latency_ms = (time.perf_counter() - start) * 1000
            latencies.append(latency_ms)
            result = sample_evaluator(sample, output)
            result.latency_ms = latency_ms
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            error_count += 1
            result = SampleResult(
                sample_id=sample.sample_id,
                kind=sample.kind,
                error=f"{type(exc).__name__}: {repr(exc)}\n{traceback.format_exc()[:400]}",
                latency_ms=latency_ms,
                passed=False,
                failure_reasons=["Execution exception"],
            )
        sample_results.append(result)

    aggregated = _aggregate_metrics(sample_results)
    pass_rate = (
        sum(1 for r in sample_results if r.passed) / len(sample_results)
        if sample_results else 0.0
    )
    avg_latency = aggregate_mean(latencies) if latencies else None

    return EvalReport(
        eval_kind=eval_kind,
        label=label,
        sample_count=len(sample_results),
        sample_results=sample_results,
        aggregated_metrics=aggregated,
        pass_rate=pass_rate,
        avg_latency_ms=avg_latency,
        error_count=error_count,
    )


def _aggregate_metrics(sample_results: list[SampleResult]) -> dict[str, float]:
    if not sample_results:
        return {}
    all_keys: set[str] = set()
    for r in sample_results:
        all_keys.update(r.metrics.keys())

    aggregated: dict[str, float] = {}
    for key in all_keys:
        values = [r.metrics[key] for r in sample_results if key in r.metrics]
        if values:
            if key in {"score_error"}:
                aggregated[f"mae_{key}"] = mean_absolute_error(values)
            else:
                aggregated[key] = aggregate_mean(values)
    return aggregated


def _default_keyword_evaluator(sample, output):
    if isinstance(output, list):
        extracted = output
    elif hasattr(output, "to_legacy_list"):
        extracted = output.to_legacy_list()
    elif isinstance(output, dict) and "keywords" in output:
        extracted = [
            kw.get("name") if isinstance(kw, dict) else str(kw)
            for kw in output["keywords"]
        ]
    else:
        extracted = []
    return evaluate_keyword_extraction(sample, extracted)


def _default_match_evaluator(sample, output):
    if not isinstance(output, dict):
        output = {"score": None}
    return evaluate_match_analysis(sample, output)


def _default_rag_evaluator(sample, output):
    if hasattr(output, "chunks"):
        chunks = [
            {"content": c.content if hasattr(c, "content") else c.get("content", "")}
            for c in output.chunks
        ]
    elif isinstance(output, list):
        chunks = output
    else:
        chunks = []
    return evaluate_rag_retrieval(sample, chunks)


def compare_reports(baseline: EvalReport, current: EvalReport) -> str:
    if baseline.eval_kind != current.eval_kind:
        return f"Cannot compare different kinds: {baseline.eval_kind} vs {current.eval_kind}"

    lines = [
        f"=== Eval Comparison [{current.eval_kind}] ===",
        f"Baseline: {baseline.label or baseline.run_id} (n={baseline.sample_count})",
        f"Current : {current.label or current.run_id} (n={current.sample_count})",
        "",
        f"Pass rate : {baseline.pass_rate * 100:.1f}% → {current.pass_rate * 100:.1f}% "
        f"({_fmt_diff(current.pass_rate - baseline.pass_rate, percent=True)})",
    ]
    if baseline.avg_latency_ms and current.avg_latency_ms:
        lines.append(f"Latency   : {baseline.avg_latency_ms:.0f}ms → {current.avg_latency_ms:.0f}ms")

    all_keys = set(baseline.aggregated_metrics) | set(current.aggregated_metrics)
    for key in sorted(all_keys):
        b = baseline.aggregated_metrics.get(key)
        c = current.aggregated_metrics.get(key)
        if b is None or c is None:
            continue
        better_when_lower = key.startswith("mae_") or "violations" in key
        diff = c - b
        symbol = "✓" if (
            (diff < 0 and better_when_lower) or (diff > 0 and not better_when_lower)
        ) else ("=" if diff == 0 else "✗")
        lines.append(f"{key:25s}: {b:.3f} → {c:.3f} ({_fmt_diff(diff)}) {symbol}")
    return "\n".join(lines)


def _fmt_diff(diff: float, percent: bool = False) -> str:
    if percent:
        return f"{'+' if diff >= 0 else ''}{diff * 100:.1f}pp"
    return f"{'+' if diff >= 0 else ''}{diff:.3f}"