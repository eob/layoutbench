export type LayoutDirection = "row" | "column" | "grid-2col" | "grid-3col";
export type JustifyContent = "start" | "center" | "end" | "space-between" | "space-around";
export type AlignItems = "start" | "center" | "end" | "stretch";
export type GapToken = "0px" | "4px" | "8px" | "12px" | "16px" | "24px" | "32px";
export type PaddingToken = "8px" | "16px" | "24px" | "32px";
export type BackgroundTheme = "light" | "dark";
export type ItemContentVariant = "uniform" | "variable";

export interface LayoutSpecimenConfig {
  id: string;
  direction: LayoutDirection;
  justify_content: JustifyContent;
  align_items: AlignItems;
  gap: GapToken;
  gap_px: number;
  padding: PaddingToken;
  padding_px: number;
  item_count: number;
  content_variant: ItemContentVariant;
  theme: BackgroundTheme;
  title: string;
  subtitle: string;
  tag: string;
}

export interface LayoutBenchmarkManifestItem {
  taskId: string;
  imagePath: string;
  imageFilename: string;
  groundTruth: {
    direction: LayoutDirection;
    justify_content: JustifyContent;
    align_items: AlignItems;
    gap: GapToken;
    gap_px: number;
    padding: PaddingToken;
    padding_px: number;
    item_count: number;
    content_variant: ItemContentVariant;
    theme: BackgroundTheme;
  };
  prompt: string;
}
