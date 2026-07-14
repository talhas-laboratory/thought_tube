import { useRef, useState, type CSSProperties } from "react";
import { CaptureModeDebug } from "./capture-mode-overlay";
import { CaptureField } from "./capture-field";
import { CaptureDock } from "./capture-dock";
import { LibraryOverview, buildLibrarySections } from "./library-overview";
import { useScrollEngine } from "../scroll/use-scroll-engine";
import {
  useElementHeight,
  useVisualViewportHeight,
  useVisualViewportKeyboardOffset,
} from "../shell/viewport";
import { SwipeSurface, useHorizontalSwipe } from "./swipe-surface";
import { useCaptureStream } from "./use-capture-stream";
import type { SurfacePane } from "./types";
import "./capture.css";

export function CapturePage() {
  const {
    fieldUnits,
    libraryUnits,
    focusId,
    modeState,
    composingDepositId,
    loading,
    deposit,
    selectUnit,
    beginNewField,
  } = useCaptureStream();
  const [surfacePane, setSurfacePane] = useState<SurfacePane>("capture");
  const [expandedSections, setExpandedSections] = useState<string[]>([
    "now",
    "still_moving",
    "resting",
  ]);
  const swipe = useHorizontalSwipe(surfacePane, setSurfacePane);
  const dockRef = useRef<HTMLElement>(null);
  const keyboardOffset = useVisualViewportKeyboardOffset();
  const viewportHeight = useVisualViewportHeight();
  const dockHeight = useElementHeight(dockRef, [loading]);

  const scroll = useScrollEngine({
    units: fieldUnits,
    focusDepositId: focusId,
    enabled: !loading && surfacePane === "capture",
  });

  const sections = buildLibrarySections(libraryUnits, focusId);

  function toggleSection(id: string) {
    setExpandedSections((prev) =>
      prev.includes(id) ? prev.filter((entry) => entry !== id) : [...prev, id],
    );
  }

  async function selectFromLibrary(depositId: string) {
    scroll.reopenAtDeposit(depositId);
    await selectUnit(depositId);
    swipe.resetPane();
    setSurfacePane("capture");
  }

  return (
    <div
      className="capture-page"
      style={
        viewportHeight
          ? ({ "--capture-viewport-height": `${viewportHeight}px` } as CSSProperties)
          : undefined
      }
    >
      <div className="capture-page__vignette" aria-hidden="true" />

      <div
        className="capture-page__body"
        style={{ paddingBottom: dockHeight > 0 ? `${dockHeight}px` : undefined }}
      >
        <div className="capture-page__nav">
          <button
            type="button"
            className="capture-page__nav-chip motion-confirm"
            onClick={() =>
              setSurfacePane(surfacePane === "capture" ? "overview" : "capture")
            }
          >
            {surfacePane === "capture" ? "library →" : "← field"}
          </button>
          {surfacePane === "capture" ? (
            <button
              type="button"
              className="capture-page__nav-chip motion-confirm"
              onClick={() => void beginNewField()}
              disabled={loading || composingDepositId !== null}
            >
              new field
            </button>
          ) : null}
          <CaptureModeDebug state={modeState} />
        </div>

        {loading ? (
          <p className="capture-page__loading">loading…</p>
        ) : (
          <SwipeSurface
            pane={surfacePane}
            dragX={swipe.dragX}
            gesture={swipe.gesture}
            onPointerDown={swipe.onPointerDown}
            onPointerMove={swipe.onPointerMove}
            onPointerUp={swipe.onPointerUp}
          >
            <div className="capture-page__pane capture-page__pane--field">
              <CaptureField
                units={fieldUnits}
                composingDepositId={composingDepositId}
                containerRef={scroll.containerRef}
                liveEdgeRef={scroll.liveEdgeRef}
                showJumpLatest={scroll.showJumpLatest}
                onJumpLatest={scroll.jumpToLatest}
                onContainerScroll={scroll.onContainerScroll}
              />
            </div>
            <div
              className="capture-page__pane capture-page__pane--library"
              data-library-pane
              data-no-swipe
            >
              <LibraryOverview
                sections={sections}
                focusId={focusId}
                expandedSections={expandedSections}
                onToggleSection={toggleSection}
                onSelect={(id) => void selectFromLibrary(id)}
              />
            </div>
          </SwipeSurface>
        )}
      </div>

      <CaptureDock
        dockRef={dockRef}
        keyboardOffset={keyboardOffset}
        modeState={modeState}
        onDeposit={async (body) => {
          await deposit(body);
        }}
        onFocusField={() => scroll.signalIntent("type")}
        disabled={loading || composingDepositId !== null}
      />
    </div>
  );
}
