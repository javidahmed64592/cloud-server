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
      className="group flex flex-col items-center gap-2 rounded-lg border border-border bg-background-secondary p-3 transition-colors duration-150 hover:border-border-accent hover:bg-background-tertiary w-full focus:outline-none focus-visible:ring-2 focus-visible:ring-border-accent"
    >
      <svg
        className="h-10 w-10 text-neon-blue opacity-75 transition-opacity group-hover:opacity-100"
        viewBox="0 0 24 24"
        fill="currentColor"
      >
        <path d="M20 6h-8l-2-2H4C2.9 4 2 4.9 2 6v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2z" />
      </svg>
      <span
        className="w-full truncate text-center text-xs text-text-secondary transition-colors group-hover:text-text-primary"
        title={name}
      >
        {name}
      </span>
    </button>
  );
}
