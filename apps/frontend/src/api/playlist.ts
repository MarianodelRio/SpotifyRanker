import { apiFetch } from "./client";
import type { GeneratedPlaylist, PlaylistGenerateRequest } from "../types/api";

export function generatePlaylist(req: PlaylistGenerateRequest): Promise<GeneratedPlaylist> {
  return apiFetch<GeneratedPlaylist>("/playlist/generate", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export function getPlaylistHistory(): Promise<GeneratedPlaylist[]> {
  return apiFetch<GeneratedPlaylist[]>("/playlist/history");
}

export function getPlaylist(id: string): Promise<GeneratedPlaylist> {
  return apiFetch<GeneratedPlaylist>(`/playlist/${id}`);
}

export function exportPlaylist(id: string): Promise<{ url: string }> {
  return apiFetch<{ url: string }>(`/playlist/${id}/export`, { method: "POST" });
}
