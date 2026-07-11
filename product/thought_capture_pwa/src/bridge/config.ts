import { MOBILE_CAPTURE_SURFACE_PROFILE } from "./types";

const DEFAULT_API_BASE = "/api/mobile";

export function getSectionApiBase(): string {
  const fromSection = import.meta.env.VITE_BRIDGE_SECTION_API_BASE;
  if (typeof fromSection === "string" && fromSection.trim()) {
    return fromSection.replace(/\/$/, "");
  }

  const legacy = import.meta.env.VITE_API_BASE;
  if (typeof legacy === "string" && legacy.trim()) {
    return legacy.replace(/\/$/, "");
  }

  return DEFAULT_API_BASE;
}

export function isSectionSyncEnabled(): boolean {
  const flag = import.meta.env.VITE_BRIDGE_SECTION_SYNC_ENABLED;
  if (flag === "false" || flag === "0") {
    return false;
  }
  return true;
}

export function isSectionComposeEnabled(): boolean {
  const flag = import.meta.env.VITE_BRIDGE_SECTION_COMPOSE_ENABLED;
  if (flag === "false" || flag === "0") {
    return false;
  }
  if (flag === "true" || flag === "1") {
    return true;
  }
  return import.meta.env.DEV;
}

export function getSurfaceProfile() {
  return MOBILE_CAPTURE_SURFACE_PROFILE;
}
