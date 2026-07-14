import { describe, expect, it } from "vitest";
import { createInitialScrollState } from "./scroll-types";
import {
  isWithinLiveEdge,
  measureDistanceFromLiveEdge,
  reduceScrollState,
  shouldShowOffscreenIndicator,
} from "./scroll-engine";
import { shouldDetachOnIntent } from "./scroll-intent-bus";

describe("scroll state machine", () => {
  it("detaches on intent", () => {
    const next = reduceScrollState(createInitialScrollState(), {
      type: "intent_detach",
    });
    expect(next.follow_state).toBe("detached");
  });

  it("resumes following at live edge", () => {
    const detached = reduceScrollState(createInitialScrollState(), {
      type: "intent_detach",
    });
    const next = reduceScrollState(detached, { type: "at_live_edge" });
    expect(next.follow_state).toBe("following");
  });

  it("jump latest forces following", () => {
    const detached = reduceScrollState(createInitialScrollState(), {
      type: "intent_detach",
    });
    const next = reduceScrollState(detached, { type: "jump_latest" });
    expect(next.follow_state).toBe("following");
    expect(next.anchor_element_id).toBeNull();
  });
});

describe("intent bus", () => {
  it("detaches on reader intent signals", () => {
    expect(shouldDetachOnIntent("scroll")).toBe(true);
    expect(shouldDetachOnIntent("type")).toBe(true);
  });
});

describe("live edge measurement", () => {
  it("measures distance from live edge", () => {
    const container = document.createElement("div");
    Object.defineProperty(container, "scrollHeight", { value: 1000 });
    Object.defineProperty(container, "clientHeight", { value: 400 });
    container.scrollTop = 500;
    expect(measureDistanceFromLiveEdge(container)).toBe(100);
    expect(isWithinLiveEdge(container, 48)).toBe(false);
    container.scrollTop = 560;
    expect(isWithinLiveEdge(container, 48)).toBe(true);
  });
});

describe("offscreen indicator", () => {
  it("shows when detached and away from live edge", () => {
    expect(shouldShowOffscreenIndicator("detached", 120, 48)).toBe(true);
    expect(shouldShowOffscreenIndicator("following", 120, 48)).toBe(false);
    expect(shouldShowOffscreenIndicator("detached", 12, 48)).toBe(false);
  });
});
