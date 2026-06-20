import { useAuthContext } from "../../hooks/useAuthContext";

export default function Header() {
  const { displayName, logout } = useAuthContext();

  return (
    <header className="h-14 shrink-0 flex items-center justify-between px-6 border-b border-zinc-800">
      <span className="text-base font-bold text-white tracking-tight">TasteRanker</span>
      <div className="flex items-center gap-4">
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
