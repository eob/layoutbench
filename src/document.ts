import type {
  DocumentDesign,
  LayoutFamily,
  Specimen,
  Theme,
} from "./types.ts";
import {
  assignCrossed,
  balancedLetters,
  fnv1a,
  mulberry32,
  shuffled,
  stratifiedLetters,
  tokenOptions,
} from "./abstract.ts";

export const SENTENCES = [
  "Quiet harbors shelter wooden boats during autumn storms.",
  "Fresh bread and warm soup welcome tired travelers.",
  "River birches lean over slow water near old stone bridges.",
  "Cedar smoke drifts through sleepy mountain villages.",
  "Wild geese cross silver skies in loose wavering lines.",
  "Soft rain settles dusty paths around rural orchards.",
];

export const HEADER_TEXT = "Harbor Report";

export const TABLE_WORDS = [
  "elm",
  "oak",
  "pine",
  "fern",
  "moss",
  "brook",
  "stone",
  "cloud",
  "rain",
];

function fullCross<T>(...axes: T[][]): T[][] {
  return axes.reduce<T[][]>(
    (acc, axis) => acc.flatMap((combo) => axis.map((value) => [...combo, value])),
    [[]],
  );
}

interface DocumentArgs {
  family: LayoutFamily;
  design: Omit<DocumentDesign, "kind" | "options" | "decoded">;
  choice: string;
  options?: string[];
  numericSibling?: LayoutFamily;
  sharedStem?: string;
}

const documentTasks: DocumentArgs[] = [];
const alignChoice = { left: "A", center: "B", right: "C", justify: "D" } as const;

// columns + textjustify share the 8 intersecting renders
// (counts {1,2} x aligns {left,justify} x themes); each family asks its
// own question about the same stimulus. Remaining cells render alone.
const sharedCells = fullCross(
  [1, 2],
  ["left", "justify"] as const,
  ["light", "dark"] as Theme[],
);
sharedCells.forEach(([count, align, theme], cellIndex) => {
  const stem = `shared-cols-${String(cellIndex + 1).padStart(2, "0")}`;
  const design = {
    archetype: "columns" as const,
    theme: theme as Theme,
    column_count: count as number,
    text_align: align as "left" | "justify",
    copy_id: "para-6",
  };
  documentTasks.push({
    family: "columns",
    design: { ...design },
    choice: ["A", "B", "C"][(count as number) - 1]!,
    sharedStem: stem,
  });
  documentTasks.push({
    family: "textjustify",
    design: { ...design },
    choice: alignChoice[align as "left" | "justify"],
    sharedStem: stem,
  });
});

// columns: remaining count-3 cells x 2 aligns x 2 themes = 4
for (const [align, theme] of fullCross(
  ["left", "justify"] as const,
  ["light", "dark"] as Theme[],
)) {
  documentTasks.push({
    family: "columns",
    design: {
      archetype: "columns",
      theme,
      column_count: 3,
      text_align: align,
      copy_id: "para-6",
    },
    choice: "C",
  });
}

// textjustify: remaining center/right x 2 counts x 2 themes = 8
for (const [align, count, theme] of fullCross(
  ["center", "right"] as const,
  [1, 2],
  ["light", "dark"] as Theme[],
)) {
  documentTasks.push({
    family: "textjustify",
    design: {
      archetype: "text",
      theme,
      column_count: count,
      text_align: align,
      copy_id: "para-6",
    },
    choice: alignChoice[align],
  });
}

// headerpad: 3 answers x 3 magnitudes x 2 themes = 18
const headerPairs: { above: number; below: number; choice: string }[] = [
  { above: 24, below: 8, choice: "A" },
  { above: 32, below: 16, choice: "A" },
  { above: 48, below: 24, choice: "A" },
  { above: 8, below: 24, choice: "B" },
  { above: 16, below: 32, choice: "B" },
  { above: 24, below: 48, choice: "B" },
  { above: 16, below: 16, choice: "C" },
  { above: 24, below: 24, choice: "C" },
  { above: 32, below: 32, choice: "C" },
];
for (const theme of ["light", "dark"] as Theme[]) {
  for (const pair of headerPairs) {
    documentTasks.push({
      family: "headerpad",
      design: {
        archetype: "header",
        theme,
        above_px: pair.above,
        below_px: pair.below,
        copy_id: "header-3",
      },
      choice: pair.choice,
      numericSibling: "headerpx",
    });
  }
}

// regionpad: 5 tokens x bordered/bare x themes = 16. Tokens are fixed slots;
// bordered, theme and truth letter shuffle independently under crossing
// constraints, so no nuisance axis predicts the token.
const REGION_TOKENS = [8, 16, 24, 32, 48];
{
  const plan: { token: number; bordered: boolean; theme: Theme; letter: string }[] = [];
  const tokens = [8, 8, 8, 16, 16, 16, 16, 24, 24, 24, 32, 32, 32, 48, 48, 48];
  const group = (slot: number) => `token:${tokens[slot]}`;
  const assigned = assignCrossed(
    tokens.length,
    [
      { key: "bordered", levels: [...Array<boolean>(8).fill(true), ...Array<boolean>(8).fill(false)] },
      { key: "theme", levels: [...Array<Theme>(8).fill("light"), ...Array<Theme>(8).fill("dark")] },
      { key: "letter", levels: balancedLetters(tokens.length, ["A", "B", "C", "D", "E"], "regionpad") },
    ],
    [
      { group, axisKey: "bordered" },
      { group, axisKey: "theme" },
    ],
    [{ group, axisKey: "letter" }],
    [{ group, axisKeys: ["bordered", "theme"] }],
    "regionpad",
  );
  const rng = mulberry32(fnv1a("region:order"));
  for (const i of shuffled(tokens.map((_, slot) => slot), rng)) {
    plan.push({
      token: tokens[i]!,
      bordered: assigned[i]!["bordered"] as boolean,
      theme: assigned[i]!["theme"] as Theme,
      letter: assigned[i]!["letter"] as string,
    });
  }
  plan.forEach((item) => {
    const sampled = tokenOptions(item.token, REGION_TOKENS, item.letter);
    documentTasks.push({
      family: "regionpad",
      design: {
        archetype: "region",
        theme: item.theme,
        pad_px: item.token,
        bordered: item.bordered,
        copy_id: "para-3",
      },
      choice: sampled.choice,
      options: sampled.options,
      numericSibling: "regionpx",
    });
  });
}

// tablepad: 4 tokens x 3 table sizes = 12. Themes shuffle under explicit
// constraints: every token and every table size spans both themes.
{
  const plan: { token: number; rows: number; cols: number; theme: Theme }[] = [];
  const combos = fullCross([4, 8, 12, 16], [
    [2, 2],
    [2, 3],
    [3, 3],
  ]);
  const assigned = assignCrossed(
    combos.length,
    [{ key: "theme", levels: [...Array<Theme>(6).fill("light"), ...Array<Theme>(6).fill("dark")] }],
    [
      { group: (slot) => `token:${combos[slot]![0]}`, axisKey: "theme" },
      { group: (slot) => `size:${(combos[slot]![1] as number[]).join("x")}`, axisKey: "theme" },
    ],
    [],
    [],
    "tablepad",
  );
  combos.forEach(([token, size], i) => {
    plan.push({
      token: token as number,
      rows: (size as number[])[0]!,
      cols: (size as number[])[1]!,
      theme: assigned[i]!["theme"] as Theme,
    });
  });
  const letters = stratifiedLetters(plan.map((t) => `${t.rows}x${t.cols}`), "tablepad", ["A", "B", "C", "D"]);
  plan.forEach((item, index) => {
    const sampled = tokenOptions(item.token, [4, 8, 12, 16], letters[index]!);
    documentTasks.push({
      family: "tablepad",
      design: {
        archetype: "table",
        theme: item.theme,
        cell_pad_px: item.token,
        rows: item.rows,
        cols: item.cols,
      },
      choice: sampled.choice,
      options: sampled.options,
    });
  });
}

export function buildDocumentSpecimens(): Specimen[] {
  const specimens: Specimen[] = [];
  const counters = new Map<LayoutFamily, number>();
  for (const task of documentTasks) {
    const index = (counters.get(task.family) ?? 0) + 1;
    counters.set(task.family, index);
    const stem = `${task.family}-${String(index).padStart(2, "0")}`;
    const imageStem = task.sharedStem ?? stem;
    specimens.push({
      id: `layoutbench-${stem}`,
      family: task.family,
      groupId: imageStem,
      imageFilename: `${imageStem}.png`,
      design: { kind: "document", ...task.design, options: task.options },
      groundTruth: { choice: task.choice },
      options: task.options,
    });
    if (task.numericSibling === "headerpx") {
      specimens.push({
        id: `layoutbench-headerpx-${String(index).padStart(2, "0")}`,
        family: "headerpx",
        groupId: stem,
        imageFilename: `${stem}.png`,
        design: { kind: "document", ...task.design, options: task.options },
        groundTruth: {
          above_px: task.design.above_px!,
          below_px: task.design.below_px!,
        },
        options: task.options,
      });
    }
    if (task.numericSibling === "regionpx") {
      specimens.push({
        id: `layoutbench-regionpx-${String(index).padStart(2, "0")}`,
        family: "regionpx",
        groupId: stem,
        imageFilename: `${stem}.png`,
        design: { kind: "document", ...task.design, options: task.options },
        groundTruth: { pad_px: task.design.pad_px! },
        options: task.options,
      });
    }
  }
  return specimens;
}
