import { createContext } from "react";
import type { Track, FeedbackType, PlaySource } from "../types/api";

export interface FeedbackContextValue {
  feedbackMap: Record<string, FeedbackType | null>;
  submitFeedback: (track: Track, type: FeedbackType, source: PlaySource) => void;
}

export const FeedbackContext = createContext<FeedbackContextValue | null>(null);
