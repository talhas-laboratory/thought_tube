import {
  EDGE_GUARD_PX,
  SWIPE_COMMIT_PX,
  SWIPE_LOCK_PX,
  type GestureLens,
  type GesturePointerState,
} from "./gesture-types";

export function isWithinEdgeGuard(clientX: number, viewportWidth: number): boolean {
  return (
    clientX >= EDGE_GUARD_PX && clientX <= viewportWidth - EDGE_GUARD_PX
  );
}

export function isInteractiveGestureTarget(target: EventTarget | null): boolean {
  if (!(target instanceof Element)) {
    return false;
  }
  return Boolean(
    target.closest("button, textarea, input, select, a, [data-no-swipe]"),
  );
}

export function isScrollRegionTarget(target: EventTarget | null): boolean {
  if (!(target instanceof Element)) {
    return false;
  }
  return Boolean(target.closest("[data-scroll-region]"));
}

export function reducePointerDown(
  state: GesturePointerState,
  clientX: number,
  clientY: number,
  pointerId: number,
  viewportWidth: number,
  interactive: boolean,
): GesturePointerState {
  if (interactive || !isWithinEdgeGuard(clientX, viewportWidth)) {
    return state;
  }
  return { kind: "down", pointerId, startX: clientX, startY: clientY };
}

export function reducePointerMove(
  state: GesturePointerState,
  clientX: number,
  clientY: number,
): { state: GesturePointerState; dragX: number } {
  if (state.kind === "idle" || state.kind === "lock-v") {
    return { state, dragX: 0 };
  }

  if (state.kind === "down") {
    const dx = clientX - state.startX;
    const dy = clientY - state.startY;
    if (Math.abs(dx) < SWIPE_LOCK_PX && Math.abs(dy) < SWIPE_LOCK_PX) {
      return { state, dragX: 0 };
    }
    if (Math.abs(dy) > Math.abs(dx)) {
      return { state: { kind: "lock-v" }, dragX: 0 };
    }
    return {
      state: {
        kind: "lock-h",
        pointerId: state.pointerId,
        startX: state.startX,
        startY: state.startY,
      },
      dragX: dx,
    };
  }

  if (state.kind === "lock-h") {
    return { state, dragX: clientX - state.startX };
  }

  return { state, dragX: 0 };
}

export function resistedDragX(
  dragX: number,
  lens: GestureLens,
): number {
  const atThreadEnd = lens === "thread" && dragX > 0;
  const atFacetEnd = lens === "facet" && dragX < 0;
  if (atThreadEnd || atFacetEnd) {
    return dragX * 0.25;
  }
  return dragX;
}

export function resolveLensOnRelease(
  lens: GestureLens,
  dragX: number,
): GestureLens {
  if (lens === "center") {
    if (dragX <= -SWIPE_COMMIT_PX) {
      return "thread";
    }
    if (dragX >= SWIPE_COMMIT_PX) {
      return "facet";
    }
    return "center";
  }

  if (lens === "thread" && dragX >= SWIPE_COMMIT_PX) {
    return "center";
  }
  if (lens === "facet" && dragX <= -SWIPE_COMMIT_PX) {
    return "center";
  }
  return lens;
}

export function lensBaseOffsetPercent(lens: GestureLens): number {
  switch (lens) {
    case "thread":
      return 0;
    case "center":
      return -100;
    case "facet":
      return -200;
  }
}

export function isHorizontalDragging(state: GesturePointerState): boolean {
  return state.kind === "lock-h";
}
