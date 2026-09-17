import { createHash } from "node:crypto";
import * as fs from "node:fs";
import * as path from "node:path";
import { chromium } from "playwright";
import catalog from "../config/qualitative.json";
import { balancedLetters, fnv1a, mulberry32, shuffled } from "./abstract.ts";
import { buildQualitativeScenes } from "./qualitative.ts";
import { buildHierarchyScenes } from "./hierarchy.ts";
import { resolveRenderOutput } from "./render-output.ts";

const root = path.resolve(import.meta.dir, "..");
const out = resolveRenderOutput(process.argv[2]);
const font = fs.readFileSync(path.join(root, "src/assets/DejaVuSans.ttf"));
const sha = (data: Buffer | string) => createHash("sha256").update(data).digest("hex");

async function main() {
  fs.mkdirSync(out, { recursive: true });
  fs.mkdirSync(path.join(out, "fonts"), { recursive: true });
  for (const name of ["DejaVuSans.ttf", "DejaVuSans.LICENSE"]) fs.copyFileSync(path.join(root, "src/assets", name), path.join(out, "fonts", name));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 800, height: 600 }, deviceScaleFactor: 2 });
  const session = await page.context().newCDPSession(page);
  await session.send("DOM.enable");
  await session.send("CSS.enable");
  const tasks: object[] = [];
  const counters: Record<string, number> = {};
  const imageGroups = new Map<string, string>();
  const scenes = [...buildQualitativeScenes(), ...buildHierarchyScenes()];
  const familyCounts: Record<string, number> = {};
  for (const scene of scenes) for (const q of scene.questions) familyCounts[q.family] = (familyCounts[q.family] ?? 0) + 1;
  const truthSlots = Object.fromEntries(Object.entries(familyCounts).map(([family, count]) => {
    const size = Object.keys((catalog as Record<string, { options: object }>)[family]!.options).length;
    return [family, balancedLetters(count, Array.from({ length: size }, (_, i) => String.fromCharCode(65 + i)), `qualitative:${family}`)];
  }));
  try {
    for (const scene of scenes) {
      const dark = scene.theme === "dark";
      const css = `*{box-sizing:border-box;margin:0} @font-face{font-family:LayoutBench;src:url(data:font/ttf;base64,${font.toString("base64")})} body{width:800px;height:600px;display:flex;align-items:center;justify-content:center;font-family:LayoutBench,sans-serif;font-size:17px;--bg:${dark ? "#101725" : "#eef2f6"};--panel:${dark ? "#182235" : "#ffffff"};--ink:${dark ? "#f1f5f9" : "#172033"};--muted:${dark ? "#b7c5d9" : "#4b5d73"};--line:${dark ? "#9aabc2" : "#52677f"};--tile:${dark ? "#344960" : "#dae5ef"};background:var(--bg);color:var(--ink)} .frame{width:660px;height:440px;border:2px solid var(--line);background:var(--panel)} .tile{flex-shrink:0;background:var(--tile);border:1px solid var(--line);padding:8px;display:flex;align-items:center;justify-content:center;text-align:center} ${scene.css}`;
      await page.setContent(`<html><head><style>${css}</style></head><body>${scene.html}</body></html>`);
      await page.evaluate(async () => { await document.fonts.load("17px LayoutBench"); await document.fonts.ready; if (!document.fonts.check("17px LayoutBench")) throw Error("font missing"); });
      const documentNode = await session.send("DOM.getDocument");
      const { nodeIds } = await session.send("DOM.querySelectorAll", { nodeId: documentNode.root.nodeId, selector: "[data-box],h2,p,.caption" });
      const fonts = (await Promise.all(nodeIds.map(async nodeId => (await session.send("CSS.getPlatformFontsForNode", { nodeId })).fonts))).flat();
      if (!fonts.length || fonts.some(f => !f.isCustomFont || f.familyName !== "DejaVu Sans")) throw Error(`Font fallback: ${scene.id}`);
      const measured = await page.evaluate(() => {
        const rect = (r: DOMRect) => ({ x: r.x, y: r.y, width: r.width, height: r.height });
        const regions = Array.from(document.querySelectorAll<HTMLElement>("[data-box]")).map(el => ({ id: el.dataset.box!, role: "box", ...rect(el.getBoundingClientRect()) }));
        const lines: Record<string, ReturnType<typeof rect>[]> = {};
        for (const el of Array.from(document.querySelectorAll<HTMLElement>("[data-lines]"))) {
          const range = document.createRange(); range.selectNodeContents(el);
          lines[el.dataset.lines!] = Array.from(range.getClientRects()).filter(r => r.width > 0).map(rect);
        }
        const overflow = Array.from(document.querySelectorAll<HTMLElement>("[data-box]")).filter(el => el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1).map(el => el.dataset.box);
        return { regions, lines, overflow, domText: document.body.innerText };
      });
      if (measured.overflow.length) throw Error(`Overflow ${scene.id}: ${measured.overflow}`);
      const png = await page.screenshot();
      const imageHash = sha(png);
      const groupId = imageGroups.get(imageHash) ?? scene.id;
      const imageFilename = `${groupId}.png`;
      if (!imageGroups.has(imageHash)) fs.writeFileSync(path.join(out, imageFilename), png);
      imageGroups.set(imageHash, groupId);
      for (const question of scene.questions) {
        const spec = (catalog as Record<string, { label: string; question: string; options: Record<string, string> }>)[question.family]!;
        const keys = Object.keys(spec.options);
        const index = counters[question.family] = (counters[question.family] ?? 0) + 1;
        const taskId = `layoutbench-${question.family}-${String(index).padStart(3, "0")}`;
        const truthIndex = truthSlots[question.family]![index - 1]!.charCodeAt(0) - 65;
        const other = shuffled(keys.filter(k => k !== question.answer), mulberry32(fnv1a(taskId)));
        other.splice(truthIndex, 0, question.answer);
        const prompt = `${spec.question}\n${other.map((k, i) => `${String.fromCharCode(65 + i)}: ${spec.options[k]}`).join("\n")}\nReturn only a JSON object with one key, "choice", whose value is the selected option letter.`;
        tasks.push({ taskId, family: question.family, groupId, imageFilename, imageSha256: imageHash, groundTruth: { choice: String.fromCharCode(65 + truthIndex) }, prompt,
          design: { kind: "qualitative", theme: scene.theme, variant: scene.variant, answer: question.answer, options: other, factors: scene.factors, lines: measured.lines }, domText: measured.domText,
          rendered: { width: 800, height: 600, dpr: 2, colorSpace: "srgb", font: { path: "fonts/DejaVuSans.ttf", sha256: sha(font), used: fonts }, browser: browser.version(), regions: measured.regions, overflow: measured.overflow } });
      }
    }
  } finally { await browser.close(); }
  const imageNames = new Set([...imageGroups.values()].map(id => `${id}.png`));
  for (const name of fs.readdirSync(out)) if (name.endsWith(".png") && !imageNames.has(name)) fs.unlinkSync(path.join(out, name));
  fs.writeFileSync(path.join(out, "manifest.json"), JSON.stringify(tasks, null, 2) + "\n");
  console.log(`Rendered ${tasks.length} questions across ${new Set(tasks.map(t => (t as { imageFilename: string }).imageFilename)).size} images to ${out}`);
}

await main();
