import { Loader2 } from "lucide-react";

type Props = {
  text?: string;
};

export default function LoadingCard({ text = "正在加载..." }: Props) {
  return (
    <div className="flex items-center justify-center gap-3 rounded-3xl bg-white p-8 text-slate-500 shadow-sm">
      <Loader2 className="h-5 w-5 animate-spin" />
      <span>{text}</span>
    </div>
  );
}