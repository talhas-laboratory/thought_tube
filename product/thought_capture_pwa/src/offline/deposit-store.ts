import type {
  CompositionUnit,
  DepositRecord,
  InsertionRecord,
  SyncStatus,
} from "../capture/types";
import { db, DEFAULT_FIELD_ID } from "./db";

function makeId(prefix: string): string {
  return `${prefix}-${crypto.randomUUID().slice(0, 8)}`;
}

export async function getMeta(key: string): Promise<string | undefined> {
  const row = await db.meta.get(key);
  return row?.value;
}

export async function setMeta(key: string, value: string): Promise<void> {
  await db.meta.put({ key, value });
}

export async function getActiveFieldId(): Promise<string> {
  const stored = await getMeta("active_field_id");
  if (stored) {
    return stored;
  }
  await setMeta("active_field_id", DEFAULT_FIELD_ID);
  return DEFAULT_FIELD_ID;
}

export async function setActiveFieldId(fieldId: string): Promise<void> {
  await setMeta("active_field_id", fieldId);
}

export async function listAllCompositionUnits(): Promise<CompositionUnit[]> {
  const deposits = await db.deposits.orderBy("created_at").toArray();
  const insertions = await db.insertions.toArray();
  const byDeposit = new Map<string, InsertionRecord>();

  for (const insertion of insertions) {
    byDeposit.set(insertion.deposit_id, insertion);
  }

  return deposits.map((deposit) => ({
    deposit,
    insertion: byDeposit.get(deposit.id),
  }));
}

export async function listCompositionUnits(fieldId?: string): Promise<CompositionUnit[]> {
  const activeFieldId = fieldId ?? (await getActiveFieldId());
  const all = await listAllCompositionUnits();
  return all.filter((unit) => (unit.deposit.field_id ?? DEFAULT_FIELD_ID) === activeFieldId);
}

export async function startNewField(): Promise<string> {
  const fieldId = makeId("field");
  await setActiveFieldId(fieldId);
  await setMeta("session_id", "");
  await setFocusDepositId("");
  return fieldId;
}

export async function activateFieldForDeposit(depositId: string): Promise<void> {
  const deposit = await db.deposits.get(depositId);
  if (!deposit?.field_id) {
    return;
  }
  await setActiveFieldId(deposit.field_id);
  if (deposit.session_id) {
    await setMeta("session_id", deposit.session_id);
  }
}

export async function createDeposit(body: string): Promise<DepositRecord> {
  const trimmed = body.trim();
  if (!trimmed) {
    throw new Error("deposit body is required");
  }

  const sessionId = await getMeta("session_id");
  const fieldId = await getActiveFieldId();
  const record: DepositRecord = {
    id: makeId("t"),
    body: trimmed,
    created_at: Date.now(),
    sync_status: "pending",
    session_id: sessionId,
    field_id: fieldId,
  };

  await db.deposits.add(record);
  return record;
}

export async function updateDepositSync(
  id: string,
  patch: { sync_status: SyncStatus; remote_capture_id?: string; session_id?: string },
): Promise<void> {
  await db.deposits.update(id, patch);
}

export async function listPendingDeposits(): Promise<DepositRecord[]> {
  return db.deposits.where("sync_status").equals("pending").sortBy("created_at");
}

export async function upsertInsertion(
  depositId: string,
  insertion: Omit<InsertionRecord, "id" | "created_at" | "deposit_id">,
): Promise<InsertionRecord> {
  const existing = await db.insertions.where("deposit_id").equals(depositId).first();
  const record: InsertionRecord = {
    id: existing?.id ?? makeId("i"),
    deposit_id: depositId,
    created_at: existing?.created_at ?? Date.now(),
    ...insertion,
  };

  await db.insertions.put(record);
  return record;
}

export async function removeInsertion(depositId: string): Promise<void> {
  await db.insertions.where("deposit_id").equals(depositId).delete();
}

export async function getFocusDepositId(): Promise<string | undefined> {
  return getMeta("focus_deposit_id");
}

export async function setFocusDepositId(id: string): Promise<void> {
  await setMeta("focus_deposit_id", id);
}
