import { describe, expect, it } from "vitest";
import { sanitizeReturnPath } from "./return-path";

describe("sanitizeReturnPath", () => {
  it("keeps a genuine relative path", () => {
    expect(sanitizeReturnPath("/w/123/settings?tab=general")).toBe("/w/123/settings?tab=general");
  });

  it.each([
    ["missing value", undefined],
    ["empty string", ""],
    ["protocol-relative URL", "//evil.example.com"],
    ["backslash-prefixed protocol-relative URL", "/\\evil.example.com"],
    ["absolute URL with an embedded scheme", "https://evil.example.com/login"],
    ["scheme hidden mid-path", "/redirect?to=https://evil.example.com"],
    ["not a path at all", "javascript:alert(1)"],
  ])("falls back to / for %s", (_label, candidate) => {
    expect(sanitizeReturnPath(candidate)).toBe("/");
  });
});
