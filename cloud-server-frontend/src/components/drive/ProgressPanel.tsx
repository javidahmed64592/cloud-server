interface ProgressItem {
  name: string;
  percent: number;
}

interface ProgressPanelProps {
  title: string;
  detail?: string;
  /** 0..100, or null for an indeterminate bar (e.g. server preparing a zip) */
  percent: number | null;
  items?: ProgressItem[];
}

function Bar({
  percent,
  label,
  small = false,
}: {
  percent: number | null;
  label: string;
  small?: boolean;
}) {
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      {...(percent !== null ? { "aria-valuenow": percent } : {})}
      className={`w-full overflow-hidden rounded-full bg-background-tertiary ${small ? "h-1" : "h-1.5"}`}
    >
      <div
        className={`h-full rounded-full bg-border-accent transition-[width] duration-150 ${percent === null ? "w-full animate-pulse" : ""}`}
        style={percent !== null ? { width: `${percent}%` } : undefined}
      />
    </div>
  );
}

export default function ProgressPanel({
  title,
  detail,
  percent,
  items = [],
}: ProgressPanelProps) {
  return (
    <div className="rounded-lg border border-border bg-background-secondary p-3 shadow-lg">
      <div className="mb-1.5 flex items-center justify-between gap-2 text-xs">
        <span className="font-medium text-text-primary">{title}</span>
        <span className="text-text-muted">{detail}</span>
      </div>
      <Bar percent={percent} label={title} />
      {items.length > 0 && (
        <ul className="mt-2 flex flex-col gap-1.5">
          {items.map((item, i) => (
            <li key={`${i}-${item.name}`}>
              <div className="mb-0.5 flex justify-between gap-2 text-[11px] text-text-muted">
                <span className="truncate" title={item.name}>
                  {item.name}
                </span>
                <span>{item.percent}%</span>
              </div>
              <Bar percent={item.percent} label={item.name} small />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
