import type {
  LayoutSpecimenConfig,
  LayoutDirection,
  JustifyContent,
  AlignItems,
  GapToken,
  PaddingToken,
  BackgroundTheme,
  ItemContentVariant,
} from "./types.ts";

export const SPECIMENS: LayoutSpecimenConfig[] = [];

function addSpecimen(cfg: Omit<LayoutSpecimenConfig, "id"> & { id?: string }) {
  const index = SPECIMENS.length + 1;
  const id = cfg.id || `layoutbench-${String(index).padStart(3, "0")}`;
  SPECIMENS.push({ ...cfg, id });
}

// -------------------------------------------------------------
// 1. DIRECTION SWEEP (Holding justify: start, align: center, gap: 16px, pad: 24px)
// -------------------------------------------------------------
const directions: { dir: LayoutDirection; count: number }[] = [
  { dir: "row", count: 3 },
  { dir: "column", count: 3 },
  { dir: "grid-2col", count: 4 },
  { dir: "grid-3col", count: 6 },
];

for (const d of directions) {
  for (const variant of ["uniform", "variable"] as ItemContentVariant[]) {
    addSpecimen({
      direction: d.dir,
      justify_content: "start",
      align_items: "center",
      gap: "16px",
      gap_px: 16,
      padding: "24px",
      padding_px: 24,
      item_count: d.count,
      content_variant: variant,
      theme: "light",
      title: `${d.dir.toUpperCase()} Layout Flow`,
      subtitle: `Direction test: ${d.dir} with ${variant} items`,
      tag: "Direction",
    });
  }
}

// -------------------------------------------------------------
// 2. JUSTIFY-CONTENT SWEEP (Row mode, testing main-axis distribution)
// -------------------------------------------------------------
const justifyOptions: JustifyContent[] = ["start", "center", "end", "space-between", "space-around"];

for (const jc of justifyOptions) {
  for (const count of [2, 3]) {
    addSpecimen({
      direction: "row",
      justify_content: jc,
      align_items: "center",
      gap: jc.startsWith("space") ? "0px" : "12px",
      gap_px: jc.startsWith("space") ? 0 : 12,
      padding: "24px",
      padding_px: 24,
      item_count: count,
      content_variant: "uniform",
      theme: "light",
      title: `Justify Content: ${jc}`,
      subtitle: `Main-axis distribution: ${jc} (${count} items)`,
      tag: "Justification",
    });
  }
}

// -------------------------------------------------------------
// 3. ALIGN-ITEMS SWEEP (Row mode with variable heights to make cross-axis obvious)
// -------------------------------------------------------------
const alignOptions: AlignItems[] = ["start", "center", "end", "stretch"];

for (const ai of alignOptions) {
  addSpecimen({
    direction: "row",
    justify_content: "start",
    align_items: ai,
    gap: "16px",
    gap_px: 16,
    padding: "24px",
    padding_px: 24,
    item_count: 3,
    content_variant: "variable",
    theme: "light",
    title: `Row Align Items: ${ai}`,
    subtitle: `Cross-axis vertical alignment: ${ai}`,
    tag: "Alignment",
  });
}

// -------------------------------------------------------------
// 4. ALIGN-ITEMS IN COLUMN MODE (Cross-axis is horizontal)
// -------------------------------------------------------------
for (const ai of alignOptions) {
  addSpecimen({
    direction: "column",
    justify_content: "start",
    align_items: ai,
    gap: "12px",
    gap_px: 12,
    padding: "24px",
    padding_px: 24,
    item_count: 3,
    content_variant: "variable",
    theme: "light",
    title: `Column Align Items: ${ai}`,
    subtitle: `Cross-axis horizontal alignment: ${ai}`,
    tag: "Alignment",
  });
}

// -------------------------------------------------------------
// 5. GAP TOKEN SWEEP (Row & Column)
// -------------------------------------------------------------
const gapTokens: { token: GapToken; px: number }[] = [
  { token: "0px", px: 0 },
  { token: "4px", px: 4 },
  { token: "8px", px: 8 },
  { token: "12px", px: 12 },
  { token: "16px", px: 16 },
  { token: "24px", px: 24 },
  { token: "32px", px: 32 },
];

for (const g of gapTokens) {
  // Row gap
  addSpecimen({
    direction: "row",
    justify_content: "start",
    align_items: "center",
    gap: g.token,
    gap_px: g.px,
    padding: "24px",
    padding_px: 24,
    item_count: 3,
    content_variant: "uniform",
    theme: "light",
    title: `Row Gap: ${g.token}`,
    subtitle: `Spacing scale test: ${g.token} (${g.px}px)`,
    tag: "GapSpacing",
  });

  // Column gap
  addSpecimen({
    direction: "column",
    justify_content: "start",
    align_items: "stretch",
    gap: g.token,
    gap_px: g.px,
    padding: "24px",
    padding_px: 24,
    item_count: 3,
    content_variant: "uniform",
    theme: "light",
    title: `Column Gap: ${g.token}`,
    subtitle: `Vertical spacing test: ${g.token} (${g.px}px)`,
    tag: "GapSpacing",
  });
}

// -------------------------------------------------------------
// 6. PADDING TOKEN SWEEP
// -------------------------------------------------------------
const paddingTokens: { token: PaddingToken; px: number }[] = [
  { token: "8px", px: 8 },
  { token: "16px", px: 16 },
  { token: "24px", px: 24 },
  { token: "32px", px: 32 },
];

for (const p of paddingTokens) {
  addSpecimen({
    direction: "row",
    justify_content: "start",
    align_items: "center",
    gap: "16px",
    gap_px: 16,
    padding: p.token,
    padding_px: p.px,
    item_count: 3,
    content_variant: "uniform",
    theme: "light",
    title: `Container Padding: ${p.token}`,
    subtitle: `Inset border token test: ${p.token} (${p.px}px)`,
    tag: "Padding",
  });
}

// -------------------------------------------------------------
// 7. GRID LAYOUT SWEEPS (2-col and 3-col variations)
// -------------------------------------------------------------
const gridConfigs = [
  { dir: "grid-2col" as LayoutDirection, items: 4, gap: "8px" as GapToken, px: 8 },
  { dir: "grid-2col" as LayoutDirection, items: 4, gap: "16px" as GapToken, px: 16 },
  { dir: "grid-2col" as LayoutDirection, items: 4, gap: "24px" as GapToken, px: 24 },
  { dir: "grid-3col" as LayoutDirection, items: 6, gap: "8px" as GapToken, px: 8 },
  { dir: "grid-3col" as LayoutDirection, items: 6, gap: "16px" as GapToken, px: 16 },
  { dir: "grid-3col" as LayoutDirection, items: 6, gap: "24px" as GapToken, px: 24 },
];

for (const gc of gridConfigs) {
  addSpecimen({
    direction: gc.dir,
    justify_content: "start",
    align_items: "stretch",
    gap: gc.gap,
    gap_px: gc.px,
    padding: "24px",
    padding_px: 24,
    item_count: gc.items,
    content_variant: "uniform",
    theme: "light",
    title: `${gc.dir.toUpperCase()} Grid Matrix`,
    subtitle: `Multi-column grid with gap ${gc.gap}`,
    tag: "Grid",
  });
}

// -------------------------------------------------------------
// 8. REALISTIC UI PATTERNS (Archetypes)
// -------------------------------------------------------------
const realWorldPatterns: {
  title: string;
  subtitle: string;
  direction: LayoutDirection;
  justify: JustifyContent;
  align: AlignItems;
  gap: GapToken;
  gap_px: number;
  padding: PaddingToken;
  padding_px: number;
  count: number;
  variant: ItemContentVariant;
}[] = [
  {
    title: "Navbar Action Header",
    subtitle: "Header pattern: logo on left, actions on right",
    direction: "row",
    justify: "space-between",
    align: "center",
    gap: "0px",
    gap_px: 0,
    padding: "16px",
    padding_px: 16,
    count: 2,
    variant: "uniform",
  },
  {
    title: "Action Button Cluster",
    subtitle: "Form footer: Cancel and Save right-aligned",
    direction: "row",
    justify: "end",
    align: "center",
    gap: "12px",
    gap_px: 12,
    padding: "16px",
    padding_px: 16,
    count: 2,
    variant: "uniform",
  },
  {
    title: "Centered Modal Actions",
    subtitle: "Dialog choices centered on canvas",
    direction: "row",
    justify: "center",
    align: "center",
    gap: "16px",
    gap_px: 16,
    padding: "24px",
    padding_px: 24,
    count: 2,
    variant: "uniform",
  },
  {
    title: "Stacked Form Fields",
    subtitle: "Standard vertical input stack",
    direction: "column",
    justify: "start",
    align: "stretch",
    gap: "12px",
    gap_px: 12,
    padding: "24px",
    padding_px: 24,
    count: 3,
    variant: "uniform",
  },
  {
    title: "Metrics Overview Cards",
    subtitle: "3 metric KPI chips distributed evenly",
    direction: "row",
    justify: "space-between",
    align: "stretch",
    gap: "0px",
    gap_px: 0,
    padding: "24px",
    padding_px: 24,
    count: 3,
    variant: "uniform",
  },
  {
    title: "Tag Cloud Toolbar",
    subtitle: "Filter chips packed tightly at start",
    direction: "row",
    justify: "start",
    align: "center",
    gap: "8px",
    gap_px: 8,
    padding: "16px",
    padding_px: 16,
    count: 4,
    variant: "variable",
  },
];

for (const pat of realWorldPatterns) {
  addSpecimen({
    direction: pat.direction,
    justify_content: pat.justify,
    align_items: pat.align,
    gap: pat.gap,
    gap_px: pat.gap_px,
    padding: pat.padding,
    padding_px: pat.padding_px,
    item_count: pat.count,
    content_variant: pat.variant,
    theme: "light",
    title: pat.title,
    subtitle: pat.subtitle,
    tag: "Archetype",
  });
}

// -------------------------------------------------------------
// 9. DARK MODE SWEEP (Representative cross-section)
// -------------------------------------------------------------
const darkModeCandidates = [
  { dir: "row" as LayoutDirection, jc: "start" as JustifyContent, ai: "center" as AlignItems, gap: "16px" as GapToken, px: 16, pad: "24px" as PaddingToken, pad_px: 24, count: 3 },
  { dir: "row" as LayoutDirection, jc: "space-between" as JustifyContent, ai: "center" as AlignItems, gap: "0px" as GapToken, px: 0, pad: "24px" as PaddingToken, pad_px: 24, count: 3 },
  { dir: "row" as LayoutDirection, jc: "center" as JustifyContent, ai: "stretch" as AlignItems, gap: "12px" as GapToken, px: 12, pad: "16px" as PaddingToken, pad_px: 16, count: 2 },
  { dir: "column" as LayoutDirection, jc: "start" as JustifyContent, ai: "stretch" as AlignItems, gap: "12px" as GapToken, px: 12, pad: "24px" as PaddingToken, pad_px: 24, count: 3 },
  { dir: "column" as LayoutDirection, jc: "start" as JustifyContent, ai: "center" as AlignItems, gap: "16px" as GapToken, px: 16, pad: "24px" as PaddingToken, pad_px: 24, count: 3 },
  { dir: "grid-2col" as LayoutDirection, jc: "start" as JustifyContent, ai: "stretch" as AlignItems, gap: "16px" as GapToken, px: 16, pad: "24px" as PaddingToken, pad_px: 24, count: 4 },
];

for (const dm of darkModeCandidates) {
  addSpecimen({
    direction: dm.dir,
    justify_content: dm.jc,
    align_items: dm.ai,
    gap: dm.gap,
    gap_px: dm.px,
    padding: dm.pad,
    padding_px: dm.pad_px,
    item_count: dm.count,
    content_variant: "uniform",
    theme: "dark",
    title: `Dark Mode ${dm.dir.toUpperCase()}`,
    subtitle: `Dark theme contrast: ${dm.dir} layout`,
    tag: "DarkMode",
  });
}

// -------------------------------------------------------------
// 10. COLUMN JUSTIFY-CONTENT SWEEP (Vertical main-axis distribution)
// -------------------------------------------------------------
for (const jc of ["start", "center", "end", "space-between"] as JustifyContent[]) {
  addSpecimen({
    direction: "column",
    justify_content: jc,
    align_items: "stretch",
    gap: jc === "space-between" ? "0px" : "12px",
    gap_px: jc === "space-between" ? 0 : 12,
    padding: "24px",
    padding_px: 24,
    item_count: 3,
    content_variant: "uniform",
    theme: "light",
    title: `Column Justify: ${jc}`,
    subtitle: `Vertical distribution along column: ${jc}`,
    tag: "ColumnJustify",
  });
}

// -------------------------------------------------------------
// 11. CROSS-AXIS & MAIN-AXIS COMBINATORIAL MATRIX
// -------------------------------------------------------------
const crossCombos: { jc: JustifyContent; ai: AlignItems; pad: PaddingToken; pad_px: number; gap: GapToken; gap_px: number }[] = [
  { jc: "center", ai: "start", pad: "16px", pad_px: 16, gap: "12px", gap_px: 12 },
  { jc: "center", ai: "end", pad: "16px", pad_px: 16, gap: "12px", gap_px: 12 },
  { jc: "center", ai: "stretch", pad: "24px", pad_px: 24, gap: "16px", gap_px: 16 },
  { jc: "end", ai: "start", pad: "24px", pad_px: 24, gap: "8px", gap_px: 8 },
  { jc: "end", ai: "end", pad: "24px", pad_px: 24, gap: "8px", gap_px: 8 },
  { jc: "end", ai: "stretch", pad: "16px", pad_px: 16, gap: "12px", gap_px: 12 },
  { jc: "space-between", ai: "start", pad: "24px", pad_px: 24, gap: "0px", gap_px: 0 },
  { jc: "space-between", ai: "end", pad: "24px", pad_px: 24, gap: "0px", gap_px: 0 },
  { jc: "space-between", ai: "stretch", pad: "24px", pad_px: 24, gap: "0px", gap_px: 0 },
  { jc: "space-around", ai: "stretch", pad: "24px", pad_px: 24, gap: "0px", gap_px: 0 },
];

for (const combo of crossCombos) {
  addSpecimen({
    direction: "row",
    justify_content: combo.jc,
    align_items: combo.ai,
    gap: combo.gap,
    gap_px: combo.gap_px,
    padding: combo.pad,
    padding_px: combo.pad_px,
    item_count: 3,
    content_variant: "variable",
    theme: "light",
    title: `Row ${combo.jc} + ${combo.ai}`,
    subtitle: `Dual-axis test: justify ${combo.jc}, align ${combo.ai}`,
    tag: "DualAxis",
  });
}

// -------------------------------------------------------------
// 12. HIGH-DENSITY ITEM COUNTS (4 and 5 items in row)
// -------------------------------------------------------------
const densityItems = [
  { count: 4, gap: "8px" as GapToken, px: 8, jc: "start" as JustifyContent },
  { count: 4, gap: "12px" as GapToken, px: 12, jc: "center" as JustifyContent },
  { count: 4, gap: "0px" as GapToken, px: 0, jc: "space-between" as JustifyContent },
  { count: 5, gap: "4px" as GapToken, px: 4, jc: "start" as JustifyContent },
  { count: 5, gap: "8px" as GapToken, px: 8, jc: "center" as JustifyContent },
  { count: 5, gap: "0px" as GapToken, px: 0, jc: "space-between" as JustifyContent },
];

for (const di of densityItems) {
  addSpecimen({
    direction: "row",
    justify_content: di.jc,
    align_items: "center",
    gap: di.gap,
    gap_px: di.px,
    padding: "16px",
    padding_px: 16,
    item_count: di.count,
    content_variant: "uniform",
    theme: "light",
    title: `High Density Row (${di.count} items)`,
    subtitle: `${di.count} items with ${di.gap} gap, justify ${di.jc}`,
    tag: "Density",
  });
}

// -------------------------------------------------------------
// 13. ADDITIONAL DARK MODE DUAL-AXIS COMBINATIONS
// -------------------------------------------------------------
const darkCombos = [
  { dir: "row" as LayoutDirection, jc: "end" as JustifyContent, ai: "center" as AlignItems, gap: "8px" as GapToken, px: 8, pad: "16px" as PaddingToken, pad_px: 16, count: 2 },
  { dir: "row" as LayoutDirection, jc: "space-between" as JustifyContent, ai: "stretch" as AlignItems, gap: "0px" as GapToken, px: 0, pad: "24px" as PaddingToken, pad_px: 24, count: 3 },
  { dir: "column" as LayoutDirection, jc: "space-between" as JustifyContent, ai: "stretch" as AlignItems, gap: "0px" as GapToken, px: 0, pad: "24px" as PaddingToken, pad_px: 24, count: 3 },
  { dir: "grid-2col" as LayoutDirection, jc: "start" as JustifyContent, ai: "stretch" as AlignItems, gap: "8px" as GapToken, px: 8, pad: "16px" as PaddingToken, pad_px: 16, count: 4 },
  { dir: "grid-3col" as LayoutDirection, jc: "start" as JustifyContent, ai: "stretch" as AlignItems, gap: "12px" as GapToken, px: 12, pad: "24px" as PaddingToken, pad_px: 24, count: 6 },
];

for (const dc of darkCombos) {
  addSpecimen({
    direction: dc.dir,
    justify_content: dc.jc,
    align_items: dc.ai,
    gap: dc.gap,
    gap_px: dc.px,
    padding: dc.pad,
    padding_px: dc.pad_px,
    item_count: dc.count,
    content_variant: "uniform",
    theme: "dark",
    title: `Dark Mode ${dc.dir} (${dc.jc})`,
    subtitle: `Dark theme test: ${dc.dir} with justify ${dc.jc}`,
    tag: "DarkMode",
  });
}

// -------------------------------------------------------------
// 14. SEGMENTED CONTROLS & FLUSH GROUPS (0px gap flush row/column)
// -------------------------------------------------------------
for (const dir of ["row", "column"] as LayoutDirection[]) {
  for (const jc of ["start", "center"] as JustifyContent[]) {
    addSpecimen({
      direction: dir,
      justify_content: jc,
      align_items: dir === "row" ? "center" : "stretch",
      gap: "0px",
      gap_px: 0,
      padding: "16px",
      padding_px: 16,
      item_count: 3,
      content_variant: "uniform",
      theme: "light",
      title: `Flush Segmented ${dir} (${jc})`,
      subtitle: `0px gap flush group in ${dir} flow`,
      tag: "FlushGroup",
    });
  }
}

// -------------------------------------------------------------
// 15. PADDING SWEEP IN COLUMN MODE
// -------------------------------------------------------------
for (const p of [{ tok: "8px" as PaddingToken, px: 8 }, { tok: "16px" as PaddingToken, px: 16 }, { tok: "24px" as PaddingToken, px: 24 }, { tok: "32px" as PaddingToken, px: 32 }]) {
  addSpecimen({
    direction: "column",
    justify_content: "start",
    align_items: "stretch",
    gap: "12px",
    gap_px: 12,
    padding: p.tok,
    padding_px: p.px,
    item_count: 3,
    content_variant: "uniform",
    theme: "light",
    title: `Column Padding: ${p.tok}`,
    subtitle: `Vertical container inset test: ${p.tok} (${p.px}px)`,
    tag: "Padding",
  });
}

// -------------------------------------------------------------
// 16. ASYMMETRIC / VARIABLE ITEM PROPORTIONS
// -------------------------------------------------------------
const variableProportions = [
  { dir: "row" as LayoutDirection, jc: "start" as JustifyContent, ai: "center" as AlignItems, gap: "12px" as GapToken, px: 12 },
  { dir: "row" as LayoutDirection, jc: "center" as JustifyContent, ai: "center" as AlignItems, gap: "16px" as GapToken, px: 16 },
  { dir: "column" as LayoutDirection, jc: "start" as JustifyContent, ai: "start" as AlignItems, gap: "12px" as GapToken, px: 12 },
  { dir: "column" as LayoutDirection, jc: "start" as JustifyContent, ai: "end" as AlignItems, gap: "12px" as GapToken, px: 12 },
  { dir: "grid-2col" as LayoutDirection, jc: "start" as JustifyContent, ai: "stretch" as AlignItems, gap: "12px" as GapToken, px: 12 },
];

for (const vp of variableProportions) {
  addSpecimen({
    direction: vp.dir,
    justify_content: vp.jc,
    align_items: vp.ai,
    gap: vp.gap,
    gap_px: vp.px,
    padding: "24px",
    padding_px: 24,
    item_count: vp.dir === "grid-2col" ? 4 : 3,
    content_variant: "variable",
    theme: "light",
    title: `Variable ${vp.dir} (${vp.ai})`,
    subtitle: `Variable dimension test: ${vp.dir} with cross-axis ${vp.ai}`,
    tag: "VariableDimension",
  });
}
