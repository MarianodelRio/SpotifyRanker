import { useEffect, useRef, useState } from "react";
import { usePlayer } from "../../hooks/usePlayer";

export default function PlayerPanel() {
  const { currentTrack, isPlaying, togglePlay, skipToNext, getPositionMs } = usePlayer();

  const [displayPositionMs, setDisplayPositionMs] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    if (isPlaying) {
      intervalRef.current = setInterval(() => {
        setDisplayPositionMs(getPositionMs());
      }, 1000);
    } else {
      setDisplayPositionMs(getPositionMs());
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isPlaying, getPositionMs]);

  const durationMs = currentTrack?.duration_ms ?? 0;
  const progress = durationMs > 0 ? (displayPositionMs / durationMs) * 100 : 0;

  const formatTime = (ms: number) => {
    const totalSec = Math.floor(ms / 1000);
    const min = Math.floor(totalSec / 60);
    const sec = totalSec % 60;
    return `${min}:${sec.toString().padStart(2, "0")}`;
  };

  return (
    <aside className="w-72 shrink-0 flex flex-col items-center border-l border-zinc-800 p-6 gap-4">
      {currentTrack?.image_url ? (
        <img
          src={currentTrack.image_url}
          alt={currentTrack.album_title}
          className="w-full aspect-square rounded object-cover"
        />
      ) : (
        <div className="w-full aspect-square bg-zinc-800 rounded" aria-hidden="true" />
      )}

      <div className="w-full text-center">
        <p className="text-sm text-white font-medium truncate">
          {currentTrack?.title ?? "—"}
        </p>
        <p className="text-xs text-zinc-500 truncate">
          {currentTrack?.artist_name ?? "No track playing"}
        </p>
      </div>

      <div className="w-full flex flex-col gap-1">
        <div className="w-full h-1 bg-zinc-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-white rounded-full transition-[width] duration-1000 ease-linear"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-zinc-500">
          <span>{formatTime(displayPositionMs)}</span>
          <span>{formatTime(durationMs)}</span>
        </div>
      </div>

      <div className="flex items-center gap-6">
        <button
          aria-label={isPlaying ? "Pause" : "Play"}
          onClick={togglePlay}
          disabled={!currentTrack}
          className="text-zinc-400 hover:text-white transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-white rounded disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {isPlaying ? "⏸" : "▶"}
        </button>
        <button
          aria-label="Skip"
          onClick={skipToNext}
          disabled={!currentTrack}
          className="text-zinc-400 hover:text-white transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-white rounded disabled:opacity-40 disabled:cursor-not-allowed"
        >
          ⏭
        </button>
        <button
          aria-label="Like"
          disabled={!currentTrack}
          className="text-zinc-400 hover:text-white transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-white rounded disabled:opacity-40 disabled:cursor-not-allowed"
        >
          ♥
        </button>
        <button
          aria-label="Dislike"
          disabled={!currentTrack}
          className="text-zinc-400 hover:text-white transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-white rounded disabled:opacity-40 disabled:cursor-not-allowed"
        >
          ✕
        </button>
      </div>
    </aside>
  );
}
