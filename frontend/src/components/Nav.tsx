"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { SignInButton, SignedIn, SignedOut, UserButton } from "@clerk/nextjs";
import { WaveformMark } from "./WaveformMark";

const LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/conversations", label: "Conversations" },
  { href: "/clients", label: "Clients" },
];

export function Nav({ authEnabled = false }: { authEnabled?: boolean }) {
  const pathname = usePathname();

  return (
    <header className="border-b border-line bg-surface">
      <div className="mx-auto flex max-w-6xl flex-col items-start gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <Link href="/" className="flex items-center gap-2.5 text-ink">
          <WaveformMark className="h-5 w-auto text-accent" />
          <span className="font-display text-lg tracking-tight">ConversationOS</span>
        </Link>
        <nav className="flex w-full items-center justify-between gap-1 sm:w-auto sm:justify-start">
          {LINKS.map((link) => {
            const isActive =
              link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-accent-soft text-accent"
                    : "text-ink/60 hover:bg-paper hover:text-ink"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
          {authEnabled ? (
            <>
              <SignedOut>
                <SignInButton mode="modal">
                  <button className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white">
                    Sign in
                  </button>
                </SignInButton>
              </SignedOut>
              <SignedIn>
                <UserButton />
              </SignedIn>
            </>
          ) : null}
        </nav>
      </div>
    </header>
  );
}
