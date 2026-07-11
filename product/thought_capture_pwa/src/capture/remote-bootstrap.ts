import { db, DEFAULT_FIELD_ID } from "../offline/db";
import { getMeta, setActiveFieldId, setFocusDepositId, setMeta } from "../offline/deposit-store";
import type { CompositionUnit, DepositRecord, InsertionRecord } from "./types";

const REMOTE_BOOTSTRAP_META_KEY = "remote_bootstrap_feed_v1";
const REMOTE_BOOTSTRAP_FIELD_ID = "field-remote-bootstrap";
const REMOTE_BOOTSTRAP_LIMIT = 6;

export interface MobileFeedItem {
  thought_id?: string;
  insight_id?: string;
  title?: string;
  summary?: string;
}

export interface MobileFeedPayload {
  items?: MobileFeedItem[];
}

function stableRemoteId(item: MobileFeedItem, index: number): string {
  return item.insight_id || item.thought_id || `remote-feed-${index}`;
}

function bootstrapBody(item: MobileFeedItem): string {
  const title = (item.title || "").trim();
  const summary = (item.summary || "").trim();
  return title || summary || "Untitled thought";
}

export function buildBootstrapCompositionUnits(
  payload: MobileFeedPayload,
  now = Date.now(),
): CompositionUnit[] {
  const items = Array.isArray(payload.items) ? payload.items.slice(0, REMOTE_BOOTSTRAP_LIMIT) : [];
  return items.map((item, index) => {
    const remoteId = stableRemoteId(item, index);
    const summary = (item.summary || "").trim();
    const deposit: DepositRecord = {
      id: `remote-deposit-${remoteId}`,
      body: bootstrapBody(item),
      created_at: now - (items.length - index) * 1_000,
      sync_status: "synced",
      remote_capture_id: item.thought_id || item.insight_id || remoteId,
      field_id: REMOTE_BOOTSTRAP_FIELD_ID,
    };
    const insertion: InsertionRecord | undefined = summary && summary !== deposit.body
      ? {
          id: `remote-insertion-${remoteId}`,
          deposit_id: deposit.id,
          utterance_type: "mirror",
          body: summary,
          composition_phase: "capture",
          created_at: deposit.created_at,
        }
      : undefined;
    return { deposit, insertion };
  });
}

async function fetchRemoteFeed(): Promise<MobileFeedPayload | null> {
  const response = await fetch("/api/mobile/feed", {
    method: "GET",
    credentials: "include",
  });
  if (!response.ok) {
    return null;
  }
  return response.json() as Promise<MobileFeedPayload>;
}

export async function bootstrapFromRemoteFeedIfEmpty(): Promise<boolean> {
  const existingBootstrap = await getMeta(REMOTE_BOOTSTRAP_META_KEY);
  if (existingBootstrap) {
    return false;
  }

  const existingDeposits = await db.deposits.count();
  if (existingDeposits > 0) {
    await setMeta(REMOTE_BOOTSTRAP_META_KEY, "skipped-nonempty");
    return false;
  }

  let payload: MobileFeedPayload | null = null;
  try {
    payload = await fetchRemoteFeed();
  } catch {
    return false;
  }
  if (!payload) {
    return false;
  }

  const units = buildBootstrapCompositionUnits(payload);
  if (units.length === 0) {
    await setMeta(REMOTE_BOOTSTRAP_META_KEY, "empty");
    return false;
  }

  await db.transaction("rw", db.deposits, db.insertions, db.meta, async () => {
    await db.deposits.bulkPut(units.map((unit) => unit.deposit));
    await db.insertions.bulkPut(units.flatMap((unit) => (unit.insertion ? [unit.insertion] : [])));
    await setMeta(REMOTE_BOOTSTRAP_META_KEY, "done");
    await setActiveFieldId(REMOTE_BOOTSTRAP_FIELD_ID || DEFAULT_FIELD_ID);
    await setFocusDepositId(units[units.length - 1]?.deposit.id || "");
  });
  return true;
}

