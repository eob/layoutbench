import { describe, expect, it } from "bun:test";
import { SPECIMENS } from "./specimens.ts";

describe("LayoutBench Specimens", () => {
  it("generates exactly 100 specimens", () => {
    expect(SPECIMENS.length).toBe(100);
  });

  it("assigns unique IDs to each specimen", () => {
    const ids = new Set(SPECIMENS.map((s) => s.id));
    expect(ids.size).toBe(SPECIMENS.length);
  });

  it("ensures every specimen matches its gap token to numeric px", () => {
    for (const s of SPECIMENS) {
      const parsedPx = parseInt(s.gap.replace("px", ""), 10);
      expect(s.gap_px).toBe(parsedPx);
    }
  });

  it("ensures every specimen matches its padding token to numeric px", () => {
    for (const s of SPECIMENS) {
      const parsedPx = parseInt(s.padding.replace("px", ""), 10);
      expect(s.padding_px).toBe(parsedPx);
    }
  });

  it("covers all 4 directions", () => {
    const dirs = new Set(SPECIMENS.map((s) => s.direction));
    expect(dirs.has("row")).toBe(true);
    expect(dirs.has("column")).toBe(true);
    expect(dirs.has("grid-2col")).toBe(true);
    expect(dirs.has("grid-3col")).toBe(true);
  });

  it("covers all justification options", () => {
    const jcs = new Set(SPECIMENS.map((s) => s.justify_content));
    expect(jcs.has("start")).toBe(true);
    expect(jcs.has("center")).toBe(true);
    expect(jcs.has("end")).toBe(true);
    expect(jcs.has("space-between")).toBe(true);
    expect(jcs.has("space-around")).toBe(true);
  });

  it("covers all alignment options", () => {
    const ais = new Set(SPECIMENS.map((s) => s.align_items));
    expect(ais.has("start")).toBe(true);
    expect(ais.has("center")).toBe(true);
    expect(ais.has("end")).toBe(true);
    expect(ais.has("stretch")).toBe(true);
  });
});
