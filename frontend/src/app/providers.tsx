"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { AuthTokenBridge } from "@/components/AuthTokenBridge";

export function Providers({
  children,
  authEnabled = false,
}: {
  children: React.ReactNode;
  authEnabled?: boolean;
}) {
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
      {authEnabled ? <AuthTokenBridge /> : null}
      {children}
    </QueryClientProvider>
  );
}
