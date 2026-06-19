import { apiFetch } from "./client";
import type { FeedbackEntry } from "../types/api";

export async function submitFeedback(entry: FeedbackEntry): Promise<void> {
  await apiFetch<unknown>("/feedback", {
    method: "POST",
    body: JSON.stringify(entry),
  });
}
