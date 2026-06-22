import { useState, useCallback, type ReactNode } from "react";
import { FeedbackContext } from "./feedback-context";
import { submitFeedback as apiSubmitFeedback } from "../api/feedback";
import type { Track, FeedbackType, PlaySource } from "../types/api";

export function FeedbackProvider({ children }: { children: ReactNode }) {
  const [feedbackMap, setFeedbackMap] = useState<Record<string, FeedbackType | null>>({});

  const submitFeedback = useCallback(
    (track: Track, type: FeedbackType, source: PlaySource) => {
      const previous = feedbackMap[track.spotify_id] ?? null;
      setFeedbackMap((prev) => ({ ...prev, [track.spotify_id]: type }));

      apiSubmitFeedback({
        track_id: track.spotify_id,
        feedback_type: type,
        source,
        playlist_id: null,
      }).catch(() => {
        setFeedbackMap((prev) => ({ ...prev, [track.spotify_id]: previous }));
      });
    },
    [feedbackMap],
  );

  return (
    <FeedbackContext.Provider value={{ feedbackMap, submitFeedback }}>
      {children}
    </FeedbackContext.Provider>
  );
}
