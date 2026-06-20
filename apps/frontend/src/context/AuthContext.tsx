import type { ReactNode } from "react";
import { AuthContext } from "./auth-context";
import type { AuthState } from "../hooks/useAuth";

interface AuthProviderProps {
  value: AuthState;
  children: ReactNode;
}

export function AuthProvider({ value, children }: AuthProviderProps) {
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
