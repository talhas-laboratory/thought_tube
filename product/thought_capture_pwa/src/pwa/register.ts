import { registerSW } from "virtual:pwa-register";

let updateSW: ((reloadPage?: boolean) => Promise<void>) | undefined;

export function registerServiceWorker(): void {
  updateSW = registerSW({
    immediate: true,
    onNeedRefresh() {
      window.dispatchEvent(new CustomEvent("pwa:update-available"));
    },
    onOfflineReady() {
      window.dispatchEvent(new CustomEvent("pwa:offline-ready"));
    },
  });
}

export async function applyServiceWorkerUpdate(): Promise<void> {
  if (updateSW) {
    await updateSW(true);
  }
}
