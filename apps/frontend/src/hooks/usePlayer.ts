import { useContext } from "react";
import { PlayerContext } from "../context/player-context";
import type { PlayerContextValue } from "../context/player-context";

export function usePlayer(): PlayerContextValue {
  const ctx = useContext(PlayerContext);
  if (!ctx) throw new Error("usePlayer must be used inside PlayerProvider");
  return ctx;
}
