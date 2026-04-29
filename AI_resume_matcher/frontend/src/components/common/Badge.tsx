type BadgeTone = "default" | "success" | "warning" | "danger" | "dark";

type Props = {
  children: React.ReactNode;
  tone?: BadgeTone;
};

export default function Badge({ children, tone = "default" }: Props) {
  const classNameMap: Record<BadgeTone, string> = {
    default: "bg-slate-100 text-slate-600",
    success: "bg-emerald-50 text-emerald-700",
    warning: "bg-amber-50 text-amber-700",
    danger: "bg-red-50 text-red-700",
    dark: "bg-white/10 text-white/75",
  };

  return (
    <span
      className={[
        "inline-flex items-center rounded-full px-3 py-1 text-xs font-medium",
        classNameMap[tone],
      ].join(" ")}
    >
      {children}
    </span>
  );
}