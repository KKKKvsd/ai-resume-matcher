import { CheckCircle2, FileText } from "lucide-react";
import type { Resume } from "../../types/api";
import Badge from "../common/Badge";

type Props = {
  resumes: Resume[];
  selectedResumeId: number | null;
  onSelect: (resumeId: number) => void;
};

export default function ResumeSelector({
  resumes,
  selectedResumeId,
  onSelect,
}: Props) {
  return (
    <section className="rounded-3xl bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-slate-700" />
          <h2 className="font-semibold text-slate-950">2. 选择简历</h2>
        </div>

        <Badge>{resumes.length} resumes</Badge>
      </div>

      {resumes.length === 0 ? (
        <div className="mt-5 rounded-2xl bg-slate-50 p-4 text-sm text-slate-400">
          暂无简历，请先上传 PDF。
        </div>
      ) : (
        <div className="mt-5 space-y-3">
          {resumes.map((resume) => {
            const active = selectedResumeId === resume.id;

            return (
              <button
                key={resume.id}
                onClick={() => onSelect(resume.id)}
                className={[
                  "w-full rounded-2xl border p-4 text-left transition",
                  active
                    ? "border-slate-950 bg-slate-50"
                    : "border-slate-200 bg-white hover:bg-slate-50",
                ].join(" ")}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold text-slate-950">
                      {resume.file_name || `Resume #${resume.id}`}
                    </div>

                    <div className="mt-1 text-xs text-slate-500">
                      #{resume.id} · {resume.parsed_status || "unknown"} ·{" "}
                      {formatDate(resume.created_at)}
                    </div>
                  </div>

                  {active && (
                    <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-600" />
                  )}
                </div>
              </button>
            );
          })}
        </div>
      )}
    </section>
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