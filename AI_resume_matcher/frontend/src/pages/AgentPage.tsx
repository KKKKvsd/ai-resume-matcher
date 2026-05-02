import { useEffect, useRef, useState } from "react";
import {
  Bot,
  BrainCircuit,
  CheckCircle2,
  Copy,
  Loader2,
  RefreshCw,
  Send,
  Sparkles,
  User2,
  Wand2,
} from "lucide-react";
import { askFollowUp, createAgentSession, streamAgent } from "../lib/api";
import type { AgentResponse } from "../types/api";
import PageHeader from "../components/common/PageHeader";

const quickPrompts = [
  {
    label: "改写简历",
    prompt: "请基于我最近一次匹配结果，帮我改写简历项目经历 bullet points。",
  },
  {
    label: "生成面试题",
    prompt: "请基于我最近一次匹配结果，生成 8 个面试问题和回答提示。",
  },
  {
    label: "关键词缺口",
    prompt: "请总结我当前简历相对目标岗位最重要的关键词缺口。",
  },
  {
    label: "7 天计划",
    prompt: "请根据我最近一次匹配结果，制定一个 7 天技能补强计划。",
  },
];

// ---------------------------------------------------------------------------
// 一条对话消息(可以是 user / agent / follow_up)
// ---------------------------------------------------------------------------
type Message =
  | {
      id: string;
      role: "user";
      content: string;
    }
  | {
      id: string;
      role: "agent";
      content: string;
      data: AgentResponse; // 完整数据,用于展示 trace 和 memory
    }
  | {
      id: string;
      role: "follow_up";
      content: string;
      basedOnResultId: number;
    };

function newId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export default function AgentPage() {
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState<"agent" | "follow_up">("agent");

  // 多轮对话状态
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionLoading, setSessionLoading] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const scrollRef = useRef<HTMLDivElement>(null);

  // 自动滚到最新消息
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [messages, loading]);

  // 进入页面自动创建 session
  useEffect(() => {
    initSession();
  }, []);

  async function initSession() {
    try {
      setSessionLoading(true);
      const data = await createAgentSession();
      setSessionId(data.session_id);
    } catch (err) {
      console.warn("创建 session 失败,Agent 将以无记忆模式运行:", err);
    } finally {
      setSessionLoading(false);
    }
  }

  async function startNewConversation() {
    await initSession();
    setMessages([]);
    setError("");
  }

  async function handleSubmit() {
    const trimmed = question.trim();
    if (!trimmed) {
      setError("请输入问题");
      return;
    }

    const userMsg: Message = {
      id: newId(),
      role: "user",
      content: trimmed,
    };

    // 占位的 agent 消息,边收边追加
    const placeholderId = newId();
    const placeholderMsg: Message = {
      id: placeholderId,
      role: "agent",
      content: "",
      data: {
        intent: "",
        final_answer: "",
        plan: {},
        steps: [],
        result: {},
        confidence: null,
        mode: null,
        warnings: [],
        memory: null,
      },
    };

    setMessages((prev) => [...prev, userMsg, placeholderMsg]);
    setQuestion("");
    setError("");
    setLoading(true);

    // ===== 关键:抽出一个类型安全的 helper,只更新 placeholder agent 消息 =====
    const updatePlaceholder = (
      updater: (msg: Extract<Message, { role: "agent" }>) => Extract<Message, { role: "agent" }>,
    ) => {
      setMessages((prev) =>
        prev.map((m): Message => {
          if (m.id !== placeholderId) return m;
          if (m.role !== "agent") return m;
          // 这里 TS 知道 m 一定是 agent 分支
          return updater(m);
        }),
      );
    };

    try {
      if (mode === "agent") {
        await streamAgent(trimmed, sessionId, (event) => {
          switch (event.type) {
            case "status": {
              const message = event.data.message;
              updatePlaceholder((m) => {
                // 只在还没开始打字时显示状态(content 为空或者以 ▸ 开头)
                if (m.content && !m.content.startsWith("▸")) return m;
                return { ...m, content: `▸ ${message}` };
              });
              break;
            }

            case "tool_start": {
              const toolName = event.data.tool_name;
              updatePlaceholder((m) => {
                if (m.content && !m.content.startsWith("▸")) return m;
                return { ...m, content: `▸ 执行 ${toolName}...` };
              });
              break;
            }

            case "tool_done": {
              const toolEvent = event.data;
              updatePlaceholder((m) => ({
                ...m,
                data: {
                  ...m.data,
                  steps: [...m.data.steps, toolEvent],
                },
              }));
              break;
            }

            case "memory": {
              const memData = event.data;
              updatePlaceholder((m) => ({
                ...m,
                data: { ...m.data, memory: memData },
              }));
              break;
            }

            case "token": {
              const text = event.data.text;
              updatePlaceholder((m) => {
                const wasStatus = m.content.startsWith("▸");
                return {
                  ...m,
                  content: wasStatus ? text : m.content + text,
                };
              });
              break;
            }

            case "warning":
              console.warn("Agent warning:", event.data.message);
              break;

            case "error":
              setError(event.data.message);
              break;

            case "done": {
              const doneData = event.data;
              updatePlaceholder((m) => ({
                ...m,
                data: {
                  ...m.data,
                  intent: doneData.intent,
                  final_answer: doneData.final_answer,
                  plan: doneData.plan,
                  steps: doneData.steps,
                  result: doneData.result,
                  confidence: doneData.confidence,
                  mode: doneData.mode,
                  warnings: doneData.warnings,
                  memory: doneData.memory,
                },
              }));
              break;
            }
          }
        });
      } else {
        // follow_up 模式:把占位 agent 消息整条替换为 follow_up 消息
        const data = await askFollowUp(trimmed);
        setMessages((prev) =>
          prev.map((m): Message => {
            if (m.id !== placeholderId) return m;
            return {
              id: m.id,
              role: "follow_up",
              content: data.answer,
              basedOnResultId: data.based_on_result_id,
            };
          }),
        );
      }
    } catch (err: any) {
      console.error("Stream agent failed:", err);
      setError(err?.message || "请求失败");
      setMessages((prev) =>
        prev.filter((m) => m.id !== userMsg.id && m.id !== placeholderId),
      );
      setQuestion(trimmed);
    } finally {
      setLoading(false);
    }
  }
   

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Cmd/Ctrl + Enter 发送
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit();
    }
  }

  return (
    <div>
      <PageHeader
        title="Agent 问答"
        description="基于最近一次匹配分析结果，可连续多轮追问。Agent 会记住本次会话内的上下文。"
      />

      <section className="mt-6 flex h-[calc(100vh-220px)] flex-col rounded-3xl bg-white shadow-sm">
        {/* ============== 顶部:状态栏 ============== */}
        <div className="flex items-center justify-between gap-4 border-b border-slate-200 px-6 py-4">
          <div className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-slate-700" />
            <h2 className="font-semibold text-slate-950">AI 求职助手</h2>

            {sessionLoading ? (
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-400">
                会话连接中...
              </span>
            ) : sessionId ? (
              <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700">
                记忆已开启
              </span>
            ) : (
              <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-700">
                无记忆模式
              </span>
            )}
          </div>

          <div className="flex items-center gap-3">
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

            <button
              onClick={startNewConversation}
              className="inline-flex items-center gap-1.5 rounded-2xl border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
              title="清空对话并开启新会话"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              新对话
            </button>
          </div>
        </div>

        {/* ============== 中部:消息列表 ============== */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-6">
          {messages.length === 0 ? (
            <EmptyConversation
              onPick={(prompt) => setQuestion(prompt)}
            />
          ) : (
            <div className="space-y-4">
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              {loading && <ThinkingBubble />}
            </div>
          )}
        </div>

        {/* ============== 底部:输入框 ============== */}
        <div className="border-t border-slate-200 px-6 py-4">
          {error && (
            <div className="mb-3 rounded-2xl bg-red-50 p-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={handleKeyDown}
              className="h-20 w-full resize-none bg-transparent text-sm leading-6 outline-none placeholder:text-slate-400"
              placeholder="向 Agent 提问... (Cmd/Ctrl + Enter 发送)"
            />

            <div className="flex items-center justify-between border-t border-slate-200 pt-2">
              <div className="text-xs text-slate-400">
                {question.length}/1000
              </div>

              <button
                onClick={handleSubmit}
                disabled={loading || !question.trim()}
                className="inline-flex items-center gap-2 rounded-2xl bg-slate-950 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-60"
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
        </div>
      </section>
    </div>
  );
}

// ===========================================================================
// 消息气泡组件
// ===========================================================================
function MessageBubble({ message }: { message: Message }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="flex max-w-[75%] items-start gap-2">
          <div className="rounded-2xl rounded-tr-sm bg-slate-950 px-4 py-3 text-sm leading-6 text-white">
            <div className="whitespace-pre-wrap">{message.content}</div>
          </div>
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-200">
            <User2 className="h-4 w-4 text-slate-600" />
          </div>
        </div>
      </div>
    );
  }

  if (message.role === "follow_up") {
    return (
      <div className="flex justify-start">
        <div className="flex max-w-[85%] items-start gap-2">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-100">
            <Bot className="h-4 w-4 text-slate-600" />
          </div>
          <div className="rounded-2xl rounded-tl-sm bg-slate-100 px-4 py-3 text-sm leading-6 text-slate-700">
            <div className="whitespace-pre-wrap">{message.content}</div>
            <div className="mt-2 text-xs text-slate-400">
              Based on Result #{message.basedOnResultId}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // agent 消息:带可展开的 trace 和 memory 信息
  return <AgentMessageBubble message={message} />;
}

function AgentMessageBubble({
  message,
}: {
  message: Extract<Message, { role: "agent" }>;
}) {
  const [showDetails, setShowDetails] = useState(false);

  return (
    <div className="flex justify-start">
      <div className="flex max-w-[85%] items-start gap-2">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-100">
          <Bot className="h-4 w-4 text-slate-600" />
        </div>
        <div className="flex-1 space-y-2">
          {/* 主回答 */}
          <div className="rounded-2xl rounded-tl-sm bg-slate-100 px-4 py-3 text-sm leading-6 text-slate-700">
            <div className="whitespace-pre-wrap">{message.content}</div>

            <div className="mt-2 flex items-center gap-3 border-t border-slate-200 pt-2 text-xs">
              <button
                onClick={() => navigator.clipboard.writeText(message.content)}
                className="inline-flex items-center gap-1 text-slate-500 hover:text-slate-700"
              >
                <Copy className="h-3 w-3" />
                复制
              </button>

              <button
                onClick={() => setShowDetails((v) => !v)}
                className="inline-flex items-center gap-1 text-slate-500 hover:text-slate-700"
              >
                <BrainCircuit className="h-3 w-3" />
                {showDetails ? "隐藏" : "查看"}执行细节
              </button>

              <span className="ml-auto text-slate-400">
                {message.data.intent} · {message.data.mode}
                {message.data.confidence != null &&
                  ` · ${(message.data.confidence * 100).toFixed(0)}%`}
              </span>
            </div>
          </div>

          {/* 展开:memory + steps */}
          {showDetails && (
            <div className="rounded-2xl bg-slate-50 p-4 text-xs">
              {/* memory 状态 */}
              {message.data.memory && (
                <div className="mb-3 grid grid-cols-2 gap-2 text-slate-600 sm:grid-cols-4">
                  <MemoryStat
                    label="会话记忆"
                    value={
                      message.data.memory.used_session_memory ? "已注入" : "未用"
                    }
                    active={message.data.memory.used_session_memory}
                  />
                  <MemoryStat
                    label="长期记忆"
                    value={
                      message.data.memory.used_longterm_memory
                        ? "已注入"
                        : "未用"
                    }
                    active={message.data.memory.used_longterm_memory}
                  />
                  <MemoryStat
                    label="摘要压缩"
                    value={
                      message.data.memory.summary_compressed ? "已触发" : "未触发"
                    }
                    active={message.data.memory.summary_compressed}
                  />
                  <MemoryStat
                    label="记忆 token"
                    value={`≈ ${message.data.memory.tokens_estimate}`}
                    active={false}
                  />
                </div>
              )}

              {/* 工具步骤 */}
              <div className="flex items-center gap-2 font-semibold text-slate-700">
                <Wand2 className="h-3.5 w-3.5" />
                工具执行步骤 ({message.data.steps.length})
              </div>

              <div className="mt-2 space-y-2">
                {message.data.steps.map((step, idx) => (
                  <div
                    key={idx}
                    className="rounded-xl border border-slate-200 bg-white p-3"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="font-medium text-slate-700">
                          {String(step.step_id || idx + 1)}.{" "}
                          {String(step.tool_name || "unknown")}
                        </div>
                        <div className="mt-0.5 text-slate-500">
                          {String(step.reason || "")}
                        </div>
                      </div>
                      <span
                        className={[
                          "inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5",
                          String(step.status) === "success"
                            ? "bg-emerald-50 text-emerald-700"
                            : "bg-red-50 text-red-700",
                        ].join(" ")}
                      >
                        <CheckCircle2 className="h-3 w-3" />
                        {String(step.status || "success")}
                      </span>
                    </div>
                  </div>
                ))}
              </div>

              {/* warnings */}
              {message.data.warnings && message.data.warnings.length > 0 && (
                <div className="mt-3 rounded-xl bg-amber-50 p-2 text-amber-700">
                  {message.data.warnings.map((w, i) => (
                    <div key={i}>• {w}</div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ThinkingBubble() {
  return (
    <div className="flex justify-start">
      <div className="flex items-start gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100">
          <Bot className="h-4 w-4 text-slate-600" />
        </div>
        <div className="rounded-2xl rounded-tl-sm bg-slate-100 px-4 py-3">
          <div className="flex items-center gap-1">
            <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.3s]" />
            <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.15s]" />
            <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400" />
          </div>
        </div>
      </div>
    </div>
  );
}

function MemoryStat({
  label,
  value,
  active,
}: {
  label: string;
  value: string;
  active: boolean;
}) {
  return (
    <div className="rounded-xl bg-white px-2 py-1.5">
      <div className="text-[10px] text-slate-400">{label}</div>
      <div
        className={[
          "mt-0.5 font-medium",
          active ? "text-emerald-700" : "text-slate-500",
        ].join(" ")}
      >
        {value}
      </div>
    </div>
  );
}

function EmptyConversation({ onPick }: { onPick: (prompt: string) => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100">
        <Sparkles className="h-6 w-6 text-slate-500" />
      </div>
      <h3 className="mt-3 text-base font-semibold text-slate-700">
        开始和 Agent 对话
      </h3>
      <p className="mt-1 text-sm text-slate-500">
        Agent 会基于你的最近一次匹配结果回答,并记住本次会话内的上下文。
      </p>

      <div className="mt-5 flex flex-wrap justify-center gap-2">
        {quickPrompts.map((item) => (
          <button
            key={item.label}
            onClick={() => onPick(item.prompt)}
            className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-200"
          >
            <Sparkles className="h-3.5 w-3.5" />
            {item.label}
          </button>
        ))}
      </div>
    </div>
  );
}