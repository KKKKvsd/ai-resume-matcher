import { useState } from "react";
import {
  Bot,
  BrainCircuit,
  CheckCircle2,
  Copy,
  Loader2,
  MessageSquareText,
  Send,
  Sparkles,
  Wand2,
} from "lucide-react";
import { askFollowUp, runAgent } from "../../lib/api";
import type { AgentResponse, FollowUpResponse } from "../../types/api";

type Props = {
  resultId: number;
};

const quickPrompts = [
  {
    label: "改写项目经历",
    prompt:
      "请根据这次简历与岗位匹配结果，帮我改写 3 条更适合该岗位的项目经历 bullet points。",
  },
  {
    label: "生成面试题",
    prompt:
      "请根据这次匹配结果和缺失关键词，生成 8 个高频面试问题，并给出回答提示。",
  },
  {
    label: "关键词缺口",
    prompt:
      "请总结我当前简历相对这个岗位最重要的关键词缺口，并按优先级排序。",
  },
  {
    label: "7 天补强计划",
    prompt:
      "请基于这次匹配结果，为我制定一个 7 天技能补强计划。",
  },
];

export default function AgentFollowUpPanel({ resultId }: Props) {
  const [question, setQuestion] = useState(
    "请根据这次匹配结果，帮我改写简历项目经历。"
  );

  const [mode, setMode] = useState<"follow_up" | "agent">("agent");
  const [followUpResult, setFollowUpResult] =
    useState<FollowUpResponse | null>(null);
  const [agentResult, setAgentResult] = useState<AgentResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit() {
    if (!question.trim()) {
      setError("请输入问题");
      return;
    }

    try {
      setLoading(true);
      setError("");
      setFollowUpResult(null);
      setAgentResult(null);

      if (mode === "follow_up") {
        const data = await askFollowUp(question.trim());
        setFollowUpResult(data);
      } else {
        const data = await runAgent(question.trim());
        setAgentResult(data);
      }
    } catch (err: any) {
      console.error("Agent 追问失败：", err);

      setError(
        err?.response?.data?.detail ||
          err?.response?.data?.message ||
          err?.message ||
          "请求失败"
      );
    } finally {
      setLoading(false);
    }
  }

  function handleUsePrompt(prompt: string) {
    setQuestion(prompt);
  }

  const finalAnswer =
    mode === "follow_up"
      ? followUpResult?.answer || ""
      : agentResult?.final_answer || "";

  return (
    <section className="rounded-3xl bg-white p-6 shadow-sm">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
        <div>
          <div className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-slate-700" />
            <h2 className="font-semibold text-slate-950">Agent 追问</h2>
          </div>

          <p className="mt-2 text-sm leading-6 text-slate-500">
            基于匹配结果继续追问，让系统生成简历改写、面试题、关键词缺口和学习计划。
          </p>

          <p className="mt-2 text-xs text-amber-600">
            当前页面 Result #{resultId}。注意：当前后端追问接口基于最近一次分析结果。
          </p>
        </div>

        <div className="flex rounded-2xl bg-slate-100 p-1 text-sm">
          <button
            onClick={() => setMode("agent")}
            className={[
              "rounded-xl px-3 py-1.5 transition",
              mode === "agent"
                ? "bg-white text-slate-950 shadow-sm"
                : "text-slate-500 hover:text-slate-950",
            ].join(" ")}
          >
            Agent
          </button>

          <button
            onClick={() => setMode("follow_up")}
            className={[
              "rounded-xl px-3 py-1.5 transition",
              mode === "follow_up"
                ? "bg-white text-slate-950 shadow-sm"
                : "text-slate-500 hover:text-slate-950",
            ].join(" ")}
          >
            Follow-up
          </button>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        {quickPrompts.map((item) => (
          <button
            key={item.label}
            onClick={() => handleUsePrompt(item.prompt)}
            className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:bg-slate-200"
          >
            <Sparkles className="h-3.5 w-3.5" />
            {item.label}
          </button>
        ))}
      </div>

      <div className="mt-5 rounded-3xl border border-slate-200 bg-slate-50 p-3">
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          className="h-28 w-full resize-none bg-transparent p-3 text-sm leading-6 outline-none placeholder:text-slate-400"
          placeholder="例如：请帮我把项目经历改写得更贴合这个岗位"
        />

        <div className="flex items-center justify-between border-t border-slate-200 pt-3">
          <div className="text-xs text-slate-400">
            {question.length}/1000
          </div>

          <button
            onClick={handleSubmit}
            disabled={loading || !question.trim()}
            className="inline-flex items-center gap-2 rounded-2xl bg-slate-950 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                生成中...
              </>
            ) : (
              <>
                <Send className="h-4 w-4" />
                发送
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="mt-4 rounded-2xl bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {(followUpResult || agentResult) && (
        <div className="mt-6 space-y-4">
          <div className="rounded-3xl bg-slate-950 p-5 text-white">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 font-semibold">
                <MessageSquareText className="h-5 w-5" />
                AI 回答
              </div>

              {finalAnswer && (
                <button
                  onClick={() => navigator.clipboard.writeText(finalAnswer)}
                  className="inline-flex items-center gap-1 rounded-full bg-white/10 px-3 py-1 text-xs text-white/70 transition hover:bg-white/20"
                >
                  <Copy className="h-3.5 w-3.5" />
                  复制
                </button>
              )}
            </div>

            <p className="whitespace-pre-wrap text-sm leading-7 text-white/80">
              {finalAnswer || "暂无回答"}
            </p>

            {followUpResult && (
              <div className="mt-4 rounded-2xl bg-white/10 p-3 text-xs text-white/60">
                Based on Result #{followUpResult.based_on_result_id}
              </div>
            )}
          </div>

          {agentResult && (
            <div className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
              <div className="rounded-3xl bg-slate-50 p-5">
                <div className="flex items-center gap-2 font-semibold text-slate-950">
                  <BrainCircuit className="h-5 w-5 text-slate-700" />
                  Agent 状态
                </div>

                <div className="mt-4 space-y-2 text-sm text-slate-600">
                  <InfoRow label="Intent" value={agentResult.intent} />
                  <InfoRow label="Mode" value={agentResult.mode || "-"} />
                  <InfoRow
                    label="Confidence"
                    value={
                      agentResult.confidence === null ||
                      agentResult.confidence === undefined
                        ? "-"
                        : String(agentResult.confidence)
                    }
                  />
                </div>

                {agentResult.warning.length > 0 && (
                  <div className="mt-4 rounded-2xl bg-amber-50 p-3 text-xs leading-5 text-amber-700">
                    {agentResult.warning.map((warning, index) => (
                      <div key={index}>• {warning}</div>
                    ))}
                  </div>
                )}
              </div>

              <div className="rounded-3xl bg-slate-50 p-5">
                <div className="flex items-center gap-2 font-semibold text-slate-950">
                  <Wand2 className="h-5 w-5 text-slate-700" />
                  工具执行步骤
                </div>

                {agentResult.steps.length === 0 ? (
                  <div className="mt-4 text-sm text-slate-400">
                    暂无执行步骤
                  </div>
                ) : (
                  <div className="mt-4 space-y-3">
                    {agentResult.steps.map((step, index) => (
                      <div
                        key={index}
                        className="rounded-2xl border border-slate-200 bg-white p-4"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="text-sm font-semibold text-slate-950">
                              {getStepTitle(step, index)}
                            </div>

                            <p className="mt-1 text-xs leading-5 text-slate-500">
                              {getStepReason(step)}
                            </p>
                          </div>

                          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
                            <CheckCircle2 className="h-3.5 w-3.5" />
                            {getStepStatus(step)}
                          </span>
                        </div>

                        <details className="mt-3">
                          <summary className="cursor-pointer text-xs text-slate-400">
                            查看原始步骤数据
                          </summary>

                          <pre className="mt-3 overflow-auto rounded-xl bg-slate-50 p-3 text-xs leading-6 text-slate-600">
                            {JSON.stringify(step, null, 2)}
                          </pre>
                        </details>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-2xl bg-white px-3 py-2">
      <span className="text-slate-400">{label}</span>
      <span className="font-medium text-slate-700">{value}</span>
    </div>
  );
}

function getStepTitle(step: Record<string, unknown>, index: number) {
  const stepId = step.step_id || index + 1;
  const toolName = step.tool_name || "unknown_tool";

  return `${stepId}. ${String(toolName)}`;
}

function getStepReason(step: Record<string, unknown>) {
  const reason = step.reason;

  if (typeof reason === "string" && reason.trim()) {
    return reason;
  }

  return "暂无 reason";
}

function getStepStatus(step: Record<string, unknown>) {
  const status = step.status;

  if (typeof status === "string" && status.trim()) {
    return status;
  }

  return "success";
}