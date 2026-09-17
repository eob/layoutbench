export interface QualitativeScene {
  id: string;
  theme: "light" | "dark";
  variant: number;
  html: string;
  css: string;
  questions: { family: string; answer: string }[];
  factors: Record<string, string | number>;
}

// Use data-box="unique-id" on every measured visible region. The shared
// renderer records bounding rectangles without exposing HTML to models.
export const COPY = [
  ["Harbor walk", "Cedar trail", "Autumn rain", "Quiet boats", "Garden path", "Silver cloud", "Wooden bridge", "Morning light", "River bank", "Forest moss", "Open meadow", "Warm bread"],
  ["Willow bend", "Orchard gate", "Summer breeze", "Stone steps", "Meadow grass", "Golden leaves", "Evening glow", "Ocean mist", "Maple grove", "Gentle brook", "Distant hills", "Fresh apples"],
];
