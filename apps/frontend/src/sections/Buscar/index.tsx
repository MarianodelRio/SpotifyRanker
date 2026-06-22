import { useState, useEffect, useRef } from "react";
import { searchTracks } from "../../api/search";
import TrackCard from "../../components/track/TrackCard";
import type { Track } from "../../types/api";

export default function Buscar() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Track[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    if (!query.trim()) {
      setResults([]);
      setIsLoading(false);
      setError(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    debounceRef.current = setTimeout(() => {
      searchTracks(query)
        .then((data) => {
          setResults(data.tracks);
        })
        .catch(() => {
          setError("Search failed. Please try again.");
          setResults([]);
        })
        .finally(() => {
          setIsLoading(false);
        });
    }, 300);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [query]);

  useEffect(() => {
    return () => {
      setResults([]);
      setQuery("");
    };
  }, []);

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 pb-2">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search tracks, artists, albums…"
          aria-label="Search Spotify catalog"
          className="w-full rounded-lg bg-zinc-800 text-white placeholder-zinc-500 px-4 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-white transition-colors duration-150"
        />
      </div>

      <div className="flex-1 overflow-y-auto px-4 pb-4">
        {!query.trim() && (
          <p className="text-sm text-zinc-400 mt-6 text-center">
            Type to search the Spotify catalog.
          </p>
        )}

        {query.trim() && isLoading && (
          <p className="text-sm text-zinc-400 mt-6 text-center" aria-busy="true">
            Searching…
          </p>
        )}

        {query.trim() && error && !isLoading && (
          <p className="text-sm text-red-400 mt-6 text-center">{error}</p>
        )}

        {query.trim() && !isLoading && !error && results.length === 0 && (
          <p className="text-sm text-zinc-400 mt-6 text-center">
            No results found for &ldquo;{query}&rdquo;.
          </p>
        )}

        {results.length > 0 && (
          <ul className="mt-2 space-y-1">
            {results.map((track) => (
              <li key={track.spotify_id}>
                <TrackCard track={track} source="search" />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
