import type {
  AlignOption,
  ContentVariant,
  DistributeOption,
  FlowDirection,
  LayoutFamily,
  Specimen,
  Theme,
} from "./types.ts";

export function fnv1a(text: string): number {
  let hash = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  return hash >>> 0;
}

export function mulberry32(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function shuffled<T>(items: T[], rng: () => number): T[] {
  const rest = [...items];
  const out: T[] = [];
  while (rest.length) {
    const index = Math.floor(rng() * rest.length);
    out.push(rest.splice(index, 1)[0]!);
  }
  return out;
}

function nearestNeighbors(truth: number, tokens: number[], count: number): number[] {
  return [...tokens]
    .filter((t) => t !== truth)
    .sort((a, b) => Math.abs(a - truth) - Math.abs(b - truth))
    .slice(0, count);
}

export interface TokenOptions {
  options: string[];
  choice: string;
}

export function tokenOptions(
  truthPx: number,
  tokens: number[],
  truthLetter: string,
): TokenOptions {
  const letters = ["A", "B", "C", "D"];
  const distractors = nearestNeighbors(truthPx, tokens, 3);
  const ordered = [truthPx, ...distractors].sort((a, b) => a - b);
  const truthIndex = letters.indexOf(truthLetter);
  const others = ordered.filter((v) => v !== truthPx);
  const placed: number[] = [];
  for (let i = 0; i < 4; i++) {
    placed.push(i === truthIndex ? truthPx : others.shift()!);
  }
  return {
    options: placed.map((v) => `${v}px`),
    choice: truthLetter,
  };
}

export function stratifiedLetters(keys: string[], seed: string, letters: string[]): string[] {
  const assigned: string[] = new Array(keys.length);
  const groups = new Map<string, number[]>();
  keys.forEach((key, index) => {
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(index);
  });
  for (const [key, indices] of groups) {
    if (indices.length % letters.length !== 0)
      throw new Error(`Stratum ${key} cannot balance ${letters.length} letters`);
    const rng = mulberry32(fnv1a(`letters:${seed}:${key}`));
    const sequence: string[] = [];
    for (let i = 0; i < indices.length; i++) sequence.push(letters[i % letters.length]!);
    const order = shuffled(sequence, rng);
    indices.forEach((taskIndex, position) => {
      assigned[taskIndex] = order[position]!;
    });
  }
  return assigned;
}

interface AbstractArgs {
  family: LayoutFamily;
  direction: FlowDirection;
  justify_content: DistributeOption;
  align_items: AlignOption;
  gap_px: number;
  padding_px: number;
  item_count: number;
  content_variant: ContentVariant;
  theme: Theme;
  choice: string;
  options?: string[];
  numericSibling?: LayoutFamily;
}

const abstractTasks: AbstractArgs[] = [];

function fullCross<T>(...axes: T[][]): T[][] {
  return axes.reduce<T[][]>(
    (acc, axis) => acc.flatMap((combo) => axis.map((value) => [...combo, value])),
    [[]],
  );
}

// flow: 4 dirs x 2 themes x 2 variants = 16
for (const [direction, theme, variant] of fullCross<FlowDirection | Theme | ContentVariant>(
  ["row", "column", "grid-2col", "grid-3col"],
  ["light", "dark"],
  ["uniform", "variable"],
)) {
  const dir = direction as FlowDirection;
  abstractTasks.push({
    family: "flow",
    direction: dir,
    justify_content: "start",
    align_items: "center",
    gap_px: 16,
    padding_px: 24,
    item_count: dir === "grid-2col" ? 4 : dir === "grid-3col" ? 6 : 3,
    content_variant: variant as ContentVariant,
    theme: theme as Theme,
    choice: { row: "A", column: "B", "grid-2col": "C", "grid-3col": "D" }[dir]!,
  });
}

// distribute: 5 options x 2 flow dirs x 2 themes = 20 (gap fixed 12: no gap confound)
const distributeChoice: Record<DistributeOption, string> = {
  start: "A",
  center: "B",
  end: "C",
  "space-between": "D",
  "space-around": "E",
};
for (const [option, direction, theme] of fullCross(
  ["start", "center", "end", "space-between", "space-around"] as DistributeOption[],
  ["row", "column"] as FlowDirection[],
  ["light", "dark"] as Theme[],
)) {
  abstractTasks.push({
    family: "distribute",
    direction,
    justify_content: option,
    align_items: "center",
    gap_px: 12,
    padding_px: 24,
    item_count: 3,
    content_variant: "uniform",
    theme,
    choice: distributeChoice[option],
  });
}

// align: 4 options x 2 flow dirs x 2 themes = 16 (variable sizes: stretch is visible)
const alignChoice: Record<AlignOption, string> = {
  start: "A",
  center: "B",
  end: "C",
  stretch: "D",
};
for (const [option, direction, theme] of fullCross(
  ["start", "center", "end", "stretch"] as AlignOption[],
  ["row", "column"] as FlowDirection[],
  ["light", "dark"] as Theme[],
)) {
  abstractTasks.push({
    family: "align",
    direction,
    justify_content: "start",
    align_items: option,
    gap_px: 12,
    padding_px: 24,
    item_count: 3,
    content_variant: "variable",
    theme,
    choice: alignChoice[option],
  });
}

const GAP_TOKENS = [0, 4, 8, 12, 16, 24, 32];
const PAD_TOKENS = [8, 16, 24, 32, 48];

// gap: 16 tasks, each token >= 2, row/col x theme balanced
const gapPlan: { token: number; direction: FlowDirection; theme: Theme }[] = [];
{
  const tokens = [0, 0, 4, 4, 8, 8, 8, 12, 12, 16, 16, 16, 24, 24, 32, 32];
  const dirs: FlowDirection[] = tokens.map((_, i) => (i % 2 === 0 ? "row" : "column"));
  const themes: Theme[] = tokens.map((_, i) => (i % 4 < 2 ? "light" : "dark"));
  const rng = mulberry32(fnv1a("gap:nuisance"));
  const order = shuffled(tokens.map((_, i) => i), rng);
  for (const i of order) {
    gapPlan.push({ token: tokens[i]!, direction: dirs[i]!, theme: themes[i]! });
  }
}
{
  const letters = stratifiedLetters(gapPlan.map((t) => `${t.theme}:${t.direction}`), "gap", ["A", "B", "C", "D"]);
  gapPlan.forEach((plan, index) => {
    const sampled = tokenOptions(plan.token, GAP_TOKENS, letters[index]!);
    abstractTasks.push({
      family: "gap",
      direction: plan.direction,
      justify_content: "start",
      align_items: "center",
      gap_px: plan.token,
      padding_px: 40,
      item_count: 3,
      content_variant: "uniform",
      theme: plan.theme,
      choice: sampled.choice,
      options: sampled.options,
      numericSibling: "gapnum",
    });
  });
}

// pad: 16 tasks across 5 tokens, row/col x theme balanced
const padPlan: { token: number; direction: FlowDirection; theme: Theme }[] = [];
{
  const tokens = [8, 8, 8, 16, 16, 16, 16, 24, 24, 24, 32, 32, 32, 48, 48, 48];
  const dirs: FlowDirection[] = tokens.map((_, i) => (i % 2 === 0 ? "row" : "column"));
  const themes: Theme[] = tokens.map((_, i) => (i % 4 < 2 ? "light" : "dark"));
  const rng = mulberry32(fnv1a("pad:nuisance"));
  const order = shuffled(tokens.map((_, i) => i), rng);
  for (const i of order) {
    padPlan.push({ token: tokens[i]!, direction: dirs[i]!, theme: themes[i]! });
  }
}
{
  const letters = stratifiedLetters(padPlan.map((t) => `${t.theme}:${t.direction}`), "pad", ["A", "B", "C", "D"]);
  padPlan.forEach((plan, index) => {
    const sampled = tokenOptions(plan.token, PAD_TOKENS, letters[index]!);
    abstractTasks.push({
      family: "pad",
      direction: plan.direction,
      justify_content: "start",
      align_items: "center",
      gap_px: 20,
      padding_px: plan.token,
      item_count: 3,
      content_variant: "uniform",
      theme: plan.theme,
      choice: sampled.choice,
      options: sampled.options,
    });
  });
}

export function buildAbstractSpecimens(): Specimen[] {
  const specimens: Specimen[] = [];
  const counters = new Map<LayoutFamily, number>();
  for (const task of abstractTasks) {
    const index = (counters.get(task.family) ?? 0) + 1;
    counters.set(task.family, index);
    const stem = `${task.family}-${String(index).padStart(2, "0")}`;
    const {
      family,
      choice,
      options,
      numericSibling,
      ...design
    } = task;
    specimens.push({
      id: `layoutbench-${stem}`,
      family,
      groupId: stem,
      imageFilename: `${stem}.png`,
      design: { kind: "abstract", ...design, options },
      groundTruth: { choice },
      options,
    });
    if (numericSibling === "gapnum") {
      specimens.push({
        id: `layoutbench-gapnum-${String(index).padStart(2, "0")}`,
        family: "gapnum",
        groupId: stem,
        imageFilename: `${stem}.png`,
        design: { kind: "abstract", ...design, options },
        groundTruth: { gap_px: task.gap_px },
        options,
      });
    }
  }
  return specimens;
}
