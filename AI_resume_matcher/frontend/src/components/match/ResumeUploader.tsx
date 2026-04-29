import { useState } from "react";
import { Upload, Loader2, FileText } from "lucide-react";
import { uploadResume } from "../../lib/api";
import type { Resume } from "../../types/api";

type Props = {
  onUploaded: (resume: Resume) => void;
};

export default function ResumeUploader({ onUploaded }: Props) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  async function handleFileChange(file: File | null) {
    if (!file) return;

    if (file.type !== "application/pdf") {
      setError("请上传 PDF 文件");
      return;
    }

    try {
      setUploading(true);
      setError("");

      const resume = await uploadResume(file);
      onUploaded(resume);
    } catch (err: any) {
      console.error("上传简历失败：", err);

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

  return (
    <section className="rounded-3xl bg-white p-6 shadow-sm">
      <div className="flex items-center gap-2">
        <FileText className="h-5 w-5 text-slate-700" />
        <h2 className="font-semibold text-slate-950">1. 上传简历 PDF</h2>
      </div>

      <p className="mt-2 text-sm leading-6 text-slate-500">
        上传 PDF 简历后，后端会解析文本并保存到简历列表。
      </p >

      <label className="mt-5 flex cursor-pointer flex-col items-center justify-center rounded-3xl border-2 border-dashed border-slate-200 bg-slate-50 px-6 py-8 text-center transition hover:border-slate-300 hover:bg-slate-100">
        {uploading ? (
          <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
        ) : (
          <Upload className="h-8 w-8 text-slate-400" />
        )}

        <div className="mt-3 text-sm font-medium text-slate-700">
          {uploading ? "正在上传..." : "点击选择 PDF 文件"}
        </div>

        <div className="mt-1 text-xs text-slate-400">
          仅支持 .pdf 文件
        </div>

        <input
          type="file"
          accept="application/pdf"
          disabled={uploading}
          onChange={(event) =>
            handleFileChange(event.target.files?.[0] || null)
          }
          className="hidden"
        />
      </label>

      {error && (
        <div className="mt-4 rounded-2xl bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}
    </section>
  );
}