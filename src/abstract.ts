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

export interface TokenOptions {
  options: string[];
  choice: string;
}

// Full token set on every task: the option SET is identical across tasks, so
// it cannot leak the truth (a nearest-neighbor subset would). Only the truth's
// slot varies, assigned independently of the token value.
export function tokenOptions(
  truthPx: number,
  tokens: number[],
  truthLetter: string,
): TokenOptions {
  const letters = ["A", "B", "C", "D", "E", "F", "G"];
  if (!tokens.includes(truthPx)) throw new Error(`Truth ${truthPx} outside token set`);
  const truthIndex = letters.indexOf(truthLetter);
  if (truthIndex < 0 || truthIndex >= tokens.length)
    throw new Error(`Truth letter ${truthLetter} outside option range`);
  const others = [...tokens].sort((a, b) => a - b).filter((v) => v !== truthPx);
  const placed: number[] = [];
  for (let i = 0; i < tokens.length; i++) {
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

// Balanced letter multiset for counts that do not divide evenly: counts differ
// by at most one, extras fall on shuffled letters, order shuffled.
export function balancedLetters(count: number, letters: string[], seed: string): string[] {
  const rng = mulberry32(fnv1a(`balanced-letters:${seed}`));
  const base = Math.floor(count / letters.length);
  const extras = shuffled([...letters], rng).slice(0, count % letters.length);
  const sequence: string[] = [];
  for (const letter of letters) {
    const n = base + (extras.includes(letter) ? 1 : 0);
    for (let i = 0; i < n; i++) sequence.push(letter);
  }
  return shuffled(sequence, rng);
}

export interface CrossedAxis {
  key: string;
  levels: unknown[];
}

export interface SpanConstraint {
  group: (slot: number) => string;
  axisKey: string;
}

export interface UniqueConstraint {
  group: (slot: number) => string;
  axisKeys: string[];
}

// Seeded rejection sampler: shuffles each axis multiset independently until
// every span group covers every level of its axis, every distinct group holds
// no repeated level, and every unique group holds no repeated level tuple.
// Deterministic; throws instead of silently biasing.
export function assignCrossed(
  slotCount: number,
  axes: CrossedAxis[],
  span: SpanConstraint[],
  distinct: SpanConstraint[],
  unique: UniqueConstraint[],
  seed: string,
): Record<string, unknown>[] {
  for (const axis of axes) {
    if (axis.levels.length !== slotCount)
      throw new Error(`Axis ${axis.key} has ${axis.levels.length} levels for ${slotCount} slots`);
  }
  const rng = mulberry32(fnv1a(`crossed:${seed}`));
  for (let attempt = 0; attempt < 20000; attempt++) {
    const shuffledAxes = new Map<string, unknown[]>();
    for (const axis of axes) shuffledAxes.set(axis.key, shuffled(axis.levels, rng));
    const valuesFor = (constraint: SpanConstraint) => {
      const groups = new Map<string, unknown[]>();
      for (let slot = 0; slot < slotCount; slot++) {
        const key = constraint.group(slot);
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key)!.push(shuffledAxes.get(constraint.axisKey)![slot]);
      }
      return groups;
    };
    const spansHold = span.every((constraint) => {
      const axis = axes.find((a) => a.key === constraint.axisKey)!;
      return [...valuesFor(constraint).values()].every(
        (values) => new Set(values).size === new Set(axis.levels).size,
      );
    });
    const distinctHold = distinct.every((constraint) =>
      [...valuesFor(constraint).values()].every((values) => new Set(values).size === values.length),
    );
    const uniqueHold = unique.every((constraint) => {
      const groups = new Map<string, string[]>();
      for (let slot = 0; slot < slotCount; slot++) {
        const key = constraint.group(slot);
        if (!groups.has(key)) groups.set(key, []);
        groups
          .get(key)!
          .push(constraint.axisKeys.map((axisKey) => String(shuffledAxes.get(axisKey)![slot])).join("|"));
      }
      return [...groups.values()].every((tuples) => new Set(tuples).size === tuples.length);
    });
    if (spansHold && distinctHold && uniqueHold) {
      return Array.from({ length: slotCount }, (_, slot) => {
        const assignment: Record<string, unknown> = {};
        for (const axis of axes) assignment[axis.key] = shuffledAxes.get(axis.key)![slot];
        return assignment;
      });
    }
  }
  throw new Error(`No crossed assignment found for ${seed}`);
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

// flow: 4 dirs x 2 themes x 2 variants = 16. Item counts overlap across
// directions (3: row/column/grid-2col; 4: all four; 6: both grids) so no count
// value identifies a direction. Grid-3col never takes 3: a single row of three
// would be indistinguishable from a row.
const FLOW_COUNTS: Record<FlowDirection, number[]> = {
  row: [3, 3, 4, 4],
  column: [3, 3, 4, 4],
  "grid-2col": [3, 3, 4, 6],
  "grid-3col": [4, 4, 6, 6],
};
for (const [direction, theme, variant] of fullCross<FlowDirection | Theme | ContentVariant>(
  ["row", "column", "grid-2col", "grid-3col"],
  ["light", "dark"],
  ["uniform", "variable"],
)) {
  const dir = direction as FlowDirection;
  const cells: [Theme, ContentVariant][] = [
    ["light", "uniform"],
    ["light", "variable"],
    ["dark", "uniform"],
    ["dark", "variable"],
  ];
  const order = shuffled(
    [0, 1, 2, 3],
    mulberry32(fnv1a(`flow-counts:${dir}`)),
  );
  const cellIndex = cells.findIndex(([t, v]) => t === theme && v === variant);
  abstractTasks.push({
    family: "flow",
    direction: dir,
    justify_content: "start",
    align_items: "center",
    gap_px: 16,
    padding_px: 24,
    item_count: FLOW_COUNTS[dir]![order[cellIndex]!],
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

// gap: 16 tasks, each token >= 2. Tokens are fixed slots; theme, direction and
// truth letter are shuffled independently under crossing constraints, so no
// nuisance axis predicts the token.
const gapPlan: { token: number; direction: FlowDirection; theme: Theme; letter: string }[] = [];
{
  const tokens = [0, 0, 4, 4, 8, 8, 8, 12, 12, 16, 16, 16, 24, 24, 32, 32];
  const group = (slot: number) => `token:${tokens[slot]}`;
  const assigned = assignCrossed(
    tokens.length,
    [
      { key: "theme", levels: [...Array<Theme>(8).fill("light"), ...Array<Theme>(8).fill("dark")] },
      { key: "direction", levels: [...Array<FlowDirection>(8).fill("row"), ...Array<FlowDirection>(8).fill("column")] },
      { key: "letter", levels: balancedLetters(tokens.length, ["A", "B", "C", "D", "E", "F", "G"], "gap") },
    ],
    [
      { group, axisKey: "theme" },
      { group, axisKey: "direction" },
    ],
    [{ group, axisKey: "letter" }],
    [{ group, axisKeys: ["theme", "direction"] }],
    "gap",
  );
  const rng = mulberry32(fnv1a("gap:order"));
  for (const i of shuffled(tokens.map((_, slot) => slot), rng)) {
    gapPlan.push({
      token: tokens[i]!,
      direction: assigned[i]!["direction"] as FlowDirection,
      theme: assigned[i]!["theme"] as Theme,
      letter: assigned[i]!["letter"] as string,
    });
  }
}
{
  gapPlan.forEach((plan) => {
    const sampled = tokenOptions(plan.token, GAP_TOKENS, plan.letter);
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

// pad: 16 tasks across 5 tokens. Same crossed construction as gap.
const padPlan: { token: number; direction: FlowDirection; theme: Theme; letter: string }[] = [];
{
  const tokens = [8, 8, 8, 16, 16, 16, 16, 24, 24, 24, 32, 32, 32, 48, 48, 48];
  const group = (slot: number) => `token:${tokens[slot]}`;
  const assigned = assignCrossed(
    tokens.length,
    [
      { key: "theme", levels: [...Array<Theme>(8).fill("light"), ...Array<Theme>(8).fill("dark")] },
      { key: "direction", levels: [...Array<FlowDirection>(8).fill("row"), ...Array<FlowDirection>(8).fill("column")] },
      { key: "letter", levels: balancedLetters(tokens.length, ["A", "B", "C", "D", "E"], "pad") },
    ],
    [
      { group, axisKey: "theme" },
      { group, axisKey: "direction" },
    ],
    [{ group, axisKey: "letter" }],
    [{ group, axisKeys: ["theme", "direction"] }],
    "pad",
  );
  const rng = mulberry32(fnv1a("pad:order"));
  for (const i of shuffled(tokens.map((_, slot) => slot), rng)) {
    padPlan.push({
      token: tokens[i]!,
      direction: assigned[i]!["direction"] as FlowDirection,
      theme: assigned[i]!["theme"] as Theme,
      letter: assigned[i]!["letter"] as string,
    });
  }
}
{
  padPlan.forEach((plan) => {
    const sampled = tokenOptions(plan.token, PAD_TOKENS, plan.letter);
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
