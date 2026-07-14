import {
  SCROLL_DEFAULTS,
  type ScrollEngineState,
  type ScrollFollowState,
} from "./scroll-types";

export type ScrollEngineAction =
  | { type: "intent_detach" }
  | { type: "at_live_edge" }
  | { type: "jump_latest" }
  | { type: "set_last_user_turn"; turnId: string };

export function reduceScrollState(
  state: ScrollEngineState,
  action: ScrollEngineAction,
): ScrollEngineState {
  switch (action.type) {
    case "intent_detach":
      if (state.follow_state === "detached") {
        return state;
      }
      return { ...state, follow_state: "detached" };

    case "at_live_edge":
      if (state.follow_state === "following") {
        return state;
      }
      return { ...state, follow_state: "following" };

    case "jump_latest":
      return {
        ...state,
        follow_state: "following",
        anchor_element_id: null,
        anchor_offset_px: 0,
      };

    case "set_last_user_turn":
      return { ...state, last_user_turn_id: action.turnId };

    default:
      return state;
  }
}

export function measureDistanceFromLiveEdge(container: HTMLElement): number {
  const distance =
    container.scrollHeight - container.scrollTop - container.clientHeight;
  return Math.max(0, distance);
}

export function isWithinLiveEdge(
  container: HTMLElement,
  thresholdPx: number,
): boolean {
  return measureDistanceFromLiveEdge(container) <= thresholdPx;
}

export function getScrollUnitElement(
  container: HTMLElement,
  unitId: string,
): HTMLElement | null {
  return container.querySelector<HTMLElement>(
    `[data-scroll-unit="${unitId}"]`,
  );
}

/** Instant anchor placement — rule 4 / 11. No animated scroll. */
export function applyInstantAnchor(
  container: HTMLElement,
  anchor: HTMLElement,
  topPaddingPx: number = SCROLL_DEFAULTS.ANCHOR_TOP_PADDING_PX,
): void {
  const containerRect = container.getBoundingClientRect();
  const anchorRect = anchor.getBoundingClientRect();
  const delta = anchorRect.top - containerRect.top - topPaddingPx;
  container.scrollTop += delta;
}

export function applyJumpToLatest(container: HTMLElement): void {
  container.scrollTop = container.scrollHeight - container.clientHeight;
}

export function applyPreserveAnchorOnResize(
  container: HTMLElement,
  anchor: HTMLElement,
  previousAnchorTop: number,
): number {
  const nextAnchorTop = anchor.getBoundingClientRect().top;
  const delta = nextAnchorTop - previousAnchorTop;
  if (Math.abs(delta) > 0.5) {
    container.scrollTop += delta;
  }
  return nextAnchorTop;
}

export function shouldShowOffscreenIndicator(
  followState: ScrollFollowState,
  distanceFromLiveEdge: number,
  thresholdPx: number,
): boolean {
  return followState === "detached" && distanceFromLiveEdge > thresholdPx;
}
