import { describe, expect, it } from "bun:test";
import { buildAbstractSpecimens, tokenOptions } from "./abstract.ts";
import { buildDocumentSpecimens } from "./document.ts";
import type { LayoutFamily } from "./types.ts";

const EXPECTED: Record<LayoutFamily, number> = {
  flow: 16,
  distribute: 20,
  align: 16,
  gap: 16,
  pad: 16,
  columns: 12,
  textjustify: 16,
  headerpad: 18,
  regionpad: 16,
  tablepad: 12,
  gapnum: 16,
  headerpx: 18,
  regionpx: 16,
};

describe("LayoutBench builders", () => {
  it("builds 208 specimens with planned per-family counts", () => {
    const all = [...buildAbstractSpecimens(), ...buildDocumentSpecimens()];
    expect(all.length).toBe(208);
    const counts = {} as Record<string, number>;
    for (const s of all) counts[s.family] = (counts[s.family] ?? 0) + 1;
    expect(counts).toEqual(EXPECTED);
  });

  it("assigns unique ids and shares 58 images across siblings", () => {
    const all = [...buildAbstractSpecimens(), ...buildDocumentSpecimens()];
    expect(new Set(all.map((s) => s.id)).size).toBe(208);
    const images = new Map<string, string[]>();
    for (const s of all) {
      if (!images.has(s.imageFilename)) images.set(s.imageFilename, []);
      images.get(s.imageFilename)!.push(s.family);
    }
    expect(images.size).toBe(150);
    for (const [name, families] of images) {
      expect(families.length).toBeLessThanOrEqual(2);
      if (families.length === 2) {
        const pair = [...families].sort().join("+");
        expect([
          "gap+gapnum",
          "headerpad+headerpx",
          "regionpad+regionpx",
          "columns+textjustify",
        ]).toContain(pair);
      }
      const [stem] = name.split(".");
      for (const s of all.filter((x) => x.imageFilename === name)) {
        expect(s.groupId).toBe(stem);
      }
    }
  });

  it("builds deterministically across runs", () => {
    const first = JSON.stringify([...buildAbstractSpecimens(), ...buildDocumentSpecimens()]);
    const second = JSON.stringify([...buildAbstractSpecimens(), ...buildDocumentSpecimens()]);
    expect(second).toBe(first);
  });

  it("samples nearest-neighbor distractors with balanced truth letters", () => {
    const sampled = tokenOptions(16, [0, 4, 8, 12, 16, 24, 32], "C");
    expect(sampled.options).toHaveLength(4);
    expect(new Set(sampled.options).size).toBe(4);
    expect(sampled.options).toContain("16px");
    expect(sampled.options[2]).toBe("16px");
    expect(sampled.choice).toBe("C");
    const values = sampled.options.map((o) => parseInt(o, 10)).sort((a, b) => a - b);
    expect(values).toEqual([8, 12, 16, 24]);
  });

  it("balances every choice letter within each family", () => {
    const all = [...buildAbstractSpecimens(), ...buildDocumentSpecimens()];
    const labels: Record<string, string[]> = {
      flow: ["A", "B", "C", "D"],
      distribute: ["A", "B", "C", "D", "E"],
      align: ["A", "B", "C", "D"],
      gap: ["A", "B", "C", "D"],
      pad: ["A", "B", "C", "D"],
      columns: ["A", "B", "C"],
      textjustify: ["A", "B", "C", "D"],
      headerpad: ["A", "B", "C"],
      regionpad: ["A", "B", "C", "D"],
      tablepad: ["A", "B", "C", "D"],
    };
    for (const [family, letters] of Object.entries(labels)) {
      const members = all.filter((s) => s.family === family);
      const seen: Record<string, number> = {};
      for (const s of members) {
        const choice = (s.groundTruth as { choice: string }).choice;
        expect(letters).toContain(choice);
        seen[choice] = (seen[choice] ?? 0) + 1;
      }
      expect(Object.keys(seen).sort()).toEqual([...letters].sort());
      const counts = Object.values(seen);
      expect(Math.max(...counts) - Math.min(...counts)).toBeLessThanOrEqual(1);
    }
  });
});
