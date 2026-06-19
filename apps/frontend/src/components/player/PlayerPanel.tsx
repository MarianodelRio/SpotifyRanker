export default function PlayerPanel() {
  return (
    <aside className="w-72 shrink-0 flex flex-col items-center border-l border-zinc-800 p-6 gap-4">
      <div className="w-full aspect-square bg-zinc-800 rounded" />
      <div className="w-full text-center">
        <p className="text-sm text-white font-medium truncate">—</p>
        <p className="text-xs text-zinc-500 truncate">No track playing</p>
      </div>
      <div className="w-full h-1 bg-zinc-800 rounded-full" />
      <div className="flex items-center gap-6">
        <button
          aria-label="Previous"
          className="text-zinc-400 hover:text-white transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-white rounded"
        >
          ◀
        </button>
        <button
          aria-label="Play"
          className="text-zinc-400 hover:text-white transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-white rounded"
        >
          ▶
        </button>
        <button
          aria-label="Like"
          className="text-zinc-400 hover:text-white transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-white rounded"
        >
          ♥
        </button>
        <button
          aria-label="Dislike"
          className="text-zinc-400 hover:text-white transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-white rounded"
        >
          ✕
        </button>
      </div>
    </aside>
  );
}
