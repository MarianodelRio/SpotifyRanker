import { useContext } from "react";
import { FeedbackContext } from "../context/feedback-context";
import type { FeedbackContextValue } from "../context/feedback-context";

export function useFeedback(): FeedbackContextValue {
  const ctx = useContext(FeedbackContext);
  if (!ctx) throw new Error("useFeedback must be used inside FeedbackProvider");
  return ctx;
}
