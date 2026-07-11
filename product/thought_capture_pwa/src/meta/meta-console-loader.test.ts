import { describe, expect, it, vi } from "vitest";
import { loadMetaConsoleDocument } from "./meta-console-loader";

describe("loadMetaConsoleDocument", () => {
  it("fetches the server-owned meta surface and replaces the current document", async () => {
    const fetchFn = vi.fn(
      async () =>
        ({
          ok: true,
          text: async () => "<!doctype html><title>Self Improvement Console</title>",
        }) as Response,
    ) as typeof fetch;
    const doc = {
      open: vi.fn(),
      write: vi.fn(),
      close: vi.fn(),
    } as const;

    await loadMetaConsoleDocument({
      fetchFn,
      documentRef: doc,
      consoleUrl: "/api/self-improvement/console",
    });

    expect(fetchFn).toHaveBeenCalledWith("/api/self-improvement/console", {
      cache: "no-store",
      credentials: "same-origin",
      headers: { Accept: "text/html" },
    });
    expect(doc.open).toHaveBeenCalledOnce();
    expect(doc.write).toHaveBeenCalledWith(
      "<!doctype html><title>Self Improvement Console</title>",
    );
    expect(doc.close).toHaveBeenCalledOnce();
  });

  it("throws when the server-owned meta surface cannot be fetched", async () => {
    const fetchFn = vi.fn(
      async () =>
        ({
          ok: false,
          status: 503,
        }) as Response,
    ) as typeof fetch;

    await expect(
      loadMetaConsoleDocument({
        fetchFn,
        documentRef: {
          open: vi.fn(),
          write: vi.fn(),
          close: vi.fn(),
        },
        consoleUrl: "/api/self-improvement/console",
      }),
    ).rejects.toThrow("Failed to load meta surface (503)");
  });
});
