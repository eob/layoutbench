import { COPY, type QualitativeScene } from "./qualitative-types.ts";
import catalog from "../config/qualitative.json";

const paragraph = [
  "Quiet harbors shelter wooden boats during autumn storms. Fresh bread and warm soup welcome tired travelers. River birches lean over slow water near old stone bridges. Cedar smoke drifts through sleepy mountain villages. Wild geese cross silver skies in loose wavering lines. Soft rain settles dusty paths around rural orchards.",
  "Gentle breezes carry orchard scents along the village lanes. Travelers gather near the old stone well before dusk. Willow branches sweep the calm river while swallows circle overhead. Golden leaves drift across the garden paths. Warm light shines through cottage windows as the evening settles over distant hills.",
];

export function buildQualitativeScenes(): QualitativeScene[] {
  const scenes: QualitativeScene[] = [];
  const families = Object.keys(catalog).filter(f => !["topflow", "nestedflow", "nestedwrap"].includes(f));
  for (const family of families) {
    const options = (catalog as Record<string, { options: Record<string, string> }>)[family]!.options;
    for (const answer of Object.keys(options)) for (const theme of ["light", "dark"] as const) for (const variant of [0, 1]) {
      const words = COPY[variant]!;
      const tile = (i: number, style = "", name?: string) => `<div class="tile" data-box="${name ?? `item-${i}`}" style="${style}">${words[i % words.length]}</div>`;
      let html = "", css = "";
      const factors: Record<string, string | number> = {};
      const frame = (content: string, style = "") => `<div class="frame" data-box="frame" style="${style}">${content}</div>`;
      const direction = variant === 0 ? "row" : "column";
      if (family === "direction") {
        html = frame(Array.from({ length: 4 }, (_, i) => tile(i)).join(""), `display:flex;flex-direction:${answer};gap:20px;align-items:center;justify-content:center`);
        css = ".tile{width:130px;height:64px}";
      } else if (family === "distribution" || family === "crossalign") {
        factors.direction = direction;
        const justify = { start: "flex-start", end: "flex-end", center: "center", between: "space-between", around: "space-around", evenly: "space-evenly" }[answer] ?? "center";
        const align = { start: "flex-start", end: "flex-end", center: "center", stretch: "stretch" }[answer] ?? "center";
        html = frame(Array.from({ length: 3 }, (_, i) => {
          const main = direction === "row" ? "width" : "height";
          const cross = direction === "row" ? "height" : "width";
          const size = family === "distribution" ? 78 : [66, 108, 150][i]!;
          return tile(i, `${main}:${direction === "row" ? 100 : 62}px;${family === "crossalign" && answer === "stretch" ? "" : `${cross}:${size}px`}`);
        }).join(""), `display:flex;flex-direction:${direction};justify-content:${family === "distribution" ? justify : "center"};align-items:${family === "crossalign" ? align : "center"};gap:${family === "distribution" && ["between", "around", "evenly"].includes(answer) ? 0 : 12}px`);
      } else if (family === "textalign" || family === "textcolumns") {
        const count = family === "textcolumns" ? Number(answer) : 1;
        html = frame(Array.from({ length: count }, (_, i) => `<div class="prose" data-box="text-${i}" data-lines="text-${i}" style="text-align:${family === "textalign" ? answer : variant ? "justify" : "left"}">${paragraph[variant]}</div>`).join(""), `display:grid;grid-template-columns:repeat(${count},1fr);gap:30px;padding:24px`);
        css = `.prose{font-size:${count === 3 ? 15 : 18}px;line-height:1.55}${family === "textalign" ? ".frame{width:530px;height:440px}" : ""}`;
      } else if (["gridcols", "gridrows", "gridgaps", "gridtracks", "gridspan"].includes(family)) {
        const cols = family === "gridcols" ? Number(answer) : family === "gridrows" ? 2 + variant : 3;
        const rows = family === "gridrows" ? Number(answer) : family === "gridspan" ? 2 : family === "gridcols" ? 2 + variant : 3;
        const gx = family === "gridgaps" && answer === "horizontal" ? 48 : 16;
        const gy = family === "gridgaps" && answer === "vertical" ? 48 : 16;
        const tracks = family === "gridtracks" && answer !== "equal" ? answer === "left" ? "2fr 1fr 1fr" : "1fr 1fr 2fr" : `repeat(${cols},1fr)`;
        const content = family === "gridspan" ? tile(0, `grid-column:1 / span ${answer};grid-row:1`, "span") + Array.from({ length: 3 }, (_, i) => tile(i + 1, `grid-column:${i + 1};grid-row:2`, `guide-${i}`)).join("") : Array.from({ length: cols * rows }, (_, i) => tile(i)).join("");
        html = frame(content, `display:grid;grid-template-columns:${tracks};grid-template-rows:repeat(${rows},1fr);column-gap:${gx}px;row-gap:${gy}px;padding:20px`);
        css = ".tile{font-size:15px}";
      } else if (family === "wrapcount" || family === "wrapalign") {
        const count = family === "wrapcount" ? 6 : 5;
        const columns = family === "wrapcount" ? 6 / Number(answer) : 3;
        const width = (656 - (columns - 1) * 16) / columns;
        html = frame(Array.from({ length: count }, (_, i) => tile(i, `width:${width}px;height:72px`)).join(""), `display:flex;flex-wrap:wrap;align-content:center;gap:20px 16px;justify-content:${family === "wrapalign" ? { left: "flex-start", center: "center", right: "flex-end" }[answer] : "flex-start"}`);
        css = ".tile{font-size:14px}";
      } else if (family === "gapcompare") {
        factors.direction = direction;
        html = frame([0, 1, 2].map(i => tile(i, `${i > 0 ? `margin-${direction === "row" ? "left" : "top"}:${answer === (i === 1 ? "first" : "last") ? 60 : 20}px;` : ""}width:140px;height:64px`)).join(""), `display:flex;flex-direction:${direction};align-items:center;justify-content:center`);
      } else if (family === "padcompare") {
        const horizontal = answer === "horizontal" ? 84 : 28;
        const vertical = answer === "vertical" ? 84 : 28;
        html = frame(`<div class="tile inset" data-box="inset">${paragraph[variant]}</div>`, `padding:${vertical}px ${horizontal}px`);
        css = ".inset{height:100%;width:100%;padding:20px;line-height:1.7;display:block}";
      } else if (family === "blockalign") {
        html = frame(`<div class="tile block" data-box="block" data-lines="block" style="text-align:${variant ? "right" : "left"}">${paragraph[variant]}</div>`, `display:flex;align-items:center;justify-content:${{ left: "flex-start", center: "center", right: "flex-end" }[answer]}`);
        css = ".block{width:340px;padding:20px;display:block;line-height:1.55;font-size:16px}";
      } else if (family === "widthcompare") {
        html = frame(tile(0, `width:${answer === "first" ? 340 : answer === "equal" ? 260 : 180}px;height:200px`) + tile(1, `width:${answer === "last" ? 340 : answer === "equal" ? 260 : 180}px;height:200px`), "display:flex;align-items:center;justify-content:center;gap:24px");
      } else if (family === "groupgap") {
        const within = answer === "within" ? 60 : 20;
        const between = answer === "between" ? 60 : 20;
        html = frame([0, 1].map(g => `<div class="group" data-box="group-${g}" style="gap:${within}px"><div class="caption">${g ? "Meadow" : "Harbor"}</div>${[0, 1].map(i => tile(g * 2 + i, "width:100px;height:96px")).join("")}</div>`).join(""), `display:flex;align-items:center;justify-content:center;gap:${between}px`);
        css = ".group{display:flex;position:relative}.caption{position:absolute;top:-32px;left:0;color:var(--muted)}";
      }
      scenes.push({ id: `${family}-${answer}-${theme}-${variant}`, theme, variant, html, css, questions: [{ family, answer }], factors });
    }
  }
  return scenes;
}
