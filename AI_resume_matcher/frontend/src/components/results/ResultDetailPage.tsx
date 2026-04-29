import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { AlertCircle, ArrowLeft, RefreshCw } from "lucide-react";
import { getMatchResultDetail } from "@/lib/api";
import type { MatchResult } from "@/types/api";

import Badge from "@/components/common/Badge";
import ErrorCard from "@/components/common/ErrorCard";
import LoadingCard from "@/components/common/LoadingCard";
import RawJsonPanel from "@/components/common/RawJsonPanel";

import AgentFollowUpPanel from "@/components/match/AgentFollowUpPanel";

import ResultScoreCard from "@/components/results/ResultScoreCard";
import ResultSummaryCard from "@/components/results/ResultSummaryCard";
import ResultAnalysisGrid from "@/components/results/ResultAnalysisGrid";
import ResultKeywordGrid from "@/components/results/ResultKeywordGrid";
import ResultEvidencePanel from "@/components/results/ResultEvidencePanel";

import {
  formatDate,
  safeArray,
  safeEvidence,
} from "@/lib/resultUtils";

export default function ResultDetailPage() {
  const params = useParams();
  const navigate = useNavigate();

  const resultId = Number(params.id);

  const [result, setResult] = useState<MatchResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadDetail() {
    if (!resultId || Number.isNaN(resultId)) {
      setError("无效的结果 ID");
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError("");

      const data = await getMatchResultDetail(resultId);

      console.log("详情接口返回：", data);

      setResult(data);
    } catch (err: any) {
      console.error("详情接口错误：", err);

      setError(
        err?.response?.data?.detail ||
          err?.response?.data?.message ||
          err?.message ||
          "加载详情失败"
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDetail();
  }, [resultId]);

  if (loading) {
    return <LoadingCard text="正在加载结果详情..." />;
  }

  if (error) {
    return <ErrorCard message={error} />;
  }

  if (!result) {
    return (
      <div className="rounded-3xl bg-white p-8 text-slate-500 shadow-sm">
        没有找到结果。
      </div>
    );
  }

  const strengths = safeArray(result.strengths);
  const weaknesses = safeArray(result.weaknesses);
  const suggestions = safeArray(result.suggestions);
  const matchedKeywords = safeArray(result.matched_keywords);
  const missingKeywords = safeArray(result.missing_keywords);
  const evidence = safeEvidence(result.evidence);

  return (
    <div className="space-y-6">
      <header className="rounded-3xl bg-white p-6 shadow-sm">
        <button
          onClick={() => navigate("/results")}
          className="mb-4 inline-flex items-center gap-2 rounded-2xl border px-4 py-2 text-sm text-slate-600 transition hover:bg-slate-50 hover:text-slate-950"
        >
          <ArrowLeft className="h-4 w-4" />
          返回历史结果
        </button>

        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
          <div>
            <h1 className="text-2xl font-semibold text-slate-950">
              Match Result #{result.id}
            </h1>

            <p className="mt-2 text-sm text-slate-500">
              Resume #{result.resume_id} · Job #{result.job_id}
            </p>

            <div className="mt-4 flex flex-wrap gap-2">
              <Badge>{result.status || "unknown status"}</Badge>
              <Badge>{result.analysis_mode || "unknown mode"}</Badge>
              {result.model_name && <Badge>{result.model_name}</Badge>}
              {result.created_at && (
                <Badge>{formatDate(result.created_at)}</Badge>
              )}
            </div>
          </div>

          <button
            onClick={loadDetail}
            className="inline-flex items-center justify-center gap-2 rounded-2xl border px-4 py-2 text-sm transition hover:bg-slate-50"
          >
            <RefreshCw className="h-4 w-4" />
            刷新
          </button>
        </div>
      </header>

      <section className="grid gap-6 lg:grid-cols-[260px_1fr]">
        <ResultScoreCard
          score={result.score}
          status={result.status}
          analysisMode={result.analysis_mode}
          modelName={result.model_name}
        />

        <ResultSummaryCard
          summary={result.summary}
          resumeId={result.resume_id}
          jobId={result.job_id}
          createdAt={result.created_at}
        />
      </section>

      {result.error_message && (
        <section className="rounded-3xl bg-red-50 p-6 text-red-700 shadow-sm">
          <div className="flex items-center gap-2 font-semibold">
            <AlertCircle className="h-5 w-5" />
            Error Message
          </div>

          <p className="mt-3 whitespace-pre-wrap text-sm leading-6">
            {result.error_message}
          </p>
        </section>
      )}

      <ResultAnalysisGrid
        strengths={strengths}
        weaknesses={weaknesses}
        suggestions={suggestions}
      />

      <ResultKeywordGrid
        matchedKeywords={matchedKeywords}
        missingKeywords={missingKeywords}
      />

      <ResultEvidencePanel evidence={evidence} />

      <AgentFollowUpPanel resultId={result.id} />

      <RawJsonPanel data={result} />
    </div>
  );
}