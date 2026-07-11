import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type RefObject,
} from "react";
import {
  applyInstantAnchor,
  applyJumpToLatest,
  applyPreserveAnchorOnResize,
  getScrollUnitElement,
  isWithinLiveEdge,
  measureDistanceFromLiveEdge,
  reduceScrollState,
  shouldShowOffscreenIndicator,
} from "./scroll-engine";
import {
  emitScrollIntent,
  shouldDetachOnIntent,
  subscribeScrollIntent,
} from "./scroll-intent-bus";
import {
  createInitialScrollState,
  SCROLL_DEFAULTS,
  type ScrollEngineState,
  type ScrollFollowState,
  type ScrollIntentSignal,
} from "./scroll-types";

export type UseScrollEngineOptions = {
  units: Array<{ deposit: { id: string } }>;
  focusDepositId: string;
  enabled?: boolean;
};

export type UseScrollEngineResult = {
  containerRef: RefObject<HTMLDivElement | null>;
  liveEdgeRef: RefObject<HTMLDivElement | null>;
  state: ScrollEngineState;
  followState: ScrollFollowState;
  showJumpLatest: boolean;
  signalIntent: (signal: ScrollIntentSignal, detail?: unknown) => void;
  jumpToLatest: () => void;
  onContainerScroll: () => void;
  anchorNewUserTurn: (depositId: string) => void;
  reopenAtDeposit: (depositId: string) => void;
  onStreamGrowth: () => void;
};

export function useScrollEngine({
  units,
  focusDepositId,
  enabled = true,
}: UseScrollEngineOptions): UseScrollEngineResult {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const liveEdgeRef = useRef<HTMLDivElement | null>(null);
  const [state, setState] = useState<ScrollEngineState>(createInitialScrollState);
  const [showJumpLatest, setShowJumpLatest] = useState(false);

  const stateRef = useRef(state);
  stateRef.current = state;

  const lastDepositIdRef = useRef<string | null>(null);
  const reopenTargetRef = useRef<string | null>(null);
  const anchorTopRef = useRef<number | null>(null);

  const dispatch = useCallback((action: Parameters<typeof reduceScrollState>[1]) => {
    setState((prev) => reduceScrollState(prev, action));
  }, []);

  const refreshIndicator = useCallback(() => {
    const container = containerRef.current;
    if (!container) {
      setShowJumpLatest(false);
      return;
    }
    const distance = measureDistanceFromLiveEdge(container);
    setShowJumpLatest(
      shouldShowOffscreenIndicator(
        stateRef.current.follow_state,
        distance,
        stateRef.current.live_edge_threshold_px,
      ),
    );
  }, []);

  const signalIntent = useCallback(
    (signal: ScrollIntentSignal, detail?: unknown) => {
      emitScrollIntent(signal, detail);
      if (shouldDetachOnIntent(signal)) {
        dispatch({ type: "intent_detach" });
      }
      refreshIndicator();
    },
    [dispatch, refreshIndicator],
  );

  const jumpToLatest = useCallback(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }
    applyJumpToLatest(container);
    dispatch({ type: "jump_latest" });
    refreshIndicator();
  }, [dispatch, refreshIndicator]);

  const anchorDeposit = useCallback((depositId: string) => {
    const container = containerRef.current;
    if (!container) {
      return;
    }
    const anchor = getScrollUnitElement(container, depositId);
    if (!anchor) {
      return;
    }
    applyInstantAnchor(container, anchor, SCROLL_DEFAULTS.ANCHOR_TOP_PADDING_PX);
    anchorTopRef.current = anchor.getBoundingClientRect().top;
    dispatch({ type: "set_last_user_turn", turnId: depositId });
    refreshIndicator();
  }, [dispatch, refreshIndicator]);

  const anchorNewUserTurn = useCallback(
    (depositId: string) => {
      if (stateRef.current.follow_state !== "following") {
        dispatch({ type: "set_last_user_turn", turnId: depositId });
        refreshIndicator();
        return;
      }
      anchorDeposit(depositId);
    },
    [anchorDeposit, dispatch, refreshIndicator],
  );

  const reopenAtDeposit = useCallback(
    (depositId: string) => {
      reopenTargetRef.current = depositId;
      dispatch({ type: "intent_detach" });
      signalIntent("tap-message", { depositId });
    },
    [dispatch, signalIntent],
  );

  const onContainerScroll = useCallback(() => {
    const container = containerRef.current;
    if (!container || !enabled) {
      return;
    }

    if (isWithinLiveEdge(container, stateRef.current.live_edge_threshold_px)) {
      dispatch({ type: "at_live_edge" });
    } else if (stateRef.current.follow_state === "following") {
      dispatch({ type: "intent_detach" });
    }

    refreshIndicator();
  }, [dispatch, enabled, refreshIndicator, signalIntent]);

  const onStreamGrowth = useCallback(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    if (stateRef.current.follow_state === "following") {
      applyJumpToLatest(container);
    } else {
      refreshIndicator();
    }
  }, [refreshIndicator]);

  useEffect(() => {
    if (!enabled) {
      return;
    }
    return subscribeScrollIntent((signal) => {
      if (shouldDetachOnIntent(signal)) {
        dispatch({ type: "intent_detach" });
        refreshIndicator();
      }
    });
  }, [dispatch, enabled, refreshIndicator]);

  useEffect(() => {
    const onSelectionChange = () => {
      const selection = document.getSelection();
      const container = containerRef.current;
      if (!selection || selection.isCollapsed || !container) {
        return;
      }
      const anchorNode = selection.anchorNode;
      if (anchorNode && container.contains(anchorNode)) {
        signalIntent("select");
      }
    };

    document.addEventListener("selectionchange", onSelectionChange);
    return () => {
      document.removeEventListener("selectionchange", onSelectionChange);
    };
  }, [signalIntent]);

  useEffect(() => {
    if (!enabled || units.length === 0) {
      return;
    }

    const lastId = units[units.length - 1]?.deposit.id;
    if (!lastId) {
      return;
    }

    if (!lastDepositIdRef.current) {
      requestAnimationFrame(() => {
        jumpToLatest();
      });
    } else if (lastDepositIdRef.current !== lastId) {
      anchorNewUserTurn(lastId);
    }

    lastDepositIdRef.current = lastId;
  }, [units, enabled, anchorNewUserTurn, jumpToLatest]);

  useEffect(() => {
    if (!enabled || !focusDepositId) {
      return;
    }

    if (reopenTargetRef.current === focusDepositId) {
      requestAnimationFrame(() => {
        anchorDeposit(focusDepositId);
        reopenTargetRef.current = null;
      });
    }
  }, [focusDepositId, enabled, anchorDeposit]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !enabled || !focusDepositId) {
      return;
    }

    const anchor = getScrollUnitElement(container, focusDepositId);
    if (!anchor) {
      return;
    }

    const observer = new ResizeObserver(() => {
      if (anchorTopRef.current === null) {
        anchorTopRef.current = anchor.getBoundingClientRect().top;
        return;
      }
      anchorTopRef.current = applyPreserveAnchorOnResize(
        container,
        anchor,
        anchorTopRef.current,
      );
    });

    observer.observe(anchor);
    for (const child of anchor.querySelectorAll("[data-scroll-resize]")) {
      observer.observe(child);
    }

    return () => {
      observer.disconnect();
    };
  }, [units, focusDepositId, enabled]);

  useEffect(() => {
    onStreamGrowth();
  }, [units, onStreamGrowth]);

  return {
    containerRef,
    liveEdgeRef,
    state,
    followState: state.follow_state,
    showJumpLatest,
    signalIntent,
    jumpToLatest,
    onContainerScroll,
    anchorNewUserTurn,
    reopenAtDeposit,
    onStreamGrowth,
  };
}
