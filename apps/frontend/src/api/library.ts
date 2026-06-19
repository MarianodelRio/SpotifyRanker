import { apiFetch } from "./client";
import type { LibraryPage, ImportProgress } from "../types/api";

export function getLibrary(page = 1, perPage = 50): Promise<LibraryPage> {
  return apiFetch<LibraryPage>(`/library?page=${page}&per_page=${perPage}`);
}

export async function startImport(): Promise<void> {
  await apiFetch<unknown>("/import/start", { method: "POST" });
}

export function getImportStatus(): Promise<ImportProgress> {
  return apiFetch<ImportProgress>("/import/status");
}
