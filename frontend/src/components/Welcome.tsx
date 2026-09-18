"use client";

import { SignInButton, SignUpButton } from "@clerk/nextjs";

export function Welcome() {
  return <main className="mx-auto max-w-2xl px-6 py-16">
    <p className="font-display text-xl text-accent">ConversationOS</p>
    <h1 className="mt-8 font-display text-4xl">Turn a conversation into clear next steps.</h1>
    <p className="mt-5">Record a voice note or upload audio, then review the transcript, summary, and follow-up actions.</p>
    <div className="mt-8 flex flex-wrap gap-4">
      <SignUpButton mode="modal"><button className="rounded-lg bg-accent px-5 py-3 text-white">Create an account</button></SignUpButton>
      <SignInButton mode="modal"><button className="rounded-lg border border-line px-5 py-3">Sign in</button></SignInButton>
    </div>
    <p className="mt-8 text-sm text-ink/70">Family and friends pilot: use fictional information. AI can make mistakes; review the results before acting on them. Uploads are limited to 100 MB per file. Unlimited storage is not promised.</p>
    <p className="mt-4 text-sm text-ink/70">Your account keeps your conversations separate from other users. Audio is stored and processed by our service providers to generate results. This pilot is not intended for confidential information.</p>
  </main>;
}
