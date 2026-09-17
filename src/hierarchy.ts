import type { QualitativeScene } from "./qualitative-types.ts";

type Direction = "row" | "column";
type ChildFlow = Direction | "wrapped";
type Alignment = "left" | "center" | "right";

const WORDS = [
  ["Elm", "Oak", "Pine", "Fern", "Moss"],
  ["Ash", "Reed", "Beech", "Sage", "Iris"],
];
const COPY = [
  "Quiet boats drift past the old harbor. Cedar branches sway in a gentle breeze.",
  "Willow trees shade the garden path. Autumn leaves settle beside the stone bridge.",
];

function hierarchyScene(
  id: string,
  parent: Direction,
  child: ChildFlow,
  theme: "light" | "dark",
  variant: number,
  alignment?: Alignment,
): QualitativeScene {
  const width = parent === "row" ? (child === "wrapped" ? 108 : 60) : (child === "wrapped" ? 180 : 112);
  const justify = { left: "flex-start", center: "center", right: "flex-end" }[alignment ?? "left"];
  const children = WORDS[variant]!.map((word, i) => `<div class="hierarchy-child" data-box="child-${i}">${word}</div>`).join("");
  const notes = `<section class="hierarchy-section hierarchy-notes" data-box="section-0"><h2 class="hierarchy-title">Field notes</h2><div class="hierarchy-target" data-box="target">${children}</div></section>`;
  const log = `<section class="hierarchy-section hierarchy-log" data-box="section-1"><h2 class="hierarchy-title">Harbor log</h2><p class="hierarchy-copy">${COPY[variant]}</p></section>`;
  return {
    id,
    theme,
    variant,
    factors: { parent, child, ...(alignment ? { alignment } : {}) },
    questions: alignment
      ? [{ family: "nestedwrap", answer: alignment }]
      : [{ family: "topflow", answer: parent }, { family: "nestedflow", answer: child }],
    html: `<main class="hierarchy-frame" data-box="frame">${variant === 0 ? notes + log : log + notes}</main>`,
    css: `
      .hierarchy-frame{width:720px;height:480px;display:flex;flex-direction:${parent};gap:20px;padding:20px;border:2px solid var(--line);background:var(--panel);color:var(--ink)}
      .hierarchy-section{min-width:0;min-height:0;border:2px solid var(--line);padding:14px;display:flex;flex-direction:column}
      .hierarchy-notes{flex:0 0 ${parent === "row" ? 396 : 280}px}
      .hierarchy-log{flex:1}
      .hierarchy-title{margin:0 0 12px;font-size:18px;font-weight:600;line-height:24px}
      .hierarchy-copy{margin:0;font-size:15px;line-height:22px;color:var(--muted)}
      .hierarchy-target{flex:1;min-height:0;border:2px solid var(--line);display:flex;flex-direction:${child === "column" ? "column" : "row"};flex-wrap:${child === "wrapped" ? "wrap" : "nowrap"};gap:12px;align-items:flex-start;align-content:flex-start;justify-content:${justify}}
      .hierarchy-child{flex:0 0 auto;width:${child === "column" ? 180 : width}px;height:${child === "column" ? 30 : 38}px;border:1px solid var(--line);background:var(--tile);padding:4px 6px;font-size:14px;line-height:${child === "column" ? 20 : 28}px;text-align:center}
    `,
  };
}

export function buildHierarchyScenes(): QualitativeScene[] {
  const scenes: QualitativeScene[] = [];
  for (const parent of ["row", "column"] as const)
    for (const child of ["row", "column", "wrapped"] as const)
      for (const theme of ["light", "dark"] as const)
        for (const variant of [0, 1]) {
          const scene = hierarchyScene(`h-${String(scenes.length + 1).padStart(2, "0")}`, parent, child, theme, variant);
          if (child === "wrapped") {
            scene.questions.push({ family: "nestedwrap", answer: "left" });
            scene.factors.alignment = "left";
          }
          scenes.push(scene);
        }
  for (const parent of ["row", "column"] as const)
    for (const alignment of ["center", "right"] as const)
      for (const theme of ["light", "dark"] as const)
        for (const variant of [0, 1])
          scenes.push(hierarchyScene(`h-${String(scenes.length + 1).padStart(2, "0")}`, parent, "wrapped", theme, variant, alignment));
  return scenes;
}
