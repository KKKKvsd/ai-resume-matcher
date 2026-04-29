type Props = {
  title?: string;
  description?: string;
  data: unknown;
};

export default function RawJsonPanel({
  title = "完整原始数据",
  description = "调试用区域。确认页面稳定后，可以把这一块删掉。",
  data,
}: Props) {
  return (
    <section className="rounded-3xl bg-white p-6 shadow-sm">
      <h2 className="font-semibold text-slate-950">{title}</h2>

      {description && (
        <p className="mt-2 text-sm text-slate-500">{description}</p >
      )}

      <pre className="mt-4 overflow-auto rounded-2xl bg-slate-50 p-4 text-xs leading-6 text-slate-600">
        {JSON.stringify(data, null, 2)}
      </pre>
    </section>
  );
}