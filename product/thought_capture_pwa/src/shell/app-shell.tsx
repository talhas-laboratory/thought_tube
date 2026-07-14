import { useEffect, useState, type ReactNode } from "react";
import { applyServiceWorkerUpdate } from "../pwa/register";
import {
  canShowInstallCoach,
  dismissInstallCoach,
  hasDeferredInstallPrompt,
  initInstallPrompt,
  isIosSafari,
  promptAndroidInstall,
} from "../pwa/install-prompt";
import { getDisplayMode } from "../pwa/display-mode";
import { useVisualViewportHeight } from "./viewport";
import { CAPTURE_ROUTE_PATH } from "../meta/meta-routes";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const viewportHeight = useVisualViewportHeight();
  const [showUpdateBanner, setShowUpdateBanner] = useState(false);
  const [showInstallCoach, setShowInstallCoach] = useState(false);

  useEffect(() => {
    initInstallPrompt();

    const onUpdate = () => setShowUpdateBanner(true);
    const onInstall = () => {
      if (canShowInstallCoach()) {
        setShowInstallCoach(true);
      }
    };

    window.addEventListener("pwa:update-available", onUpdate);
    window.addEventListener("pwa:install-available", onInstall);

    if (canShowInstallCoach() && (isIosSafari() || hasDeferredInstallPrompt())) {
      setShowInstallCoach(true);
    }

    return () => {
      window.removeEventListener("pwa:update-available", onUpdate);
      window.removeEventListener("pwa:install-available", onInstall);
    };
  }, []);

  return (
    <div
      className="app-shell"
      data-display-mode={getDisplayMode()}
      style={{ minHeight: viewportHeight ? `${viewportHeight}px` : undefined }}
    >
      {showUpdateBanner ? (
        <div className="app-shell__banner" role="status">
          <span>Update ready — refresh when you&apos;re done.</span>
          <button
            type="button"
            className="app-shell__banner-action motion-confirm"
            onClick={() => void applyServiceWorkerUpdate()}
          >
            Refresh
          </button>
          <button
            type="button"
            className="app-shell__banner-dismiss motion-confirm"
            onClick={() => setShowUpdateBanner(false)}
            aria-label="Dismiss update notice"
          >
            ×
          </button>
        </div>
      ) : null}

      {showInstallCoach ? (
        <div className="app-shell__coach" role="dialog" aria-label="Install app">
          <p className="app-shell__coach-title">Install for instant open and offline capture</p>
          {isIosSafari() ? (
            <p className="app-shell__coach-copy">
              Tap Share, then &ldquo;Add to Home Screen&rdquo;.
            </p>
          ) : (
            <button
              type="button"
              className="app-shell__coach-install motion-confirm"
              onClick={() => void promptAndroidInstall()}
            >
              Install app
            </button>
          )}
          <button
            type="button"
            className="app-shell__coach-dismiss motion-confirm"
            onClick={() => {
              dismissInstallCoach();
              setShowInstallCoach(false);
            }}
          >
            Not now
          </button>
        </div>
      ) : null}

      <div className="app-shell__surface-switch" aria-label="Surface mode">
        <a
          href={CAPTURE_ROUTE_PATH}
          className="app-shell__surface-chip app-shell__surface-chip--active motion-confirm"
        >
          capture
        </a>
      </div>

      <main className="app-shell__main">{children}</main>
    </div>
  );
}
