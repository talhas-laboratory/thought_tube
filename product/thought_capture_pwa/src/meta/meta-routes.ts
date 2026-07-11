export const CAPTURE_ROUTE_PATH = "/capture";
export const META_ROUTE_PATH = "/meta";

export function buildMetaConsoleUrl(apiBase: string): string {
  const normalized = apiBase.trim().replace(/\/$/, "") || "/api";
  const rootBase = normalized.endsWith("/mobile")
    ? normalized.slice(0, -"/mobile".length) || "/api"
    : normalized;
  return `${rootBase}/self-improvement/console`;
}
