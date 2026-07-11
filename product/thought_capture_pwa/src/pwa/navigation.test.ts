import { describe, expect, it } from "vitest";
import {
  isServerOwnedSurfacePath,
  META_SURFACE_PATH_PATTERN,
  SELF_IMPROVEMENT_PATH_PATTERN,
} from "./navigation";

describe("server-owned surface routing", () => {
  it("marks meta routes as server-owned", () => {
    expect(META_SURFACE_PATH_PATTERN.test("/meta")).toBe(true);
    expect(META_SURFACE_PATH_PATTERN.test("/meta/")).toBe(true);
    expect(META_SURFACE_PATH_PATTERN.test("/meta/session")).toBe(true);
  });

  it("marks self-improvement routes as server-owned", () => {
    expect(SELF_IMPROVEMENT_PATH_PATTERN.test("/self-improvement")).toBe(true);
    expect(SELF_IMPROVEMENT_PATH_PATTERN.test("/self-improvement/console")).toBe(true);
  });

  it("only bypasses app-shell for server-owned surfaces", () => {
    expect(isServerOwnedSurfacePath("/capture")).toBe(false);
    expect(isServerOwnedSurfacePath("/meta")).toBe(true);
    expect(isServerOwnedSurfacePath("/self-improvement/console")).toBe(true);
    expect(isServerOwnedSurfacePath("/library")).toBe(false);
  });
});
