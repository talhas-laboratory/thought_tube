import type { ScrollIntentSignal } from "./scroll-types";

export type ScrollIntentListener = (
  signal: ScrollIntentSignal,
  detail?: unknown,
) => void;

const listeners = new Set<ScrollIntentListener>();

export function emitScrollIntent(
  signal: ScrollIntentSignal,
  detail?: unknown,
): void {
  for (const listener of listeners) {
    listener(signal, detail);
  }
}

export function subscribeScrollIntent(
  listener: ScrollIntentListener,
): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export const DETACH_INTENT_SIGNALS: ReadonlySet<ScrollIntentSignal> = new Set([
  "scroll",
  "select",
  "type",
  "keyboard",
  "link",
  "search",
  "expand",
  "tap-message",
  "media",
  "regenerate",
  "error",
]);

export function shouldDetachOnIntent(signal: ScrollIntentSignal): boolean {
  return DETACH_INTENT_SIGNALS.has(signal);
}
