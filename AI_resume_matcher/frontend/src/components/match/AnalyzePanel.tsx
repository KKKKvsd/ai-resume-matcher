import { Loader2, Play, Target } from "lucide-react";
import Badge from "../common/Badge";

type Props = {
  selectedResumeId: number | null;
  selectedJobId: number | null;
  analyzing: boolean;
  onAnalyze: () => void;
};

export default function AnalyzePanel({
  selectedResumeId,
  selectedJobId,
  analyzing,
  onAnalyze,
}: Props) {
  const ready = Boolean(selectedResumeId && selectedJobId);

  return (
    <section className="rounded-3xl bg-slate-950 p-6 text-white shadow-sm">
      <div className="flex items-center gap-2">
        <Target className="h-5 w-5" />
        <h2 className="font-semibold">5. 开始匹配分析</h2>
      </div>

      <p className="mt-2 text-sm leading-6 text-white/60">
        选择简历和岗位后，调用后端匹配分析接口，成功后自动跳转到结果详情页。
      </p >

      <div className="mt-5 flex flex-wrap gap-2">
        <Badge tone="dark">
          Resume {selectedResumeId ? `#${selectedResumeId}` : "未选择"}
        </Badge>

        <Badge tone="dark">
          Job {selectedJobId ? `#${selectedJobId}` : "未选择"}
        </Badge>

        <Badge tone="dark">{ready ? "Ready" : "Not ready"}</Badge>
      </div>

      <button
        onClick={onAnalyze}
        disabled={!ready || analyzing}
        className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-white px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {analyzing ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            分析中...
          </>
        ) : (
          <>
            <Play className="h-4 w-4" />
            开始分析
          </>
        )}
      </button>
    </section>
  );
}