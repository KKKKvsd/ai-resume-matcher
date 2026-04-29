import Badge from "../common/Badge";
import { getScoreLabel } from "../../lib/resultUtils";

type Props = {
  score: number | null;
  status?: string | null;
  analysisMode?: string | null;
  modelName?: string | null;
};

export default function ResultScoreCard({
  score,
  status,
  analysisMode,
  modelName,
}: Props) {
  return (
    <div className="rounded-3xl bg-slate-950 p-6 text-center text-white shadow-sm">
      <div className="text-sm text-white/50">匹配分</div>

      <div className="mt-3 text-6xl font-semibold">{score ?? "-"}</div>

      <div className="mt-5 text-sm text-white/50">
        {getScoreLabel(score)}
      </div>

      <div className="mt-6 flex flex-wrap justify-center gap-2">
        <Badge tone="dark">{status || "unknown status"}</Badge>
        <Badge tone="dark">{analysisMode || "unknown mode"}</Badge>
      </div>

      {modelName && (
        <div className="mt-3 text-xs text-white/45">Model: {modelName}</div>
      )}
    </div>
  );
}