import TrackCard from "../../components/track/TrackCard";
import { useDescubrir } from "./useDescubrir";
import type { PlaylistMode, RankedTrack } from "../../types/api";

const MODES: { value: PlaylistMode; label: string }[] = [
  { value: "safe", label: "Segura" },
  { value: "balanced", label: "Mezcla" },
  { value: "adventurous", label: "Novedad" },
];

function ScoreBreakdown({ ranked }: { ranked: RankedTrack }) {
  return (
    <details className="ml-14 mb-1">
      <summary className="text-xs text-zinc-500 cursor-pointer hover:text-zinc-300 transition-colors duration-150 select-none">
        Score: {ranked.final_score.toFixed(3)}
      </summary>
      <div className="mt-1 pl-2 border-l border-zinc-700 space-y-0.5">
        {Object.entries(ranked.score_breakdown).map(([key, val]) => (
          <div key={key} className="flex justify-between text-xs text-zinc-500">
            <span>{key}</span>
            <span>{typeof val === "number" ? val.toFixed(4) : String(val)}</span>
          </div>
        ))}
      </div>
    </details>
  );
}

export default function Descubrir() {
  const {
    mode, size, generating, exporting, currentPlaylist, history,
    spotifyUrl, error, setMode, setSize, generate, exportCurrent, loadFromHistory,
  } = useDescubrir();

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Controls */}
      <div className="p-4 border-b border-zinc-800 shrink-0">
        <h2 className="text-xl font-semibold text-white mb-4">Descubrir</h2>
        <div className="flex flex-wrap items-center gap-3">
          {/* Tone selector */}
          <div className="flex rounded-lg overflow-hidden border border-zinc-700">
            {MODES.map(({ value, label }) => (
              <button
                key={value}
                onClick={() => setMode(value)}
                aria-pressed={mode === value}
                className={`px-4 py-2 text-sm font-medium transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-white outline-none ${
                  mode === value
                    ? "bg-green-600 text-white"
                    : "bg-zinc-900 text-zinc-400 hover:text-white hover:bg-zinc-800"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Size input */}
          <div className="flex items-center gap-2">
            <label htmlFor="playlist-size" className="text-sm text-zinc-400">
              Tracks
            </label>
            <input
              id="playlist-size"
              type="number"
              min={5}
              max={50}
              value={size}
              onChange={(e) => setSize(Math.max(1, Math.min(50, parseInt(e.target.value) || 20)))}
              className="w-16 px-2 py-1.5 text-sm text-white bg-zinc-800 border border-zinc-700 rounded-lg focus-visible:ring-2 focus-visible:ring-white outline-none"
            />
          </div>

          {/* Generate button */}
          <button
            onClick={generate}
            disabled={generating}
            aria-busy={generating}
            className="px-5 py-2 text-sm font-semibold rounded-lg bg-green-600 text-white hover:bg-green-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-white outline-none"
          >
            {generating ? (
              <span className="flex items-center gap-2">
                <span className="inline-block w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" aria-hidden="true" />
                Generating…
              </span>
            ) : (
              "Generate"
            )}
          </button>

          {/* Export button */}
          {currentPlaylist && (
            <button
              onClick={exportCurrent}
              disabled={exporting || !!spotifyUrl}
              aria-busy={exporting}
              className="px-5 py-2 text-sm font-semibold rounded-lg border border-green-600 text-green-400 hover:bg-green-600 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-white outline-none"
            >
              {exporting ? (
                <span className="flex items-center gap-2">
                  <span className="inline-block w-3.5 h-3.5 border-2 border-green-400/30 border-t-green-400 rounded-full animate-spin" aria-hidden="true" />
                  Exporting…
                </span>
              ) : spotifyUrl ? (
                "✓ Exported"
              ) : (
                "Export to Spotify"
              )}
            </button>
          )}

          {/* Spotify URL */}
          {spotifyUrl && (
            <a
              href={spotifyUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-green-400 underline hover:text-green-300 transition-colors duration-150"
            >
              Open in Spotify ↗
            </a>
          )}
        </div>

        {error && (
          <p role="alert" className="mt-3 text-sm text-red-400">
            {error}
          </p>
        )}
      </div>

      {/* Track list */}
      <div className="flex-1 overflow-y-auto">
        {currentPlaylist ? (
          <>
            <div className="px-4 py-2 text-xs text-zinc-500 border-b border-zinc-800 shrink-0">
              {currentPlaylist.name} · {currentPlaylist.tracks.length} tracks
            </div>
            <div className="py-2">
              {currentPlaylist.tracks.map((ranked) => (
                <div key={ranked.candidate.track.spotify_id}>
                  <TrackCard track={ranked.candidate.track} source="discover" />
                  <ScoreBreakdown ranked={ranked} />
                </div>
              ))}
            </div>
          </>
        ) : !generating ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <p className="text-zinc-400 text-sm">
              Select a tone and press <span className="text-white font-medium">Generate</span> to discover new music.
            </p>
          </div>
        ) : null}
      </div>

      {/* History panel */}
      {history.length > 0 && (
        <details className="border-t border-zinc-800 shrink-0">
          <summary className="px-4 py-3 text-sm text-zinc-400 cursor-pointer hover:text-white hover:bg-zinc-800 transition-colors duration-150 select-none">
            History ({history.length} playlist{history.length !== 1 ? "s" : ""})
          </summary>
          <div className="max-h-48 overflow-y-auto bg-zinc-950">
            {history.map((p) => (
              <button
                key={p.id}
                onClick={() => loadFromHistory(p)}
                className={`w-full text-left px-4 py-2.5 flex items-center justify-between gap-2 hover:bg-zinc-800 transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-white outline-none ${
                  currentPlaylist?.id === p.id ? "bg-zinc-800" : ""
                }`}
              >
                <span className="text-sm text-white truncate">{p.name}</span>
                <span className="text-xs text-zinc-500 shrink-0">
                  {new Date(p.created_at).toLocaleDateString()} · {p.tracks.length} tracks
                </span>
              </button>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}
