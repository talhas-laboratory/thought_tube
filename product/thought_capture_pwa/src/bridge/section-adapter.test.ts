import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { buildCaptureSyncPayload, buildProvenance } from "./transport";
import { MOBILE_CAPTURE_SURFACE_PROFILE } from "./types";
import { getSurfaceProfile, isSectionSyncEnabled } from "./config";

describe("bridge section types", () => {
  it("defines mobile_capture surface profile with no steering authority", () => {
    expect(MOBILE_CAPTURE_SURFACE_PROFILE.surface_id).toBe("mobile_capture");
    expect(MOBILE_CAPTURE_SURFACE_PROFILE.steering_authority).toBe("none");
    expect(MOBILE_CAPTURE_SURFACE_PROFILE.element_key).toBe("frontend");
    expect(MOBILE_CAPTURE_SURFACE_PROFILE.bridge_reads).toContain("compose_insertion");
  });
});

describe("buildProvenance", () => {
  beforeEach(() => {
    vi.stubGlobal("matchMedia", (query: string) => ({
      matches: query === "(display-mode: browser)",
      media: query,
    }));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("includes required provenance fields", () => {
    const provenance = buildProvenance("t-abc123", "sess-1", 1_700_000_000_000);
    expect(provenance).toEqual({
      source: "thought_capture_pwa",
      surface_id: "mobile_capture",
      display_mode: "browser",
      element_key: "frontend",
      holodeck_id: "sol-frontend",
      session_id: "sess-1",
      local_deposit_id: "t-abc123",
      client_timestamp: 1_700_000_000_000,
    });
  });

  it("wraps content with provenance in sync payload", () => {
    const payload = buildCaptureSyncPayload(
      "quiet thought",
      "t-1",
      null,
      100,
    );
    expect(payload.content).toBe("quiet thought");
    expect(payload.provenance.local_deposit_id).toBe("t-1");
    expect(payload.provenance.session_id).toBeNull();
  });
});

describe("section config", () => {
  it("exposes surface profile snapshot", () => {
    expect(getSurfaceProfile().persistence).toBe("indexeddb_first");
  });

  it("defaults sync to enabled", () => {
    expect(isSectionSyncEnabled()).toBe(true);
  });
});
