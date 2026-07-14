import type { CompositionPhase, UtteranceType } from "./types";
import type {
  CaptureModeState,
  ResponseContract,
} from "./capture-mode";

export const DEFAULT_ANSWER_TEMPLATE = `{
  "no_response": "",
  "acknowledgment_only": "landed.",
  "continuation_cue": "still open around: {theme}",
  "clarification": "narrower: what would change if {theme}?",
  "summary": "thread so far — {summary}",
  "structural_extraction": "",
  "emotional_mirroring": "weight on: {theme}",
  "option_generation": "hold it / name it / branch it",
  "conversion": "next concrete step: one line, no plan",
  "deeper_reasoning": "{input} — what assumption sits underneath?"
}`;

export type CompositionGate = "silent" | "invited";

export type BuiltInsertion = {
  skip: false;
  utterance_type: UtteranceType;
  body: string;
  blocks?: string[];
  composition_phase: CompositionPhase;
  mode_state: CaptureModeState;
};

export type SkippedInsertion = { skip: true };

export type CompositionResult = BuiltInsertion | SkippedInsertion;

function themeFromInput(input: string): string {
  const words = input.trim().split(/\s+/).slice(0, 6);
  return words.join(" ").replace(/[?.!,;:]+$/, "");
}

function summaryFromDeposits(deposits: { body: string }[]): string {
  return deposits
    .slice(-3)
    .map((d) => d.body.slice(0, 42))
    .join(" / ");
}

export function shapeBlocksFromInput(input: string): string[] {
  const trimmed = input.trim();
  if (!trimmed) return [];

  const onDash = trimmed
    .split(/\s*[—–]\s*/)
    .map((s) => s.trim())
    .filter(Boolean);
  if (onDash.length >= 2 && onDash.length <= 4) return onDash;

  const sentences = trimmed
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter(Boolean);
  if (sentences.length >= 2 && sentences.length <= 4) return sentences;

  const onComma = trimmed
    .split(/\s*,\s+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 6);
  if (onComma.length >= 2 && onComma.length <= 4) return onComma;

  return [trimmed];
}

export function contractToUtterance(
  contract: ResponseContract,
  phase: CompositionPhase,
): UtteranceType {
  if (
    phase === "develop" &&
    (contract === "structural_extraction" ||
      contract === "option_generation" ||
      contract === "deeper_reasoning")
  ) {
    return "block_cluster";
  }
  switch (contract) {
    case "acknowledgment_only":
      return "ack";
    case "continuation_cue":
      return "cue";
    case "emotional_mirroring":
      return "mirror";
    case "clarification":
    case "summary":
    case "conversion":
      return "sharpen";
    default:
      return "cue";
  }
}

function parseTemplate(raw: string): Record<string, string> {
  try {
    return JSON.parse(raw) as Record<string, string>;
  } catch {
    return JSON.parse(DEFAULT_ANSWER_TEMPLATE) as Record<string, string>;
  }
}

function interpolate(
  pattern: string,
  input: string,
  deposits: { body: string }[],
): string {
  const theme = themeFromInput(input);
  const summary = summaryFromDeposits(deposits);
  const blocks = deposits.slice(-2).map((d) => d.body.slice(0, 48));
  return pattern
    .replace(/\{input\}/g, input)
    .replace(/\{theme\}/g, theme)
    .replace(/\{summary\}/g, summary)
    .replace(/\{block_a\}/g, blocks[0] ?? theme)
    .replace(/\{block_b\}/g, blocks[1] ?? "—")
    .replace(/\\n/g, "\n");
}

export function buildLocalInsertion(
  state: CaptureModeState,
  input: string,
  deposits: { body: string }[],
  compositionPhase: CompositionPhase,
  gate: CompositionGate,
  templateRaw = DEFAULT_ANSWER_TEMPLATE,
): CompositionResult {
  if (gate === "silent") {
    return { skip: true };
  }

  const templates = parseTemplate(templateRaw);
  const pattern = templates[state.response_contract] ?? "";
  const isStructural = state.response_contract === "structural_extraction";

  if (
    state.response_contract === "no_response" ||
    state.ai_presence === 0 ||
    (!pattern.trim() && !isStructural)
  ) {
    return { skip: true };
  }

  const filled = interpolate(pattern, input, deposits).trim();
  if (!filled && !isStructural) {
    return { skip: true };
  }

  const utteranceType = contractToUtterance(
    state.response_contract,
    compositionPhase,
  );

  if (utteranceType === "block_cluster") {
    const blocks = shapeBlocksFromInput(input);
    return {
      skip: false,
      utterance_type: utteranceType,
      body: "",
      blocks,
      composition_phase: compositionPhase,
      mode_state: state,
    };
  }

  if (compositionPhase === "capture" && utteranceType === "sharpen") {
    return {
      skip: false,
      utterance_type: utteranceType,
      body: filled.split("\n").slice(0, 2).join("\n"),
      composition_phase: compositionPhase,
      mode_state: state,
    };
  }

  if (utteranceType === "cue" || utteranceType === "mirror") {
    return {
      skip: false,
      utterance_type: utteranceType,
      body: filled.split("\n").slice(0, 2).join("\n"),
      composition_phase: compositionPhase,
      mode_state: state,
    };
  }

  return {
    skip: false,
    utterance_type: utteranceType,
    body: filled.split("\n")[0] ?? filled,
    composition_phase: compositionPhase,
    mode_state: state,
  };
}
