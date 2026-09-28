"use client";

import { SignInButton, SignUpButton } from "@clerk/nextjs";
import { PilotGuide } from "./PilotGuide";

export function Welcome() {
  return (
    <main className="mx-auto max-w-5xl px-5 py-8 sm:px-8 sm:py-12">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <p className="font-display text-xl text-accent">ConversationOS</p>
        <SignInButton mode="modal">
          <button className="rounded-lg border border-line px-4 py-2 text-sm font-medium">Sign in</button>
        </SignInButton>
      </header>

      <div className="mt-10 grid items-center gap-8 lg:grid-cols-2 lg:gap-12">
        <section aria-labelledby="welcome-title">
          <p className="text-xs font-semibold uppercase tracking-widest text-accent">Family & friends pilot</p>
          <h1 id="welcome-title" className="mt-4 font-display text-4xl leading-tight text-ink sm:text-5xl">
            Remember the conversation. Know what to do next.
          </h1>
          <p className="mt-5 max-w-lg text-base leading-relaxed text-ink/70">
            Turn voice notes into clear summaries, organized client history, and follow-up tasks you can review and edit.
          </p>
          <SignUpButton mode="modal" forceRedirectUrl="/conversations">
            <button className="mt-6 w-full rounded-lg bg-accent px-6 py-3 font-medium text-white sm:w-auto">Try your first recording</button>
          </SignUpButton>
          <p className="mt-3 text-sm text-ink/60">Create an account, choose a client, then record right on your phone.</p>
          <a href="#pilot-help" className="mt-4 inline-block text-sm text-accent underline underline-offset-4">Privacy, pilot limits & common questions</a>
        </section>

        <section aria-labelledby="example-title" className="rounded-2xl border border-line bg-surface p-5 shadow-sm sm:p-6">
          <p className="text-xs font-semibold uppercase tracking-widest text-accent">Fictional example · not a live result</p>
          <h2 id="example-title" className="mt-3 font-display text-2xl">A short note. A useful next step.</h2>
          <blockquote className="mt-4 rounded-xl bg-paper p-4 text-sm leading-relaxed text-ink/70">
            “Jordan wants a three-bedroom home with a fenced yard, up to $350,000. I’ll send three listings by Friday. Jordan will call their lender.”
          </blockquote>
          <div className="mt-5 border-t border-line pt-4">
            <h3 className="text-sm font-semibold">Your summary</h3>
            <p className="mt-2 text-sm leading-relaxed text-ink/70">Jordan is looking for three bedrooms and a fenced yard, with a $350,000 budget.</p>
            <h3 className="mt-4 text-sm font-semibold">Tasks to review</h3>
            <ul className="mt-2 space-y-2 text-sm text-ink/70">
              <li className="rounded-lg bg-paper p-3">Send three listings <span className="block text-xs">You · By Friday</span></li>
              <li className="rounded-lg bg-paper p-3">Call the lender <span className="block text-xs">Jordan</span></li>
            </ul>
          </div>
        </section>
      </div>

      <section aria-label="How it works" className="mt-8 grid gap-4 border-y border-line py-6 sm:grid-cols-3">
        <div><h2 className="font-semibold">1. Choose who it’s about</h2><p className="mt-1 text-sm text-ink/70">Select a client, add someone new, or assign later.</p></div>
        <div><h2 className="font-semibold">2. Record or upload</h2><p className="mt-1 text-sm text-ink/70">Start with a short voice note using fictional details.</p></div>
        <div><h2 className="font-semibold">3. Review and follow up</h2><p className="mt-1 text-sm text-ink/70">Check your notes, correct tasks, and find them again by client.</p></div>
      </section>
      <p className="mt-5 text-sm leading-relaxed text-ink/70">AI can make mistakes: review your notes before acting. Use fictional information during this pilot. Audio and text are handled by our service providers; this pilot is not intended for confidential information.</p>
      <PilotGuide />
    </main>
  );
}
