import type { NextConfig } from "next";
import { PHASE_PRODUCTION_BUILD } from "next/constants";
import { validateEnvironment } from "./environment";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  turbopack: {
    root: process.cwd(),
  },
};

export default function config(phase: string): NextConfig {
  validateEnvironment(process.env, phase === PHASE_PRODUCTION_BUILD);
  return nextConfig;
}
