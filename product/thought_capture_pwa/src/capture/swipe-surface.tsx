import { useRef, useState, type ReactNode } from "react";
import type { SurfacePane } from "./types";
import {
  isInteractiveGestureTarget,
  isScrollRegionTarget,
  isWithinEdgeGuard,
  reducePointerDown,
  reducePointerMove,
} from "../gesture/gesture-engine";
import { SWIPE_COMMIT_PX } from "../gesture/gesture-types";
import type { GesturePointerState } from "../gesture/gesture-types";

export function useHorizontalSwipe(
  pane: SurfacePane,
  setPane: (pane: SurfacePane) => void,
) {
  const [dragX, setDragX] = useState(0);
  const pointerRef = useRef<GesturePointerState>({ kind: "idle" });

  function resetPane() {
    pointerRef.current = { kind: "idle" };
    setDragX(0);
  }

  function onPointerDown(e: React.PointerEvent<HTMLDivElement>) {
    if (isScrollRegionTarget(e.target)) {
      return;
    }
    const next = reducePointerDown(
      pointerRef.current,
      e.clientX,
      e.clientY,
      e.pointerId,
      window.innerWidth,
      isInteractiveGestureTarget(e.target),
    );
    if (next.kind !== "down") {
      return;
    }
    e.currentTarget.setPointerCapture(e.pointerId);
    pointerRef.current = next;
    setDragX(0);
  }

  function onPointerMove(e: React.PointerEvent<HTMLDivElement>) {
    const { state } = reducePointerMove(
      pointerRef.current,
      e.clientX,
      e.clientY,
    );
    pointerRef.current = state;

    if (state.kind === "lock-v") {
      try {
        e.currentTarget.releasePointerCapture(e.pointerId);
      } catch {
        /* released */
      }
      pointerRef.current = { kind: "idle" };
      setDragX(0);
      return;
    }

    if (state.kind !== "lock-h") {
      return;
    }

    const startX = state.startX;
    const dx = e.clientX - startX;
    const atCaptureEnd = pane === "capture" && dx > 0;
    const atOverviewEnd = pane === "overview" && dx < 0;
    const resisted = atCaptureEnd || atOverviewEnd ? dx * 0.25 : dx;
    setDragX(resisted);
  }

  function onPointerUp(e: React.PointerEvent<HTMLDivElement>) {
    try {
      e.currentTarget.releasePointerCapture(e.pointerId);
    } catch {
      /* released */
    }

    if (pointerRef.current.kind === "lock-h") {
      if (pane === "capture" && dragX <= -SWIPE_COMMIT_PX) {
        setPane("overview");
      } else if (pane === "overview" && dragX >= SWIPE_COMMIT_PX) {
        setPane("capture");
      }
    }

    resetPane();
  }

  const gesture =
    pointerRef.current.kind === "lock-h"
      ? "lock-h"
      : pointerRef.current.kind === "lock-v"
        ? "lock-v"
        : pointerRef.current.kind === "down"
          ? "down"
          : "idle";

  return {
    dragX,
    gesture,
    onPointerDown,
    onPointerMove,
    onPointerUp,
    resetPane,
  };
}

export function SwipeSurface({
  pane,
  dragX,
  gesture,
  onPointerDown,
  onPointerMove,
  onPointerUp,
  children,
}: {
  pane: SurfacePane;
  dragX: number;
  gesture: string;
  onPointerDown: (e: React.PointerEvent<HTMLDivElement>) => void;
  onPointerMove: (e: React.PointerEvent<HTMLDivElement>) => void;
  onPointerUp: (e: React.PointerEvent<HTMLDivElement>) => void;
  children: ReactNode;
}) {
  const dragging = gesture === "lock-h";
  const baseOffset = pane === "overview" ? -50 : 0;

  return (
    <div
      className="swipe-surface"
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
    >
      <div
        className={`swipe-surface__track${dragging ? " swipe-surface__track--dragging" : ""}`}
        style={{ transform: `translateX(calc(${baseOffset}% + ${dragX}px))` }}
      >
        {children}
      </div>
    </div>
  );
}

export { isWithinEdgeGuard };
