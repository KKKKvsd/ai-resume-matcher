import { useEffect, useState } from "react";
import { Briefcase, RefreshCw, Save } from "lucide-react";
import { createJob, getJobs } from "../lib/api";
import type { Job } from "../types/api";
import PageHeader from "../components/common/PageHeader";
import LoadingCard from "../components/common/LoadingCard";
import ErrorCard from "../components/common/ErrorCard";
import EmptyState from "../components/common/EmptyState";
import Badge from "../components/common/Badge";

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [title, setTitle] = useState("Backend Engineer - AI Platform");
  const [companyName, setCompanyName] = useState("Demo Company");
  const [source, setSource] = useState("manual");
  const [content, setContent] = useState(
    "We are looking for a backend engineer with FastAPI, MySQL, Docker, LLM API, RAG and production API experience."
  );

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function loadJobs() {
    try {
      setLoading(true);
      setError("");

      const data = await getJobs();
      setJobs(Array.isArray(data) ? data : []);
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          err?.response?.data?.message ||
          err?.message ||
          "加载岗位失败"
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateJob() {
    if (!title.trim()) {
      setError("请输入岗位标题");
      return;
    }

    if (!content.trim()) {
      setError("请输入岗位 JD 内容");
      return;
    }

    try {
      setSaving(true);
      setError("");

      const job = await createJob({
        title: title.trim(),
        company_name: companyName.trim() || undefined,
        source: source.trim() || "manual",
        content: content.trim(),
      });

      setJobs((current) => [job, ...current]);
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          err?.response?.data?.message ||
          err?.message ||
          "创建岗位失败"
      );
    } finally {
      setSaving(false);
    }
  }

  useEffect(() => {
    loadJobs();
  }, []);

  return (
    <div>
      <PageHeader
        title="岗位管理"
        description="创建和查看用于匹配分析的岗位 JD。"
        actions={
          <button
            onClick={loadJobs}
            className="inline-flex items-center gap-2 rounded-2xl border px-4 py-2 text-sm hover:bg-slate-50"
          >
            <RefreshCw className="h-4 w-4" />
            刷新
          </button>
        }
      />

      <section className="mt-6 rounded-3xl bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2">
          <Briefcase className="h-5 w-5 text-slate-700" />
          <h2 className="font-semibold text-slate-950">创建岗位 JD</h2>
        </div>

        <div className="mt-5 grid gap-3">
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="岗位标题"
            className="rounded-2xl border px-4 py-3 text-sm outline-none focus:border-slate-400"
          />

          <input
            value={companyName}
            onChange={(event) => setCompanyName(event.target.value)}
            placeholder="公司名称，可选"
            className="rounded-2xl border px-4 py-3 text-sm outline-none focus:border-slate-400"
          />

          <input
            value={source}
            onChange={(event) => setSource(event.target.value)}
            placeholder="来源，例如 manual / LinkedIn"
            className="rounded-2xl border px-4 py-3 text-sm outline-none focus:border-slate-400"
          />

          <textarea
            value={content}
            onChange={(event) => setContent(event.target.value)}
            placeholder="粘贴岗位 JD 内容"
            className="h-40 resize-none rounded-2xl border px-4 py-3 text-sm leading-6 outline-none focus:border-slate-400"
          />

          <button
            onClick={handleCreateJob}
            disabled={saving}
            className="inline-flex items-center justify-center gap-2 rounded-2xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-60"
          >
            <Save className="h-4 w-4" />
            {saving ? "保存中..." : "保存岗位"}
          </button>
        </div>
      </section>

      <div className="mt-6">
        {loading && <LoadingCard text="正在加载岗位..." />}

        {!loading && error && <ErrorCard message={error} />}

        {!loading && !error && jobs.length === 0 && (
          <EmptyState
            title="暂无岗位"
            description="创建一个岗位 JD 后，这里会显示记录。"
          />
        )}

        {!loading && !error && jobs.length > 0 && (
          <section className="space-y-4">
            {jobs.map((job) => (
              <article
                key={job.id}
                className="rounded-3xl bg-white p-6 shadow-sm"
              >
                <div className="flex flex-col justify-between gap-3 md:flex-row md:items-start">
                  <div>
                    <h2 className="font-semibold text-slate-950">
                      {job.title || `Job #${job.id}`}
                    </h2>

                    <p className="mt-2 text-sm text-slate-500">
                      {job.company_name || "Unknown company"}
                    </p>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <Badge>Job #{job.id}</Badge>
                    <Badge>{job.source || "unknown source"}</Badge>
                  </div>
                </div>

                <p className="mt-4 whitespace-pre-wrap rounded-2xl bg-slate-50 p-4 text-sm leading-6 text-slate-600">
                  {job.content}
                </p>

                <div className="mt-4 text-xs text-slate-400">
                  创建时间：{formatDate(job.created_at)}
                </div>
              </article>
            ))}
          </section>
        )}
      </div>
    </div>
  );
}

function formatDate(value?: string) {
  if (!value) return "-";

  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}