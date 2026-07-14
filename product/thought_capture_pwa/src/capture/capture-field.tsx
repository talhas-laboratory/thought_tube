import { FieldExchange } from "./field-exchange";
import type { CompositionUnit } from "./types";
import type { RefObject } from "react";

export function CaptureField({
  units,
  composingDepositId,
  containerRef,
  liveEdgeRef,
  showJumpLatest,
  onJumpLatest,
  onContainerScroll,
}: {
  units: CompositionUnit[];
  composingDepositId?: string | null;
  containerRef: RefObject<HTMLDivElement | null>;
  liveEdgeRef: RefObject<HTMLDivElement | null>;
  showJumpLatest: boolean;
  onJumpLatest: () => void;
  onContainerScroll: () => void;
}) {
  return (
    <div className="capture-field">
      {showJumpLatest ? (
        <button
          type="button"
          className="capture-field__jump motion-confirm"
          onClick={onJumpLatest}
        >
          jump to latest
        </button>
      ) : null}

      <div
        ref={containerRef}
        className="capture-field__stream"
        data-scroll-region
        onScroll={onContainerScroll}
      >
        {units.length === 0 ? (
          <div className="capture-field capture-field--empty">
            <p className="capture-field__invitation">
              Drop a thought. The assistant answers below it.
            </p>
          </div>
        ) : (
          units.map((unit) => (
            <FieldExchange
              key={unit.deposit.id}
              unit={unit}
              composing={unit.deposit.id === composingDepositId}
            />
          ))
        )}
        <div ref={liveEdgeRef} className="capture-field__live-edge" data-scroll-live-edge />
      </div>
    </div>
  );
}
