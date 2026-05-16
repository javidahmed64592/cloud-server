"use client";

interface Segment {
  label: string;
  path: string;
}

function getSegments(path: string): Segment[] {
  if (path === ".") return [];
  const parts = path.split("/");
  return parts.map((part, i) => ({
    label: part,
    path: parts.slice(0, i + 1).join("/"),
  }));
}

interface BreadcrumbProps {
  path: string;
  onNavigate: (path: string) => void;
}

export default function Breadcrumb({ path, onNavigate }: BreadcrumbProps) {
  const segments = getSegments(path);

  return (
    <nav
      className="flex items-center gap-1 text-sm"
      aria-label="Directory path"
    >
      <button
        onClick={() => onNavigate(".")}
        className={`rounded px-1 transition-colors hover:text-text-primary ${
          path === "."
            ? "font-semibold text-text-primary"
            : "text-text-secondary"
        }`}
      >
        Drive
      </button>
      {segments.map((seg, i) => (
        <span key={seg.path} className="flex items-center gap-1">
          <span className="text-text-muted select-none">/</span>
          <button
            onClick={() => onNavigate(seg.path)}
            className={`rounded px-1 transition-colors hover:text-text-primary ${
              i === segments.length - 1
                ? "font-semibold text-text-primary"
                : "text-text-secondary"
            }`}
          >
            {seg.label}
          </button>
        </span>
      ))}
    </nav>
  );
}
