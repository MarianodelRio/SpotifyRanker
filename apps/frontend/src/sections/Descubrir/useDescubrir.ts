import { useState, useEffect, useCallback } from "react";
import { generatePlaylist, getPlaylistHistory, exportPlaylist } from "../../api/playlist";
import type { GeneratedPlaylist, PlaylistMode } from "../../types/api";

interface DescubrirState {
  mode: PlaylistMode;
  size: number;
  generating: boolean;
  exporting: boolean;
  currentPlaylist: GeneratedPlaylist | null;
  history: GeneratedPlaylist[];
  spotifyUrl: string | null;
  error: string | null;
}

export function useDescubrir() {
  const [state, setState] = useState<DescubrirState>({
    mode: "balanced",
    size: 20,
    generating: false,
    exporting: false,
    currentPlaylist: null,
    history: [],
    spotifyUrl: null,
    error: null,
  });

  useEffect(() => {
    getPlaylistHistory()
      .then((history) => setState((s) => ({ ...s, history })))
      .catch(() => {});
  }, []);

  const setMode = useCallback((mode: PlaylistMode) => {
    setState((s) => ({ ...s, mode }));
  }, []);

  const setSize = useCallback((size: number) => {
    setState((s) => ({ ...s, size }));
  }, []);

  const generate = useCallback(async () => {
    setState((s) => ({ ...s, generating: true, error: null, spotifyUrl: null }));
    try {
      const playlist = await generatePlaylist({ mode: state.mode, size: state.size });
      setState((s) => ({
        ...s,
        generating: false,
        currentPlaylist: playlist,
        history: [playlist, ...s.history.filter((h) => h.id !== playlist.id)],
      }));
    } catch {
      setState((s) => ({ ...s, generating: false, error: "Failed to generate playlist. Try again." }));
    }
  }, [state.mode, state.size]);

  const exportCurrent = useCallback(async () => {
    if (!state.currentPlaylist) return;
    setState((s) => ({ ...s, exporting: true, error: null }));
    try {
      const { url } = await exportPlaylist(state.currentPlaylist.id);
      setState((s) => ({
        ...s,
        exporting: false,
        spotifyUrl: url,
        currentPlaylist: s.currentPlaylist ? { ...s.currentPlaylist, spotify_url: url } : null,
      }));
    } catch {
      setState((s) => ({ ...s, exporting: false, error: "Failed to export playlist." }));
    }
  }, [state.currentPlaylist]);

  const loadFromHistory = useCallback((playlist: GeneratedPlaylist) => {
    setState((s) => ({ ...s, currentPlaylist: playlist, spotifyUrl: playlist.spotify_url, error: null }));
  }, []);

  return { ...state, setMode, setSize, generate, exportCurrent, loadFromHistory };
}
