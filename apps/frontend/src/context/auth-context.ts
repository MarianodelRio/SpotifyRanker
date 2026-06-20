import { createContext } from "react";
import type { AuthState } from "../hooks/useAuth";

export const AuthContext = createContext<AuthState | null>(null);
