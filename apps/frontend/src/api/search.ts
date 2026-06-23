import { apiFetch } from "./client";
import type { SearchResult, Artist } from "../types/api";

export function searchTracks(query: string): Promise<SearchResult> {
  return apiFetch<SearchResult>(`/search?q=${encodeURIComponent(query)}&type=track`);
}

export interface ArtistSearchResult {
  tracks: Artist[];
  type: string;
  count: number;
}

export function searchArtists(query: string): Promise<ArtistSearchResult> {
  return apiFetch<ArtistSearchResult>(`/search?q=${encodeURIComponent(query)}&type=artist`);
}
