type Props = {
  title: string;
  description?: string;
  eyebrow?: React.ReactNode;
  actions?: React.ReactNode;
};

export default function PageHeader({
  title,
  description,
  eyebrow,
  actions,
}: Props) {
  return (
    <header className="flex flex-col justify-between gap-4 rounded-3xl bg-white p-6 shadow-sm md:flex-row md:items-center">
      <div>
        {eyebrow && <div className="mb-3">{eyebrow}</div>}

        <h1 className="text-2xl font-semibold tracking-tight text-slate-950">
          {title}
        </h1>

        {description && (
          <p className="mt-2 text-sm leading-6 text-slate-500">
            {description}
          </p >
        )}
      </div>

      {actions && <div className="shrink-0">{actions}</div>}
    </header>
  );
}