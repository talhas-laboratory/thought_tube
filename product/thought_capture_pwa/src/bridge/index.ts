export type {
  BridgeSectionProvenance,
  CaptureSyncPayload,
  CaptureSyncResult,
  ComposeIntent,
  InsertionPayload,
  MobileCaptureSurfaceProfile,
  SectionFlushResult,
} from "./types";

export {
  flushDepositsToBridge,
  ensureSectionSession,
  getSurfaceProfileSnapshot,
  isSectionComposeEnabled,
  isSectionSyncEnabled,
  requestInsertion,
  syncDepositToBridge,
} from "./section-adapter";

export { getSurfaceProfile } from "./config";

export { buildProvenance, buildCaptureSyncPayload } from "./transport";

export type { CaptureModeStateEnvelope } from "./capture-mode-hook";
export {
  publishCaptureModeState,
  readLatestCaptureModeState,
} from "./capture-mode-hook";
