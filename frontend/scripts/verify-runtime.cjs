/* Run inside the final image, e.g. docker run --rm -i --network none IMAGE node
 * with this file on stdin. Uses only Node built-ins and production packages. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

async function main() {
  const root = process.cwd();
  const lock = JSON.parse(fs.readFileSync(path.join(root, "package-lock.json"), "utf8"));
  const developmentPackages = Object.entries(lock.packages)
    .filter(([location, metadata]) => location && metadata.dev)
    .map(([location]) => location);
  const shipped = developmentPackages.filter(location => fs.existsSync(path.join(root, location)));
  assert.deepEqual(shipped, [], "Development-only packages must not exist in the runtime image");
  assert.notEqual(process.getuid(), 0, "Runtime must not run as root");
  assert.equal(fs.existsSync(path.join(root, "next.config.ts")), false);
  assert.equal(fs.existsSync(path.join(root, "src")), false);

  // A CommonJS default-export object is silently ignored by next start. Require
  // the actual generated entry point so this cannot bypass startup validation.
  const config = require(path.join(root, "next.config.js"));
  assert.equal(typeof config, "function");
  process.env.APP_ENV = "production";
  process.env.NEXT_PUBLIC_API_URL = "https://api.example.invalid";
  process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY =
    "pk_test_" + Buffer.from("security-test.clerk.accounts.dev$").toString("base64");
  delete process.env.CLERK_SECRET_KEY;
  delete process.env.PORT;
  assert.throws(() => config("phase-production-server"), /CLERK_SECRET_KEY/);
  process.env.CLERK_SECRET_KEY = "sk_test_local_fixture_only";
  assert.equal(config("phase-production-server").reactStrictMode, true);
  process.env.PORT = "0";
  assert.throws(() => config("phase-production-server"), /PORT/);
  delete process.env.PORT;
  process.env.NEXT_PUBLIC_API_URL = "http://localhost:8000";
  assert.throws(() => config("phase-production-server"), /NEXT_PUBLIC_API_URL/);

  const sharp = require("sharp");
  const png = await sharp({create: {width: 2, height: 2, channels: 3, background: "red"}}).png().toBuffer();
  assert.equal((await sharp(png).metadata()).width, 2);
  console.log(JSON.stringify({
    node: process.version, uid: process.getuid(),
    developmentPackageLocationsChecked: developmentPackages.length,
    developmentPackagesPresent: shipped,
    configurationExportAndValidation: "passed", sharpRoundtrip: "passed",
  }, null, 2));
}
main().catch(error => { console.error(error); process.exitCode = 1; });
