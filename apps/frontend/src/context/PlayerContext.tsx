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
  const [playerError, setPlayerError] = useState<string | null>(null);

  const playerRef = useRef<Spotify.Player | null>(null);
  const deviceIdRef = useRef<string | null>(null);
  const devicePollAbortRef = useRef<AbortController | null>(null);
  const positionMsRef = useRef(0);
  const trackStartMsRef = useRef(0);
  const prevTrackIdRef = useRef<string | null>(null);
  const currentSourceRef = useRef<PlaySource | null>(null);

  const getAccessToken = useCallback(async (): Promise<string> => {
    const { access_token } = await getToken();
    return access_token;
  }, []);

  // Background diagnostic: poll /devices to see if SDK device ever registers.
  // Does NOT gate playback — only used for logging.
  const watchDeviceRegistration = useCallback(
    async (id: string, signal?: AbortSignal): Promise<void> => {
      const token = await getAccessToken();
      for (let attempt = 0; attempt < 20; attempt++) {
        if (signal?.aborted) return;
        try {
          const res = await fetch(`${SPOTIFY_API}/me/player/devices`, {
            headers: { Authorization: `Bearer ${token}` },
            signal,
          });
          const body = await res.text().catch(() => "");
          if (res.ok) {
            const data = JSON.parse(body) as { devices?: Array<{ id: string; name: string }> };
            const devices = data.devices ?? [];

            // Spotify may assign a different server-side id than the SDK's ready id.
            // Match by name and use the server-assigned id for REST calls.
            const myDevice = devices.find(d => d.name === "TasteRanker");
            if (myDevice) {
              if (myDevice.id !== id) {
                console.log(`[Player] TasteRanker registered with server id=${myDevice.id} (SDK id was ${id})`);
                deviceIdRef.current = myDevice.id;
                setDeviceId(myDevice.id);
              }
              return;
            }
          }
        } catch (err) {
          if (signal?.aborted) return;
          console.warn("[Player] /devices poll error:", err);
        }
        await new Promise(r => setTimeout(r, 1000));
      }
      console.warn(`[Player] ✗ device ${id} never appeared in /devices after 20s`);
    },
    [getAccessToken],
  );

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

      devicePollAbortRef.current?.abort();
      const controller = new AbortController();
      devicePollAbortRef.current = controller;
      watchDeviceRegistration(device_id, controller.signal).catch(console.error);
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

    player.addListener("authentication_error", ({ message }) => {
      console.warn("[Player] authentication_error:", message);
      devicePollAbortRef.current?.abort();
      devicePollAbortRef.current = null;
      player.disconnect();
      playerRef.current = null;
      setTimeout(createAndConnectPlayer, 1000);
    });

    player.addListener("account_error", () => {
      setPlayerError("Spotify Premium is required for browser playback.");
    });

    player.addListener("playback_error", ({ message }) => {
      console.error("[Player] playback_error:", message);
    });

    player.connect().catch(console.error);

    playerRef.current = player;
  }, [getAccessToken, watchDeviceRegistration]);

  useEffect(() => {
    if ((window as typeof window & { __spotifyReady?: boolean }).__spotifyReady || window.Spotify) {
      createAndConnectPlayer();
    } else {
      const prev = window.onSpotifyWebPlaybackSDKReady;
      window.onSpotifyWebPlaybackSDKReady = () => {
        if (prev) prev();
        createAndConnectPlayer();
      };
    }

    return () => {
      devicePollAbortRef.current?.abort();
      playerRef.current?.disconnect();
      playerRef.current = null;
    };
  // createAndConnectPlayer is stable
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const playTrack = useCallback(
    async (track: Track, source: PlaySource) => {
      const id = deviceIdRef.current;
      if (!id) {
        console.warn("[Player] playTrack called but no device_id yet");
        return;
      }

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

      // Retry on 404: SDK device may take a few seconds to propagate to Spotify's REST API.
      for (let attempt = 0; attempt < 10; attempt++) {
        const res = await fetch(`${SPOTIFY_API}/me/player/play?device_id=${id}`, {
          method: "PUT",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ uris: [`spotify:track:${track.spotify_id}`] }),
        });

        if (res.ok) return;

        if (res.status === 403) {
          setPlayerError("Playback failed: check Spotify Premium or app permissions.");
          return;
        }
        if (res.status !== 404) return;

        await new Promise(r => setTimeout(r, 1000));
      }

      console.error(`[Player] play failed after 10 attempts for device ${id}`);
    },
    [getAccessToken],
  );

  const togglePlay = useCallback(async () => {
    const id = deviceIdRef.current;
    if (!id) return;
    const token = await getAccessToken();
    const sdkState = await playerRef.current?.getCurrentState().catch(() => null) ?? null;
    const paused = sdkState ? sdkState.paused : !isPlaying;
    const url = paused
      ? `${SPOTIFY_API}/me/player/play?device_id=${id}`
      : `${SPOTIFY_API}/me/player/pause`;
    await fetch(url, {
      method: "PUT",
      headers: { Authorization: `Bearer ${token}` },
    }).catch(console.error);
  }, [getAccessToken, isPlaying]);

  const skipToNext = useCallback(async () => {
    const id = deviceIdRef.current;
    if (!id) return;
    const token = await getAccessToken();
    await fetch(`${SPOTIFY_API}/me/player/next?device_id=${id}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    }).catch(console.error);
  }, [getAccessToken]);

  const getPositionMs = useCallback(() => positionMsRef.current, []);

  return (
    <PlayerContext.Provider
      value={{
        currentTrack,
        isPlaying,
        deviceId,
        currentSource: currentSourceRef.current,
        error: playerError,
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
