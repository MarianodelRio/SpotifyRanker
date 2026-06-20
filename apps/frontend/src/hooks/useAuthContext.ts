import { useContext } from "react";
import { AuthContext } from "../context/auth-context";
import type { AuthState } from "./useAuth";

export function useAuthContext(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuthContext must be used within AuthProvider");
  return ctx;
}
