import { describe, expect, it } from "vitest";
import { classifyInput } from "./capture-mode";
import { buildLocalInsertion, shapeBlocksFromInput } from "./local-composer";

describe("presence gating", () => {
  it("skips insertion on silent gate (deposit path)", () => {
    const state = classifyInput("rapid fragment one");
    const result = buildLocalInsertion(
      state,
      "rapid fragment one",
      [{ body: "rapid fragment one" }],
      "capture",
      "silent",
    );
    expect(result.skip).toBe(true);
  });

  it("produces cue on nudge for exploration", () => {
    const state = classifyInput("what if we tried a quieter library");
    const result = buildLocalInsertion(
      state,
      "what if we tried a quieter library",
      [{ body: "what if we tried a quieter library" }],
      "capture",
      "invited",
    );
    expect(result.skip).toBe(false);
    if (!result.skip) {
      expect(result.utterance_type).toBe("cue");
      expect(result.body.split("\n").length).toBeLessThanOrEqual(2);
    }
  });

  it("produces block_cluster on shape with presence 3+", () => {
    const state = classifyInput("facet one — facet two — facet three");
    const result = buildLocalInsertion(
      { ...state, mode: "development", response_contract: "structural_extraction", ai_presence: 3 },
      "facet one — facet two — facet three",
      [{ body: "facet one — facet two — facet three" }],
      "develop",
      "invited",
    );
    expect(result.skip).toBe(false);
    if (!result.skip) {
      expect(result.utterance_type).toBe("block_cluster");
      expect(result.blocks?.length).toBeGreaterThanOrEqual(2);
      expect(result.mode_state.ai_presence).toBeGreaterThanOrEqual(3);
    }
  });
});

describe("shapeBlocksFromInput", () => {
  it("splits on em dash", () => {
    expect(shapeBlocksFromInput("a — b — c")).toEqual(["a", "b", "c"]);
  });
});
