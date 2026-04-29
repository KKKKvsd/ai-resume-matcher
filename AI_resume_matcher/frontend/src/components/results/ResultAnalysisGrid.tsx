import type { ReactNode } from "react";
import { CheckCircle2, Lightbulb, XCircle } from "lucide-react";

type Props = {
  strengths: string[];
  weaknesses: string[];
  suggestions: string[];
};

export default function ResultAnalysisGrid({
  strengths,
  weaknesses,
  suggestions,
}: Props) {
  return (
    <section className="grid gap-4 lg:grid-cols-3">
      <AnalysisCard
        title="优势"
        icon={<CheckCircle2 className="h-5 w-5 text-emerald-600" />}
        items={strengths}
        emptyText="暂无优势分析"
      />

      <AnalysisCard
        title="不足"
        icon={<XCircle className="h-5 w-5 text-amber-600" />}
        items={weaknesses}
        emptyText="暂无不足分析"
      />

      <AnalysisCard
        title="优化建议"
        icon={<Lightbulb className="h-5 w-5 text-sky-600" />}
        items={suggestions}
        emptyText="暂无优化建议"
      />
    </section>
  );
}

function AnalysisCard({
  title,
  icon,
  items,
  emptyText,
}: {
  title: string;
  icon: ReactNode;
  items: string[];
  emptyText: string;
}) {
  return (
    <div className="rounded-3xl bg-white p-6 shadow-sm">
      <div className="flex items-center gap-2 font-semibold text-slate-950">
        {icon}
        {title}
      </div>

      {items.length === 0 ? (
        <p className="mt-4 rounded-2xl bg-slate-50 p-4 text-sm text-slate-400">
          {emptyText}
        </p >
      ) : (
        <ul className="mt-4 space-y-3 text-sm leading-6 text-slate-600">
          {items.map((item, index) => (
            <li key={`${title}-${index}`}>• {item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}