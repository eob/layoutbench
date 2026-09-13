export type LayoutFamily =
  | "flow"
  | "distribute"
  | "align"
  | "gap"
  | "pad"
  | "columns"
  | "textjustify"
  | "headerpad"
  | "regionpad"
  | "tablepad"
  | "gapnum"
  | "headerpx"
  | "regionpx";

export const CHOICE_FAMILIES: LayoutFamily[] = [
  "flow",
  "distribute",
  "align",
  "gap",
  "pad",
  "columns",
  "textjustify",
  "headerpad",
  "regionpad",
  "tablepad",
];

export const NUMERIC_FAMILIES: LayoutFamily[] = [
  "gapnum",
  "headerpx",
  "regionpx",
];

export const FAMILIES: LayoutFamily[] = [
  ...CHOICE_FAMILIES,
  ...NUMERIC_FAMILIES,
];

export function choiceLabels(family: LayoutFamily): string[] {
  switch (family) {
    case "distribute":
      return ["A", "B", "C", "D", "E"];
    case "columns":
    case "headerpad":
      return ["A", "B", "C"];
    case "gapnum":
    case "headerpx":
    case "regionpx":
      throw new Error(`Not a choice family: ${family}`);
    default:
      return ["A", "B", "C", "D"];
  }
}

export type FlowDirection = "row" | "column" | "grid-2col" | "grid-3col";
export type DistributeOption =
  | "start"
  | "center"
  | "end"
  | "space-between"
  | "space-around";
export type AlignOption = "start" | "center" | "end" | "stretch";
export type Theme = "light" | "dark";
export type ContentVariant = "uniform" | "variable";

export interface DecodedRect {
  role: string;
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface AbstractDesign {
  kind: "abstract";
  direction: FlowDirection;
  justify_content: DistributeOption;
  align_items: AlignOption;
  gap_px: number;
  padding_px: number;
  item_count: number;
  content_variant: ContentVariant;
  theme: Theme;
  options?: string[];
  decoded?: Record<string, number>;
  lines?: Record<string, DecodedRect[]>;
  overflow?: Record<string, { scroll: number; client: number }>;
}

export interface DocumentDesign {
  kind: "document";
  archetype: "columns" | "text" | "header" | "region" | "table";
  theme: Theme;
  column_count?: number;
  text_align?: "left" | "center" | "right" | "justify";
  above_px?: number;
  below_px?: number;
  pad_px?: number;
  bordered?: boolean;
  cell_pad_px?: number;
  rows?: number;
  cols?: number;
  options?: string[];
  copy_id?: string;
  decoded?: Record<string, number>;
  lines?: Record<string, DecodedRect[]>;
  overflow?: Record<string, { scroll: number; client: number }>;
}

export type LayoutDesign = AbstractDesign | DocumentDesign;

export type LayoutGroundTruth =
  | { choice: string }
  | { gap_px: number }
  | { above_px: number; below_px: number }
  | { pad_px: number };

export interface Specimen {
  id: string;
  family: LayoutFamily;
  groupId: string;
  imageFilename: string;
  design: LayoutDesign;
  groundTruth: LayoutGroundTruth;
  options?: string[];
}

export interface LayoutTask {
  taskId: string;
  family: LayoutFamily;
  groupId: string;
  imageFilename: string;
  imageSha256: string;
  groundTruth: LayoutGroundTruth;
  prompt: string;
  design: LayoutDesign;
  domText: string;
  rendered: {
    width: number;
    height: number;
    dpr: number;
    colorSpace: "srgb";
    font: { path: string; sha256: string };
    regions: DecodedRect[];
  };
}
