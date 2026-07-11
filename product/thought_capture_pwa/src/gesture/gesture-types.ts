/** GestureZone — binding: CONTRACTS.md §GestureZone */

export const EDGE_GUARD_PX = 32;
export const SWIPE_LOCK_PX = 10;
export const SWIPE_COMMIT_PX = 52;

export type GestureLens = "thread" | "center" | "facet";

export type GesturePhase = "idle" | "lock-v" | "lock-h" | "dragging";

export type GesturePointerState =
  | { kind: "idle" }
  | { kind: "down"; pointerId: number; startX: number; startY: number }
  | { kind: "lock-v" }
  | { kind: "lock-h"; pointerId: number; startX: number; startY: number };
