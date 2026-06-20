import { useState, useCallback, useRef, useEffect, type ReactNode } from "react";
import { PlayerContext } from "./player-context";
import type { Track, PlaySource } from "../types/api";
import { getToken } from "../api/auth";
import { recordPlayerEvent } from "../api/player";

interface PlayerProviderProps {
  children: ReactNode;
}

const SPOTIFY_API = "https://api.spotify.com/v1";

export function PlayerProvider({ children }: PlayerProviderProps) {
  const [currentTrack, setCurrentTrack] = useState<Track | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [deviceId, setDeviceId] = useState<string | null>(null);

  const playerRef = useRef<Spotify.Player | null>(null);
  const deviceIdRef = useRef<string | null>(null);
  const positionMsRef = useRef(0);
  const trackStartMsRef = useRef(0);
  const prevTrackIdRef = useRef<string | null>(null);
  // Use a ref so the player_state_changed callback always has the latest source
  const currentSourceRef = useRef<PlaySource | null>(null);

  const getAccessToken = useCallback(async (): Promise<string> => {
    const { access_token } = await getToken();
    return access_token;
  }, []);

  const transferPlayback = useCallback(async (id: string) => {
    const token = await getAccessToken();
    await fetch(`${SPOTIFY_API}/me/player`, {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ device_ids: [id], play: false }),
    });
  }, [getAccessToken]);

  const createAndConnectPlayer = useCallback(() => {
    const player = new window.Spotify.Player({
      name: "TasteRanker",
      getOAuthToken: (cb) => {
        getAccessToken().then(cb).catch(console.error);
      },
      volume: 0.8,
    });

    player.addListener("ready", ({ device_id }) => {
      deviceIdRef.current = device_id;
      setDeviceId(device_id);
      transferPlayback(device_id).catch(console.error);
    });

    player.addListener("player_state_changed", (state) => {
      if (!state) return;

      positionMsRef.current = state.position;
      setIsPlaying(!state.paused);

      const sdkTrackId = state.track_window.current_track?.id ?? null;
      if (sdkTrackId && sdkTrackId !== prevTrackIdRef.current) {
        if (prevTrackIdRef.current && currentSourceRef.current) {
          const msPlayed = Date.now() - trackStartMsRef.current;
          recordPlayerEvent({
            track_id: prevTrackIdRef.current,
            ms_played: msPlayed,
            source: currentSourceRef.current,
            playlist_id: null,
          }).catch(console.error);
        }
        prevTrackIdRef.current = sdkTrackId;
        trackStartMsRef.current = Date.now();
      }
    });

    player.addListener("authentication_error", () => {
      player.disconnect();
      playerRef.current = null;
      // Reinitialize after a brief delay to avoid rapid retry loops
      setTimeout(createAndConnectPlayer, 1000);
    });

    player.addListener("account_error", () => {
      console.error("Spotify Premium is required for browser playback.");
    });

    player.connect().catch(console.error);
    playerRef.current = player;
  }, [getAccessToken, transferPlayback]);

  useEffect(() => {
    if (window.Spotify) {
      createAndConnectPlayer();
    } else {
      const prev = window.onSpotifyWebPlaybackSDKReady;
      window.onSpotifyWebPlaybackSDKReady = () => {
        if (prev) prev();
        createAndConnectPlayer();
      };
    }

    return () => {
      playerRef.current?.disconnect();
      playerRef.current = null;
    };
  // createAndConnectPlayer is stable (no state deps, only refs and stable callbacks)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const playTrack = useCallback(
    async (track: Track, source: PlaySource) => {
      const id = deviceIdRef.current;
      if (!id) return;

      if (prevTrackIdRef.current && currentSourceRef.current && prevTrackIdRef.current !== track.spotify_id) {
        const msPlayed = Date.now() - trackStartMsRef.current;
        recordPlayerEvent({
          track_id: prevTrackIdRef.current,
          ms_played: msPlayed,
          source: currentSourceRef.current,
          playlist_id: null,
        }).catch(console.error);
      }

      setCurrentTrack(track);
      currentSourceRef.current = source;
      prevTrackIdRef.current = track.spotify_id;
      trackStartMsRef.current = Date.now();

      const token = await getAccessToken();
      await fetch(`${SPOTIFY_API}/me/player/play?device_id=${id}`, {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ uris: [`spotify:track:${track.spotify_id}`] }),
      });
    },
    [getAccessToken],
  );

  const togglePlay = useCallback(() => {
    playerRef.current?.togglePlay().catch(console.error);
  }, []);

  const skipToNext = useCallback(() => {
    playerRef.current?.nextTrack().catch(console.error);
  }, []);

  const getPositionMs = useCallback(() => positionMsRef.current, []);

  return (
    <PlayerContext.Provider
      value={{
        currentTrack,
        isPlaying,
        deviceId,
        currentSource: currentSourceRef.current,
        playTrack,
        togglePlay,
        skipToNext,
        getPositionMs,
      }}
    >
      {children}
    </PlayerContext.Provider>
  );
}
