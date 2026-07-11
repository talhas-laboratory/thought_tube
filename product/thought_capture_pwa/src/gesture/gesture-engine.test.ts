import { describe, expect, it } from "vitest";
import {
  isScrollRegionTarget,
  isWithinEdgeGuard,
  lensBaseOffsetPercent,
  reducePointerDown,
  reducePointerMove,
  resolveLensOnRelease,
  resistedDragX,
} from "./gesture-engine";
import { EDGE_GUARD_PX, SWIPE_COMMIT_PX } from "./gesture-types";

describe("scroll region", () => {
  it("detects touches inside the thread scroll container", () => {
    const stream = document.createElement("div");
    stream.setAttribute("data-scroll-region", "");
    const line = document.createElement("p");
    stream.appendChild(line);
    document.body.appendChild(stream);
    expect(isScrollRegionTarget(line)).toBe(true);
    document.body.removeChild(stream);
  });
});

describe("edge guard", () => {
  it("rejects pointerdown in left margin", () => {
    expect(isWithinEdgeGuard(EDGE_GUARD_PX - 1, 400)).toBe(false);
    expect(isWithinEdgeGuard(EDGE_GUARD_PX, 400)).toBe(true);
  });

  it("rejects pointerdown in right margin", () => {
    expect(isWithinEdgeGuard(400 - EDGE_GUARD_PX + 1, 400)).toBe(false);
  });
});

describe("direction lock", () => {
  it("locks vertical when dy dominates", () => {
    const down = reducePointerDown(
      { kind: "idle" },
      100,
      100,
      1,
      400,
      false,
    );
    expect(down.kind).toBe("down");
    const moved = reducePointerMove(down, 102, 130);
    expect(moved.state.kind).toBe("lock-v");
    expect(moved.dragX).toBe(0);
  });

  it("locks horizontal when dx dominates", () => {
    const down = reducePointerDown(
      { kind: "idle" },
      100,
      100,
      1,
      400,
      false,
    );
    const moved = reducePointerMove(down, 130, 102);
    expect(moved.state.kind).toBe("lock-h");
    expect(moved.dragX).toBe(30);
  });
});

describe("lens commit", () => {
  it("commits to thread from center on left swipe", () => {
    expect(resolveLensOnRelease("center", -(SWIPE_COMMIT_PX + 1))).toBe("thread");
  });

  it("commits to facet from center on right swipe", () => {
    expect(resolveLensOnRelease("center", SWIPE_COMMIT_PX + 1)).toBe("facet");
  });

  it("returns to center from thread on right swipe", () => {
    expect(resolveLensOnRelease("thread", SWIPE_COMMIT_PX + 1)).toBe("center");
  });

  it("resists drag at thread edge", () => {
    expect(resistedDragX(40, "thread")).toBe(10);
  });
});

describe("lens offsets", () => {
  it("centers main pane at -100%", () => {
    expect(lensBaseOffsetPercent("center")).toBe(-100);
  });
});
