export function isStandaloneDisplay(): boolean {
  if (window.matchMedia("(display-mode: standalone)").matches) {
    return true;
  }

  const nav = navigator as Navigator & { standalone?: boolean };
  return Boolean(nav.standalone);
}

export function getDisplayMode(): string {
  if (isStandaloneDisplay()) {
    return "standalone";
  }
  return window.matchMedia("(display-mode: browser)").matches ? "browser" : "minimal-ui";
}
