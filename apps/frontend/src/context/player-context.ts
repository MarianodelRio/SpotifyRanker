import { createContext } from "react";
import type { Track, PlaySource } from "../types/api";

export interface PlayerContextValue {
  currentTrack: Track | null;
  isPlaying: boolean;
  deviceId: string | null;
  currentSource: PlaySource | null;
  playTrack: (track: Track, source: PlaySource) => Promise<void>;
  togglePlay: () => void;
  skipToNext: () => void;
  getPositionMs: () => number;
}

export const PlayerContext = createContext<PlayerContextValue | null>(null);
