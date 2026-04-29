type Props = {
  matchedKeywords: string[];
  missingKeywords: string[];
};

export default function ResultKeywordGrid({
  matchedKeywords,
  missingKeywords,
}: Props) {
  return (
    <section className="grid gap-4 lg:grid-cols-2">
      <KeywordCard
        title="已匹配关键词"
        items={matchedKeywords}
        emptyText="暂无匹配关键词"
      />

      <KeywordCard
        title="缺失关键词"
        items={missingKeywords}
        emptyText="暂无缺失关键词"
      />
    </section>
  );
}

function KeywordCard({
  title,
  items,
  emptyText,
}: {
  title: string;
  items: string[];
  emptyText: string;
}) {
  return (
    <div className="rounded-3xl bg-white p-6 shadow-sm">
      <h2 className="font-semibold text-slate-950">{title}</h2>

      {items.length === 0 ? (
        <p className="mt-4 rounded-2xl bg-slate-50 p-4 text-sm text-slate-400">
          {emptyText}
        </p >
      ) : (
        <div className="mt-4 flex flex-wrap gap-2">
          {items.map((item, index) => (
            <span
              key={`${item}-${index}`}
              className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600"
            >
              {item}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}