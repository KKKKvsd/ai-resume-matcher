"""
tests/eval/metrics.py

评测指标计算。

为什么自己写而不用 sklearn:
- 每个函数 10 行内,用不上 sklearn 的 100MB 依赖。
- 边界情况可以更精确控制(空集 F1=0 还是 1 这种细节)。

每个指标都做了边界处理(空集、除零、None)。
"""

from typing import Iterable


def precision_recall_f1(predicted: Iterable[str], expected: Iterable[str]) -> dict[str, float]:
    """关键词集合的 P/R/F1。大小写不敏感、自动 trim。"""
    pred_set = {s.strip().lower() for s in predicted if s and s.strip()}
    exp_set = {s.strip().lower() for s in expected if s and s.strip()}

    if not exp_set and not pred_set:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    if not pred_set:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    if not exp_set:
        return {"precision": 0.0, "recall": 1.0, "f1": 0.0}

    intersection = pred_set & exp_set
    precision = len(intersection) / len(pred_set)
    recall = len(intersection) / len(exp_set)
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return {"precision": precision, "recall": recall, "f1": f1}


def must_not_include_violations(predicted: Iterable[str], must_not_include: Iterable[str]) -> int:
    """统计 predicted 中触碰 forbidden 列表的关键词数。"""
    pred_set = {s.strip().lower() for s in predicted if s and s.strip()}
    forbidden = {s.strip().lower() for s in must_not_include if s and s.strip()}
    return len(pred_set & forbidden)


def absolute_error(actual: float, expected_min: float, expected_max: float) -> float:
    """区间偏差。actual 在 [min, max] 内 → 0,否则距离最近边界的距离。"""
    if expected_min <= actual <= expected_max:
        return 0.0
    if actual < expected_min:
        return expected_min - actual
    return actual - expected_max


def mean_absolute_error(errors: Iterable[float]) -> float:
    errors_list = [e for e in errors if e is not None]
    if not errors_list:
        return 0.0
    return sum(errors_list) / len(errors_list)


def hit_rate(retrieved_contents: Iterable[str], must_retrieve_keywords: Iterable[str]) -> float:
    """所有 chunk 文本中,期望关键词的覆盖比例。"""
    keywords = [k.strip().lower() for k in must_retrieve_keywords if k and k.strip()]
    if not keywords:
        return 1.0
    combined = " ".join(retrieved_contents).lower()
    hit_count = sum(1 for k in keywords if k in combined)
    return hit_count / len(keywords)


def mrr_at_k(retrieved_contents: Iterable[str], must_retrieve_keywords: Iterable[str], k: int = 5) -> float:
    """Mean Reciprocal Rank @ K。第一条命中关键词的 chunk 在第几名。"""
    contents = list(retrieved_contents)[:k]
    keywords = [kw.strip().lower() for kw in must_retrieve_keywords if kw and kw.strip()]
    if not keywords or not contents:
        return 0.0
    for i, content in enumerate(contents, start=1):
        if any(kw in content.lower() for kw in keywords):
            return 1.0 / i
    return 0.0


def aggregate_mean(values: Iterable[float]) -> float:
    values_list = [v for v in values if v is not None]
    if not values_list:
        return 0.0
    return sum(values_list) / len(values_list)