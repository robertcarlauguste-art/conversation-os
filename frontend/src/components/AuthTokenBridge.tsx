"use client";

import { useAuth } from "@clerk/nextjs";
import { useEffect, useState } from "react";
import { setAccessTokenProvider } from "@/lib/auth-token";

export function AuthTokenBridge({ children }: { children: React.ReactNode }) {
  const { getToken } = useAuth();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setAccessTokenProvider(() => getToken());
    setReady(true);
    return () => setAccessTokenProvider(null);
  }, [getToken]);

  return ready ? children : null;
}
