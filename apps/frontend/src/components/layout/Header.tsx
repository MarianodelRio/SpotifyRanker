import { useAuthContext } from "../../hooks/useAuthContext";
import { useModelStatus } from "../../hooks/useModelStatus";

function formatAgo(isoString: string): string {
  const diffMin = Math.floor((Date.now() - new Date(isoString).getTime()) / 60000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${String(diffMin)} min ago`;
  const h = Math.floor(diffMin / 60);
  return `${String(h)}h ago`;
}

export default function Header() {
  const { displayName, logout } = useAuthContext();
  const { status } = useModelStatus();

  return (
    <header className="h-14 shrink-0 flex items-center justify-between px-6 border-b border-zinc-800">
      <span className="text-base font-bold text-white tracking-tight">TasteRanker</span>
      <div className="flex items-center gap-4">
        {status && (
          <span
            className={`text-xs ${status.training_in_progress ? "text-amber-400" : "text-zinc-500"}`}
            aria-live="polite"
          >
            {status.training_in_progress
              ? "Training…"
              : status.trained_at
              ? `Trained ${formatAgo(status.trained_at)}`
              : "Model not trained"}
          </span>
        )}
        {displayName && (
          <span className="text-sm text-zinc-400">{displayName}</span>
        )}
        <button
          onClick={() => void logout()}
          className="text-xs text-zinc-500 transition-colors duration-150 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400"
          aria-label="Log out"
        >
          Log out
        </button>
      </div>
    </header>
  );
}
