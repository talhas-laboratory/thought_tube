import { getDisplayMode } from "../pwa/display-mode";
import { getSectionApiBase } from "./config";
import type {
  BridgeSectionProvenance,
  CaptureSyncPayload,
  ComposeIntent,
  SectionCaptureResponse,
  SectionComposeRequest,
  SectionComposeResponse,
  SectionSessionResponse,
} from "./types";

export async function postSectionJson<T>(
  path: string,
  body: unknown,
  options?: { timeoutMs?: number },
): Promise<T> {
  const controller = new AbortController();
  const timeoutMs = options?.timeoutMs ?? 30_000;
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${getSectionApiBase()}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    if (!response.ok) {
      const text = await response.text().catch(() => "");
      throw new Error(text || `Section transport failed (${response.status})`);
    }

    return response.json() as Promise<T>;
  } finally {
    window.clearTimeout(timer);
  }
}

export function buildProvenance(
  localDepositId: string,
  sessionId: string | null,
  clientTimestamp: number,
): BridgeSectionProvenance {
  return {
    source: "thought_capture_pwa",
    surface_id: "mobile_capture",
    display_mode: getDisplayMode() as BridgeSectionProvenance["display_mode"],
    element_key: "frontend",
    holodeck_id: "sol-frontend",
    session_id: sessionId,
    local_deposit_id: localDepositId,
    client_timestamp: clientTimestamp,
  };
}

export function buildCaptureSyncPayload(
  content: string,
  localDepositId: string,
  sessionId: string | null,
  clientTimestamp: number,
): CaptureSyncPayload {
  return {
    content,
    session_id: sessionId,
    provenance: buildProvenance(localDepositId, sessionId, clientTimestamp),
  };
}

export async function transportEnsureSession(
  existingSessionId: string | null = null,
): Promise<string | null> {
  const payload = await postSectionJson<SectionSessionResponse>("/capture/session", {
    session_id: existingSessionId,
    source: "thought_capture_pwa",
    surface_id: "mobile_capture",
  });
  return payload.session_id;
}

export async function transportSyncCapture(
  payload: CaptureSyncPayload,
): Promise<SectionCaptureResponse> {
  return postSectionJson<SectionCaptureResponse>("/capture", payload);
}

export function buildComposePayload(
  deposit: {
    id: string;
    body: string;
    created_at: number;
    session_id?: string;
  },
  sessionId: string | null,
  captureModeState: SectionComposeRequest["capture_mode_state"],
  intent: ComposeIntent,
  compositionPhase: "capture" | "develop",
): SectionComposeRequest {
  return {
    deposit: {
      local_deposit_id: deposit.id,
      body: deposit.body,
      created_at: deposit.created_at,
    },
    provenance: buildProvenance(deposit.id, sessionId, deposit.created_at),
    session_id: sessionId ?? deposit.session_id ?? null,
    capture_mode_state: captureModeState,
    intent,
    composition_phase: compositionPhase,
  };
}

export async function transportComposeInsertion(
  payload: SectionComposeRequest,
): Promise<SectionComposeResponse> {
  if (!payload.session_id) {
    throw new Error("session_id required for compose");
  }
  return postSectionJson<SectionComposeResponse>("/compose", payload, {
    timeoutMs: 60_000,
  });
}
