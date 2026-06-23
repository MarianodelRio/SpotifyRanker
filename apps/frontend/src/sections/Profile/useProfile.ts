import { useState, useEffect, useCallback } from "react";
import { getProfile, getDeclared } from "../../api/profile";
import type { ProfileResponse, DeclaredResponse } from "../../types/api";

interface ProfileState {
  profile: ProfileResponse | null;
  declared: DeclaredResponse | null;
  isLoading: boolean;
  error: string | null;
}

export function useProfile() {
  const [state, setState] = useState<ProfileState>({
    profile: null,
    declared: null,
    isLoading: true,
    error: null,
  });

  const refresh = useCallback(() => {
    setState((s) => ({ ...s, isLoading: true, error: null }));
    Promise.all([getProfile(), getDeclared()])
      .then(([profile, declared]) => {
        setState({ profile, declared, isLoading: false, error: null });
      })
      .catch(() => {
        setState((s) => ({
          ...s,
          isLoading: false,
          error: "Failed to load profile data.",
        }));
      });
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { ...state, refresh };
}
