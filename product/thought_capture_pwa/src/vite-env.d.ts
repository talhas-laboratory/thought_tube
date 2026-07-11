/// <reference types="vite/client" />
/// <reference types="vite-plugin-pwa/client" />

interface ImportMetaEnv {
  readonly VITE_BRIDGE_SECTION_API_BASE?: string;
  readonly VITE_BRIDGE_SECTION_SYNC_ENABLED?: string;
  readonly VITE_BRIDGE_SECTION_COMPOSE_ENABLED?: string;
  readonly VITE_CAPTURE_MODE_DEBUG?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
