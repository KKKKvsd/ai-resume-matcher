import { Target } from "lucide-react";
import Badge from "../common/Badge";
import { formatDate } from "../../lib/resultUtils";

type Props = {
  summary?: string | null;
  resumeId: number;
  jobId: number;
  createdAt?: string;
};

export default function ResultSummaryCard({
  summary,
  resumeId,
  jobId,
  createdAt,
}: Props) {
  return (
    <div className="rounded-3xl bg-white p-6 shadow-sm">
      <div className="flex items-center gap-2">
        <Target className="h-5 w-5 text-slate-700" />
        <h2 className="font-semibold text-slate-950">AI 总结</h2>
      </div>

      <p className="mt-4 whitespace-pre-wrap leading-7 text-slate-600">
        {summary || "暂无 summary"}
      </p >

      <div className="mt-5 flex flex-wrap gap-2">
        <Badge>Resume #{resumeId}</Badge>
        <Badge>Job #{jobId}</Badge>
        <Badge>Created: {formatDate(createdAt)}</Badge>
      </div>
    </div>
  );
}