import { Search } from "lucide-react";
import { safeStringify } from "../../lib/resultUtils";

type Props = {
  evidence: unknown[];
};

export default function ResultEvidencePanel({ evidence }: Props) {
  return (
    <section className="rounded-3xl bg-white p-6 shadow-sm">
      <div className="flex items-center gap-2">
        <Search className="h-5 w-5 text-slate-700" />
        <h2 className="font-semibold text-slate-950">RAG Evidence</h2>
      </div>

      <p className="mt-2 text-sm text-slate-500">
        这里展示后端返回的 evidence，用来解释 AI 分析参考了哪些知识片段。
      </p >

      {evidence.length === 0 ? (
        <div className="mt-5 rounded-2xl bg-slate-50 p-5 text-sm text-slate-400">
          暂无 evidence
        </div>
      ) : (
        <div className="mt-5 space-y-3">
          {evidence.map((item, index) => (
            <div
              key={index}
              className="rounded-2xl border border-slate-200 p-4"
            >
              <div className="mb-2 text-sm font-semibold text-slate-950">
                Evidence #{index + 1}
              </div>

              <pre className="overflow-auto whitespace-pre-wrap rounded-xl bg-slate-50 p-3 text-xs leading-6 text-slate-600">
                {safeStringify(item)}
              </pre>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}