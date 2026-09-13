import { createHash } from "node:crypto";
import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import { buildAbstractSpecimens } from "./abstract.ts";
import { HEADER_TEXT, SENTENCES, TABLE_WORDS, buildDocumentSpecimens } from "./document.ts";
import type {
  AbstractDesign,
  DecodedRect,
  DocumentDesign,
  LayoutTask,
  Specimen,
} from "./types.ts";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUTPUT_DIR = path.join(ROOT, "dataset", "layoutbench-v0.1");
const FONT_PATH = path.join(ROOT, "src", "assets", "DejaVuSans.ttf");
const FONT_SHA256 = createHash("sha256").update(fs.readFileSync(FONT_PATH)).digest("hex");
const FONT_BYTES = fs.readFileSync(FONT_PATH).toString("base64");
const PROMPTS = JSON.parse(
  fs.readFileSync(path.join(ROOT, "baseline", "prompts.json"), "utf8"),
) as Record<string, string>;

export const CANVAS = { width: 800, height: 600, dpr: 2 };
export const CARD = { width: 640, height: 440 };

export function themeColors(theme: "light" | "dark") {
  const isDark = theme === "dark";
  return {
    isDark,
    canvasBg: isDark ? "#090d16" : "#f1f5f9",
    cardBg: isDark ? "#111827" : "#ffffff",
    cardBorder: isDark ? "#4b5563" : "#94a3b8",
    textColor: isDark ? "#f3f4f6" : "#0f172a",
    mutedColor: isDark ? "#9ca3af" : "#64748b",
    blockTint: isDark ? "#2d3a50" : "#d6e0eb",
    barColor: isDark ? "#374151" : "#cbd5e1",
  };
}

const ITEM_BGS = {
  light: ["#f8fafc", "#f1f5f9", "#f3f4f6", "#eef2f6", "#f0fdf4", "#fef3c7"],
  dark: ["#1f2937", "#1e293b", "#27272a", "#182230", "#1e1e24", "#22272e"],
};
const ITEM_BORDERS = {
  light: ["#e2e8f0", "#cbd5e1", "#e5e7eb", "#d1d5db", "#bbf7d0", "#fde68a"],
  dark: ["#374151", "#334155", "#3f3f46", "#2d3748", "#3b4252", "#38414a"],
};
const ACCENT_DOTS = ["#3b82f6", "#10b981", "#8b5cf6", "#f59e0b", "#ec4899", "#06b6d4"];

const ROW_VARIABLE = {
  heights: [44, 72, 56, 84, 48],
  widths: [85, 115, 95, 125, 90],
};
const COL_VARIABLE = { widths: [130, 210, 160, 240] };
const GRID_VARIABLE = { heights: [52, 68, 60, 76, 54, 70] };

function abstractItemsHtml(design: AbstractDesign): string {
  const palette = design.theme;
  return Array.from({ length: design.item_count }, (_, i) => {
    const bg = ITEM_BGS[palette][i % ITEM_BGS[palette].length];
    const border = ITEM_BORDERS[palette][i % ITEM_BORDERS[palette].length];
    const dot = ACCENT_DOTS[i % ACCENT_DOTS.length];
    let widthStyle = "";
    let heightStyle = "";
    if (design.content_variant === "variable") {
      if (design.direction === "row") {
        if (design.align_items !== "stretch")
          heightStyle = `height: ${ROW_VARIABLE.heights[i % ROW_VARIABLE.heights.length]}px;`;
        widthStyle = `min-width: ${ROW_VARIABLE.widths[i % ROW_VARIABLE.widths.length]}px;`;
      } else if (design.direction === "column") {
        widthStyle =
          design.align_items === "stretch"
            ? "width: 100%;"
            : `width: ${COL_VARIABLE.widths[i % COL_VARIABLE.widths.length]}px;`;
        heightStyle = "min-height: 44px;";
      } else {
        if (design.align_items !== "stretch")
          heightStyle = `min-height: ${GRID_VARIABLE.heights[i % GRID_VARIABLE.heights.length]}px;`;
      }
    } else {
      if (design.direction === "row") {
        widthStyle = "min-width: 82px;";
        if (design.align_items !== "stretch") heightStyle = "height: 48px;";
      } else if (design.direction === "column") {
        widthStyle = design.align_items === "stretch" ? "width: 100%;" : "width: 180px;";
        heightStyle = "height: 44px;";
      } else {
        if (design.align_items !== "stretch") heightStyle = "height: 52px;";
      }
    }
    let radius = "border-radius: 8px;";
    if (design.gap_px === 0 && design.item_count > 1) {
      if (design.direction === "row") {
        if (i === 0) radius = "border-radius: 8px 0 0 8px;";
        else if (i === design.item_count - 1) radius = "border-radius: 0 8px 8px 0;";
        else radius = "border-radius: 0; border-left: none;";
      } else if (design.direction === "column") {
        if (i === 0) radius = "border-radius: 8px 8px 0 0;";
        else if (i === design.item_count - 1) radius = "border-radius: 0 0 8px 8px;";
        else radius = "border-radius: 0; border-top: none;";
      }
    }
    return `<div class="item" data-role="item" data-id="${i}" style="background: ${bg}; border: 1px solid ${border}; ${radius} ${widthStyle} ${heightStyle}"><div class="dot" style="background: ${dot};"></div><div class="bars"><div class="bar" style="width: 62%;"></div><div class="bar" style="width: 41%;"></div></div></div>`;
  }).join("\n");
}

function abstractStageCss(design: AbstractDesign): string {
  let display = "display: flex;";
  let dirCss = `flex-direction: ${design.direction === "column" ? "column" : "row"};`;
  let gridCss = "";
  if (design.direction === "grid-2col") {
    display = "display: grid;";
    gridCss = "grid-template-columns: repeat(2, 1fr);";
    dirCss = "";
  } else if (design.direction === "grid-3col") {
    display = "display: grid;";
    gridCss = "grid-template-columns: repeat(3, 1fr);";
    dirCss = "";
  }
  let justifyCss = `justify-content: ${design.justify_content};`;
  const alignCss = `align-items: ${design.align_items};`;
  if (design.direction.startsWith("grid")) {
    // Grid cells always stretch: the grid structure is carried by full
    // boxes, and box gaps equal the CSS gutter. justify_content is not
    // swept for grids (flow family only); methodology documents this.
    justifyCss = "justify-items: stretch;";
  }
  return `${display} ${dirCss} ${gridCss} ${justifyCss} ${alignCss} gap: ${design.gap_px}px; padding: ${design.padding_px}px;`;
}

function pageShell(bodyInner: string, css: string): string {
  return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  @font-face{font-family:LayoutBench;src:url(data:font/ttf;base64,${FONT_BYTES}) format("truetype");font-weight:400;font-style:normal}
  body {
    width: ${CANVAS.width}px;
    height: ${CANVAS.height}px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: LayoutBench, sans-serif;
  }
${css}
</style>
</head>
<body>
${bodyInner}
</body>
</html>`;
}

function abstractHtml(design: AbstractDesign): string {
  const c = themeColors(design.theme);
  const css = `
  body { background: ${c.canvasBg}; }
  .card {
    width: ${CARD.width}px;
    height: ${CARD.height}px;
    background: ${c.cardBg};
    border: 1px solid ${c.cardBorder};
    border-radius: 8px;
    overflow: hidden;
    flex-shrink: 0;
  }
  .stage {
    width: 100%;
    height: 100%;
    ${abstractStageCss(design)}
    overflow: hidden;
  }
  .item {
    display: flex;
    align-items: center;
    padding: 8px 12px;
    gap: 8px;
  }
  .dot { width: 8px; height: 8px; border-radius: 9999px; flex-shrink: 0; }
  .bars { display: flex; flex-direction: column; gap: 5px; flex: 1; }
  .bar { height: 7px; border-radius: 4px; background: ${c.barColor}; }`;
  const bodyInner = `<div class="card" data-role="card" data-id="card"><div class="stage" data-role="stage" data-id="stage">${abstractItemsHtml(design)}</div></div>`;
  return pageShell(bodyInner, css);
}

function paragraphs(count: number): string {
  return SENTENCES.slice(0, count)
    .map((s) => `<p>${s}</p>`)
    .join("\n");
}

function columnChunk(sentences: string[], columns: number, index: number): string {
  const per = Math.ceil(sentences.length / columns);
  const chunk = sentences.slice(index * per, index * per + per).join(" ");
  return `<p>${chunk}</p>`;
}

function documentHtml(design: DocumentDesign): string {
  const c = themeColors(design.theme);
  const baseCss = `
  body { background: ${c.canvasBg}; }
  .card {
    width: ${CARD.width}px;
    height: ${CARD.height}px;
    background: ${c.cardBg};
    border: 1px solid ${c.cardBorder};
    border-radius: 8px;
    overflow: hidden;
    flex-shrink: 0;
    color: ${c.textColor};
    font-size: 16px;
    line-height: 1.55;
  }
  .doc { width: 100%; height: 100%; padding: 40px; }
  .tcols { display: flex; flex-direction: row; gap: 32px; height: 100%; }
  .tcol { flex: 1 1 0; min-width: 0; }
  .tcol p, .tbody p { margin: 0 0 0.9em 0; }
  .tcol p:last-child, .tbody p:last-child { margin-bottom: 0; }
  .header-line { font-size: 28px; font-weight: 700; line-height: 1.25; }
  .content-block { background: ${c.blockTint}; border-radius: 6px; color: ${c.textColor}; font-size: 16px; line-height: 1.55; }
  table.grid { border-collapse: separate; border-spacing: 0; table-layout: fixed; }
  table.grid td { border: 1px solid ${c.cardBorder}; background: ${c.blockTint}; color: ${c.textColor}; font-size: 15px; line-height: normal; vertical-align: top; }`;
  let bodyInner = "";
  if (design.archetype === "columns" || design.archetype === "text") {
    const count = design.column_count!;
    const align = design.text_align!;
    const cols = Array.from(
      { length: count },
      (_, i) =>
        `<div class="tcol" data-role="tcol" data-id="${i}" style="text-align: ${align};">${columnChunk(SENTENCES, count, i)}</div>`,
    ).join("\n");
    bodyInner = `<div class="card" data-role="card" data-id="card"><div class="doc" data-role="doc" data-id="doc"><div class="tcols" data-role="tcols" data-id="tcols">${cols}</div></div></div>`;
  } else if (design.archetype === "header") {
    bodyInner = `<div class="card" data-role="card" data-id="card"><div class="doc" data-role="doc" data-id="doc" style="padding: 0 48px;"><div class="above-spacer" data-role="above-spacer" data-id="above" style="height: ${design.above_px}px;"></div><div class="header-line" data-role="header" data-id="header">${HEADER_TEXT}</div><div class="below-spacer" data-role="below-spacer" data-id="below" style="height: ${design.below_px}px;"></div><div class="tbody" data-role="tbody" data-id="tbody">${paragraphs(3)}</div></div></div>`;
  } else if (design.archetype === "region") {
    const pad = design.pad_px!;
    const inner = `<div class="content-block" data-role="content" data-id="content" style="padding: 24px; height: 100%;">${paragraphs(3)}</div>`;
    if (design.bordered) {
      bodyInner = `<div class="card" data-role="card" data-id="card"><div class="doc" data-role="doc" data-id="doc" style="padding: ${pad}px;">${inner}</div></div>`;
    } else {
      bodyInner = `<div class="bare-wrap" data-role="bare-wrap" data-id="bare" style="width: ${CANVAS.width - 2 * pad}px; height: ${CANVAS.height - 2 * pad}px; flex-shrink: 0;">${inner}</div>`;
      return pageShell(bodyInner, baseCss);
    }
  } else if (design.archetype === "table") {
    const rows = design.rows!;
    const cols = design.cols!;
    const cellPad = design.cell_pad_px!;
    const width = 200 + cols * 90;
    let word = 0;
    const body = Array.from(
      { length: rows },
      (_, r) =>
        `<tr>${Array.from(
          { length: cols },
          (_, cc) =>
            `<td data-role="cell" data-id="${r}-${cc}" style="padding: ${cellPad}px;"><span data-role="celltext" data-id="${r}-${cc}">${TABLE_WORDS[word++ % TABLE_WORDS.length]}</span></td>`,
        ).join("")}</tr>`,
    ).join("\n");
    bodyInner = `<div class="card" data-role="card" data-id="card"><div class="doc" data-role="doc" data-id="doc" style="display: flex; align-items: center; justify-content: center;"><table class="grid" data-role="table" data-id="table" style="width: ${width}px;">${body}</table></div></div>`;
  }
  return pageShell(bodyInner, baseCss);
}

interface DecodedPage {
  regions: DecodedRect[];
  domText: string;
  lineRects: Record<string, DecodedRect[]>;
  overflow: Record<string, { scroll: number; client: number }>;
}

async function decodePage(page: {
  $$eval: Function;
  evaluate: Function;
}): Promise<DecodedPage> {
  const regions = (await page.$$eval("[data-role]", (elements: Element[]) =>
    elements.map((el) => {
      const rect = el.getBoundingClientRect();
      return {
        role: (el as HTMLElement).dataset.role!,
        id: (el as HTMLElement).dataset.id!,
        x: rect.x,
        y: rect.y,
        width: rect.width,
        height: rect.height,
      };
    }),
  )) as DecodedRect[];
  const cellLines = (await page.evaluate(`(() => {
    const out = {};
    for (const span of document.querySelectorAll('[data-role="celltext"]')) {
      const range = document.createRange();
      range.selectNodeContents(span);
      const first = range.getClientRects()[0];
      out[span.dataset.id] = first
        ? { x: first.x, y: first.y, width: first.width, height: first.height }
        : null;
    }
    return out;
  })()`)) as Record<string, { x: number; y: number; width: number; height: number } | null>;
  for (const region of regions) {
    if (region.role === "celltext") {
      const line = cellLines[region.id];
      if (!line) throw new Error(`Missing cell line rect ${region.id}`);
      region.x = line.x;
      region.y = line.y;
      region.width = line.width;
      region.height = line.height;
    }
  }
  const domText = (await page.evaluate(
    "document.body.innerText",
  )) as string;
  const lineRects = (await page.evaluate(`(() => {
    const out = {};
    for (const col of document.querySelectorAll(".tcol")) {
      const range = document.createRange();
      range.selectNodeContents(col);
      const rects = Array.from(range.getClientRects()).map((r) => ({
        role: "line",
        id: col.dataset.id,
        x: r.x,
        y: r.y,
        width: r.width,
        height: r.height,
      }));
      out[col.dataset.id] = rects;
    }
    return out;
  })()`)) as Record<string, DecodedRect[]>;
  const overflow = (await page.evaluate(`(() => {
    const out = {};
    for (const el of document.querySelectorAll(".tcol, .tbody, .content-block")) {
      const key = (el.dataset.role || "el") + ":" + (el.dataset.id || "0");
      out[key] = { scroll: el.scrollHeight, client: el.clientHeight };
    }
    return out;
  })()`)) as Record<string, { scroll: number; client: number }>;
  return { regions, domText, lineRects, overflow };
}

const round1 = (value: number) => Math.round(value * 10) / 10;

function findRegion(regions: DecodedRect[], role: string, id?: string): DecodedRect {
  const found = regions.find((r) => r.role === role && (id === undefined || r.id === id));
  if (!found) throw new Error(`Missing decoded region ${role}:${id ?? "*"}`);
  return found;
}

function deriveSpacing(specimen: Specimen, regions: DecodedRect[]): Record<string, number> {
  const design = specimen.design;
  const decoded: Record<string, number> = {};
  if (design.kind === "abstract") {
    const stage = findRegion(regions, "stage");
    const items = regions
      .filter((r) => r.role === "item")
      .sort((a, b) => Number(a.id) - Number(b.id));
    if (design.direction === "row") {
      const gaps = items.slice(1).map((item, i) => item.x - (items[i]!.x + items[i]!.width));
      decoded.gap = round1(Math.min(...gaps));
      decoded.pad_left = round1(items[0]!.x - stage.x);
      decoded.pad_top = round1(items[0]!.y - stage.y);
    } else if (design.direction === "column") {
      const gaps = items.slice(1).map((item, i) => item.y - (items[i]!.y + items[i]!.height));
      decoded.gap = round1(Math.min(...gaps));
      decoded.pad_left = round1(items[0]!.x - stage.x);
      decoded.pad_top = round1(items[0]!.y - stage.y);
    } else {
      const sorted = [...items].sort((a, b) => a.y - b.y || a.x - b.x);
      const firstRow = [sorted[0]!];
      for (const item of sorted.slice(1)) {
        const first = firstRow[0]!;
        if (item.y < first.y + first.height && first.y < item.y + item.height) firstRow.push(item);
        else break;
      }
      firstRow.sort((a, b) => a.x - b.x);
      const gaps = firstRow.slice(1).map((item, i) => item.x - (firstRow[i]!.x + firstRow[i]!.width));
      decoded.gap = round1(Math.min(...gaps));
      decoded.grid_columns = firstRow.length;
      decoded.pad_left = round1(Math.min(...items.map((item) => item.x)) - stage.x);
      decoded.pad_top = round1(Math.min(...items.map((item) => item.y)) - stage.y);
    }
  } else {
    if (design.archetype === "header") {
      const above = findRegion(regions, "above-spacer");
      const below = findRegion(regions, "below-spacer");
      decoded.above = round1(above.height);
      decoded.below = round1(below.height);
    } else if (design.archetype === "region") {
      const content = findRegion(regions, "content");
      if (design.bordered) {
        const card = findRegion(regions, "card");
        decoded.pad_top = round1(content.y - (card.y + 1));
        decoded.pad_left = round1(content.x - (card.x + 1));
        decoded.pad_bottom = round1(card.y + card.height - 1 - (content.y + content.height));
        decoded.pad_right = round1(card.x + card.width - 1 - (content.x + content.width));
      } else {
        decoded.pad_top = round1(content.y);
        decoded.pad_left = round1(content.x);
        decoded.pad_bottom = round1(CANVAS.height - (content.y + content.height));
        decoded.pad_right = round1(CANVAS.width - (content.x + content.width));
      }
      decoded.pad = round1(
        Math.min(decoded.pad_top!, decoded.pad_left!, decoded.pad_bottom!, decoded.pad_right!),
      );
    } else if (design.archetype === "table") {
      const cell = findRegion(regions, "cell", "0-0");
      const text = findRegion(regions, "celltext", "0-0");
      decoded.cell_pad_top = round1(text.y - (cell.y + 1));
      decoded.cell_pad_left = round1(text.x - (cell.x + 1));
    } else {
      const tcols = regions.filter((r) => r.role === "tcol");
      decoded.column_count = tcols.length;
      if (tcols.length > 1) {
        const sorted = [...tcols].sort((a, b) => a.x - b.x);
        decoded.column_gap = round1(
          Math.min(...sorted.slice(1).map((col, i) => col.x - (sorted[i]!.x + sorted[i]!.width))),
        );
      }
    }
  }
  return decoded;
}

function buildPrompt(specimen: Specimen): string {
  const template = PROMPTS[specimen.family];
  if (!template) throw new Error(`Missing prompt template for ${specimen.family}`);
  if (!template.includes("{options}")) return template;
  const options = specimen.options ?? [];
  const letters = ["A", "B", "C", "D", "E"];
  const block = options.map((value, i) => `${letters[i]}: ${value}`).join("\n");
  return template.replace("{options}", block);
}

async function main() {
  const specimens: Specimen[] = [...buildAbstractSpecimens(), ...buildDocumentSpecimens()];
  console.log(`Rendering ${specimens.length} specimens...`);
  fs.rmSync(OUTPUT_DIR, { recursive: true, force: true });
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  fs.mkdirSync(path.join(OUTPUT_DIR, "fonts"), { recursive: true });
  fs.copyFileSync(FONT_PATH, path.join(OUTPUT_DIR, "fonts", "DejaVuSans.ttf"));
  fs.copyFileSync(
    path.join(ROOT, "src", "assets", "DejaVuSans.LICENSE"),
    path.join(OUTPUT_DIR, "fonts", "DejaVuSans.LICENSE"),
  );

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport: { width: CANVAS.width, height: CANVAS.height },
    deviceScaleFactor: CANVAS.dpr,
  });
  const tasks: LayoutTask[] = [];
  const seenImages = new Set<string>();
  for (const specimen of specimens) {
    const html =
      specimen.design.kind === "abstract"
        ? abstractHtml(specimen.design as AbstractDesign)
        : documentHtml(specimen.design as DocumentDesign);
    await page.setContent(html);
    await page.evaluate("document.fonts.load('16px LayoutBench')");
    await page.evaluate("document.fonts.ready");
    const loaded = await page.evaluate('document.fonts.check("16px LayoutBench")');
    if (!loaded) throw new Error(`Pinned font failed to load for ${specimen.id}`);

    let png: Buffer;
    let decoded: Record<string, number>;
    let regions: DecodedRect[];
    let domText: string;
    let lineRects: Record<string, DecodedRect[]>;
    let overflow: Record<string, { scroll: number; client: number }>;
    if (seenImages.has(specimen.imageFilename)) {
      const prior = tasks.find((t) => t.imageFilename === specimen.imageFilename)!;
      png = fs.readFileSync(path.join(OUTPUT_DIR, specimen.imageFilename));
      regions = prior.rendered.regions;
      domText = prior.domText;
      lineRects = prior.design.lines ?? {};
      overflow = prior.design.overflow ?? {};
      decoded = { ...(prior.design.decoded ?? {}) };
    } else {
      seenImages.add(specimen.imageFilename);
      png = await page.screenshot({ type: "png" });
      const page2 = await decodePage(page);
      regions = page2.regions;
      domText = page2.domText;
      lineRects = page2.lineRects;
      overflow = page2.overflow;
      decoded = deriveSpacing(specimen, regions);
      fs.writeFileSync(path.join(OUTPUT_DIR, specimen.imageFilename), png);
    }
    let groundTruth: LayoutTask["groundTruth"] = { ...specimen.groundTruth };
    if (specimen.family === "gapnum") groundTruth = { gap_px: Math.round(decoded.gap!) };
    if (specimen.family === "headerpx")
      groundTruth = { above_px: Math.round(decoded.above!), below_px: Math.round(decoded.below!) };
    if (specimen.family === "regionpx") groundTruth = { pad_px: Math.round(decoded.pad!) };
    tasks.push({
      taskId: specimen.id,
      family: specimen.family,
      groupId: specimen.groupId,
      imageFilename: specimen.imageFilename,
      imageSha256: createHash("sha256").update(png).digest("hex"),
      groundTruth,
      prompt: buildPrompt(specimen),
      design: {
        ...specimen.design,
        decoded,
        lines: lineRects,
        overflow,
      },
      domText,
      rendered: {
        width: CANVAS.width,
        height: CANVAS.height,
        dpr: CANVAS.dpr,
        colorSpace: "srgb",
        font: { path: "fonts/DejaVuSans.ttf", sha256: FONT_SHA256 },
        regions: regions.map((r) => ({
          ...r,
          x: round1(r.x),
          y: round1(r.y),
          width: round1(r.width),
          height: round1(r.height),
        })),
      },
    });
  }
  await browser.close();
  tasks.sort((a, b) => a.taskId.localeCompare(b.taskId));
  fs.writeFileSync(path.join(OUTPUT_DIR, "manifest.json"), JSON.stringify(tasks, null, 2));
  console.log(`Rendered ${tasks.length} tasks to ${OUTPUT_DIR}`);
}

main().catch((err) => {
  console.error("Render failed:", err);
  process.exit(1);
});

