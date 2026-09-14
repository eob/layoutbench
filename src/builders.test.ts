import { describe, expect, it } from "bun:test";
import { assignCrossed, balancedLetters, buildAbstractSpecimens, tokenOptions } from "./abstract.ts";
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
  it("randomizes distractors independently of the truth slot", () => {
    const orders = new Set<string>();
    for (let seed = 0; seed < 256; seed++) {
      const sampled = tokenOptions(16, [8, 16, 24, 32, 48], "C", `audit:${seed}`);
      expect(sampled.options[2]).toBe("16px");
      orders.add(sampled.options.filter((_, i) => i !== 2).join(","));
    }
    expect(orders.size).toBe(24);
  });

  it("balances item counts across flow answers", () => {
    const counts = new Map<number, Record<string, number>>();
    for (const task of buildAbstractSpecimens().filter((task) => task.family === "flow")) {
      if (task.design.kind !== "abstract") throw new Error("Flow requires abstract items");
      const count = task.design.item_count!;
      const answers = counts.get(count) ?? {};
      const choice = (task.groundTruth as { choice: string }).choice;
      answers[choice] = (answers[choice] ?? 0) + 1;
      counts.set(count, answers);
    }
    for (const answers of counts.values()) {
      expect(Object.keys(answers).sort()).toEqual(["A", "B", "C", "D"]);
      expect(new Set(Object.values(answers)).size).toBe(1);
    }
  });

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

  it("offers the full token set with the truth at the letter slot", () => {
    const sampled = tokenOptions(16, [0, 4, 8, 12, 16, 24, 32], "C", "example");
    expect(sampled.options).toHaveLength(7);
    expect(new Set(sampled.options).size).toBe(7);
    expect(sampled.options).toContain("16px");
    expect(sampled.options[2]).toBe("16px");
    expect(sampled.choice).toBe("C");
    const values = sampled.options.map((o) => parseInt(o, 10)).sort((a, b) => a - b);
    expect(values).toEqual([0, 4, 8, 12, 16, 24, 32]);
  });

  it("balances letters within one for indivisible counts", () => {
    for (const [count, letters] of [[16, 7], [16, 5], [12, 4]] as [number, number][]) {
      const alphabet = ["A", "B", "C", "D", "E", "F", "G"].slice(0, letters);
      const assigned = balancedLetters(count, alphabet, `test:${count}:${letters}`);
      expect(assigned).toHaveLength(count);
      const seen: Record<string, number> = {};
      for (const letter of assigned) seen[letter] = (seen[letter] ?? 0) + 1;
      expect(Object.keys(seen).sort()).toEqual([...alphabet].sort());
      const counts = Object.values(seen);
      expect(Math.max(...counts) - Math.min(...counts)).toBeLessThanOrEqual(1);
    }
  });

  it("crosses nuisance axes within every token group", () => {
    const tokens = [0, 0, 4, 4, 8, 8, 8, 12, 12, 12];
    const group = (slot: number) => `token:${tokens[slot]}`;
    const assigned = assignCrossed(
      tokens.length,
      [
        { key: "theme", levels: [0, 1, 2, 3, 4].flatMap(() => ["light", "dark"]) },
        { key: "letter", levels: balancedLetters(tokens.length, ["A", "B", "C", "D"], "test") },
      ],
      [{ group, axisKey: "theme" }],
      [{ group, axisKey: "letter" }],
      [],
      "test",
    );
    expect(assigned).toHaveLength(tokens.length);
    const byToken = new Map<number, { themes: unknown[]; letters: unknown[] }>();
    tokens.forEach((token, slot) => {
      if (!byToken.has(token)) byToken.set(token, { themes: [], letters: [] });
      byToken.get(token)!.themes.push(assigned[slot]!["theme"]);
      byToken.get(token)!.letters.push(assigned[slot]!["letter"]);
    });
    for (const [token, values] of byToken) {
      if (values.themes.length >= 2)
        expect(new Set(values.themes)).toEqual(new Set(["light", "dark"]));
      expect(new Set(values.letters).size).toBe(values.letters.length);
    }
  });

  it("balances every choice letter within each family", () => {
    const all = [...buildAbstractSpecimens(), ...buildDocumentSpecimens()];
    const labels: Record<string, string[]> = {
      flow: ["A", "B", "C", "D"],
      distribute: ["A", "B", "C", "D", "E"],
      align: ["A", "B", "C", "D"],
      gap: ["A", "B", "C", "D", "E", "F", "G"],
      pad: ["A", "B", "C", "D", "E"],
      columns: ["A", "B", "C"],
      textjustify: ["A", "B", "C", "D"],
      headerpad: ["A", "B", "C"],
      regionpad: ["A", "B", "C", "D", "E"],
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
