import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { createElement } from "react";
import { MetaPage } from "./meta-page";

describe("MetaPage transition surface", () => {
  it("describes Telegram as the primary meta workspace", () => {
    const html = renderToStaticMarkup(createElement(MetaPage));
    expect(html).toContain("System editing moved");
    expect(html).toContain("Telegram meta agent");
    expect(html).not.toContain("Opening meta surface");
  });
});
