import type { CaptureModeState } from "./capture-mode";

export function isCaptureModeDebugEnabled(): boolean {
  return (
    import.meta.env.DEV && import.meta.env.VITE_CAPTURE_MODE_DEBUG === "true"
  );
}

export function CaptureModeDebug({
  state,
}: {
  state: CaptureModeState | null;
}) {
  if (!isCaptureModeDebugEnabled()) {
    return null;
  }

  if (!state) {
    return (
      <span className="capture-mode-debug" aria-label="Capture mode state">
        mode —
      </span>
    );
  }

  const summary = `${state.mode} · p${state.ai_presence}`;

  return (
    <span
      className="capture-mode-debug"
      aria-label="Capture mode state"
      title={`${state.mode} · ${state.response_contract} · presence ${state.ai_presence} · conf ${state.confidence.toFixed(2)}`}
    >
      {summary}
    </span>
  );
}
