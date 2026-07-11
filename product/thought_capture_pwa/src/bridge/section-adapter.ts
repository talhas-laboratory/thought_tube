import type { DepositRecord } from "../capture/types";
import type { CaptureModeState } from "../capture/capture-mode";
import { getMeta, setMeta } from "../offline/deposit-store";
import { getSurfaceProfile, isSectionComposeEnabled, isSectionSyncEnabled } from "./config";
import {
  buildCaptureSyncPayload,
  buildComposePayload,
  transportComposeInsertion,
  transportEnsureSession,
  transportSyncCapture,
} from "./transport";
import type {
  CaptureSyncResult,
  ComposeIntent,
  InsertionPayload,
  MobileCaptureSurfaceProfile,
  SectionFlushResult,
} from "./types";

export { getSurfaceProfile, isSectionComposeEnabled, isSectionSyncEnabled };

export function getSurfaceProfileSnapshot(): MobileCaptureSurfaceProfile {
  return getSurfaceProfile();
}

export async function ensureSectionSession(): Promise<string | null> {
  if (!isSectionSyncEnabled() || !navigator.onLine) {
    return (await getMeta("session_id")) ?? null;
  }

    const cached = await getMeta("session_id");
    if (cached) {
      return cached;
    }

    try {
      const sessionId = await transportEnsureSession(null);
    if (sessionId) {
      await setMeta("session_id", sessionId);
    }
    return sessionId;
  } catch {
    return null;
  }
}

/**
 * Outbound capture sync — read-only toward bridge control plane.
 * Dexie remains authoritative; bridge ack is optional durability.
 */
export async function syncDepositToBridge(
  deposit: DepositRecord,
): Promise<CaptureSyncResult | null> {
  if (!isSectionSyncEnabled() || !navigator.onLine) {
    return null;
  }

  const sessionId = deposit.session_id ?? (await ensureSectionSession());
  const payload = buildCaptureSyncPayload(
    deposit.body,
    deposit.id,
    sessionId,
    deposit.created_at,
  );

  try {
    const result = await transportSyncCapture(payload);
    if (result.session_id) {
      await setMeta("session_id", result.session_id);
    }
    return result;
  } catch {
    return null;
  }
}

function captureModeStateForRequest(
  state: CaptureModeState,
): InsertionPayload["mode_state"] {
  return {
    mode: state.mode,
    response_contract: state.response_contract,
    ai_presence: state.ai_presence,
    goal_state: state.goal_state,
    confidence: state.confidence,
  };
}

/**
 * Invited assist only (nudge / shape). Server runs bridge compose and returns
 * a coupled insertion payload. Dexie remains authoritative on failure.
 */
export async function requestInsertion(
  deposit: DepositRecord,
  intent: ComposeIntent,
  modeState: CaptureModeState,
  compositionPhase: "capture" | "develop",
): Promise<InsertionPayload | null> {
  if (!isSectionComposeEnabled() || !navigator.onLine) {
    return null;
  }

  let sessionId = deposit.session_id ?? (await getMeta("session_id")) ?? null;
  if (!sessionId) {
    sessionId = await ensureSectionSession();
  }
  if (!sessionId && isSectionSyncEnabled()) {
    const ack = await syncDepositToBridge(deposit);
    sessionId = ack?.session_id ?? null;
  }
  if (!sessionId) {
    return null;
  }

  const payload = buildComposePayload(
    deposit,
    sessionId,
    captureModeStateForRequest(modeState),
    intent,
    compositionPhase,
  );

  try {
    const result = await transportComposeInsertion(payload);
    if (result.insertion && !result.fallback) {
      return result.insertion;
    }
    return null;
  } catch {
    return null;
  }
}

export async function flushDepositsToBridge(
  deposits: DepositRecord[],
): Promise<SectionFlushResult> {
  const result: SectionFlushResult = { synced: 0, failed: 0, skipped: 0 };

  if (!isSectionSyncEnabled() || !navigator.onLine || deposits.length === 0) {
    result.skipped = deposits.length;
    return result;
  }

  await ensureSectionSession();

  for (const deposit of deposits) {
    const ack = await syncDepositToBridge(deposit);
    if (!ack) {
      result.failed += 1;
      continue;
    }
    result.synced += 1;
  }

  return result;
}
