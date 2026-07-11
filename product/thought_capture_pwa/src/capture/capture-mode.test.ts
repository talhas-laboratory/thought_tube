import { describe, expect, it } from "vitest";
import {
  capPresenceForCapture,
  classifyInput,
  resolveModeState,
  shouldRequestAssistantResponse,
} from "./capture-mode";

describe("classifyInput", () => {
  it("classifies short fragments as raw_dump", () => {
    const state = classifyInput("hmm");
    expect(state.mode).toBe("raw_dump");
    expect(state.ai_presence).toBeLessThanOrEqual(2);
  });

  it("classifies questions as clarification", () => {
    const state = classifyInput("Why does this feel stuck?");
    expect(state.mode).toBe("clarification");
    expect(state.response_contract).toBe("clarification");
  });

  it("classifies emotional language", () => {
    const state = classifyInput("feeling anxious about the deadline");
    expect(state.mode).toBe("emotional_processing");
  });
});

describe("resolveModeState", () => {
  it("forces development mode for shape", () => {
    const state = resolveModeState("a short note", {
      mode: "development",
      contract: "structural_extraction",
    });
    expect(state.mode).toBe("development");
    expect(state.ai_presence).toBe(3);
    expect(state.response_contract).toBe("structural_extraction");
  });
});

describe("capPresenceForCapture", () => {
  it("caps presence above 2 in capture", () => {
    const state = resolveModeState("build a spec outline", {
      mode: "development",
      contract: "structural_extraction",
    });
    const capped = capPresenceForCapture(state);
    expect(capped.ai_presence).toBe(2);
  });
});

describe("shouldRequestAssistantResponse", () => {
  it("keeps the connected assistant active even for a locally silent mode", () => {
    expect(
      shouldRequestAssistantResponse({
        mode: "raw_dump",
        response_contract: "no_response",
        ai_presence: 0,
        goal_state: "preserve_flow",
        confidence: 1,
      }),
    ).toBe(true);
  });
});
