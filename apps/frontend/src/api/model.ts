import { apiFetch } from "./client";
import type { ModelStatus } from "../types/api";

export async function trainModel(): Promise<void> {
  await apiFetch<unknown>("/model/train", { method: "POST" });
}

export function getModelStatus(): Promise<ModelStatus> {
  return apiFetch<ModelStatus>("/model/status");
}
