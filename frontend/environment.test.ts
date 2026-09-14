import { spawnSync } from "node:child_process";
import { describe, expect, it } from "vitest";
import { validateEnvironment } from "./environment";

const hosted = {
  APP_ENV: "staging",
  NEXT_PUBLIC_API_URL: "https://api.example.com",
  NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: `pk_test_${Buffer.from("clerk.example.com$").toString("base64")}`,
  CLERK_SECRET_KEY: "sk_test_example",
};

describe("startup configuration", () => {
  it("accepts local defaults and valid hosted configuration", () => {
    expect(() => validateEnvironment({})).not.toThrow();
    expect(() => validateEnvironment(hosted)).not.toThrow();
    expect(() => validateEnvironment({ ...hosted, APP_ENV: "production" })).not.toThrow();
  });
  it.each(["NEXT_PUBLIC_API_URL", "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", "CLERK_SECRET_KEY"])("requires %s", (name) => {
    expect(() => validateEnvironment({ ...hosted, [name]: undefined })).toThrow(name);
  });
  it("does not require a server secret in a build", () => {
    expect(() => validateEnvironment({ ...hosted, CLERK_SECRET_KEY: undefined }, true)).not.toThrow();
  });
  it("fails closed for production NODE_ENV unless local/test is explicit", () => {
    expect(() => validateEnvironment({ NODE_ENV: "production" })).toThrow("NEXT_PUBLIC_API_URL");
    expect(() => validateEnvironment({ NODE_ENV: "production", APP_ENV: "test" }, true)).not.toThrow();
  });
  it.each([
    ["NEXT_PUBLIC_API_URL", "https://user:secret@host.test"],
    ["NEXT_PUBLIC_API_URL", "http://localhost:8000"],
    ["NEXT_PUBLIC_API_URL", "https://api.example.com/path"],
    ["NEXT_PUBLIC_API_URL", "https://api.example.com:99999"],
    ["NEXT_PUBLIC_API_URL", ""],
    ["NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", "pk_test_bad"],
    ["CLERK_SECRET_KEY", "sk_live_other"],
    ["CLERK_SECRET_KEY", "sk_test_secret\n"],
    ["PORT", "0"], ["PORT", "65536"], ["PORT", "1.5"], ["APP_ENV", "prodution"],
  ])("rejects malformed %s without printing values", (name, value) => {
    try {
      validateEnvironment({ ...hosted, [name]: value });
      throw new Error("validation did not fail");
    } catch (error) {
      expect((error as Error).message).toContain(`${name}:`);
      expect((error as Error).stack).not.toContain("user:secret");
      expect((error as Error).stack).not.toContain("sk_test_secret");
    }
  });
});

it("next start rejects invalid configuration before serving without exposing secrets", () => {
  const result = spawnSync(process.execPath, ["node_modules/next/dist/bin/next", "start"], {
    env: { ...process.env, ...hosted, CLERK_SECRET_KEY: "sk_test_STARTUP_SENTINEL\n" },
    encoding: "utf8",
    timeout: 15000,
  });
  expect(result.error).toBeUndefined();
  expect(result.status).not.toBe(0);
  expect(result.stderr).toContain("CLERK_SECRET_KEY");
  expect(result.stdout + result.stderr).not.toContain("STARTUP_SENTINEL");
});
