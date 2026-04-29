import {
  Bot,
  Briefcase,
  FileText,
  History,
  Sparkles,
  Target,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

const cards = [
  {
    title: "开始匹配分析",
    desc: "上传简历、选择岗位 JD，生成匹配分和优化建议。",
    icon: Target,
    path: "/match",
  },
  {
    title: "历史分析结果",
    desc: "查看过去的匹配结果、分数和建议。",
    icon: History,
    path: "/results",
  },
  {
    title: "简历管理",
    desc: "上传 PDF 简历并解析文本内容。",
    icon: FileText,
    path: "/match",
  },
  {
    title: "岗位 JD 管理",
    desc: "创建岗位描述，作为匹配分析对象。",
    icon: Briefcase,
    path: "/match",
  },
];

export default function DashboardPage() {
  const navigate = useNavigate();

  return (
    <div>
      <header className="rounded-3xl bg-white p-6 shadow-sm">
        <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-600">
          <Sparkles className="h-4 w-4" />
          AI Resume Matcher
        </div>

        <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-950">
          把简历和岗位 JD 变成可执行的求职计划
        </h1>

        <p className="mt-3 max-w-2xl text-slate-500">
          你可以上传 PDF 简历，创建岗位 JD，生成匹配分、关键词差距、优势、不足和优化建议，
          还可以通过 Agent 继续追问。
        </p >

        <button
          onClick={() => navigate("/match")}
          className="mt-6 rounded-2xl bg-slate-950 px-5 py-3 text-sm font-medium text-white transition hover:bg-slate-800"
        >
          开始一次新的匹配分析
        </button>
      </header>

      <section className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => {
          const Icon = card.icon;

          return (
            <button
              key={card.title}
              onClick={() => navigate(card.path)}
              className="rounded-3xl bg-white p-6 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
            >
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-100">
                <Icon className="h-5 w-5 text-slate-700" />
              </div>

              <div className="mt-5 font-semibold text-slate-950">
                {card.title}
              </div>

              <p className="mt-2 text-sm leading-6 text-slate-500">
                {card.desc}
              </p >
            </button>
          );
        })}
      </section>

      <section className="mt-6 grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-3xl bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">推荐工作流</h2>

          <div className="mt-5 space-y-4">
            {[
              "上传 PDF 简历",
              "粘贴目标岗位 JD",
              "运行 AI 匹配分析",
              "查看关键词差距与优化建议",
              "使用 Agent 生成改写版简历项目经历",
            ].map((item, index) => (
              <div key={item} className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-950 text-sm font-medium text-white">
                  {index + 1}
                </div>
                <div className="text-sm text-slate-700">{item}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-3xl bg-slate-950 p-6 text-white shadow-sm">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/10">
              <Bot className="h-5 w-5" />
            </div>

            <div>
              <h2 className="font-semibold">Agent 能做什么？</h2>
              <p className="mt-1 text-sm text-white/50">基于最近一次匹配结果继续工作</p >
            </div>
          </div>

          <div className="mt-5 space-y-3 text-sm text-white/75">
            <p>• 帮你找出简历和岗位 JD 的差距</p >
            <p>• 改写项目经历 bullet points</p >
            <p>• 生成针对性面试题</p >
            <p>• 制定 7 天或 30 天补强计划</p >
          </div>
        </div>
      </section>
    </div>
  );
}