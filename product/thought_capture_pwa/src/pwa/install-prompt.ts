import { isStandaloneDisplay } from "./display-mode";

const DISMISS_KEY = "capture_pwa_install_dismissed_at";
const DISMISS_DAYS = 7;

export type InstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

let deferredPrompt: InstallPromptEvent | null = null;

export function initInstallPrompt(): void {
  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    deferredPrompt = event as InstallPromptEvent;
    window.dispatchEvent(new CustomEvent("pwa:install-available"));
  });

  window.addEventListener("appinstalled", () => {
    deferredPrompt = null;
    localStorage.setItem(DISMISS_KEY, String(Date.now()));
  });
}

export function canShowInstallCoach(): boolean {
  if (isStandaloneDisplay()) {
    return false;
  }

  const dismissedAt = Number(localStorage.getItem(DISMISS_KEY) ?? "0");
  if (!dismissedAt) {
    return true;
  }

  const elapsed = Date.now() - dismissedAt;
  return elapsed > DISMISS_DAYS * 24 * 60 * 60 * 1000;
}

export function dismissInstallCoach(): void {
  localStorage.setItem(DISMISS_KEY, String(Date.now()));
}

export async function promptAndroidInstall(): Promise<"accepted" | "dismissed" | "unavailable"> {
  if (!deferredPrompt) {
    return "unavailable";
  }

  await deferredPrompt.prompt();
  const { outcome } = await deferredPrompt.userChoice;
  if (outcome === "accepted") {
    deferredPrompt = null;
  }
  return outcome;
}

export function isIosSafari(): boolean {
  return /iphone|ipad|ipod/i.test(navigator.userAgent);
}

export function hasDeferredInstallPrompt(): boolean {
  return deferredPrompt !== null;
}
