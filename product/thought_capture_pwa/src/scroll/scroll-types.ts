/**
 * Scroll Engineering types and defaults — binding values from SCROLL.md
 */

export type ScrollFollowState = "following" | "detached";

export type ScrollIntentSignal =
  | "scroll"
  | "select"
  | "type"
  | "keyboard"
  | "link"
  | "search"
  | "expand"
  | "tap-message"
  | "media"
  | "regenerate"
  | "error";

export type ScrollPrimitive =
  | "scroll.follow"
  | "scroll.detach"
  | "scroll.hold"
  | "scroll.anchor-turn"
  | "scroll.preserve-anchor"
  | "scroll.indicator"
  | "scroll.jump-latest"
  | "scroll.reopen"
  | "scroll.navigate";

export interface ScrollEngineState {
  follow_state: ScrollFollowState;
  anchor_element_id: string | null;
  anchor_offset_px: number;
  live_edge_threshold_px: number;
  last_user_turn_id: string | null;
}

export const SCROLL_DEFAULTS = {
  LIVE_EDGE_THRESHOLD_PX: 48,
  ANCHOR_TOP_PADDING_PX: 16,
  JUMP_LATEST_BEHAVIOR: "instant" as const,
} as const;

export function createInitialScrollState(): ScrollEngineState {
  return {
    follow_state: "following",
    anchor_element_id: null,
    anchor_offset_px: 0,
    live_edge_threshold_px: SCROLL_DEFAULTS.LIVE_EDGE_THRESHOLD_PX,
    last_user_turn_id: null,
  };
}
