declare namespace Spotify {
  interface PlayerInit {
    name: string;
    getOAuthToken: (cb: (token: string) => void) => void;
    volume?: number;
  }

  interface PlayerState {
    paused: boolean;
    position: number;
    duration: number;
    track_window: {
      current_track: Track;
      previous_tracks: Track[];
      next_tracks: Track[];
    };
  }

  interface Track {
    id: string;
    uri: string;
    name: string;
    duration_ms: number;
    artists: Array<{ name: string }>;
    album: {
      name: string;
      images: Array<{ url: string }>;
    };
  }

  interface WebPlaybackInstance {
    device_id: string;
  }

  interface WebPlaybackError {
    message: string;
  }

  class Player {
    constructor(options: PlayerInit);
    connect(): Promise<boolean>;
    disconnect(): void;
    getCurrentState(): Promise<PlayerState | null>;
    getVolume(): Promise<number>;
    setVolume(volume: number): Promise<void>;
    pause(): Promise<void>;
    resume(): Promise<void>;
    togglePlay(): Promise<void>;
    seek(position_ms: number): Promise<void>;
    previousTrack(): Promise<void>;
    nextTrack(): Promise<void>;
    addListener(event: "ready", cb: (instance: WebPlaybackInstance) => void): boolean;
    addListener(event: "not_ready", cb: (instance: WebPlaybackInstance) => void): boolean;
    addListener(event: "player_state_changed", cb: (state: PlayerState | null) => void): boolean;
    addListener(event: "authentication_error", cb: (err: WebPlaybackError) => void): boolean;
    addListener(event: "account_error", cb: (err: WebPlaybackError) => void): boolean;
    addListener(event: "playback_error", cb: (err: WebPlaybackError) => void): boolean;
    removeListener(event: string): boolean;
  }
}

interface Window {
  Spotify: typeof Spotify;
  onSpotifyWebPlaybackSDKReady: () => void;
}
