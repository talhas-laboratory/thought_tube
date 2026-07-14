import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
import {
  META_SURFACE_PATH_PATTERN,
  SELF_IMPROVEMENT_PATH_PATTERN,
} from "./src/pwa/navigation";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["icons/*", "offline.html"],
      manifest: {
        id: "/",
        name: "Thought Capture",
        short_name: "Capture",
        description: "Thoughts land before they are understood.",
        start_url: "/capture",
        scope: "/",
        display: "standalone",
        orientation: "portrait",
        theme_color: "#0a0a0c",
        background_color: "#0a0a0c",
        icons: [
          {
            src: "/icons/icon-192.png",
            sizes: "192x192",
            type: "image/png",
          },
          {
            src: "/icons/icon-512.png",
            sizes: "512x512",
            type: "image/png",
          },
          {
            src: "/icons/icon-maskable-512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
          },
        ],
        categories: ["productivity", "utilities"],
      },
      workbox: {
        navigateFallback: "/index.html",
        navigateFallbackDenylist: [
          META_SURFACE_PATH_PATTERN,
          SELF_IMPROVEMENT_PATH_PATTERN,
        ],
        cleanupOutdatedCaches: true,
        globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2}"],
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/api\./,
            handler: "NetworkFirst",
            options: {
              cacheName: "bridge-api",
              networkTimeoutSeconds: 5,
            },
          },
          {
            urlPattern: ({ request }) => request.destination === "image",
            handler: "CacheFirst",
            options: {
              cacheName: "images",
              expiration: { maxEntries: 80, maxAgeSeconds: 30 * 86400 },
            },
          },
        ],
      },
    }),
  ],
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
  server: {
    proxy: {
      "/api/mobile": {
        target: "http://127.0.0.1:8422",
        changeOrigin: true,
      },
    },
  },
});
