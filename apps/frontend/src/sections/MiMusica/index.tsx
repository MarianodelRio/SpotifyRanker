import { useState, useEffect, useCallback } from "react";
import { getLibrary } from "../../api/library";
import TrackCard from "../../components/track/TrackCard";
import type { Track } from "../../types/api";
import { useImportPoller } from "./useImportPoller";

const PER_PAGE = 50;

export default function MiMusica() {
  const [tracks, setTracks] = useState<Track[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { status, tracksImported, artistsImported, triggerImport, justCompleted } =
    useImportPoller();

  const fetchPage = useCallback(async (pageNum: number, replace: boolean) => {
    try {
      const data = await getLibrary(pageNum, PER_PAGE);
      setTracks((prev) => (replace ? data.tracks : [...prev, ...data.tracks]));
      setTotal(data.total);
      setPage(data.page);
    } catch {
      setError("Failed to load tracks. Please refresh.");
    }
  }, []);

  // Initial load
  useEffect(() => {
    setLoading(true);
    fetchPage(1, true).finally(() => setLoading(false));
  }, [fetchPage]);

  // Re-fetch from page 1 when import completes
  useEffect(() => {
    if (!justCompleted) return;
    setLoading(true);
    fetchPage(1, true).finally(() => setLoading(false));
  }, [justCompleted, fetchPage]);

  const handleLoadMore = async () => {
    setLoadingMore(true);
    await fetchPage(page + 1, false);
    setLoadingMore(false);
  };

  const handleRefresh = async () => {
    try {
      await triggerImport();
    } catch {
      setError("Failed to start import.");
    }
  };

  const hasMore = tracks.length < total;
  const isEmpty = !loading && tracks.length === 0;
  const isImporting = status === "running";

  return (
    <div className="flex flex-col h-full">
      {/* Import status banner */}
      {(isImporting || status === "failed") && (
        <div
          className={`flex items-center justify-between px-4 py-2 text-sm ${
            status === "failed" ? "bg-red-900/40 text-red-300" : "bg-zinc-800 text-zinc-300"
          }`}
          aria-live="polite"
        >
          {status === "failed" ? (
            <span>Import failed. Try refreshing.</span>
          ) : (
            <span>
              Importing from Spotify — {tracksImported} tracks, {artistsImported} artists
            </span>
          )}
          <button
            onClick={handleRefresh}
            className="ml-4 px-3 py-1 rounded text-xs bg-zinc-700 hover:bg-zinc-600 text-white transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-white outline-none"
            aria-label="Refresh import"
          >
            Refresh
          </button>
        </div>
      )}

      <div className="flex items-center justify-between px-4 pt-4 pb-2">
        <h2 className="text-xl font-semibold text-white">Mi música</h2>
        {!isImporting && (
          <button
            onClick={handleRefresh}
            disabled={isImporting}
            className="text-xs text-zinc-400 hover:text-white transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-white outline-none disabled:opacity-50"
            aria-label="Start import"
          >
            ↻ Sync library
          </button>
        )}
      </div>

      {/* Error */}
      {error && (
        <p className="px-4 py-2 text-sm text-red-400" role="alert">
          {error}
        </p>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div className="flex-1 overflow-y-auto px-2" aria-busy="true" aria-label="Loading tracks">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3 p-3 rounded-lg">
              <div className="w-10 h-10 rounded bg-zinc-800 shrink-0 animate-pulse" />
              <div className="flex-1 space-y-2">
                <div className="h-3 bg-zinc-800 rounded animate-pulse w-3/4" />
                <div className="h-2 bg-zinc-800 rounded animate-pulse w-1/2" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {isEmpty && (
        <div className="flex-1 flex flex-col items-center justify-center gap-4 text-center px-8">
          <p className="text-zinc-400 text-sm">
            Your library is empty. Import your Spotify tracks to get started.
          </p>
          <button
            onClick={handleRefresh}
            className="px-4 py-2 rounded bg-green-600 hover:bg-green-500 text-white text-sm font-medium transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-white outline-none"
          >
            Import from Spotify
          </button>
        </div>
      )}

      {/* Track list */}
      {!loading && tracks.length > 0 && (
        <div className="flex-1 overflow-y-auto px-2">
          {tracks.map((track) => (
            <TrackCard key={track.spotify_id} track={track} source="my_music" />
          ))}

          {hasMore && (
            <div className="py-4 flex justify-center">
              <button
                onClick={handleLoadMore}
                disabled={loadingMore}
                className="px-4 py-2 rounded bg-zinc-800 hover:bg-zinc-700 text-sm text-zinc-300 transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-white outline-none disabled:opacity-50"
              >
                {loadingMore ? "Loading…" : "Load more"}
              </button>
            </div>
          )}

          {!hasMore && tracks.length > 0 && (
            <p className="text-center text-xs text-zinc-600 py-4">
              {total} track{total !== 1 ? "s" : ""} total
            </p>
          )}
        </div>
      )}
    </div>
  );
}
