import { useState, useRef, useEffect } from "react";
import { useProfile } from "./useProfile";
import { useModelStatus } from "../../hooks/useModelStatus";
import { addArtist, addPlaylist, removeArtist } from "../../api/profile";
import { trainModel } from "../../api/model";
import { searchArtists } from "../../api/search";
import type { Artist } from "../../types/api";

function formatAgo(isoString: string): string {
  const diffMin = Math.floor((Date.now() - new Date(isoString).getTime()) / 60000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${String(diffMin)} min ago`;
  const h = Math.floor(diffMin / 60);
  return `${String(h)}h ago`;
}

function extractPlaylistId(input: string): string {
  const urlMatch = input.match(/playlist\/([A-Za-z0-9]+)/);
  if (urlMatch) return urlMatch[1];
  const uriMatch = input.match(/spotify:playlist:([A-Za-z0-9]+)/);
  if (uriMatch) return uriMatch[1];
  return input.trim();
}

export default function Profile() {
  const { profile, declared, isLoading, error, refresh } = useProfile();
  const { status: modelStatus, refresh: refreshModel } = useModelStatus();

  const [showArtistSearch, setShowArtistSearch] = useState(false);
  const [artistQuery, setArtistQuery] = useState("");
  const [artistResults, setArtistResults] = useState<Artist[]>([]);
  const [artistSearchLoading, setArtistSearchLoading] = useState(false);
  const [artistSearchError, setArtistSearchError] = useState<string | null>(null);
  const [addingArtistId, setAddingArtistId] = useState<string | null>(null);
  const [addArtistError, setAddArtistError] = useState<string | null>(null);
  const artistDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [showPlaylistInput, setShowPlaylistInput] = useState(false);
  const [playlistUrl, setPlaylistUrl] = useState("");
  const [addingPlaylist, setAddingPlaylist] = useState(false);
  const [addPlaylistError, setAddPlaylistError] = useState<string | null>(null);

  const [removingArtistId, setRemovingArtistId] = useState<string | null>(null);
  const [isRequestingTrain, setIsRequestingTrain] = useState(false);

  const isTraining = modelStatus?.training_in_progress ?? false;
  const prevTrainingRef = useRef(false);

  // Refresh profile when training completes
  useEffect(() => {
    if (prevTrainingRef.current && !isTraining) {
      refresh();
    }
    prevTrainingRef.current = isTraining;
  }, [isTraining, refresh]);

  // Artist search with debounce
  useEffect(() => {
    if (artistDebounceRef.current) clearTimeout(artistDebounceRef.current);
    if (!artistQuery.trim()) {
      setArtistResults([]);
      setArtistSearchLoading(false);
      setArtistSearchError(null);
      return;
    }
    setArtistSearchLoading(true);
    setArtistSearchError(null);
    artistDebounceRef.current = setTimeout(() => {
      searchArtists(artistQuery)
        .then((data) => { setArtistResults(data.tracks); })
        .catch(() => { setArtistSearchError("Search failed."); setArtistResults([]); })
        .finally(() => { setArtistSearchLoading(false); });
    }, 300);
    return () => {
      if (artistDebounceRef.current) clearTimeout(artistDebounceRef.current);
    };
  }, [artistQuery]);

  async function handleAddArtist(artist: Artist) {
    setAddingArtistId(artist.spotify_id);
    setAddArtistError(null);
    try {
      await addArtist(artist.spotify_id);
      refresh();
      setArtistQuery("");
      setArtistResults([]);
      setShowArtistSearch(false);
    } catch {
      setAddArtistError(`Failed to add ${artist.name}. Please try again.`);
    } finally {
      setAddingArtistId(null);
    }
  }

  async function handleRemoveArtist(spotifyId: string) {
    setRemovingArtistId(spotifyId);
    try {
      await removeArtist(spotifyId);
      refresh();
    } finally {
      setRemovingArtistId(null);
    }
  }

  async function handleAddPlaylist() {
    const id = extractPlaylistId(playlistUrl);
    if (!id) return;
    setAddingPlaylist(true);
    setAddPlaylistError(null);
    try {
      await addPlaylist(id);
      refresh();
      setPlaylistUrl("");
      setShowPlaylistInput(false);
    } catch {
      setAddPlaylistError("Failed to add playlist. Check the URL and try again.");
    } finally {
      setAddingPlaylist(false);
    }
  }

  async function handleRetrain() {
    setIsRequestingTrain(true);
    try {
      await trainModel();
      refreshModel();
    } finally {
      setIsRequestingTrain(false);
    }
  }

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <span className="text-sm text-zinc-500" aria-busy="true">Loading profile…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <span className="text-sm text-red-400">{error}</span>
      </div>
    );
  }

  const topGenres = profile
    ? Object.entries(profile.genre_weights).sort((a, b) => b[1] - a[1]).slice(0, 8)
    : [];
  const maxGenreWeight = topGenres[0]?.[1] ?? 1;

  const topArtists = profile
    ? Object.entries(profile.top_artists).sort((a, b) => b[1] - a[1]).slice(0, 8)
    : [];

  return (
    <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
      {/* Model Status */}
      <section>
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-medium text-white">Model</h2>
          <button
            onClick={() => void handleRetrain()}
            disabled={isTraining || isRequestingTrain}
            className="px-3 py-1 text-xs rounded bg-zinc-700 text-white transition-colors duration-150 hover:bg-zinc-600 disabled:opacity-40 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400"
            aria-label="Manually retrain model"
          >
            {isTraining ? "Training…" : "Retrain"}
          </button>
        </div>
        <div className="flex items-center gap-4 text-xs text-zinc-400">
          {isTraining ? (
            <span className="text-amber-400" aria-live="polite">Training in progress…</span>
          ) : (
            <span>
              {modelStatus?.trained_at
                ? `Trained ${formatAgo(modelStatus.trained_at)}`
                : "Not trained yet"}
            </span>
          )}
          {modelStatus && (
            <span>{modelStatus.examples_count.toLocaleString()} examples</span>
          )}
        </div>
      </section>

      {/* Genre Weights */}
      {topGenres.length > 0 && (
        <section>
          <h2 className="text-sm font-medium text-white mb-3">Top Genres</h2>
          <ul className="space-y-2">
            {topGenres.map(([genre, weight]) => (
              <li key={genre} className="flex items-center gap-3">
                <span className="w-28 shrink-0 text-xs text-zinc-400 truncate capitalize">{genre}</span>
                <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-green-500 rounded-full transition-all duration-300"
                    style={{ width: `${(weight / maxGenreWeight) * 100}%` }}
                  />
                </div>
                <span className="w-10 text-right text-xs text-zinc-500">{weight.toFixed(2)}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Top Artists */}
      {topArtists.length > 0 && (
        <section>
          <h2 className="text-sm font-medium text-white mb-3">Top Artists</h2>
          <ul className="space-y-1">
            {topArtists.map(([artist, affinity]) => (
              <li key={artist} className="flex items-center justify-between py-0.5">
                <span className="text-sm text-zinc-300 truncate">{artist}</span>
                <span className="ml-4 shrink-0 text-xs text-zinc-500">{affinity.toFixed(2)}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Stats */}
      {profile?.stats && (
        <section>
          <h2 className="text-sm font-medium text-white mb-2">Stats</h2>
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-zinc-900 rounded-lg p-3">
              <div className="text-base font-semibold text-white">
                {profile.stats.total_tracks.toLocaleString()}
              </div>
              <div className="text-xs text-zinc-500 mt-0.5">tracks</div>
            </div>
            <div className="bg-zinc-900 rounded-lg p-3">
              <div className="text-base font-semibold text-white">
                {(profile.stats.global_like_ratio * 100).toFixed(0)}%
              </div>
              <div className="text-xs text-zinc-500 mt-0.5">like ratio</div>
            </div>
            <div className="bg-zinc-900 rounded-lg p-3">
              <div className="text-base font-semibold text-white">
                {profile.stats.diversity_score.toFixed(2)}
              </div>
              <div className="text-xs text-zinc-500 mt-0.5">diversity</div>
            </div>
          </div>
        </section>
      )}

      {/* Declared Artists */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-medium text-white">
            Declared Artists{" "}
            {declared?.artists.length ? (
              <span className="text-zinc-500 font-normal">({declared.artists.length})</span>
            ) : null}
          </h2>
          <button
            onClick={() => {
              setShowArtistSearch((v) => !v);
              setArtistQuery("");
              setArtistResults([]);
              setAddArtistError(null);
            }}
            className="text-xs text-zinc-400 transition-colors duration-150 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400"
          >
            {showArtistSearch ? "Cancel" : "+ Declare artist"}
          </button>
        </div>

        {showArtistSearch && (
          <div className="mb-3">
            <input
              type="search"
              value={artistQuery}
              onChange={(e) => setArtistQuery(e.target.value)}
              placeholder="Search for an artist…"
              aria-label="Search for artist to declare"
              autoFocus
              className="w-full rounded-lg bg-zinc-800 text-white placeholder-zinc-500 px-4 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-white transition-colors duration-150"
            />
            {artistSearchLoading && (
              <p className="text-xs text-zinc-500 mt-2 pl-1" aria-busy="true">Searching…</p>
            )}
            {artistSearchError && (
              <p className="text-xs text-red-400 mt-2 pl-1">{artistSearchError}</p>
            )}
            {addArtistError && (
              <p className="text-xs text-red-400 mt-2 pl-1">{addArtistError}</p>
            )}
            {!artistSearchLoading && artistResults.length > 0 && (
              <ul className="mt-2 space-y-1" aria-label="Artist search results">
                {artistResults.map((artist) => (
                  <li
                    key={artist.spotify_id}
                    className="flex items-center justify-between py-1.5 px-2 rounded-lg hover:bg-zinc-800 transition-colors duration-150"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      {artist.image_url && (
                        <img
                          src={artist.image_url}
                          alt=""
                          className="w-8 h-8 rounded-full shrink-0 object-cover"
                        />
                      )}
                      <span className="text-sm text-zinc-200 truncate">{artist.name}</span>
                    </div>
                    <button
                      onClick={() => void handleAddArtist(artist)}
                      disabled={addingArtistId === artist.spotify_id}
                      className="ml-3 shrink-0 px-2 py-1 text-xs rounded bg-zinc-700 text-white transition-colors duration-150 hover:bg-zinc-600 disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400"
                      aria-label={`Add ${artist.name}`}
                    >
                      {addingArtistId === artist.spotify_id ? "Adding…" : "Add"}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {declared?.artists.length === 0 && !showArtistSearch && (
          <p className="text-xs text-zinc-500">No declared artists yet.</p>
        )}

        {declared && declared.artists.length > 0 && (
          <ul className="space-y-1">
            {declared.artists.map((artist) => (
              <li
                key={artist.spotify_id}
                className="flex items-center justify-between py-1.5 px-2 rounded-lg hover:bg-zinc-800 transition-colors duration-150"
              >
                <div className="flex items-center gap-2 min-w-0">
                  {artist.image_url && (
                    <img
                      src={artist.image_url}
                      alt=""
                      className="w-8 h-8 rounded-full shrink-0 object-cover"
                    />
                  )}
                  <div className="min-w-0">
                    <p className="text-sm text-zinc-200 truncate">{artist.name}</p>
                    <p className="text-xs text-zinc-500">{artist.track_count} tracks</p>
                  </div>
                </div>
                <button
                  onClick={() => void handleRemoveArtist(artist.spotify_id)}
                  disabled={removingArtistId === artist.spotify_id}
                  className="ml-3 shrink-0 text-xs text-zinc-500 transition-colors duration-150 hover:text-red-400 disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400"
                  aria-label={`Remove ${artist.name}`}
                >
                  {removingArtistId === artist.spotify_id ? "Removing…" : "Remove"}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Declared Playlists */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-medium text-white">
            Declared Playlists{" "}
            {declared?.playlists.length ? (
              <span className="text-zinc-500 font-normal">({declared.playlists.length})</span>
            ) : null}
          </h2>
          <button
            onClick={() => {
              setShowPlaylistInput((v) => !v);
              setPlaylistUrl("");
              setAddPlaylistError(null);
            }}
            className="text-xs text-zinc-400 transition-colors duration-150 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400"
          >
            {showPlaylistInput ? "Cancel" : "+ Declare playlist"}
          </button>
        </div>

        {showPlaylistInput && (
          <div className="mb-3">
            <div className="flex gap-2">
              <input
                type="text"
                value={playlistUrl}
                onChange={(e) => setPlaylistUrl(e.target.value)}
                placeholder="Paste a Spotify playlist URL or ID…"
                aria-label="Spotify playlist URL or ID"
                autoFocus
                onKeyDown={(e) => { if (e.key === "Enter") void handleAddPlaylist(); }}
                className="flex-1 rounded-lg bg-zinc-800 text-white placeholder-zinc-500 px-4 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-white transition-colors duration-150"
              />
              <button
                onClick={() => void handleAddPlaylist()}
                disabled={addingPlaylist || !playlistUrl.trim()}
                className="px-3 py-1 text-xs rounded bg-zinc-700 text-white transition-colors duration-150 hover:bg-zinc-600 disabled:opacity-40 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400"
              >
                {addingPlaylist ? "Adding…" : "Add"}
              </button>
            </div>
            {addPlaylistError && (
              <p className="text-xs text-red-400 mt-2 pl-1">{addPlaylistError}</p>
            )}
          </div>
        )}

        {declared?.playlists.length === 0 && !showPlaylistInput && (
          <p className="text-xs text-zinc-500">No declared playlists yet.</p>
        )}

        {declared && declared.playlists.length > 0 && (
          <ul className="space-y-1">
            {declared.playlists.map((playlist) => (
              <li
                key={playlist.spotify_id}
                className="py-1.5 px-2 rounded-lg hover:bg-zinc-800 transition-colors duration-150"
              >
                <p className="text-sm text-zinc-200">{playlist.name}</p>
                <p className="text-xs text-zinc-500">{playlist.track_count} tracks</p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
