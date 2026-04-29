import { useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  Loader2,
  Lock,
  Mail,
  Sparkles,
  User,
} from "lucide-react";
import { loginUser, registerUser } from "../lib/api";

type Props = {
  onLoginSuccess: () => void;
};

type Mode = "login" | "register";

export default function LoginPage({ onLoginSuccess }: Props) {
  const [mode, setMode] = useState<Mode>("login");

  const [username, setUsername] = useState("demo_user");
  const [email, setEmail] = useState("demo@example.com");
  const [password, setPassword] = useState("Password123");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const isLogin = mode === "login";

  async function handleSubmit(event?: React.FormEvent) {
    event?.preventDefault();

    const validationError = validateForm({
      mode,
      username,
      email,
      password,
    });

    if (validationError) {
      setError(validationError);
      return;
    }

    try {
      setLoading(true);
      setError("");

      if (mode === "register") {
        await registerUser({
          username: username.trim(),
          email: email.trim(),
          password,
        });
      }

      await loginUser({
        email: email.trim(),
        password,
      });

      onLoginSuccess();
    } catch (err: any) {
      console.error("登录/注册失败：", err);

      setError(
        err?.response?.data?.detail ||
          err?.response?.data?.message ||
          err?.message ||
          "操作失败，请检查邮箱或密码"
      );
    } finally {
      setLoading(false);
    }
  }

  function switchMode(nextMode: Mode) {
    setMode(nextMode);
    setError("");
  }

  return (
    <div className="min-h-screen bg-slate-950 px-4 py-8 text-white">
      <div className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-6xl items-center gap-8 lg:grid-cols-[1.05fr_0.95fr]">
        <section className="hidden lg:block">
          <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-2 text-sm text-white/70">
            <Sparkles className="h-4 w-4" />
            AI Resume Matcher
          </div>

          <h1 className="mt-6 max-w-2xl text-5xl font-semibold tracking-tight">
            用 AI 把简历和岗位 JD 变成清晰的求职行动计划
          </h1>

          <p className="mt-5 max-w-xl text-base leading-8 text-white/60">
            上传 PDF 简历，粘贴目标岗位 JD，系统会生成匹配分、关键词差距、
            优势、不足、优化建议，并支持 Agent 后续追问。
          </p>

          <div className="mt-8 grid max-w-xl gap-3">
            {[
              "自动解析 PDF 简历文本",
              "基于岗位 JD 生成匹配分析",
              "展示 matched / missing keywords",
              "支持 Agent 改写简历、生成面试题和学习计划",
            ].map((item) => (
              <div
                key={item}
                className="flex items-center gap-3 rounded-2xl bg-white/10 px-4 py-3 text-sm text-white/75"
              >
                <CheckCircle2 className="h-4 w-4 text-emerald-300" />
                {item}
              </div>
            ))}
          </div>
        </section>

        <section className="mx-auto w-full max-w-md">
          <div className="rounded-[2rem] bg-white p-6 text-slate-950 shadow-2xl">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-950 text-white">
                <Sparkles className="h-5 w-5" />
              </div>

              <div>
                <div className="text-sm text-slate-500">欢迎使用</div>
                <h2 className="text-xl font-semibold">AI Resume Matcher</h2>
              </div>
            </div>

            <div className="mt-6 grid grid-cols-2 rounded-2xl bg-slate-100 p-1 text-sm">
              <button
                type="button"
                onClick={() => switchMode("login")}
                className={[
                  "rounded-xl px-4 py-2 font-medium transition",
                  mode === "login"
                    ? "bg-white text-slate-950 shadow-sm"
                    : "text-slate-500 hover:text-slate-950",
                ].join(" ")}
              >
                登录
              </button>

              <button
                type="button"
                onClick={() => switchMode("register")}
                className={[
                  "rounded-xl px-4 py-2 font-medium transition",
                  mode === "register"
                    ? "bg-white text-slate-950 shadow-sm"
                    : "text-slate-500 hover:text-slate-950",
                ].join(" ")}
              >
                注册
              </button>
            </div>

            <form onSubmit={handleSubmit} className="mt-6 space-y-4">
              {!isLogin && (
                <Field
                  label="用户名"
                  icon={<User className="h-4 w-4" />}
                  value={username}
                  onChange={setUsername}
                  placeholder="请输入用户名"
                  autoComplete="username"
                />
              )}

              <Field
                label="邮箱"
                icon={<Mail className="h-4 w-4" />}
                value={email}
                onChange={setEmail}
                placeholder="请输入邮箱"
                type="email"
                autoComplete="email"
              />

              <Field
                label="密码"
                icon={<Lock className="h-4 w-4" />}
                value={password}
                onChange={setPassword}
                placeholder="请输入密码"
                type="password"
                autoComplete={isLogin ? "current-password" : "new-password"}
              />

              {!isLogin && (
                <div className="rounded-2xl bg-slate-50 p-4 text-xs leading-5 text-slate-500">
                  密码建议至少 8 位。当前后端会校验账号信息，如果注册成功，前端会自动帮你登录。
                </div>
              )}

              {error && (
                <div className="rounded-2xl bg-red-50 p-4 text-sm leading-6 text-red-700">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {isLogin ? "正在登录..." : "正在注册..."}
                  </>
                ) : (
                  <>
                    {isLogin ? "登录" : "注册并登录"}
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>
            </form>

            <div className="mt-6 rounded-2xl bg-slate-50 p-4">
              <div className="text-xs font-medium text-slate-500">
                Demo 账号提示
              </div>

              <div className="mt-2 space-y-1 text-xs text-slate-400">
                <p>邮箱：demo@example.com</p>
                <p>密码：Password123</p>
              </div>
            </div>
          </div>

          <p className="mt-5 text-center text-xs text-white/40">
            登录后即可进入简历匹配工作台。
          </p>
        </section>
      </div>
    </div>
  );
}

function Field({
  label,
  icon,
  value,
  onChange,
  placeholder,
  type = "text",
  autoComplete,
}: {
  label: string;
  icon: React.ReactNode;
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  type?: string;
  autoComplete?: string;
}) {
  return (
    <label className="block">
      <div className="mb-2 text-sm font-medium text-slate-700">{label}</div>

      <div className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 transition focus-within:border-slate-400">
        <div className="text-slate-400">{icon}</div>

        <input
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          type={type}
          autoComplete={autoComplete}
          className="min-w-0 flex-1 bg-transparent text-sm text-slate-950 outline-none placeholder:text-slate-400"
        />
      </div>
    </label>
  );
}

function validateForm({
  mode,
  username,
  email,
  password,
}: {
  mode: Mode;
  username: string;
  email: string;
  password: string;
}) {
  if (mode === "register" && !username.trim()) {
    return "请输入用户名";
  }

  if (!email.trim()) {
    return "请输入邮箱";
  }

  if (!email.includes("@")) {
    return "请输入有效邮箱";
  }

  if (!password) {
    return "请输入密码";
  }

  if (password.length < 8) {
    return "密码至少需要 8 位";
  }

  return "";
}