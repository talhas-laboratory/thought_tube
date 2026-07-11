import { useCallback, useEffect, useState } from "react";
import type { CaptureModeState } from "./capture-mode";
import {
  capPresenceForCapture,
  classifyInput,
  resolveModeState,
  shouldRequestAssistantResponse,
} from "./capture-mode";
import { buildLocalInsertion } from "./local-composer";
import { bootstrapFromRemoteFeedIfEmpty } from "./remote-bootstrap";
import type { CompositionUnit } from "./types";
import { publishCaptureModeState } from "../bridge/capture-mode-hook";
import {
  isSectionComposeEnabled,
  requestInsertion,
} from "../bridge";
import {
  activateFieldForDeposit,
  createDeposit,
  getFocusDepositId,
  listAllCompositionUnits,
  listCompositionUnits,
  removeInsertion,
  setFocusDepositId,
  startNewField,
  upsertInsertion,
} from "../offline/deposit-store";
import { flushPendingDeposits, initSyncReplay } from "../offline/sync-replay";

function depositBodies(units: CompositionUnit[]): { body: string }[] {
  return units.map((unit) => ({ body: unit.deposit.body }));
}

export function useCaptureStream() {
  const [fieldUnits, setFieldUnits] = useState<CompositionUnit[]>([]);
  const [libraryUnits, setLibraryUnits] = useState<CompositionUnit[]>([]);
  const [focusId, setFocusId] = useState<string>("");
  const [modeState, setModeState] = useState<CaptureModeState | null>(null);
  const [composingDepositId, setComposingDepositId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const nextFieldUnits = await listCompositionUnits();
    const nextLibraryUnits = await listAllCompositionUnits();
    setFieldUnits(nextFieldUnits);
    setLibraryUnits(nextLibraryUnits);

    const storedFocus = await getFocusDepositId();
    const resolvedFocus =
      storedFocus && nextFieldUnits.some((u) => u.deposit.id === storedFocus)
        ? storedFocus
        : nextFieldUnits[nextFieldUnits.length - 1]?.deposit.id ?? "";

    setFocusId(resolvedFocus);
    if (resolvedFocus) {
      await setFocusDepositId(resolvedFocus);
      const focusUnit = nextFieldUnits.find((u) => u.deposit.id === resolvedFocus);
      setModeState(
        focusUnit?.insertion?.mode_state ??
          (focusUnit ? classifyInput(focusUnit.deposit.body) : null),
      );
    } else {
      setModeState(null);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    void bootstrapFromRemoteFeedIfEmpty().finally(() => {
      void refresh();
    });
    const stopSync = initSyncReplay(() => {
      void refresh();
    });
    return stopSync;
  }, [refresh]);

  const upsertFromRemote = useCallback(
    async (depositId: string, remote: NonNullable<Awaited<ReturnType<typeof requestInsertion>>>) => {
      await upsertInsertion(depositId, {
        utterance_type: remote.utterance_type,
        body: remote.body,
        blocks: remote.blocks ?? undefined,
        composition_phase: remote.composition_phase,
        mode_state: {
          mode: remote.mode_state.mode as CaptureModeState["mode"],
          response_contract:
            remote.mode_state.response_contract as CaptureModeState["response_contract"],
          ai_presence: remote.mode_state.ai_presence as CaptureModeState["ai_presence"],
          goal_state: remote.mode_state.goal_state as CaptureModeState["goal_state"],
          confidence: remote.mode_state.confidence,
        },
      });
    },
    [],
  );

  const applyComposition = useCallback(
    async (
      depositId: string,
      state: CaptureModeState,
      phase: "capture" | "develop",
      intent: "nudge" | "shape",
      options: { allowLocalFallback?: boolean } = {},
    ) => {
      const { allowLocalFallback = true } = options;
      const latestUnits = await listCompositionUnits();
      const unit = latestUnits.find((u) => u.deposit.id === depositId);
      if (!unit) {
        return;
      }

      await publishCaptureModeState(depositId, state);
      setModeState(state);
      setComposingDepositId(depositId);

      try {
        if (isSectionComposeEnabled() && navigator.onLine) {
          await flushPendingDeposits();
          const syncedUnit =
            (await listCompositionUnits()).find((u) => u.deposit.id === depositId) ?? unit;
          const remote = await requestInsertion(syncedUnit.deposit, intent, state, phase);
          if (remote) {
            await upsertFromRemote(depositId, remote);
            return;
          }
        }

        if (!allowLocalFallback) {
          return;
        }

        const built = buildLocalInsertion(
          state,
          unit.deposit.body,
          depositBodies(latestUnits),
          phase,
          "invited",
        );

        if (built.skip) {
          await removeInsertion(depositId);
        } else {
          await upsertInsertion(depositId, {
            utterance_type: built.utterance_type,
            body: built.body,
            blocks: built.blocks,
            composition_phase: built.composition_phase,
            mode_state: built.mode_state,
          });
        }
      } finally {
        setComposingDepositId(null);
        await refresh();
      }
    },
    [refresh, upsertFromRemote],
  );

  const autoComposeAfterDeposit = useCallback(
    async (depositId: string, body: string) => {
      const state = capPresenceForCapture(classifyInput(body));
      if (!shouldRequestAssistantResponse(state)) {
        return;
      }
      await applyComposition(depositId, state, "capture", "nudge", {
        allowLocalFallback: !isSectionComposeEnabled(),
      });
    },
    [applyComposition],
  );

  const deposit = useCallback(
    async (body: string) => {
      const record = await createDeposit(body);
      const state = classifyInput(body);
      await publishCaptureModeState(record.id, state);
      setModeState(state);
      await setFocusDepositId(record.id);
      setFocusId(record.id);
      await refresh();
      void flushPendingDeposits()
        .then(() => refresh())
        .then(() => autoComposeAfterDeposit(record.id, body));
      return record;
    },
    [autoComposeAfterDeposit, refresh],
  );

  const selectUnit = useCallback(
    async (depositId: string) => {
      await activateFieldForDeposit(depositId);
      await setFocusDepositId(depositId);
      setFocusId(depositId);
      const unit =
        libraryUnits.find((u) => u.deposit.id === depositId) ??
        fieldUnits.find((u) => u.deposit.id === depositId);
      if (unit) {
        setModeState(
          unit.insertion?.mode_state ?? classifyInput(unit.deposit.body),
        );
      }
      await refresh();
    },
    [fieldUnits, libraryUnits, refresh],
  );

  const beginNewField = useCallback(async () => {
    await startNewField();
    setFocusId("");
    setModeState(null);
    await refresh();
  }, [refresh]);

  const nudge = useCallback(
    async (depositId: string) => {
      const unit = fieldUnits.find((u) => u.deposit.id === depositId);
      if (!unit) {
        return;
      }
      const state = capPresenceForCapture(classifyInput(unit.deposit.body));
      await applyComposition(depositId, state, "capture", "nudge");
    },
    [applyComposition, fieldUnits],
  );

  const shape = useCallback(
    async (depositId: string) => {
      const unit = fieldUnits.find((u) => u.deposit.id === depositId);
      if (!unit) {
        return;
      }
      const state = resolveModeState(unit.deposit.body, {
        mode: "development",
        contract: "structural_extraction",
      });
      await applyComposition(depositId, state, "develop", "shape");
    },
    [applyComposition, fieldUnits],
  );

  return {
    fieldUnits,
    libraryUnits,
    focusId,
    modeState,
    composingDepositId,
    loading,
    deposit,
    selectUnit,
    beginNewField,
    nudge,
    shape,
    refresh,
  };
}
