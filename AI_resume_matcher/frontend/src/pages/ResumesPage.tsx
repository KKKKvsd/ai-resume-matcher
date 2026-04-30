import { useEffect, useState } from "react";
import { FileText, RefreshCw, Upload } from "lucide-react";
import { getResumes, uploadResume } from "../lib/api";
import type { Resume } from "../types/api";
import PageHeader from "../components/common/PageHeader";
import LoadingCard from "../components/common/LoadingCard";
import ErrorCard from "../components/common/ErrorCard";
import EmptyState from "../components/common/EmptyState";
import Badge from "../components/common/Badge";

export default function ResumesPage() {
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  async function loadResumes() {
    try {
      setLoading(true);
      setError("");

      const data = await getResumes();
      setResumes(Array.isArray(data) ? data : []);
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          err?.response?.data?.message ||
          err?.message ||
          "加载简历失败"
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleUpload(file: File | null) {
    if (!file) return;

    if (file.type !== "application/pdf") {
      setError("请上传 PDF 文件");
      return;
    }

    try {
      setUploading(true);
      setError("");

      const resume = await uploadResume(file);
      setResumes((current) => [resume, ...current]);
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          err?.response?.data?.message ||
          err?.message ||
          "上传简历失败"
      );
    } finally {
      setUploading(false);
    }
  }

  useEffect(() => {
    loadResumes();
  }, []);

  return (
    <div>
      <PageHeader
        title="简历管理"
        description="上传和查看已经解析过的 PDF 简历。"
        actions={
          <button
            onClick={loadResumes}
            className="inline-flex items-center gap-2 rounded-2xl border px-4 py-2 text-sm hover:bg-slate-50"
          >
            <RefreshCw className="h-4 w-4" />
            刷新
          </button>
        }
      />

      <section className="mt-6 rounded-3xl bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2">
          <Upload className="h-5 w-5 text-slate-700" />
          <h2 className="font-semibold text-slate-950">上传新简历</h2>
        </div>

        <label className="mt-5 flex cursor-pointer flex-col items-center justify-center rounded-3xl border-2 border-dashed border-slate-200 bg-slate-50 px-6 py-8 text-center hover:bg-slate-100">
          <FileText className="h-8 w-8 text-slate-400" />

          <div className="mt-3 text-sm font-medium text-slate-700">
            {uploading ? "正在上传..." : "点击选择 PDF 文件"}
          </div>

          <div className="mt-1 text-xs text-slate-400">仅支持 .pdf</div>

          <input
            type="file"
            accept="application/pdf"
            disabled={uploading}
            onChange={(event) =>
              handleUpload(event.target.files?.[0] || null)
            }
            className="hidden"
          />
        </label>
      </section>

      <div className="mt-6">
        {loading && <LoadingCard text="正在加载简历..." />}

        {!loading && error && <ErrorCard message={error} />}

        {!loading && !error && resumes.length === 0 && (
          <EmptyState
            title="暂无简历"
            description="上传一份 PDF 简历后，这里会显示记录。"
          />
        )}

        {!loading && !error && resumes.length > 0 && (
          <section className="grid gap-4 md:grid-cols-2">
            {resumes.map((resume) => (
              <article
                key={resume.id}
                className="rounded-3xl bg-white p-6 shadow-sm"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <h2 className="truncate font-semibold text-slate-950">
                      {resume.file_name || `Resume #${resume.id}`}
                    </h2>

                    <p className="mt-2 text-sm text-slate-500">
                      Resume #{resume.id}
                    </p>
                  </div>

                  <Badge>{resume.parsed_status || "unknown"}</Badge>
                </div>

                <div className="mt-4 text-sm text-slate-500">
                  上传时间：{formatDate(resume.created_at)}
                </div>

                {resume.raw_text && (
                  <p className="mt-4 line-clamp-4 rounded-2xl bg-slate-50 p-4 text-xs leading-6 text-slate-500">
                    {resume.raw_text}
                  </p>
                )}
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