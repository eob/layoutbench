import { describe, expect, it } from "bun:test";
import { existsSync, readFileSync } from "node:fs";
import { chromium } from "playwright";
import type { QualitativeScene } from "./qualitative-types.ts";

const modulePath = new URL("./hierarchy.ts", import.meta.url);
const font = readFileSync(new URL("./assets/DejaVuSans.ttf", import.meta.url)).toString("base64");

async function scenes(): Promise<QualitativeScene[]> {
  const { buildHierarchyScenes } = await import(modulePath.pathname);
  return buildHierarchyScenes();
}

describe("qualitative layout hierarchy", () => {
  it("provides a hierarchy stimulus builder", () => {
    expect(existsSync(modulePath)).toBe(true);
  });

  it("crosses parent and child flow independently with constant child counts", async () => {
    const all = await scenes();
    expect(all).toHaveLength(40);
    expect(new Set(all.map((scene) => scene.id)).size).toBe(40);
    expect(all.flatMap((scene) => scene.questions)).toHaveLength(72);
    const flow = all.filter((scene) => scene.questions.some((q) => q.family === "nestedflow"));
    expect(flow).toHaveLength(24);
    const cells = new Set<string>();
    for (const scene of flow) {
      expect(scene.questions.slice(0, 2)).toEqual([
        { family: "topflow", answer: String(scene.factors.parent) },
        { family: "nestedflow", answer: String(scene.factors.child) },
      ]);
      expect((scene.html.match(/data-box="child-\d+"/g) ?? []).length).toBe(5);
      cells.add([scene.factors.parent, scene.factors.child, scene.theme, scene.variant].join("|"));
    }
    expect(cells.size).toBe(24);
    for (const parent of ["row", "column"])
      for (const child of ["row", "column", "wrapped"])
        for (const theme of ["light", "dark"])
          for (const variant of [0, 1])
            expect(cells.has([parent, child, theme, variant].join("|"))).toBe(true);
  });

  it("crosses incomplete-row alignment with parent direction, theme, and target position", async () => {
    const wrap = (await scenes()).filter((scene) => scene.questions.some((q) => q.family === "nestedwrap"));
    expect(wrap).toHaveLength(24);
    const cells = new Set(wrap.map((scene) => [scene.factors.parent, scene.factors.alignment, scene.theme, scene.variant].join("|")));
    for (const parent of ["row", "column"])
      for (const alignment of ["left", "center", "right"])
        for (const theme of ["light", "dark"])
          for (const variant of [0, 1])
            expect(cells.has([parent, alignment, theme, variant].join("|"))).toBe(true);
    expect(wrap.every((scene) => (scene.html.match(/data-box="child-\d+"/g) ?? []).length === 5)).toBe(true);
  });

  it("renders visible parent/child geometry with legible content and no clipping", async () => {
    const browser = await chromium.launch({ headless: true });
    try {
      const page = await browser.newPage({ viewport: { width: 800, height: 600 } });
      for (const scene of await scenes()) {
        await page.setContent(`<style>@font-face{font-family:LayoutBench;src:url(data:font/ttf;base64,${font})}*{box-sizing:border-box}body{margin:0;width:800px;height:600px;display:flex;align-items:center;justify-content:center;font-family:LayoutBench,sans-serif;--bg:#eee;--panel:#fff;--ink:#111;--muted:#444;--line:#777;--tile:#ddd}${scene.css}</style>${scene.html}`);
        await page.evaluate(() => document.fonts.ready);
        const result = await page.evaluate(() => {
          const boxes: Record<string, { x: number; y: number; width: number; height: number }> = {};
          for (const node of Array.from(document.querySelectorAll<HTMLElement>("[data-box]"))) {
            const rect = node.getBoundingClientRect();
            boxes[node.dataset.box!] = { x: rect.x, y: rect.y, width: rect.width, height: rect.height };
          }
          const clipped = Array.from(document.querySelectorAll<HTMLElement>("[data-box], .hierarchy-title, .hierarchy-copy"))
            .filter((node) => node.scrollHeight > node.clientHeight + 1 || node.scrollWidth > node.clientWidth + 1)
            .map((node) => node.dataset.box ?? node.className);
          return { boxes, clipped };
        });
        expect({ scene: scene.id, clipped: result.clipped }).toEqual({ scene: scene.id, clipped: [] });
        const { frame, target } = result.boxes;
        expect(frame.x).toBeGreaterThanOrEqual(0);
        expect(frame.y).toBeGreaterThanOrEqual(0);
        expect(frame.x + frame.width).toBeLessThanOrEqual(800);
        expect(frame.y + frame.height).toBeLessThanOrEqual(600);
        const first = result.boxes[`section-${scene.variant === 0 ? 0 : 1}`]!;
        const second = result.boxes[`section-${scene.variant === 0 ? 1 : 0}`]!;
        if (scene.factors.parent === "row") {
          expect(second.x).toBeGreaterThan(first.x + first.width);
          expect(Math.abs(first.y - second.y)).toBeLessThan(1);
        } else {
          expect(second.y).toBeGreaterThan(first.y + first.height);
          expect(Math.abs(first.x - second.x)).toBeLessThan(1);
        }
        const children = Object.entries(result.boxes).filter(([id]) => id.startsWith("child-")).map(([, rect]) => rect);
        for (const child of children) {
          expect(child.x).toBeGreaterThanOrEqual(target.x + 1.5);
          expect(child.y).toBeGreaterThanOrEqual(target.y + 1.5);
          expect(child.x + child.width).toBeLessThanOrEqual(target.x + target.width - 1.5);
          expect(child.y + child.height).toBeLessThanOrEqual(target.y + target.height - 1.5);
        }
        const rows = [...new Set(children.map((child) => Math.round(child.y)))];
        if (scene.factors.child === "row") expect(rows).toHaveLength(1);
        if (scene.factors.child === "column") expect(rows).toHaveLength(5);
        if (scene.factors.child === "wrapped") expect(rows).toHaveLength(2);
        if (scene.questions.some((q) => q.family === "nestedwrap")) {
          const last = children.filter((child) => Math.round(child.y) === rows.at(-1));
          expect(last).toHaveLength(2);
          const left = last[0]!.x - target.x - 2;
          const right = target.x + target.width - 2 - last.at(-1)!.x - last.at(-1)!.width;
          if (scene.factors.alignment === "left") { expect(left).toBeLessThan(1); expect(right).toBeGreaterThan(50); }
          if (scene.factors.alignment === "right") { expect(right).toBeLessThan(1); expect(left).toBeGreaterThan(50); }
          if (scene.factors.alignment === "center") { expect(Math.abs(left - right)).toBeLessThan(1); expect(left).toBeGreaterThan(25); }
        }
      }
    } finally {
      await browser.close();
    }
  }, 30_000);
});
