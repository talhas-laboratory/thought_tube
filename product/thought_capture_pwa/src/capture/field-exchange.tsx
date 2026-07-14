import { UnitInsertion } from "./composition-unit";
import type { CompositionUnit } from "./types";

export function FieldExchange({
  unit,
  composing,
}: {
  unit: CompositionUnit;
  composing?: boolean;
}) {
  const hasInsertion = Boolean(unit.insertion);
  const showThinking = composing && !hasInsertion;

  return (
    <article className="field-exchange" data-scroll-unit={unit.deposit.id}>
      <p className="field-exchange__user">{unit.deposit.body}</p>
      {showThinking ? (
        <p className="field-exchange__thinking motion-hold" aria-live="polite">
          thinking…
        </p>
      ) : null}
      {unit.insertion ? (
        <div className="field-exchange__assist">
          <UnitInsertion insertion={unit.insertion} />
        </div>
      ) : null}
    </article>
  );
}
