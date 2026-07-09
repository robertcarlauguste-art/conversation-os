import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "@/components/Nav";
import { ToastProvider } from "@/components/Toast";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "ConversationOS",
  description: "AI-powered Relationship Intelligence Platform",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="bg-paper font-sans text-ink antialiased">
        <Providers>
          <ToastProvider>
            <Nav />
            <main className="mx-auto max-w-6xl px-6 py-10">{children}</main>
          </ToastProvider>
        </Providers>
      </body>
    </html>
  );
}
