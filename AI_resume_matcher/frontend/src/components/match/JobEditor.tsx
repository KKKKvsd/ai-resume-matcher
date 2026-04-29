import { useState } from "react";
import { Briefcase, Loader2, Save } from "lucide-react";
import { createJob } from "../../lib/api";
import type { Job } from "../../types/api";

type Props = {
  onCreated: (job: Job) => void;
};

export default function JobEditor({ onCreated }: Props) {
  const [title, setTitle] = useState("Backend Engineer - AI Platform");
  const [companyName, setCompanyName] = useState("Demo Company");
  const [content, setContent] = useState(
    "We are looking for a backend engineer with FastAPI, MySQL, Docker, LLM API, RAG, testing and production API experience."
  );
  const [source, setSource] = useState("manual");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

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
        content: content.trim(),
        source: source.trim() || "manual",
      });

      onCreated(job);
    } catch (err: any) {
      console.error("创建岗位失败：", err);

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

  return (
    <section className="rounded-3xl bg-white p-6 shadow-sm">
      <div className="flex items-center gap-2">
        <Briefcase className="h-5 w-5 text-slate-700" />
        <h2 className="font-semibold text-slate-950">3. 创建岗位 JD</h2>
      </div>

      <p className="mt-2 text-sm leading-6 text-slate-500">
        粘贴目标岗位描述，后端会保存为可匹配的 Job。
      </p >

      <div className="mt-5 space-y-3">
        <input
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder="岗位标题"
          className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-slate-400"
        />

        <input
          value={companyName}
          onChange={(event) => setCompanyName(event.target.value)}
          placeholder="公司名称，可选"
          className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-slate-400"
        />

        <input
          value={source}
          onChange={(event) => setSource(event.target.value)}
          placeholder="来源，例如 LinkedIn / manual / company site"
          className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-slate-400"
        />

        <textarea
          value={content}
          onChange={(event) => setContent(event.target.value)}
          placeholder="粘贴岗位 JD 内容"
          className="h-40 w-full resize-none rounded-2xl border border-slate-200 px-4 py-3 text-sm leading-6 outline-none transition focus:border-slate-400"
        />

        {error && (
          <div className="rounded-2xl bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <button
          onClick={handleCreateJob}
          disabled={saving}
          className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-slate-950 px-4 py-3 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {saving ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              保存中...
            </>
          ) : (
            <>
              <Save className="h-4 w-4" />
              保存岗位
            </>
          )}
        </button>
      </div>
    </section>
  );
}