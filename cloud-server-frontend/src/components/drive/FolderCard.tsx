"use client";

interface FolderCardProps {
  name: string;
  onClick: () => void;
  onMove: () => void;
  onDelete: () => void;
}

export default function FolderCard({
  name,
  onClick,
  onMove,
  onDelete,
}: FolderCardProps) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={e => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick();
        }
      }}
      className="group flex flex-col items-center gap-2 rounded-lg p-3 transition-colors duration-150 hover:bg-background-secondary w-full focus:outline-none focus-visible:ring-2 focus-visible:ring-border-accent cursor-pointer"
    >
      <div className="relative flex h-36 w-36 items-center justify-center rounded bg-background-tertiary">
        <svg
          className="h-20 w-20 text-neon-blue opacity-75 transition-opacity group-hover:opacity-100"
          viewBox="0 0 24 24"
          fill="currentColor"
        >
          <path d="M20 6h-8l-2-2H4C2.9 4 2 4.9 2 6v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2z" />
        </svg>

        {/* Hover overlay with action buttons */}
        <div className="absolute inset-0 flex items-center justify-center gap-1 rounded bg-black/70 opacity-0 transition-opacity duration-150 group-hover:opacity-100">
          <button
            type="button"
            onClick={e => {
              e.stopPropagation();
              onMove();
            }}
            className="rounded p-1.5 bg-white/10 text-white hover:bg-white/25 transition-colors"
            title="Rename / Move"
          >
            <svg
              className="h-4 w-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
              />
            </svg>
          </button>
          <button
            type="button"
            onClick={e => {
              e.stopPropagation();
              onDelete();
            }}
            className="rounded p-1.5 bg-white/10 text-neon-red hover:bg-neon-red hover:text-white transition-colors"
            title="Delete"
          >
            <svg
              className="h-4 w-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
          </button>
        </div>
      </div>

      <div className="w-full text-center">
        <p className="truncate text-sm text-text-primary px-1" title={name}>
          {name}
        </p>
      </div>
    </div>
  );
}
