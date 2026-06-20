import { useState, useEffect, useCallback } from "react";
import { getAuthStatus, getToken, logout as apiLogout } from "../api/auth";
import type { AuthStatus } from "../types/api";

export interface AuthState {
  isAuthenticated: boolean;
  displayName: string | null;
  token: string | null;
  isLoading: boolean;
  logout: () => Promise<void>;
  recheck: () => Promise<void>;
}

export function useAuth(): AuthState {
  const [status, setStatus] = useState<AuthStatus>({ is_authenticated: false, display_name: null });
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const recheck = useCallback(async () => {
    setIsLoading(true);
    try {
      const s = await getAuthStatus();
      setStatus(s);
      if (s.is_authenticated) {
        const t = await getToken();
        setToken(t.access_token);
      } else {
        setToken(null);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    recheck();
  }, [recheck]);

  const logout = useCallback(async () => {
    await apiLogout();
    setStatus({ is_authenticated: false, display_name: null });
    setToken(null);
  }, []);

  return {
    isAuthenticated: status.is_authenticated,
    displayName: status.display_name,
    token,
    isLoading,
    logout,
    recheck,
  };
}
