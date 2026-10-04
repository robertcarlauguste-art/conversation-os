"use client";
import { SignInButton, SignUpButton } from "@clerk/nextjs";
import { PilotGuide } from "./PilotGuide";
import { LanguageNotice, LanguageSelector, useLanguage } from "./LanguageProvider";
export function Welcome() {
  const { language, t } = useLanguage();
  const steps = [
    ["1. Record", "Choose a person or assign later. Record here or upload an audio file."],
    ["2. Review", "Check names, amounts, dates, and who will do each task. AI can make mistakes."],
    ["3. Follow up", "Prepare an email or text draft. Review and copy it when ready; nothing is sent automatically."],
  ];
  return <main lang={language} className="mx-auto max-w-4xl px-5 py-8 sm:px-8">
    <header className="flex flex-wrap items-center justify-between gap-4">
      <p className="font-display text-xl text-accent">ConversationOS</p>
      <LanguageSelector />
      <SignInButton mode="modal"><button className="rounded-lg border border-line px-4 py-2 text-sm font-medium">{t("Sign in")}</button></SignInButton>
    </header>
    <section aria-labelledby="welcome-title" className="mt-10 max-w-2xl">
      <p className="text-xs font-semibold uppercase tracking-widest text-accent">{t("Family & friends pilot")}</p>
      <h1 id="welcome-title" className="mt-4 font-display text-4xl leading-tight sm:text-5xl">{t("Remember the conversation. Know what to do next.")}</h1>
      <p className="mt-5 text-base leading-relaxed text-ink/70">{t("Turn a voice note into a summary and tasks you can review, edit, and use to prepare a follow-up message.")}</p>
      <SignUpButton mode="modal" forceRedirectUrl="/conversations"><button className="mt-6 w-full rounded-lg bg-accent px-6 py-3 font-medium text-white sm:w-auto">{t("Try your first recording")}</button></SignUpButton>
      <p className="mt-3 text-sm text-ink/70">{t("Create an account, then record a short fictional note on your phone.")}</p>
    </section>
    <section className="mt-8 grid gap-4 border-y border-line py-6 sm:grid-cols-3">
      {steps.map(([title, description]) => <div key={title}><h2 className="font-semibold">{t(title)}</h2><p className="mt-2 text-sm text-ink/70">{t(description)}</p></div>)}
    </section>
    <p className="mt-5 text-sm text-ink/70">{t("Use fictional details only. Our service providers process audio and text. Do not share confidential information during this pilot.")}</p>
    <LanguageNotice />
    <details className="mt-4"><summary className="cursor-pointer text-sm text-accent underline">{t("Help and pilot limits (English)")}</summary><div lang="en"><PilotGuide /></div></details>
  </main>;
}
