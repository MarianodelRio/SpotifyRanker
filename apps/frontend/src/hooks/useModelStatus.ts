import { useState, useEffect, useCallback } from "react";
import { getModelStatus } from "../api/model";
import type { ModelStatus } from "../types/api";

export function useModelStatus() {
  const [status, setStatus] = useState<ModelStatus | null>(null);

  const refresh = useCallback(() => {
    getModelStatus().then(setStatus).catch(() => {});
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    const interval = status?.training_in_progress ? 3000 : 30000;
    const timer = setInterval(refresh, interval);
    return () => clearInterval(timer);
  }, [status?.training_in_progress, refresh]);

  return { status, refresh };
}
