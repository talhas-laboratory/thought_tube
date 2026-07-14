/**
 * SurfaceProfile slice for thought_capture_pwa — binding: BRIDGE_SECTION.md
 */
export const MOBILE_CAPTURE_SURFACE_PROFILE = {
  surface_id: "mobile_capture",
  artifact_root: "product/thought_capture_pwa/",
  element_key: "frontend",
  holodeck_id: "sol-frontend",
  persistence: "indexeddb_first",
  bridge_writes: ["element_ingest", "session_event"] as const,
  bridge_reads: ["compose_insertion"] as const,
  steering_authority: "none" as const,
} as const;

export type MobileCaptureSurfaceProfile = typeof MOBILE_CAPTURE_SURFACE_PROFILE;

export type DisplayMode = "standalone" | "browser" | "minimal-ui";

export type BridgeSectionProvenance = {
  source: "thought_capture_pwa";
  surface_id: "mobile_capture";
  display_mode: DisplayMode;
  element_key: "frontend";
  holodeck_id: "sol-frontend";
  session_id: string | null;
  local_deposit_id: string;
  client_timestamp: number;
};

export type CaptureSyncPayload = {
  content: string;
  session_id?: string | null;
  provenance: BridgeSectionProvenance;
};

export type CaptureSyncResult = {
  capture_id: string;
  session_id: string;
};

export type SectionFlushResult = {
  synced: number;
  failed: number;
  skipped: number;
};

export type SectionSessionResponse = {
  session_id: string;
};

export type SectionCaptureResponse = {
  capture_id: string;
  session_id: string;
};

export type ComposeIntent = "nudge" | "shape";

export type InsertionPayload = {
  utterance_type: "ack" | "cue" | "mirror" | "sharpen" | "block_cluster";
  body: string;
  blocks?: string[] | null;
  composition_phase: "capture" | "develop";
  mode_state: {
    mode: string;
    response_contract: string;
    ai_presence: number;
    goal_state: string;
    confidence: number;
  };
};

export type SectionComposeRequest = {
  deposit: {
    local_deposit_id: string;
    body: string;
    created_at: number;
  };
  provenance?: BridgeSectionProvenance;
  session_id: string | null;
  capture_mode_state: {
    mode: string;
    response_contract: string;
    ai_presence: number;
    goal_state: string;
    confidence: number;
  };
  intent: ComposeIntent;
  composition_phase: "capture" | "develop";
};

export type SectionComposeResponse = {
  insertion: InsertionPayload | null;
  fallback: boolean;
  reasoning?: {
    request_id: string;
    routing_source: string;
    pipeline_id: string;
    bridge_behavior_ids: string[];
    integration_verdict?: string;
  };
  provenance_refs?: string[];
  composed_at?: string;
  error?: string;
};
