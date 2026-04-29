import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Lightbulb,
  RefreshCw,
  Search,
  Target,
  XCircle,
} from "lucide-react";
import { getMatchResultDetail } from "../lib/api";
import type { MatchResult } from "../types/api";
import AgentFollowUpPanel from "@/components/match/AgentFollowUpPanel";
import RawJsonPanel from "@/components/common/RawJsonPanel";

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
    return (
      <div className="rounded-3xl bg-white p-8 text-slate-500 shadow-sm">
        正在加载详情...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-3 rounded-3xl bg-red-50 p-8 text-red-700 shadow-sm">
        <AlertCircle className="h-5 w-5 shrink-0" />
        <span>{error}</span>
      </div>
    );
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
        <div className="rounded-3xl bg-slate-950 p-6 text-center text-white shadow-sm">
          <div className="text-sm text-white/50">匹配分</div>

          <div className="mt-3 text-6xl font-semibold">
            {result.score ?? "-"}
          </div>

          <div className="mt-5 text-sm text-white/50">
            {getScoreLabel(result.score)}
          </div>
        </div>

        <div className="rounded-3xl bg-white p-6 shadow-sm">
          <div className="flex items-center gap-2">
            <Target className="h-5 w-5 text-slate-700" />
            <h2 className="font-semibold text-slate-950">AI 总结</h2>
          </div>

          <p className="mt-4 whitespace-pre-wrap leading-7 text-slate-600">
            {result.summary || "暂无 summary"}
          </p>
        </div>
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

      <section className="grid gap-4 lg:grid-cols-3">
        <InfoCard
          title="优势"
          icon={<CheckCircle2 className="h-5 w-5 text-emerald-600" />}
          items={strengths}
          emptyText="暂无优势分析"
        />

        <InfoCard
          title="不足"
          icon={<XCircle className="h-5 w-5 text-amber-600" />}
          items={weaknesses}
          emptyText="暂无不足分析"
        />

        <InfoCard
          title="优化建议"
          icon={<Lightbulb className="h-5 w-5 text-sky-600" />}
          items={suggestions}
          emptyText="暂无优化建议"
        />
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <KeywordCard
          title="已匹配关键词"
          items={matchedKeywords}
          emptyText="暂无匹配关键词"
        />

        <KeywordCard
          title="缺失关键词"
          items={missingKeywords}
          emptyText="暂无缺失关键词"
        />
      </section>

      <section className="rounded-3xl bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2">
          <Search className="h-5 w-5 text-slate-700" />
          <h2 className="font-semibold text-slate-950">RAG Evidence</h2>
        </div>

        <p className="mt-2 text-sm text-slate-500">
          这里展示后端返回的 evidence，用来解释 AI 分析参考了哪些知识片段。
        </p>

        {evidence.length === 0 ? (
          <div className="mt-5 rounded-2xl bg-slate-50 p-5 text-sm text-slate-400">
            暂无 evidence
          </div>
        ) : (
          <div className="mt-5 space-y-3">
            {evidence.map((item, index) => (
              <div
                key={index}
                className="rounded-2xl border border-slate-200 p-4"
              >
                <div className="mb-2 text-sm font-semibold text-slate-950">
                  Evidence #{index + 1}
                </div>

                <pre className="overflow-auto whitespace-pre-wrap rounded-xl bg-slate-50 p-3 text-xs leading-6 text-slate-600">
                  {safeStringify(item)}
                </pre>
              </div>
            ))}
          </div>
        )}
      </section>

      <AgentFollowUpPanel resultId={result.id} />
      <RawJsonPanel data={result} />
    </div>
  );
}

function InfoCard({
  title,
  icon,
  items,
  emptyText,
}: {
  title: string;
  icon: React.ReactNode;
  items: string[];
  emptyText: string;
}) {
  return (
    <div className="rounded-3xl bg-white p-6 shadow-sm">
      <div className="flex items-center gap-2 font-semibold text-slate-950">
        {icon}
        {title}
      </div>

      {items.length === 0 ? (
        <p className="mt-4 rounded-2xl bg-slate-50 p-4 text-sm text-slate-400">
          {emptyText}
        </p>
      ) : (
        <ul className="mt-4 space-y-3 text-sm leading-6 text-slate-600">
          {items.map((item, index) => (
            <li key={`${title}-${index}`}>• {item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function KeywordCard({
  title,
  items,
  emptyText,
}: {
  title: string;
  items: string[];
  emptyText: string;
}) {
  return (
    <div className="rounded-3xl bg-white p-6 shadow-sm">
      <h2 className="font-semibold text-slate-950">{title}</h2>

      {items.length === 0 ? (
        <p className="mt-4 rounded-2xl bg-slate-50 p-4 text-sm text-slate-400">
          {emptyText}
        </p>
      ) : (
        <div className="mt-4 flex flex-wrap gap-2">
          {items.map((item, index) => (
            <span
              key={`${item}-${index}`}
              className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600"
            >
              {item}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
      {children}
    </span>
  );
}

function safeArray(value: unknown): string[] {
  if (!value) return [];

  if (Array.isArray(value)) {
    return value.map((item) => {
      if (typeof item === "string") return item;
      return safeStringify(item);
    });
  }

  if (typeof value === "string") {
    const trimmed = value.trim();

    if (!trimmed) return [];

    try {
      const parsed = JSON.parse(trimmed);

      if (Array.isArray(parsed)) {
        return parsed.map((item) => {
          if (typeof item === "string") return item;
          return safeStringify(item);
        });
      }

      return [safeStringify(parsed)];
    } catch {
      return trimmed
        .split("\n")
        .map((item) => item.trim())
        .filter(Boolean);
    }
  }

  return [safeStringify(value)];
}

function safeEvidence(value: unknown): unknown[] {
  if (!value) return [];

  if (Array.isArray(value)) return value;

  if (typeof value === "string") {
    const trimmed = value.trim();

    if (!trimmed) return [];

    try {
      const parsed = JSON.parse(trimmed);
      return Array.isArray(parsed) ? parsed : [parsed];
    } catch {
      return [trimmed];
    }
  }

  return [value];
}

function safeStringify(value: unknown): string {
  if (typeof value === "string") return value;

  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function formatDate(value?: string) {
  if (!value) return "-";

  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function getScoreLabel(score: number | null) {
  if (score === null || score === undefined) return "暂无评分";
  if (score >= 85) return "高度匹配";
  if (score >= 70) return "较匹配";
  if (score >= 50) return "一般匹配";
  return "匹配度偏低";
}