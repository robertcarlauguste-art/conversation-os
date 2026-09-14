type Environment = Record<string, string | undefined>;

/** Called by Next before building or starting the server. Never echo values. */
export function validateEnvironment(env: Environment, building = false): void {
  const errors: string[] = [];
  const fail = (name: string, message: string) => errors.push(`${name}: ${message}`);
  const appEnv = env.APP_ENV ?? (env.NODE_ENV === "production" ? "production" : "development");
  if (!["development", "test", "staging", "production"].includes(appEnv)) {
    fail("APP_ENV", "use development, test, staging or production");
  }
  const hosted = appEnv === "staging" || appEnv === "production";
  const key = env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
  for (const name of ["NEXT_PUBLIC_API_URL", "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", "CLERK_SECRET_KEY"]) {
    const value = env[name];
    if (value && /\s/.test(value)) fail(name, "remove whitespace and line breaks");
  }
  if (hosted && !env.NEXT_PUBLIC_API_URL) fail("NEXT_PUBLIC_API_URL", "required for hosted builds and startup");
  if (env.NEXT_PUBLIC_API_URL !== undefined) {
    try {
      const url = new URL(env.NEXT_PUBLIC_API_URL);
      if (!["http:", "https:"].includes(url.protocol) || !url.hostname || url.username || url.password ||
          url.search || url.hash || url.hostname.includes("*") || (url.pathname !== "/" && url.pathname !== "") ||
          /\s|\\/.test(env.NEXT_PUBLIC_API_URL) || url.port === "0") throw new Error();
      if (hosted && (url.protocol !== "https:" || (["localhost", "[::1]"].includes(url.hostname) || url.hostname.endsWith(".localhost") || /^127\./.test(url.hostname)))) throw new Error();
    } catch {
      fail("NEXT_PUBLIC_API_URL", hosted ? "use a public HTTPS origin" : "use an HTTP(S) origin with no credentials, path or query");
    }
  }
  if (hosted && !key) fail("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", "required for hosted builds and startup");
  if (key) {
    const match = /^pk_(test|live)_([A-Za-z0-9+/]+={0,2})$/.exec(key);
    const decoded = match ? Buffer.from(match[2], "base64").toString("utf8") : "";
    if (!/^[a-zA-Z0-9.-]+\$$/.test(decoded)) fail("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", "provide a Clerk publishable key");
    if (!building && !env.CLERK_SECRET_KEY) fail("CLERK_SECRET_KEY", "required at runtime when Clerk is enabled");
    if (env.CLERK_SECRET_KEY && match && !env.CLERK_SECRET_KEY.startsWith(`sk_${match[1]}_`)) {
      fail("CLERK_SECRET_KEY", "must match the publishable key's test/live environment");
    }
  }
  if (env.CLERK_SECRET_KEY && !/^sk_(test|live)_[A-Za-z0-9_-]+$/.test(env.CLERK_SECRET_KEY)) {
    fail("CLERK_SECRET_KEY", "provide a Clerk secret key");
  }
  if (env.PORT !== undefined && (!/^[0-9]+$/.test(env.PORT) || Number(env.PORT) < 1 || Number(env.PORT) > 65535)) {
    fail("PORT", "use an integer from 1 to 65535");
  }
  if (errors.length) throw new Error(`Invalid configuration:\n- ${errors.join("\n- ")}`);
}
