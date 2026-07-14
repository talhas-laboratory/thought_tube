import type { CaptureModeState } from "./capture-mode";

export type CompositionPhase = "capture" | "develop";

export type UtteranceType =
  | "deposit"
  | "ack"
  | "cue"
  | "mirror"
  | "sharpen"
  | "block_cluster";

export type SyncStatus = "pending" | "synced" | "failed";

export interface DepositRecord {
  id: string;
  body: string;
  created_at: number;
  sync_status: SyncStatus;
  remote_capture_id?: string;
  session_id?: string;
  field_id?: string;
}

export interface InsertionRecord {
  id: string;
  deposit_id: string;
  utterance_type: UtteranceType;
  body: string;
  blocks?: string[];
  composition_phase: CompositionPhase;
  created_at: number;
  mode_state?: CaptureModeState;
}

export type CompositionUnit = {
  deposit: DepositRecord;
  insertion?: InsertionRecord;
};

export type LibrarySectionId = "now" | "still_moving" | "resting";

export type LibrarySection = {
  id: LibrarySectionId;
  label: string;
  units: CompositionUnit[];
};

export type UnitBrowseState = "open" | "waiting" | "shaped";

export type SurfacePane = "capture" | "overview";
