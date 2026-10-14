// Local policy simulation, not a substitute for GitHub-side approval enforcement.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { createRequire } = require("node:module");
const root = path.resolve(__dirname, "../..");
const yaml = createRequire(path.join(root, "frontend/package.json"))("js-yaml");
const repository = "robertcarlauguste-art/conversation-os";
const fixtures = [
  ["trusted push", "push", repository, "OWNER", true],
  ["trusted owner PR", "pull_request", repository, "OWNER", true],
  ["trusted collaborator PR", "pull_request", repository, "COLLABORATOR", true],
  ["first-time external", "pull_request", "outside/fork", "FIRST_TIME_CONTRIBUTOR", false],
  ["returning external", "pull_request", "outside/fork", "CONTRIBUTOR", false],
  ["owner fork", "pull_request", "outside/fork", "OWNER", false],
  ["unrecognized association", "pull_request", repository, "NONE", false],
  ["privileged event", "pull_request_target", repository, "OWNER", false],
  ["manual event", "workflow_dispatch", repository, "OWNER", false],
];
let checks = 0;
for (const name of ["frontend", "backend", "backup"]) {
  const text = fs.readFileSync(path.join(root, `.github/workflows/${name}-ci.yml`), "utf8");
  const workflow = yaml.load(text);
  assert.deepEqual(Object.keys(workflow.on).sort(), ["pull_request", "push"]);
  assert.deepEqual(workflow.permissions, { contents: "read" });
  assert(!/secrets\.|secrets\[|id-token:|workflow_run:|pull_request_target:/.test(text));
  const job = workflow.jobs[name];
  assert.equal(job["runs-on"], "ubuntu-latest");
  assert.equal(job["timeout-minutes"], 20);
  assert.equal(job.environment, undefined);
  assert.equal(job.permissions, undefined);
  const checkout = job.steps.find(step => step.uses === "actions/checkout@v4");
  assert.equal(checkout.with["persist-credentials"], false);
  // Evaluate the actual restricted expression, not a duplicate of the policy.
  assert(/^[a-zA-Z0-9_ ./'()&|=\n-]+$/.test(job.if));
  const allowed = new Function("github", `return Boolean(${job.if});`);
  for (const [label, event_name, full_name, author_association, expected] of fixtures) {
    assert.equal(allowed({repository, event_name, event: {pull_request: {
      head: {repo: {full_name}}, author_association,
    }}}), expected, `${name}: ${label}`);
    checks++;
  }
  assert.equal(allowed({repository: "outside/fork", event_name: "push", event: {}}), false);
  if (name === "frontend") {
    assert.equal(job.steps.find(step => step.name === "Install dependencies").run, "npm ci");
    assert.equal(job.steps.find(step => step.uses === "actions/setup-node@v4").with["cache-dependency-path"], "frontend/package-lock.json");
    const runtime = job.steps.find(step => step.name === "Verify trusted release runtime dependencies");
    assert.equal(runtime.if, "github.event_name == 'push' && github.ref == 'refs/heads/main'");
    assert(runtime.run.includes("scripts/verify-runtime.cjs"));
    assert(runtime.run.includes("npm audit --omit=dev"));
  }
}
console.log(`CI trust policy passed: ${checks} event scenarios plus permissions, timeout, checkout and release checks.`);
