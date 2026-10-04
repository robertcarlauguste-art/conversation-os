"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import { useState } from "react";
import { AuthTokenBridge } from "@/components/AuthTokenBridge";
import { LanguageProvider, useLanguage } from "@/components/LanguageProvider";
import { Welcome } from "@/components/Welcome";

export function Providers({
  children,
  authEnabled = false,
}: {
  children: React.ReactNode;
  authEnabled?: boolean;
}) {
  return <LanguageProvider>{authEnabled ? (
    <AuthenticatedProviders>{children}</AuthenticatedProviders>
  ) : (
    <ScopedProviders>{children}</ScopedProviders>
  )}</LanguageProvider>;
}

function AuthenticatedProviders({ children }: { children: React.ReactNode }) {
  const { t } = useLanguage();
  const { isLoaded, userId, sessionId } = useAuth();
  if (!isLoaded) return <p role="status" className="p-8">{t("Loading your account…")}</p>;
  if (!userId) return <Welcome />;
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
