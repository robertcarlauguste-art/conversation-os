"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { WaveformMark } from "./WaveformMark";

const LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/conversations", label: "Conversations" },
];

export function Nav() {
  const pathname = usePathname();

  return (
    <header className="border-b border-line bg-surface">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2.5 text-ink">
          <WaveformMark className="h-5 w-auto text-accent" />
          <span className="font-display text-lg tracking-tight">ConversationOS</span>
        </Link>
        <nav className="flex items-center gap-1">
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
        </nav>
      </div>
    </header>
  );
}
