"""
tests/eval/run_eval.py

主入口。

使用：
    # 跑所有评测
    python -m tests.eval.run_eval --kind all --label baseline

    # 只跑关键词评测
    python -m tests.eval.run_eval --kind keyword_extraction --label prompt_v2

    # dry-run 模式(不调真实 API,验证 runner 流程)
    python -m tests.eval.run_eval --kind keyword_extraction --dry-run

    # 对比两次报告
    python -m tests.eval.run_eval compare baseline.json prompt_v2.json
"""

import argparse
import sys
from pathlib import Path

from tests.eval.runner import compare_reports, load_dataset, run_eval, save_report
from tests.eval.schema import EvalReport


DEFAULT_DATASET = "tests/eval/datasets/dataset_v1.jsonl"


# ===========================================================================
# 真实被测函数适配器
# ===========================================================================
def _adapter_keyword_extraction(inputs: dict):
    from app.services.tools_service import extract_keywords_tool
    return extract_keywords_tool(inputs.get("job_text", ""))


def _adapter_match_analysis(inputs: dict):
    from app.services.tools_service import analyze_match_tool
    return analyze_match_tool(
        resume_text=inputs.get("resume_text", ""),
        job_text=inputs.get("job_text", ""),
        retrieved_context=inputs.get("retrieved_context", ""),
    )


def _adapter_rag_retrieval(inputs: dict):
    from app.utils.rag_retriever import retrieve_knowledge_hybrid
    return retrieve_knowledge_hybrid(
        query=inputs.get("query", ""),
        top_k=inputs.get("top_k", 5),
    )


# ===========================================================================
# Dry-run mock
# ===========================================================================
def _dry_run_keyword(inputs: dict):
    import re
    job_text = inputs.get("job_text", "")
    candidates = re.findall(r"[A-Z][a-zA-Z]+", job_text)
    return list(set(candidates))[:10]


def _dry_run_match(inputs: dict):
    return {
        "score": 75.0,
        "summary": "Mock summary",
        "strengths": ["Python 基础", "LLM 应用经验"],
        "weaknesses": ["Agent 项目较少"],
        "suggestions": ["补充 Agent 项目"],
        "matched_keywords": ["Python", "LLM"],
        "missing_keywords": ["Agent"],
    }


def _dry_run_rag(inputs: dict):
    from app.schemas.retrieval import RetrievalResult, RetrievedChunk
    return RetrievalResult(
        query=inputs.get("query", ""),
        chunks=[
            RetrievedChunk(
                content=f"Mock chunk {i} for query: {inputs.get('query', '')}",
                file_name="mock.md",
                rank=i,
            )
            for i in range(1, 4)
        ],
    )


def cmd_run(args):
    samples = load_dataset(args.dataset)
    print(f"Loaded {len(samples)} samples from {args.dataset}")

    kinds_to_run = (
        ["keyword_extraction", "match_analysis", "rag_retrieval"]
        if args.kind == "all"
        else [args.kind]
    )

    all_reports: list[EvalReport] = []
    for kind in kinds_to_run:
        kind_samples = [s for s in samples if s.kind == kind]
        if not kind_samples:
            print(f"[skip] No samples for kind={kind}")
            continue

        if args.dry_run:
            test_fn = {
                "keyword_extraction": _dry_run_keyword,
                "match_analysis": _dry_run_match,
                "rag_retrieval": _dry_run_rag,
            }[kind]
        else:
            test_fn = {
                "keyword_extraction": _adapter_keyword_extraction,
                "match_analysis": _adapter_match_analysis,
                "rag_retrieval": _adapter_rag_retrieval,
            }[kind]

        print(f"\nRunning eval [{kind}] on {len(kind_samples)} samples...")
        report = run_eval(
            samples=kind_samples,
            test_function=test_fn,
            eval_kind=kind,
            label=args.label,
        )
        print(report.summary())

        failures = [r for r in report.sample_results if not r.passed]
        if failures:
            print(f"\n--- {len(failures)} Failures ---")
            for f in failures[:5]:
                print(f"  [{f.sample_id}] {'; '.join(f.failure_reasons)}")

        if not args.no_save:
            path = save_report(report)
            print(f"Report saved to: {path}")

        all_reports.append(report)

    total_failed = sum(
        1 for r in all_reports for s in r.sample_results if not s.passed
    )
    if total_failed > 0 and not args.allow_failures:
        print(f"\n❌ {total_failed} samples failed.")
        sys.exit(1)
    print("\n✅ All evaluations completed.")


def cmd_compare(args):
    baseline = EvalReport.model_validate_json(Path(args.baseline).read_text(encoding="utf-8"))
    current = EvalReport.model_validate_json(Path(args.current).read_text(encoding="utf-8"))
    print(compare_reports(baseline, current))


def main():
    parser = argparse.ArgumentParser(description="AI Resume Matcher Eval")
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument(
        "--kind",
        choices=["all", "keyword_extraction", "match_analysis", "rag_retrieval"],
        default="all",
    )
    parser.add_argument("--label", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-save", action="store_true")
    parser.add_argument("--allow-failures", action="store_true")

    sub = parser.add_subparsers(dest="cmd")
    cmp_p = sub.add_parser("compare", help="对比两次报告")
    cmp_p.add_argument("baseline")
    cmp_p.add_argument("current")

    args = parser.parse_args()
    if args.cmd == "compare":
        cmd_compare(args)
    else:
        cmd_run(args)


if __name__ == "__main__":
    main()