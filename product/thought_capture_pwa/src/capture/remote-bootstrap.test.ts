import { describe, expect, it } from "vitest";
import { buildBootstrapCompositionUnits } from "./remote-bootstrap";

describe("buildBootstrapCompositionUnits", () => {
  it("maps mobile feed items into local composition units", () => {
    const units = buildBootstrapCompositionUnits(
      {
        items: [
          {
            thought_id: "thought-1",
            insight_id: "insight-1",
            title: "Protect The Signal",
            summary: "There is usually a live wire inside the raw material.",
          },
        ],
      },
      1_700_000_000_000,
    );

    expect(units).toHaveLength(1);
    expect(units[0]?.deposit.id).toBe("remote-deposit-insight-1");
    expect(units[0]?.deposit.body).toBe("Protect The Signal");
    expect(units[0]?.deposit.sync_status).toBe("synced");
    expect(units[0]?.deposit.field_id).toBe("field-remote-bootstrap");
    expect(units[0]?.insertion?.id).toBe("remote-insertion-insight-1");
    expect(units[0]?.insertion?.utterance_type).toBe("mirror");
    expect(units[0]?.insertion?.body).toBe(
      "There is usually a live wire inside the raw material.",
    );
  });

  it("uses the summary as body when title is absent", () => {
    const units = buildBootstrapCompositionUnits({
      items: [
        {
          thought_id: "thought-2",
          summary: "A quiet note without a title.",
        },
      ],
    });

    expect(units[0]?.deposit.body).toBe("A quiet note without a title.");
    expect(units[0]?.insertion).toBeUndefined();
  });
});
