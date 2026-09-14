"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import { useState } from "react";
import { AuthTokenBridge } from "@/components/AuthTokenBridge";

export function Providers({
  children,
  authEnabled = false,
}: {
  children: React.ReactNode;
  authEnabled?: boolean;
}) {
  return authEnabled ? (
    <AuthenticatedProviders>{children}</AuthenticatedProviders>
  ) : (
    <ScopedProviders>{children}</ScopedProviders>
  );
}

function AuthenticatedProviders({ children }: { children: React.ReactNode }) {
  const { isLoaded, userId, sessionId } = useAuth();
  if (!isLoaded) return null;
  // Remount the cache and its consumers before rendering a different identity.
  // In-flight responses from the previous session remain in its detached cache.
  return (
    <ScopedProviders key={JSON.stringify([userId, sessionId])}>
      <AuthTokenBridge>{children}</AuthTokenBridge>
    </ScopedProviders>
  );
}

function ScopedProviders({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 10_000,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}
