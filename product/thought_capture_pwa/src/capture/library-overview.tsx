import type { LibrarySection } from "./types";
import {
  buildLibrarySections,
  libraryRowRecession,
  unitBrowseBadge,
  unitBrowseState,
} from "./library";

export function LibraryOverview({
  sections,
  focusId,
  expandedSections,
  onToggleSection,
  onSelect,
}: {
  sections: LibrarySection[];
  focusId: string;
  expandedSections: string[];
  onToggleSection: (id: string) => void;
  onSelect: (depositId: string) => void;
}) {
  return (
    <div className="library-overview">
      <p className="library-overview__hint">library · swipe right to field</p>
      <h2 className="library-overview__title">field memory</h2>

      {sections.map((section) => {
        const expanded = expandedSections.includes(section.id);
        return (
          <section key={section.id} className="library-section">
            <button
              type="button"
              className="library-section__header motion-confirm"
              onClick={() => onToggleSection(section.id)}
              onPointerDown={(e) => e.stopPropagation()}
            >
              <span className="library-section__caret">{expanded ? "▾" : "▸"}</span>
              <span>{section.label}</span>
              <span className="library-section__count">{section.units.length}</span>
            </button>
            {expanded
              ? section.units.map((unit, index) => {
                  const selected = unit.deposit.id === focusId;
                  const preview = unit.deposit.body.slice(0, 72);
                  const badge = unitBrowseBadge(unitBrowseState(unit));
                  const recession = libraryRowRecession(
                    section.id,
                    index,
                    section.units.length,
                    selected,
                  );
                  return (
                    <button
                      key={unit.deposit.id}
                      type="button"
                      className={`library-row motion-confirm${selected ? " library-row--selected" : ""}`}
                      style={{
                        opacity: recession.opacity,
                        fontSize: `${recession.fontSize}px`,
                        fontWeight: recession.fontWeight,
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelect(unit.deposit.id);
                      }}
                      onPointerDown={(e) => e.stopPropagation()}
                    >
                      {preview}
                      {unit.deposit.body.length > 72 ? "…" : ""}
                      <span className="library-row__badge">{badge}</span>
                    </button>
                  );
                })
              : null}
          </section>
        );
      })}
    </div>
  );
}

export { buildLibrarySections };
