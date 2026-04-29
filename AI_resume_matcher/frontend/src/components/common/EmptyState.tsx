import type { LucideIcon } from "lucide-react";
import { Clock3 } from "lucide-react";

type Props = {
  title: string;
  description?: string;
  icon?: LucideIcon;
  action?: React.ReactNode;
};

export default function EmptyState({
  title,
  description,
  icon: Icon = Clock3,
  action,
}: Props) {
  return (
    <div className="rounded-3xl bg-white p-8 text-center shadow-sm">
      <Icon className="mx-auto h-8 w-8 text-slate-400" />

      <h2 className="mt-4 font-semibold text-slate-950">{title}</h2>

      {description && (
        <p className="mt-2 text-sm leading-6 text-slate-500">{description}</p >
      )}

      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}