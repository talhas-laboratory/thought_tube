import type {
  CompositionUnit,
  LibrarySection,
  LibrarySectionId,
  UnitBrowseState,
} from "./types";

export function unitBrowseState(unit: CompositionUnit): UnitBrowseState {
  if (!unit.insertion) return "open";
  if (unit.insertion.utterance_type === "block_cluster") return "shaped";
  return "waiting";
}

export function unitBrowseBadge(state: UnitBrowseState): string {
  return state;
}

export function buildLibrarySections(
  units: CompositionUnit[],
  focusId: string,
): LibrarySection[] {
  const focusIdx = units.findIndex((u) => u.deposit.id === focusId);
  const nowIds = new Set<string>();

  if (focusIdx >= 0) {
    for (let i = Math.max(0, focusIdx - 2); i <= focusIdx; i++) {
      nowIds.add(units[i].deposit.id);
    }
  }

  const now: CompositionUnit[] = [];
  const stillMoving: CompositionUnit[] = [];
  const resting: CompositionUnit[] = [];

  for (let i = 0; i < units.length; i++) {
    const unit = units[i];
    if (nowIds.has(unit.deposit.id)) {
      now.push(unit);
      continue;
    }

    const state = unitBrowseState(unit);
    const recent = i >= units.length - 6;

    if (state === "shaped" || !recent) {
      resting.push(unit);
    } else {
      stillMoving.push(unit);
    }
  }

  return [
    { id: "now", label: "now", units: now },
    { id: "still_moving", label: "still moving", units: stillMoving },
    { id: "resting", label: "resting", units: resting },
  ].filter((section) => section.units.length > 0) as LibrarySection[];
}

export function continuityContext(
  units: CompositionUnit[],
  focusId: string,
): CompositionUnit[] {
  const idx = units.findIndex((u) => u.deposit.id === focusId);
  if (idx <= 0) return [];
  return units.slice(Math.max(0, idx - 2), idx);
}

export function libraryRowRecession(
  sectionId: LibrarySectionId,
  index: number,
  sectionLength: number,
  isFocus: boolean,
): { opacity: number; fontSize: number; fontWeight: number } {
  if (isFocus) {
    return { opacity: 1, fontSize: 14, fontWeight: 500 };
  }

  const depth = sectionLength - 1 - index;

  if (sectionId === "now") {
    return {
      opacity: Math.max(0.72, 1 - depth * 0.1),
      fontSize: 13.5,
      fontWeight: 400,
    };
  }
  if (sectionId === "still_moving") {
    return {
      opacity: Math.max(0.58, 0.88 - depth * 0.06),
      fontSize: 13,
      fontWeight: 400,
    };
  }
  return {
    opacity: Math.max(0.42, 0.68 - depth * 0.05),
    fontSize: 12,
    fontWeight: 400,
  };
}
