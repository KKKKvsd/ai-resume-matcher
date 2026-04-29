import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CheckCircle2, RefreshCw } from "lucide-react";
import { getMatchResults } from "../lib/api";
import type { MatchResult } from "../types/api";
import Badge from "../components/common/Badge";
import EmptyState from "../components/common/EmptyState";
import ErrorCard from "../components/common/ErrorCard";
import LoadingCard from "../components/common/LoadingCard";
import PageHeader from "../components/common/PageHeader";

export default function ResultsPage() {
  const navigate = useNavigate();

  const [results, setResults] = useState<MatchResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadResults() {
    try {
      setLoading(true);
      setError("");

      const data = await getMatchResults();

      console.log("历史结果数据：", data);

      setResults(Array.isArray(data) ? data : []);
    } catch (err: any) {
      console.error("加载历史结果失败：", err);

      setError(
        err?.response?.data?.detail ||
          err?.response?.data?.message ||
          err?.message ||
          "加载历史结果失败"
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadResults();
  }, []);

  return (
    <div>
      <PageHeader
        title="历史分析结果"
        description="查看你过去运行过的简历岗位匹配分析。"
        actions={
          <button
            onClick={loadResults}
            className="inline-flex items-center justify-center gap-2 rounded-2xl border px-4 py-2 text-sm transition hover:bg-slate-50"
          >
            <RefreshCw className="h-4 w-4" />
            刷新
          </button>
        }
      />

      <div className="mt-6">
        {loading && <LoadingCard text="正在加载历史结果..." />}

        {!loading && error && <ErrorCard message={error} />}

        {!loading && !error && results.length === 0 && (
          <EmptyState
            title="暂无历史结果"
            description="先去“匹配分析”页面完成一次分析，这里就会显示记录。"
          />
        )}

        {!loading && !error && results.length > 0 && (
          <section className="space-y-4">
            {results.map((result) => (
              <article
                key={result.id}
                className="rounded-3xl bg-white p-6 shadow-sm transition hover:shadow-md"
              >
                <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="h-5 w-5 text-emerald-600" />

                      <h2 className="font-semibold text-slate-950">
                        Match Result #{result.id}
                      </h2>
                    </div>

                    <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
                      {result.summary || "暂无 summary"}
                    </p>

                    <div className="mt-4 flex flex-wrap gap-2">
                      <Badge>Resume #{result.resume_id}</Badge>
                      <Badge>Job #{result.job_id}</Badge>
                      <Badge>{result.analysis_mode || "unknown mode"}</Badge>
                      <Badge>{result.status || "unknown status"}</Badge>
                      {result.model_name && <Badge>{result.model_name}</Badge>}
                    </div>

                    <div className="mt-5 grid gap-4 md:grid-cols-2">
                      <KeywordBox
                        title="已匹配关键词"
                        items={safeArray(result.matched_keywords)}
                        emptyText="暂无匹配关键词"
                      />

                      <KeywordBox
                        title="缺失关键词"
                        items={safeArray(result.missing_keywords)}
                        emptyText="暂无缺失关键词"
                      />
                    </div>
                  </div>

                  <div className="flex flex-col items-stretch gap-3">
                    <div className="rounded-3xl bg-slate-950 px-6 py-5 text-center text-white">
                      <div className="text-sm text-white/50">Score</div>

                      <div className="mt-1 text-4xl font-semibold">
                        {result.score ?? "-"}
                      </div>
                    </div>

                    <button
                      onClick={() => navigate(`/results/${result.id}`)}
                      className="rounded-2xl border px-4 py-2 text-sm transition hover:bg-slate-50"
                    >
                      查看详情
                    </button>
                  </div>
                </div>
              </article>
            ))}
          </section>
        )}
      </div>
    </div>
  );
}

function KeywordBox({
  title,
  items,
  emptyText,
}: {
  title: string;
  items: string[];
  emptyText: string;
}) {
  return (
    <div className="rounded-2xl bg-slate-50 p-4">
      <div className="text-sm font-semibold text-slate-950">{title}</div>

      {items.length === 0 ? (
        <div className="mt-2 text-sm text-slate-400">{emptyText}</div>
      ) : (
        <div className="mt-3 flex flex-wrap gap-2">
          {items.map((item, index) => (
            <span
              key={`${item}-${index}`}
              className="rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-600 shadow-sm"
            >
              {item}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function safeArray(value: unknown): string[] {
  if (!value) return [];

  if (Array.isArray(value)) {
    return value.map((item) => {
      if (typeof item === "string") return item;
      return JSON.stringify(item);
    });
  }

  if (typeof value === "string") {
    const trimmed = value.trim();

    if (!trimmed) return [];

    try {
      const parsed = JSON.parse(trimmed);

      if (Array.isArray(parsed)) {
        return parsed.map((item) =>
          typeof item === "string" ? item : JSON.stringify(item)
        );
      }

      return [JSON.stringify(parsed)];
    } catch {
      return trimmed
        .split("\n")
        .map((item) => item.trim())
        .filter(Boolean);
    }
  }

  return [JSON.stringify(value)];
}