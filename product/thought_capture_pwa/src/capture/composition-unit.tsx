import type { InsertionRecord } from "./types";

function insertionBody(insertion: InsertionRecord): string | null {
  if (insertion.utterance_type === "block_cluster" && insertion.blocks?.length) {
    return null;
  }
  return insertion.body;
}

export function UnitInsertion({ insertion }: { insertion: InsertionRecord }) {
  if (insertion.utterance_type === "block_cluster" && insertion.blocks?.length) {
    return (
      <div className="field-exchange__blocks" data-scroll-resize>
        {insertion.blocks.map((block) => (
          <p key={block} className="field-exchange__block">
            {block}
          </p>
        ))}
      </div>
    );
  }

  return (
    <p
      className={`field-exchange__reply field-exchange__reply--${insertion.utterance_type}`}
      data-scroll-resize
    >
      {insertionBody(insertion)}
    </p>
  );
}
