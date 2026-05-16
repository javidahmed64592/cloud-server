"use client";

interface FolderCardProps {
  name: string;
  onClick: () => void;
}

export default function FolderCard({ name, onClick }: FolderCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="group flex flex-col items-center gap-2 rounded-lg p-3 transition-colors duration-150 hover:bg-background-secondary w-full focus:outline-none focus-visible:ring-2 focus-visible:ring-border-accent"
    >
      <div className="flex h-36 w-36 items-center justify-center rounded bg-background-tertiary">
        <svg
          className="h-20 w-20 text-neon-blue opacity-75 transition-opacity group-hover:opacity-100"
          viewBox="0 0 24 24"
          fill="currentColor"
        >
          <path d="M20 6h-8l-2-2H4C2.9 4 2 4.9 2 6v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2z" />
        </svg>
      </div>
      <div className="w-full text-center">
        <p className="truncate text-sm text-text-primary px-1" title={name}>
          {name}
        </p>
      </div>
    </button>
  );
}
