import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type RefObject,
} from "react";
import type { CaptureModeState } from "./capture-mode";

function placeholderForMode(mode: CaptureModeState | null): string {
  if (!mode) {
    return "…";
  }
  switch (mode.mode) {
    case "raw_dump":
      return "…";
    case "exploration":
      return "what if…";
    case "clarification":
      return "narrow it…";
    case "emotional_processing":
      return "let it land…";
    case "development":
      return "sketch it…";
    case "task_conversion":
      return "one step…";
    default:
      return "…";
  }
}

export function CaptureDock({
  onDeposit,
  onFocusField,
  disabled,
  modeState,
  keyboardOffset = 0,
  dockRef,
}: {
  onDeposit: (body: string) => Promise<void>;
  onFocusField?: () => void;
  disabled?: boolean;
  modeState?: CaptureModeState | null;
  keyboardOffset?: number;
  dockRef?: RefObject<HTMLElement | null>;
}) {
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [landed, setLanded] = useState(false);
  const fieldRef = useRef<HTMLTextAreaElement>(null);
  const localDockRef = useRef<HTMLElement>(null);
  const resolvedDockRef = dockRef ?? localDockRef;

  const syncFieldHeight = useCallback(() => {
    const field = fieldRef.current;
    if (!field) {
      return;
    }
    field.style.height = "auto";
    const maxHeight = 140;
    field.style.height = `${Math.min(field.scrollHeight, maxHeight)}px`;
  }, []);

  useEffect(() => {
    syncFieldHeight();
  }, [draft, syncFieldHeight]);

  useEffect(() => {
    if (!landed) {
      return;
    }
    const timer = window.setTimeout(() => setLanded(false), 280);
    return () => window.clearTimeout(timer);
  }, [landed]);

  const canDeposit = Boolean(draft.trim()) && !sending && !disabled;
  const composingDisabled = Boolean(disabled) && !sending;

  async function deposit() {
    const trimmed = draft.trim();
    if (!trimmed || sending) {
      return;
    }

    setSending(true);
    try {
      await onDeposit(trimmed);
      setDraft("");
      setLanded(true);
      if (fieldRef.current) {
        fieldRef.current.style.height = "auto";
      }
    } finally {
      setSending(false);
    }
  }

  const dockStyle: CSSProperties = {
    transform: keyboardOffset > 0 ? `translateY(-${keyboardOffset}px)` : undefined,
  };

  return (
    <footer ref={resolvedDockRef} className="capture-dock" style={dockStyle}>
      <div className="capture-dock__atmosphere" aria-hidden="true" />

      <label className="capture-dock__label" htmlFor="capture-draft">
        Deposit
      </label>
      <textarea
        ref={fieldRef}
        id="capture-draft"
        className={`capture-dock__field${landed ? " capture-dock__field--landed" : ""}`}
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        placeholder={placeholderForMode(modeState ?? null)}
        rows={1}
        enterKeyHint="done"
        disabled={disabled || sending}
        onFocus={() => onFocusField?.()}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            void deposit();
          }
        }}
      />

      <div className="capture-dock__action">
        <button
          type="button"
          className={`capture-deposit motion-confirm${canDeposit ? " capture-deposit--ready" : ""}`}
          disabled={!canDeposit}
          onClick={() => void deposit()}
          aria-label="Deposit thought"
        >
          <span className="capture-deposit__label">
            {sending ? "…" : composingDisabled ? "thinking…" : "deposit"}
          </span>
          <span className="capture-deposit__mark" aria-hidden="true">
            →
          </span>
        </button>
      </div>
    </footer>
  );
}

/** @deprecated use CaptureDock */
export const CaptureInput = CaptureDock;
