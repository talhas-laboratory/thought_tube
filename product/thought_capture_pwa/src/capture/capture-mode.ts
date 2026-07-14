/** CaptureModeState — binding: CONTRACTS.md §CaptureModeState */

export type CaptureMode =
  | "raw_dump"
  | "exploration"
  | "clarification"
  | "development"
  | "emotional_processing"
  | "task_conversion";

export type ResponseContract =
  | "no_response"
  | "acknowledgment_only"
  | "continuation_cue"
  | "clarification"
  | "summary"
  | "structural_extraction"
  | "emotional_mirroring"
  | "option_generation"
  | "conversion"
  | "deeper_reasoning";

export type AiPresenceLevel = 0 | 1 | 2 | 3 | 4;

export type GoalState =
  | "preserve_flow"
  | "sharpen_meaning"
  | "build_artifact"
  | "contain";

export interface CaptureModeState {
  mode: CaptureMode;
  response_contract: ResponseContract;
  ai_presence: AiPresenceLevel;
  goal_state: GoalState;
  confidence: number;
}

export const MODE_DEFAULTS: Record<
  CaptureMode,
  Omit<CaptureModeState, "mode" | "confidence">
> = {
  raw_dump: {
    response_contract: "acknowledgment_only",
    ai_presence: 1,
    goal_state: "preserve_flow",
  },
  exploration: {
    response_contract: "continuation_cue",
    ai_presence: 2,
    goal_state: "preserve_flow",
  },
  clarification: {
    response_contract: "clarification",
    ai_presence: 2,
    goal_state: "sharpen_meaning",
  },
  development: {
    response_contract: "structural_extraction",
    ai_presence: 3,
    goal_state: "build_artifact",
  },
  emotional_processing: {
    response_contract: "emotional_mirroring",
    ai_presence: 2,
    goal_state: "contain",
  },
  task_conversion: {
    response_contract: "conversion",
    ai_presence: 3,
    goal_state: "build_artifact",
  },
};

export function classifyInput(text: string): CaptureModeState {
  const lower = text.toLowerCase();
  let mode: CaptureMode = "exploration";
  let confidence = 0.55;

  if (/\?$/.test(text.trim()) || /^(how|why|when|where|who|which)\b/i.test(text)) {
    mode = "clarification";
    confidence = 0.78;
  } else if (
    /\b(feel|feeling|anxious|pressure|overwhelm|stuck|heavy|tired)\b/i.test(lower)
  ) {
    mode = "emotional_processing";
    confidence = 0.74;
  } else if (/\b(build|spec|structure|outline|design|architecture)\b/i.test(lower)) {
    mode = "development";
    confidence = 0.8;
  } else if (/\b(need to|todo|task|ship|deadline|remind)\b/i.test(lower)) {
    mode = "task_conversion";
    confidence = 0.76;
  } else if (/\bwhat if\b/i.test(lower) || text.trim().length < 42) {
    mode = text.trim().length < 28 ? "raw_dump" : "exploration";
    confidence = mode === "raw_dump" ? 0.82 : 0.7;
  }

  return { mode, confidence, ...MODE_DEFAULTS[mode] };
}

export function resolveModeState(
  text: string,
  force?: { mode?: CaptureMode; contract?: ResponseContract },
): CaptureModeState {
  if (force?.mode) {
    const base = MODE_DEFAULTS[force.mode];
    return {
      mode: force.mode,
      confidence: 1,
      ...base,
      response_contract: force.contract ?? base.response_contract,
      ai_presence: force.mode === "development" ? 3 : base.ai_presence,
    };
  }

  const classified = classifyInput(text);
  if (force?.contract) {
    return { ...classified, response_contract: force.contract };
  }
  return classified;
}

export function capPresenceForCapture(state: CaptureModeState): CaptureModeState {
  if (state.ai_presence > 2) {
    return { ...state, ai_presence: 2 };
  }
  return state;
}

export function shouldRequestAssistantResponse(_state: CaptureModeState): boolean {
  return true;
}
