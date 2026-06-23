import { apiFetch } from "./client";
import type { ProfileResponse, DeclaredResponse } from "../types/api";

export function getProfile(): Promise<ProfileResponse> {
  return apiFetch<ProfileResponse>("/profile");
}

export async function addArtist(spotifyId: string): Promise<void> {
  await apiFetch<unknown>("/profile/artist", {
    method: "POST",
    body: JSON.stringify({ spotify_id: spotifyId }),
  });
}

export async function addPlaylist(spotifyId: string): Promise<void> {
  await apiFetch<unknown>("/profile/playlist", {
    method: "POST",
    body: JSON.stringify({ spotify_id: spotifyId }),
  });
}

export function getDeclared(): Promise<DeclaredResponse> {
  return apiFetch<DeclaredResponse>("/profile/declared");
}

export async function removeArtist(id: string): Promise<void> {
  await apiFetch<unknown>(`/profile/artist/${id}`, { method: "DELETE" });
}
