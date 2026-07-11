import Dexie, { type EntityTable } from "dexie";
import type { DepositRecord, InsertionRecord } from "../capture/types";

type MetaRecord = {
  key: string;
  value: string;
};

const DEFAULT_FIELD_ID = "field-initial";

class CaptureDatabase extends Dexie {
  deposits!: EntityTable<DepositRecord, "id">;
  insertions!: EntityTable<InsertionRecord, "id">;
  meta!: EntityTable<MetaRecord, "key">;

  constructor() {
    super("thought_capture_pwa");

    this.version(1).stores({
      deposits: "id, created_at, sync_status",
      insertions: "id, deposit_id, created_at",
      meta: "key",
    });

    this.version(2)
      .stores({
        deposits: "id, created_at, sync_status, field_id",
        insertions: "id, deposit_id, created_at",
        meta: "key",
      })
      .upgrade(async (tx) => {
        await tx
          .table("deposits")
          .toCollection()
          .modify((deposit: DepositRecord) => {
            if (!deposit.field_id) {
              deposit.field_id = DEFAULT_FIELD_ID;
            }
          });
        const meta = tx.table("meta");
        const active = await meta.get("active_field_id");
        if (!active) {
          await meta.put({ key: "active_field_id", value: DEFAULT_FIELD_ID });
        }
      });
  }
}

export const db = new CaptureDatabase();
export { DEFAULT_FIELD_ID };
