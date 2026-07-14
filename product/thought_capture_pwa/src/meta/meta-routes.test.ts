import { describe, expect, it } from "vitest";
import {
  buildMetaConsoleUrl,
  CAPTURE_ROUTE_PATH,
  META_ROUTE_PATH,
} from "./meta-routes";

describe("meta routes", () => {
  it("defines stable top-level capture and meta paths", () => {
    expect(CAPTURE_ROUTE_PATH).toBe("/capture");
    expect(META_ROUTE_PATH).toBe("/meta");
  });

  it("builds the same-origin self-improvement console URL from an API base", () => {
    expect(buildMetaConsoleUrl("/api/mobile")).toBe("/api/self-improvement/console");
    expect(buildMetaConsoleUrl("/api")).toBe("/api/self-improvement/console");
    expect(buildMetaConsoleUrl("/apps/api/inner-world")).toBe(
      "/apps/api/inner-world/self-improvement/console",
    );
  });
});
