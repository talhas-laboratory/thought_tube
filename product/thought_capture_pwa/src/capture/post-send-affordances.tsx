export function PostSendAffordances({
  visible,
  onContinue,
  onNudge,
  onShape,
}: {
  visible: boolean;
  onContinue: () => void;
  onNudge: () => void;
  onShape: () => void;
}) {
  if (!visible) {
    return null;
  }

  return (
    <div className="post-send motion-reveal" data-no-swipe aria-live="polite">
      <span className="post-send__hint">optional</span>
      <button
        type="button"
        className="post-send__chip motion-confirm"
        onClick={onContinue}
      >
        continue
      </button>
      <button
        type="button"
        className="post-send__chip motion-confirm"
        onClick={onNudge}
      >
        nudge
      </button>
      <button
        type="button"
        className="post-send__chip motion-confirm"
        onClick={onShape}
      >
        shape
      </button>
    </div>
  );
}
