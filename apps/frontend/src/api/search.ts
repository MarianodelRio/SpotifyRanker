import { apiFetch } from "./client";
import type { SearchResult } from "../types/api";

export function searchTracks(query: string): Promise<SearchResult> {
  return apiFetch<SearchResult>(`/search?q=${encodeURIComponent(query)}&type=track`);
}
