"use client";

import { useAuth } from "@clerk/nextjs";
import { useEffect } from "react";
import { setAccessTokenProvider } from "@/lib/auth-token";

export function AuthTokenBridge() {
  const { getToken } = useAuth();

  useEffect(() => {
    setAccessTokenProvider(() => getToken());
    return () => setAccessTokenProvider(null);
  }, [getToken]);

  return null;
}
