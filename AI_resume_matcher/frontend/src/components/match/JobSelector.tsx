import { Briefcase, CheckCircle2 } from "lucide-react";
import type { Job } from "../../types/api";
import Badge from "../common/Badge";

type Props = {
  jobs: Job[];
  selectedJobId: number | null;
  onSelect: (jobId: number) => void;
};

export default function JobSelector({
  jobs,
  selectedJobId,
  onSelect,
}: Props) {
  return (
    <section className="rounded-3xl bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <Briefcase className="h-5 w-5 text-slate-700" />
          <h2 className="font-semibold text-slate-950">4. 选择岗位</h2>
        </div>

        <Badge>{jobs.length} jobs</Badge>
      </div>

      {jobs.length === 0 ? (
        <div className="mt-5 rounded-2xl bg-slate-50 p-4 text-sm text-slate-400">
          暂无岗位，请先创建岗位 JD。
        </div>
      ) : (
        <div className="mt-5 space-y-3">
          {jobs.map((job) => {
            const active = selectedJobId === job.id;

            return (
              <button
                key={job.id}
                onClick={() => onSelect(job.id)}
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
                      {job.title || `Job #${job.id}`}
                    </div>

                    <div className="mt-1 text-xs text-slate-500">
                      #{job.id} · {job.company_name || "Unknown company"} ·{" "}
                      {job.source || "unknown source"}
                    </div>

                    <p className="mt-2 line-clamp-2 text-xs leading-5 text-slate-400">
                      {job.content}
                    </p >
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