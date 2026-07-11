import {
  ensureSectionSession,
  isSectionSyncEnabled,
  syncDepositToBridge,
} from "../bridge";
import {
  listPendingDeposits,
  setMeta,
  updateDepositSync,
} from "./deposit-store";

let flushing = false;

export async function flushPendingDeposits(): Promise<number> {
  if (flushing || !navigator.onLine || !isSectionSyncEnabled()) {
    return 0;
  }

  flushing = true;
  let synced = 0;

  try {
    await ensureSectionSession();
    const pending = await listPendingDeposits();

    for (const deposit of pending) {
      const ack = await syncDepositToBridge(deposit);
      if (ack) {
        await updateDepositSync(deposit.id, {
          sync_status: "synced",
          remote_capture_id: ack.capture_id,
          session_id: ack.session_id,
        });
        await setMeta("session_id", ack.session_id);
        synced += 1;
        continue;
      }

      await updateDepositSync(deposit.id, { sync_status: "failed" });
    }
  } finally {
    flushing = false;
  }

  return synced;
}

export function initSyncReplay(onFlushed?: () => void): () => void {
  const run = () => {
    void flushPendingDeposits().then((count) => {
      if (count > 0) {
        onFlushed?.();
      }
    });
  };

  window.addEventListener("online", run);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      run();
    }
  });

  run();

  return () => {
    window.removeEventListener("online", run);
  };
}
