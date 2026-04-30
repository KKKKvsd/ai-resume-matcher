import { useEffect, useState } from "react";
import {
  Bot,
  Briefcase,
  FileText,
  History,
  LogOut,
  Mail,
  Menu,
  Sparkles,
  Target,
  UserCircle2,
  X,
} from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { clearToken } from "../../lib/auth";
import { getMe } from "../../lib/api";
import type { User } from "../../types/api";

type Props = {
  children: React.ReactNode;
};

const navItems = [
  {
    label: "工作台",
    path: "/dashboard",
    icon: Target,
  },
  {
    label: "匹配分析",
    path: "/match",
    icon: FileText,
  },
  {
    label: "简历管理",
    path: "/resumes",
    icon: FileText,
  },
  {
    label: "岗位管理",
    path: "/jobs",
    icon: Briefcase,
  },
  {
    label: "Agent问答",
    path: "/agent",
    icon: Bot,
  },
  {
    label: "历史结果",
    path: "/results",
    icon: History,
  },
];

export default function AppShell({ children }: Props) {
  const location = useLocation();
  const navigate = useNavigate();

  const [user, setUser] = useState<User | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  async function loadCurrentUser() {
    try {
      const data = await getMe();
      setUser(data);
    } catch (err) {
      console.error("加载当前用户失败：", err);
    }
  }

  useEffect(() => {
    loadCurrentUser();
  }, []);

  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  function handleLogout() {
    clearToken();
    navigate("/login");
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <MobileTopBar
        user={user}
        onOpenMenu={() => setMobileMenuOpen(true)}
      />

      {mobileMenuOpen && (
        <MobileMenu
          user={user}
          locationPathname={location.pathname}
          onClose={() => setMobileMenuOpen(false)}
          onLogout={handleLogout}
        />
      )}

      <div className="mx-auto flex max-w-7xl gap-6 p-4 md:p-6">
        <DesktopSidebar
          user={user}
          locationPathname={location.pathname}
          onLogout={handleLogout}
        />

        <main className="min-w-0 flex-1 pb-20 lg:pb-0">{children}</main>
      </div>

      <MobileBottomNav locationPathname={location.pathname} />
    </div>
  );
}

function MobileTopBar({
  user,
  onOpenMenu,
}: {
  user: User | null;
  onOpenMenu: () => void;
}) {
  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur lg:hidden">
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-slate-950 text-white">
            <Sparkles className="h-5 w-5" />
          </div>

          <div className="min-w-0">
            <div className="truncate text-sm font-semibold text-slate-950">
              AI Resume Matcher
            </div>

            <div className="truncate text-xs text-slate-500">
              {user ? user.email : "正在加载用户信息..."}
            </div>
          </div>
        </div>

        <button
          onClick={onOpenMenu}
          className="flex h-10 w-10 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-700"
        >
          <Menu className="h-5 w-5" />
        </button>
      </div>
    </header>
  );
}

function DesktopSidebar({
  user,
  locationPathname,
  onLogout,
}: {
  user: User | null;
  locationPathname: string;
  onLogout: () => void;
}) {
  return (
    <aside className="hidden w-72 shrink-0 lg:block">
      <div className="sticky top-6 rounded-3xl bg-slate-950 p-5 text-white shadow-xl">
        <BrandBlock />

        <UserBlock user={user} />

        <nav className="mt-6 space-y-2">
          {navItems.map((item) => (
            <NavLinkItem
              key={item.path}
              item={item}
              active={isActivePath(locationPathname, item.path)}
            />
          ))}
        </nav>

        <AgentInfo />

        <button
          onClick={onLogout}
          className="mt-6 flex w-full items-center gap-3 rounded-2xl px-4 py-3 text-sm text-white/70 transition hover:bg-white/10 hover:text-white"
        >
          <LogOut className="h-4 w-4" />
          退出登录
        </button>
      </div>
    </aside>
  );
}

function MobileMenu({
  user,
  locationPathname,
  onClose,
  onLogout,
}: {
  user: User | null;
  locationPathname: string;
  onClose: () => void;
  onLogout: () => void;
}) {
  return (
    <div className="fixed inset-0 z-40 lg:hidden">
      <button
        onClick={onClose}
        className="absolute inset-0 bg-slate-950/50"
        aria-label="关闭菜单遮罩"
      />

      <aside className="absolute right-0 top-0 h-full w-[86%] max-w-sm bg-slate-950 p-5 text-white shadow-2xl">
        <div className="flex items-center justify-between gap-3">
          <BrandBlock compact />

          <button
            onClick={onClose}
            className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/10 text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <UserBlock user={user} />

        <nav className="mt-6 space-y-2">
          {navItems.map((item) => (
            <NavLinkItem
              key={item.path}
              item={item}
              active={isActivePath(locationPathname, item.path)}
            />
          ))}
        </nav>

        <AgentInfo />

        <button
          onClick={onLogout}
          className="mt-6 flex w-full items-center gap-3 rounded-2xl px-4 py-3 text-sm text-white/70 transition hover:bg-white/10 hover:text-white"
        >
          <LogOut className="h-4 w-4" />
          退出登录
        </button>
      </aside>
    </div>
  );
}

function MobileBottomNav({
  locationPathname,
}: {
  locationPathname: string;
}) {
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-30 border-t border-slate-200 bg-white/95 px-3 py-2 backdrop-blur lg:hidden">
      <div className="grid grid-cols-3 gap-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = isActivePath(locationPathname, item.path);

          return (
            <Link
              key={item.path}
              to={item.path}
              className={[
                "flex flex-col items-center justify-center rounded-2xl px-2 py-2 text-xs transition",
                active
                  ? "bg-slate-950 text-white"
                  : "text-slate-500 hover:bg-slate-100 hover:text-slate-950",
              ].join(" ")}
            >
              <Icon className="mb-1 h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

function BrandBlock({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/10">
        <Sparkles className="h-5 w-5" />
      </div>

      <div>
        <div className="text-sm text-white/50">AI Resume Matcher</div>
        {!compact && <div className="font-semibold">求职智能工作台</div>}
      </div>
    </div>
  );
}

function UserBlock({ user }: { user: User | null }) {
  return (
    <div className="mt-6 rounded-3xl bg-white/10 p-4">
      <div className="flex items-center gap-2 text-sm font-medium">
        <UserCircle2 className="h-4 w-4" />
        当前用户
      </div>

      {user ? (
        <div className="mt-3 space-y-2">
          <div className="text-sm font-semibold text-white">
            {user.username}
          </div>

          <div className="flex items-center gap-2 text-xs text-white/55">
            <Mail className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate">{user.email}</span>
          </div>
        </div>
      ) : (
        <div className="mt-3 text-xs text-white/50">
          正在加载用户信息...
        </div>
      )}
    </div>
  );
}

function AgentInfo() {
  return (
    <div className="mt-8 rounded-3xl bg-white/10 p-4">
      <div className="flex items-center gap-2 text-sm font-medium">
        <Bot className="h-4 w-4" />
        Agent 已接入
      </div>

      <p className="mt-2 text-xs leading-5 text-white/60">
        支持简历匹配、关键词差距、优化建议和后续追问。
      </p>
    </div>
  );
}

function NavLinkItem({
  item,
  active,
}: {
  item: {
    label: string;
    path: string;
    icon: typeof Target;
  };
  active: boolean;
}) {
  const Icon = item.icon;

  return (
    <Link
      to={item.path}
      className={[
        "flex items-center gap-3 rounded-2xl px-4 py-3 text-sm transition",
        active
          ? "bg-white text-slate-950"
          : "text-white/70 hover:bg-white/10 hover:text-white",
      ].join(" ")}
    >
      <Icon className="h-4 w-4" />
      {item.label}
    </Link>
  );
}

function isActivePath(currentPath: string, itemPath: string) {
  if (itemPath === "/dashboard") {
    return currentPath === "/dashboard";
  }

  return currentPath === itemPath || currentPath.startsWith(`${itemPath}/`);
}