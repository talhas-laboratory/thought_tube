import "./meta.css";

export function MetaPage() {
  return (
    <div className="meta-page">
      <div className="meta-page__vignette" aria-hidden="true" />
      <div className="meta-page__body">
        <div className="meta-page__header">
          <p className="meta-page__eyebrow">transition</p>
          <h1 className="meta-page__title">System editing moved</h1>
          <p className="meta-page__copy">
            Product and agent adjustments now run through the Telegram meta agent on OpenClaw.
          </p>
        </div>
        <div className="meta-page__status" role="status">
          <p className="meta-page__status-title">Telegram meta agent</p>
          <p className="meta-page__status-copy">
            Use <code>/meta</code> to discuss a change and <code>/change</code> to create governed work with tests,
            release gates, and rollback requirements.
          </p>
          <p className="meta-page__status-copy">
            The notes surface remains focused on capture and assistant replies.
          </p>
        </div>
      </div>
    </div>
  );
}
