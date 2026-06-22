import { useState, useEffect, useRef, useCallback } from "react";
import { getImportStatus, startImport } from "../../api/library";
import type { ImportStatus, ImportProgress } from "../../types/api";

interface UseImportPollerResult {
  status: ImportStatus | null;
  tracksImported: number;
  artistsImported: number;
  triggerImport: () => Promise<void>;
  justCompleted: boolean;
}

export function useImportPoller(): UseImportPollerResult {
  const [progress, setProgress] = useState<ImportProgress | null>(null);
  const [justCompleted, setJustCompleted] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const prevStatusRef = useRef<ImportStatus | null>(null);

  const poll = useCallback(async () => {
    try {
      const data = await getImportStatus();
      setProgress(data);

      if (prevStatusRef.current === "running" && data.status !== "running") {
        setJustCompleted(true);
        setTimeout(() => setJustCompleted(false), 100);
      }
      prevStatusRef.current = data.status;

      if (data.status !== "running" && intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    } catch {
      // silently ignore polling errors
    }
  }, []);

  const startPolling = useCallback(() => {
    if (intervalRef.current) return;
    intervalRef.current = setInterval(poll, 3000);
  }, [poll]);

  useEffect(() => {
    poll();
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [poll]);

  useEffect(() => {
    if (progress?.status === "running") {
      startPolling();
    }
  }, [progress?.status, startPolling]);

  const triggerImport = useCallback(async () => {
    await startImport();
    prevStatusRef.current = "running";
    setProgress((prev) =>
      prev ? { ...prev, status: "running" } : { status: "running", tracks_imported: 0, artists_imported: 0 }
    );
    startPolling();
    poll();
  }, [poll, startPolling]);

  return {
    status: progress?.status ?? null,
    tracksImported: progress?.tracks_imported ?? 0,
    artistsImported: progress?.artists_imported ?? 0,
    triggerImport,
    justCompleted,
  };
}
