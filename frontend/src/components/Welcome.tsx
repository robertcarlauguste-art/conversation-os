"use client";
import { SignInButton, SignUpButton } from "@clerk/nextjs";
import { WaveformMark } from "./WaveformMark";
import { PilotGuide } from "./PilotGuide";
import { LanguageNotice, LanguageSelector, useLanguage } from "./LanguageProvider";
function WelcomeExample() {
  const { t } = useLanguage();
  return <section id="welcome-example" aria-label={t("Fictional example")} className="min-w-0 scroll-mt-6 rounded-3xl bg-accent-soft p-5 sm:p-6">
    <p className="mb-4 text-xs font-semibold uppercase tracking-wide text-accent">{t("Fictional example")}</p>
    <div className="rounded-xl bg-accent p-5 text-white">
      <WaveformMark className="mb-3 h-6 w-14" />
      <p className="font-display text-xl leading-relaxed">{t("I spoke with Mari. I’ll send her a $1,250 estimate by Friday.")}</p>
    </div>
    <div className="mt-3 rounded-xl bg-surface p-5 text-sm">
      <h2 className="font-semibold">{t("Mari · Estimate follow-up")}</h2>
      <p className="mt-2 text-ink/80">{t("You will send Mari a $1,250 estimate by Friday.")}</p>
      <div className="my-4 border-t border-line pt-4"><p className="font-medium">{t("Send Mari the $1,250 estimate")}</p><p className="mt-1 text-accent">{t("Your task · Due Friday")}</p></div>
      <h3 className="font-semibold text-accent">{t("Follow-up draft to review")}</h3>
      <p className="mt-2 text-ink/80">{t("Hi Mari, I’ll send you the $1,250 estimate by Friday.")}</p>
    </div>
  </section>;
}
export function Welcome() {
  const { language, t } = useLanguage();
  const steps = [
    ["1. Record", "Choose a person or assign later. Record here or upload an audio file."],
    ["2. Review", "Check names, amounts, dates, and who will do each task. AI can make mistakes."],
    ["3. Follow up", "Prepare an email or text draft. Review and copy it when ready; nothing is sent automatically."],
  ];
  return <main lang={language} className="mx-auto max-w-6xl px-5 py-8 sm:px-8">
    <header className="flex flex-wrap items-center justify-between gap-4 min-[380px]:grid min-[380px]:grid-cols-[1fr_auto] sm:flex">
      <p className="flex items-center gap-3 font-display text-xl text-ink"><WaveformMark className="h-6 w-10 text-accent" />ConversationOS</p>
      <div className="order-3 w-full col-span-2 sm:order-none sm:w-auto"><LanguageSelector /></div>
      <SignInButton mode="modal"><button className="min-h-11 rounded-lg border border-line px-4 py-2 text-sm font-medium">{t("Sign in")}</button></SignInButton>
    </header>
    <div className="my-8 grid items-center gap-8 lg:grid-cols-2 lg:gap-12"><section aria-labelledby="welcome-title">
      <p className="text-xs font-semibold uppercase tracking-widest text-accent">{t("Family & friends pilot")}</p>
      <h1 id="welcome-title" className="mt-4 font-display text-4xl leading-tight sm:text-5xl">{t("Less time taking notes.")} <span className="text-accent">{t("More time moving forward.")}</span></h1>
      <p className="mt-5 text-base leading-relaxed text-ink/70">{t("Turn a voice note into a summary and tasks you can review, edit, and use to prepare a follow-up message.")}</p>
      <div className="flex flex-wrap items-center gap-x-6"><SignUpButton mode="modal" forceRedirectUrl="/conversations"><button className="mt-6 w-full rounded-lg bg-accent px-6 py-3 font-medium text-white sm:w-auto">{t("Try your first recording")}</button></SignUpButton><a href="#welcome-example" className="mt-6 min-h-11 py-3 text-sm font-semibold text-accent underline">{t("See an example")}</a></div>
      <p className="mt-3 text-sm text-ink/70">{t("Create an account, then record a short fictional note on your phone.")}</p>
    </section>
    <WelcomeExample /></div>
    <section className="mt-8 grid gap-4 border-y border-line py-6 sm:grid-cols-3">
      {steps.map(([title, description]) => <div key={title}><h2 className="font-semibold">{t(title)}</h2><p className="mt-2 text-sm text-ink/70">{t(description)}</p></div>)}
    </section>
    <p className="mt-5 text-sm text-ink/70">{t("Use fictional details only. Our service providers process audio and text. Do not share confidential information during this pilot.")}</p>
    <LanguageNotice />
    <details className="mt-4"><summary className="cursor-pointer text-sm text-accent underline">{t("Help and pilot limits (English)")}</summary><div lang="en"><PilotGuide /></div></details>
  </main>;
}
