import { useEffect, useRef, useState } from "react";

type AtlasCard = {
  id: string;
  band: string;
  range: string;
  kind: string;
  title: string;
  summary: string;
  thread: string;
  status: string;
  coupling: string;
  x: number;
  y: number;
};

const CARDS: AtlasCard[] = [
  {
    id: "u.01",
    band: "Opening thesis and self-communication",
    range: "1 to 6",
    kind: "seed",
    title: "A layer where people communicate with themselves.",
    summary:
      "The thread opens by defining the product as a place where a person can encounter and refine their own thought through intelligence.",
    thread: "main-thread",
    status: "main spine",
    coupling: "shared across all surfaces",
    x: 0,
    y: 0,
  },
  {
    id: "u.02",
    band: "Opening thesis and self-communication",
    range: "1 to 6",
    kind: "refinement",
    title: "Intelligence is raw material.",
    summary:
      "The system should treat intelligence as upstream material that must be refined into the form the user needs in that moment.",
    thread: "main-thread",
    status: "promoted branch",
    coupling: "shared with assembly layer",
    x: 1,
    y: 0,
  },
  {
    id: "u.03",
    band: "Opening thesis and self-communication",
    range: "1 to 6",
    kind: "mode",
    title: "Main thread plus sidecars.",
    summary:
      "The conversation requires a long-running spine with isolated sidecars that can be reintegrated cleanly later.",
    thread: "control-topology",
    status: "operating rule",
    coupling: "shared with context packets",
    x: -1,
    y: 0,
  },
  {
    id: "u.04",
    band: "Opening thesis and self-communication",
    range: "1 to 6",
    kind: "refinement",
    title: "Organize around my input and track the flow.",
    summary:
      "The system should preserve meaningful phrasing, track motion through the thread, and avoid premature flattening.",
    thread: "main-thread",
    status: "locked instruction",
    coupling: "shared with session system",
    x: 0,
    y: -1,
  },
  {
    id: "u.05",
    band: "Topology control and routing",
    range: "7 to 14",
    kind: "control",
    title: "Meta mode can adjust topology in real time.",
    summary:
      "The user should be able to steer how contexts connect or stay isolated while the conversation is unfolding.",
    thread: "control-topology",
    status: "promoted branch",
    coupling: "shared with routing",
    x: 0,
    y: 1,
  },
  {
    id: "u.06",
    band: "Topology control and routing",
    range: "7 to 14",
    kind: "routing",
    title: "Hashtags are routing operators.",
    summary:
      "A hashtag should act as lightweight control syntax for mode switching or isolated modular content/context.",
    thread: "control-topology",
    status: "operating rule",
    coupling: "shared with parser",
    x: 1,
    y: 1,
  },
  {
    id: "u.07",
    band: "Topology control and routing",
    range: "7 to 14",
    kind: "measurement",
    title: "Track outside influences and controlled differences.",
    summary:
      "The latent topology should register external perturbations and measure conceptual shifts through stable observables.",
    thread: "control-topology",
    status: "open method",
    coupling: "shared with measurement layer",
    x: -1,
    y: 1,
  },
  {
    id: "u.08",
    band: "Context workshop and navigation",
    range: "15 to 21",
    kind: "context",
    title: "Context is the instrument set.",
    summary:
      "Stored context is not an archive alone; it is the toolset used to bend, compress, expand, and crystallize intelligence.",
    thread: "context-workshop",
    status: "main spine",
    coupling: "shared with personalization",
    x: 2,
    y: 0,
  },
  {
    id: "u.09",
    band: "Context workshop and navigation",
    range: "15 to 21",
    kind: "navigation",
    title: "Help the user know where they are.",
    summary:
      "The atlas should help a person stay in flow without losing their position in thought space or nearby options.",
    thread: "context-workshop",
    status: "promoted branch",
    coupling: "shared with display surface",
    x: 2,
    y: -1,
  },
  {
    id: "u.10",
    band: "Context workshop and navigation",
    range: "15 to 21",
    kind: "save",
    title: "Save before compression.",
    summary:
      "The conversation must be checkpointed before context compression erases usable continuity or design substrate.",
    thread: "context-workshop",
    status: "operating rule",
    coupling: "shared with session system",
    x: 2,
    y: 1,
  },
  {
    id: "u.11",
    band: "Assembly layer and cognitive clay",
    range: "22 to 30",
    kind: "stack",
    title: "There is a missing final assembly layer.",
    summary:
      "Between the raw model provider and the management layer, there is an opening for a reliable personalization and behavior-shaping layer.",
    thread: "assembly-layer",
    status: "main spine",
    coupling: "shared with runtime design",
    x: -2,
    y: 0,
  },
  {
    id: "u.12",
    band: "Assembly layer and cognitive clay",
    range: "22 to 30",
    kind: "platform",
    title: "Be invisible communicative infrastructure.",
    summary:
      "The product should sit underneath tools like Codex, Claude, and OpenClaw and carry continuity between them.",
    thread: "assembly-layer",
    status: "platform thesis",
    coupling: "shared across tools",
    x: -2,
    y: -1,
  },
  {
    id: "u.13",
    band: "Assembly layer and cognitive clay",
    range: "22 to 30",
    kind: "material",
    title: "Users shape it like cognitive clay.",
    summary:
      "The medium should be moldable, hold form once shaped, and still remain reworkable when the user changes.",
    thread: "assembly-layer",
    status: "promoted metaphor",
    coupling: "shared with personal interface",
    x: -2,
    y: 1,
  },
  {
    id: "u.14",
    band: "Mobilegrid runtime",
    range: "27 to 30",
    kind: "runtime",
    title: "Mobilegrid is the stable surface.",
    summary:
      "The mobile-facing host should be stable by default, with a separate preview surface for live experimental work.",
    thread: "mobilegrid-runtime",
    status: "deployment decision",
    coupling: "shared with OpenClaw routing",
    x: 0,
    y: 2,
  },
  {
    id: "u.15",
    band: "Mobilegrid runtime",
    range: "27 to 30",
    kind: "deploy",
    title: "Preview continuously, publish selectively.",
    summary:
      "The low-energy workflow is local live preview with deliberate promotion to the stable surface instead of constant deploy churn.",
    thread: "mobilegrid-runtime",
    status: "recommended pattern",
    coupling: "shared with deployment surface",
    x: 1,
    y: 2,
  },
  {
    id: "u.16",
    band: "Mobilegrid runtime",
    range: "27 to 30",
    kind: "approval",
    title: "Phone stays in approval mode.",
    summary:
      "The mobile surface should inspect, save, and approve promotion without becoming the primary execution plane.",
    thread: "mobilegrid-runtime",
    status: "locked decision",
    coupling: "shared with mobile protocol",
    x: -1,
    y: 2,
  },
  {
    id: "u.17",
    band: "Display surface and translation",
    range: "31 to 40",
    kind: "display",
    title: "Use the conversation itself as substrate.",
    summary:
      "The atlas should be populated from this thread rather than a generic mock so the interface becomes a real thought surface.",
    thread: "display-surface",
    status: "design request",
    coupling: "shared with specimen layer",
    x: 3,
    y: 0,
  },
  {
    id: "u.18",
    band: "Display surface and translation",
    range: "31 to 40",
    kind: "translation",
    title: "A holodeck translator should grow rough intent into systems.",
    summary:
      "Codex should act as an architect layer that expands rough input, binds it to the system, asks only the necessary clarifying questions, and shapes implementation.",
    thread: "holodeck-translation",
    status: "new spine branch",
    coupling: "shared with architect layer",
    x: 3,
    y: -1,
  },
  {
    id: "u.19",
    band: "Display surface and translation",
    range: "31 to 40",
    kind: "tracking",
    title: "Dormant concepts should keep growing.",
    summary:
      "Unimplemented ideas should stay linked and evolve as related parts of the system gain more shape.",
    thread: "holodeck-translation",
    status: "open system requirement",
    coupling: "shared with growth engine",
    x: 3,
    y: 1,
  },
];

const CARD_STEP_X = 172;
const CARD_STEP_Y = 216;
const MAX_DISTANCE = 3;
const SWIPE_THRESHOLD = 42;

function classify(dx: number, dy: number): "active" | "near" | "far" | "hidden" {
  const distance = Math.abs(dx) + Math.abs(dy);
  if (distance === 0) return "active";
  if (distance === 1) return "near";
  if (distance <= MAX_DISTANCE) return "far";
  return "hidden";
}

function findCard(x: number, y: number): AtlasCard | undefined {
  return CARDS.find((card) => card.x === x && card.y === y);
}

export function App() {
  const [activeId, setActiveId] = useState(CARDS[0].id);
  const [previewExpanded, setPreviewExpanded] = useState(false);
  const [sheetTransitioning, setSheetTransitioning] = useState(false);
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const dragStartRef = useRef<{ x: number; y: number; time: number; id: number } | null>(null);
  const sheetStartRef = useRef<{ x: number; y: number; id: number } | null>(null);
  const sheetSuppressClickRef = useRef(false);
  const animatingRef = useRef(false);

  const activeCard = CARDS.find((card) => card.id === activeId) ?? CARDS[0];

  useEffect(() => {
    if ("serviceWorker" in navigator) {
      void navigator.serviceWorker.register("./service-worker.js").catch(() => undefined);
    }
  }, []);

  useEffect(() => {
    const handleKeydown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setPreviewExpanded(false);
      }
      if (event.key === "ArrowLeft") move("left");
      if (event.key === "ArrowRight") move("right");
      if (event.key === "ArrowUp") move("up");
      if (event.key === "ArrowDown") move("down");
    };
    window.addEventListener("keydown", handleKeydown);
    return () => window.removeEventListener("keydown", handleKeydown);
  });

  function setActiveCard(next: AtlasCard): void {
    setSheetTransitioning(true);
    setActiveId(next.id);
    window.setTimeout(() => {
      setSheetTransitioning(false);
    }, 170);
  }

  function bounce(axis: "x" | "y", distance: number): void {
    const viewport = viewportRef.current;
    if (!viewport) return;
    const frames =
      axis === "x"
        ? [{ transform: "translateX(0px)" }, { transform: `translateX(${distance}px)` }, { transform: "translateX(0px)" }]
        : [{ transform: "translateY(0px)" }, { transform: `translateY(${distance}px)` }, { transform: "translateY(0px)" }];
    viewport.animate(frames, {
      duration: 240,
      easing: "cubic-bezier(0.22, 1, 0.36, 1)",
    });
  }

  function move(direction: "left" | "right" | "up" | "down"): void {
    if (animatingRef.current) return;
    const delta =
      direction === "left"
        ? [-1, 0]
        : direction === "right"
          ? [1, 0]
          : direction === "up"
            ? [0, -1]
            : [0, 1];
    const next = findCard(activeCard.x + delta[0], activeCard.y + delta[1]);
    if (!next) {
      if (direction === "left") bounce("x", 10);
      if (direction === "right") bounce("x", -10);
      if (direction === "up") bounce("y", 10);
      if (direction === "down") bounce("y", -10);
      return;
    }
    animatingRef.current = true;
    setActiveCard(next);
    window.setTimeout(() => {
      animatingRef.current = false;
    }, 320);
  }

  function handleViewportPointerDown(event: React.PointerEvent<HTMLDivElement>): void {
    if (previewExpanded) return;
    dragStartRef.current = {
      x: event.clientX,
      y: event.clientY,
      time: performance.now(),
      id: event.pointerId,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function handleViewportPointerUp(event: React.PointerEvent<HTMLDivElement>): void {
    const gesture = dragStartRef.current;
    if (!gesture || gesture.id !== event.pointerId) return;
    dragStartRef.current = null;
    const dx = event.clientX - gesture.x;
    const dy = event.clientY - gesture.y;
    const elapsed = Math.max(1, performance.now() - gesture.time);
    const absX = Math.abs(dx);
    const absY = Math.abs(dy);
    const velocity = Math.max(absX, absY) / elapsed;
    if (Math.max(absX, absY) < SWIPE_THRESHOLD && velocity < 0.24) return;
    if (absX > absY) {
      move(dx < 0 ? "right" : "left");
      return;
    }
    move(dy < 0 ? "down" : "up");
  }

  function handleSheetPointerDown(event: React.PointerEvent<HTMLElement>): void {
    if (!previewExpanded) return;
    sheetStartRef.current = {
      x: event.clientX,
      y: event.clientY,
      id: event.pointerId,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function handleSheetPointerUp(event: React.PointerEvent<HTMLElement>): void {
    const gesture = sheetStartRef.current;
    if (!previewExpanded || !gesture || gesture.id !== event.pointerId) return;
    sheetStartRef.current = null;
    const dx = event.clientX - gesture.x;
    const dy = event.clientY - gesture.y;
    if (Math.abs(dx) < 18 && Math.abs(dy) < 18) {
      sheetSuppressClickRef.current = true;
      setPreviewExpanded(false);
      return;
    }
    if (Math.abs(dy) > Math.abs(dx) && dy > 48) {
      sheetSuppressClickRef.current = true;
      setPreviewExpanded(false);
    }
  }

  function handleSheetClick(): void {
    if (sheetSuppressClickRef.current) {
      sheetSuppressClickRef.current = false;
      return;
    }
    setPreviewExpanded((value) => !value);
  }

  return (
    <main className="atlas-mobile">
      <section
        ref={viewportRef}
        className="atlas-field"
        aria-label="Conversation atlas grid"
        onPointerCancel={() => {
          dragStartRef.current = null;
        }}
        onPointerDown={handleViewportPointerDown}
        onPointerUp={handleViewportPointerUp}
      >
        <div className="field-grid" aria-hidden="true" />
        <div className="field-vignette" aria-hidden="true" />
        <div className="focus-window" aria-hidden="true" />
        {CARDS.map((card) => {
          const dx = card.x - activeCard.x;
          const dy = card.y - activeCard.y;
          const state = classify(dx, dy);
          const scale = state === "active" ? 1 : state === "near" ? 0.92 : 0.84;
          const rotation = Math.max(-5.5, Math.min(5.5, dx * 2.2));
          const transform = `translate3d(calc(-50% + ${dx * CARD_STEP_X}px), calc(-50% + ${dy * CARD_STEP_Y}px), 0) scale(${scale}) rotate(${rotation}deg)`;
          return (
            <button
              key={card.id}
              className={`atlas-card atlas-card--${state}`}
              style={{ transform }}
              type="button"
              onClick={() => {
                if (card.id !== activeCard.id && state !== "hidden") {
                  setActiveCard(card);
                }
              }}
            >
              <div className="atlas-card__meta">
                <span>{card.id}</span>
                <span className="atlas-card__kind">{card.kind}</span>
              </div>
              <h2 className="atlas-card__title">{card.title}</h2>
              <p className="atlas-card__summary">{card.summary}</p>
              <div className="atlas-card__footer">
                <div>
                  <p className="atlas-card__label">Thread</p>
                  <p>{card.thread}</p>
                </div>
                <div>
                  <p className="atlas-card__label">Status</p>
                  <p>{card.status}</p>
                </div>
              </div>
            </button>
          );
        })}
      </section>

      <aside
        className={`preview-sheet${previewExpanded ? " is-expanded" : ""}${sheetTransitioning ? " is-transitioning" : ""}`}
        aria-live="polite"
        onClick={handleSheetClick}
        onPointerCancel={() => {
          sheetStartRef.current = null;
        }}
        onPointerDown={handleSheetPointerDown}
        onPointerUp={handleSheetPointerUp}
      >
        <div className="preview-sheet__handle" aria-hidden="true" />
        <div className="preview-sheet__topline">
          <p>{activeCard.band}</p>
          <p>{activeCard.range}</p>
        </div>
        <h1 className="preview-sheet__title">{activeCard.title}</h1>
        <p className="preview-sheet__summary">{activeCard.summary}</p>
        <div className="preview-sheet__grid">
          <div>
            <p className="preview-sheet__label">Kind</p>
            <p>{activeCard.kind}</p>
          </div>
          <div>
            <p className="preview-sheet__label">Thread</p>
            <p>{activeCard.thread}</p>
          </div>
          <div>
            <p className="preview-sheet__label">Status</p>
            <p>{activeCard.status}</p>
          </div>
          <div>
            <p className="preview-sheet__label">Coupling</p>
            <p>{activeCard.coupling}</p>
          </div>
        </div>
      </aside>
    </main>
  );
}
