import { apiFetch } from "./client";
import type { PlayerEventRequest } from "../types/api";

export async function recordPlayerEvent(event: PlayerEventRequest): Promise<void> {
  await apiFetch<unknown>("/player/event", {
    method: "POST",
    body: JSON.stringify(event),
  });
}
