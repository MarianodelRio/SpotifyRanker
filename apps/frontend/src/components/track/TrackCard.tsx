import { usePlayer } from "../../hooks/usePlayer";
import { useFeedback } from "../../hooks/useFeedback";
import type { Track, PlaySource } from "../../types/api";

interface TrackCardProps {
  track: Track;
  source: PlaySource;
}

function formatDuration(ms: number): string {
  const totalSec = Math.floor(ms / 1000);
  const min = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  return `${min}:${sec.toString().padStart(2, "0")}`;
}

export default function TrackCard({ track, source }: TrackCardProps) {
  const { playTrack, currentTrack, isPlaying } = usePlayer();
  const { feedbackMap, submitFeedback } = useFeedback();

  const isActive = currentTrack?.spotify_id === track.spotify_id;
  const feedback = feedbackMap[track.spotify_id] ?? null;

  const handlePlay = () => {
    playTrack(track, source).catch(console.error);
  };

  const handleLike = (e: React.MouseEvent) => {
    e.stopPropagation();
    submitFeedback(track, "like", source);
  };

  const handleDislike = (e: React.MouseEvent) => {
    e.stopPropagation();
    submitFeedback(track, "dislike", source);
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={handlePlay}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          handlePlay();
        }
      }}
      aria-label={`Play ${track.title} by ${track.artist_name}`}
      className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-white outline-none ${
        isActive ? "bg-zinc-700" : "hover:bg-zinc-800"
      }`}
    >
      {track.image_url ? (
        <img
          src={track.image_url}
          alt={track.album_title}
          className="w-10 h-10 rounded shrink-0 object-cover"
        />
      ) : (
        <div className="w-10 h-10 rounded shrink-0 bg-zinc-700" aria-hidden="true" />
      )}

      <div className="flex-1 min-w-0">
        <p className={`text-sm font-medium truncate ${isActive ? "text-green-400" : "text-white"}`}>
          {isActive && isPlaying ? "▶ " : ""}
          {track.title}
        </p>
        <p className="text-xs text-zinc-400 truncate">{track.artist_name}</p>
      </div>

      <span className="text-xs text-zinc-500 shrink-0">{formatDuration(track.duration_ms)}</span>

      <div className="flex items-center gap-1 shrink-0" onClick={(e) => e.stopPropagation()}>
        <button
          aria-label="Like"
          onClick={handleLike}
          className={`p-1 rounded transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-white outline-none ${
            feedback === "like" ? "text-green-400" : "text-zinc-500 hover:text-white"
          }`}
        >
          {feedback === "like" ? "♥" : "♡"}
        </button>
        <button
          aria-label="Dislike"
          onClick={handleDislike}
          className={`p-1 rounded transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-white outline-none ${
            feedback === "dislike" ? "text-red-400" : "text-zinc-500 hover:text-white"
          }`}
        >
          ✕
        </button>
      </div>
    </div>
  );
}
