import type { CaptureModeState } from "../capture/capture-mode";
import { getMeta, setMeta } from "../offline/deposit-store";

export type CaptureModeStateEnvelope = {
  deposit_id: string;
  state: CaptureModeState;
  emitted_at: number;
};

const META_KEY = "latest_capture_mode_state";

/**
 * Hook point for bridge `capture_mode_state` emission.
 * Persists latest envelope locally; outbound bridge wire-up is MTC-006+.
 */
export async function publishCaptureModeState(
  depositId: string,
  state: CaptureModeState,
): Promise<CaptureModeStateEnvelope> {
  const envelope: CaptureModeStateEnvelope = {
    deposit_id: depositId,
    state,
    emitted_at: Date.now(),
  };
  await setMeta(META_KEY, JSON.stringify(envelope));
  return envelope;
}

export async function readLatestCaptureModeState(): Promise<CaptureModeStateEnvelope | null> {
  const raw = await getMeta(META_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as CaptureModeStateEnvelope;
  } catch {
    return null;
  }
}
