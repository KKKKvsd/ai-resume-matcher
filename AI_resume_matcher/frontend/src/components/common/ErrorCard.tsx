import { AlertCircle } from "lucide-react";

type Props = {
  message: string;
};

export default function ErrorCard({ message }: Props) {
  return (
    <div className="flex items-center gap-3 rounded-3xl bg-red-50 p-6 text-red-700 shadow-sm">
      <AlertCircle className="h-5 w-5 shrink-0" />
      <span>{message}</span>
    </div>
  );
}