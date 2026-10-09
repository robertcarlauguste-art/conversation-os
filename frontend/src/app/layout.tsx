import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import "./globals.css";
import { Nav } from "@/components/Nav";
import { ToastProvider } from "@/components/Toast";
import { Providers } from "./providers";
import { PilotGuide, PilotHelpLink } from "@/components/PilotGuide";
import { PilotUsage } from "@/components/PilotUsage";

export const metadata: Metadata = {
  title: "ConversationOS",
  description: "AI-powered Relationship Intelligence Platform",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const authEnabled = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);
  const content = (
    <Providers authEnabled={authEnabled}>
      <ToastProvider>
        <Nav authEnabled={authEnabled} />
        <main className="mx-auto max-w-6xl px-6 py-10"><PilotHelpLink /><PilotUsage />{children}<PilotGuide /></main>
      </ToastProvider>
    </Providers>
  );

  return (
    <html lang="en">
      <body className="bg-paper font-sans text-ink antialiased">
        {authEnabled ? <ClerkProvider>{content}</ClerkProvider> : content}
      </body>
    </html>
  );
}
