"use client";

import type { SortKey, SortOption } from "@/lib/sort";

interface SortControlProps {
  value: SortOption;
  onChange: (value: SortOption) => void;
}

export default function SortControl({ value, onChange }: SortControlProps) {
  const isAsc = value.direction === "asc";
  return (
    <div className="flex items-center gap-1">
      <div className="relative">
        <select
          aria-label="Sort by"
          value={value.key}
          onChange={e => onChange({ ...value, key: e.target.value as SortKey })}
          className="appearance-none rounded-md border border-border bg-background py-1.5 pl-2 pr-8 text-xs text-text-secondary hover:text-text-primary"
        >
          <option value="name">Name</option>
          <option value="created">Date created</option>
        </select>
        <svg
          aria-hidden="true"
          className="pointer-events-none absolute right-2 top-1/2 h-3 w-3 -translate-y-1/2 text-text-muted"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2.5}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 9l6 6 6-6" />
        </svg>
      </div>
      <button
        type="button"
        onClick={() =>
          onChange({ ...value, direction: isAsc ? "desc" : "asc" })
        }
        aria-label={isAsc ? "Ascending" : "Descending"}
        title={
          value.key === "name"
            ? isAsc
              ? "A → Z"
              : "Z → A"
            : isAsc
              ? "Oldest first"
              : "Newest first"
        }
        className="rounded-md border border-border px-2 py-1.5 text-xs text-text-secondary transition-colors hover:text-text-primary"
      >
        {isAsc ? "↑" : "↓"}
      </button>
    </div>
  );
}
