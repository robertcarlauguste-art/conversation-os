import { expect, it } from "vitest";
import { conversationTitle } from "./format";
it("preserves descriptive titles and gives old recordings a dated label", () => {
  expect(conversationTitle({ title: "Jordan — Home buying", created_at: "2026-09-18T23:42:00Z" })).toBe("Jordan — Home buying");
  expect(conversationTitle({ title: null, created_at: "2026-09-18T23:42:00Z" })).toMatch(/^Conversation — /);
  expect(conversationTitle({ title: "  ", created_at: "2026-09-18T23:42:00Z" })).not.toContain("Untitled");
});
