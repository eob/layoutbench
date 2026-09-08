import { chromium } from "playwright";
import { SPECIMENS } from "./specimens.ts";
import type { LayoutSpecimenConfig, LayoutBenchmarkManifestItem } from "./types.ts";
import * as fs from "node:fs";
import * as path from "node:path";

const OUTPUT_DIR = path.resolve("dataset/rendered");
const MANIFEST_DIR = path.resolve("dataset/layoutbench-1");
const MANIFEST_PATH = path.join(MANIFEST_DIR, "manifest.json");

fs.mkdirSync(OUTPUT_DIR, { recursive: true });
fs.mkdirSync(MANIFEST_DIR, { recursive: true });

function generateLayoutHtml(specimen: LayoutSpecimenConfig): string {
  const isDark = specimen.theme === "dark";
  const canvasBg = isDark ? "#090d16" : "#f1f5f9";
  const cardBg = isDark ? "#111827" : "#ffffff";
  const cardBorder = isDark ? "rgba(255, 255, 255, 0.12)" : "#cbd5e1";
  const textColor = isDark ? "#f3f4f6" : "#0f172a";
  const mutedColor = isDark ? "#9ca3af" : "#64748b";

  // Item styling palette
  const itemBgs = isDark
    ? ["#1f2937", "#1e293b", "#27272a", "#182230", "#1e1e24", "#22272e"]
    : ["#f8fafc", "#f1f5f9", "#f3f4f6", "#eef2f6", "#f0fdf4", "#fef3c7"];
  const itemBorders = isDark
    ? ["#374151", "#334155", "#3f3f46", "#2d3748", "#3b4252", "#38414a"]
    : ["#e2e8f0", "#cbd5e1", "#e5e7eb", "#d1d5db", "#bbf7d0", "#fde68a"];
  const accentDots = [
    "#3b82f6", // blue
    "#10b981", // emerald
    "#8b5cf6", // violet
    "#f59e0b", // amber
    "#ec4899", // pink
    "#06b6d4", // cyan
  ];

  // Container layout CSS
  let containerDisplay = "display: flex;";
  let flexDirCss = `flex-direction: ${specimen.direction === "column" ? "column" : "row"};`;
  let gridColsCss = "";

  if (specimen.direction === "grid-2col") {
    containerDisplay = "display: grid;";
    gridColsCss = "grid-template-columns: repeat(2, 1fr);";
    flexDirCss = "";
  } else if (specimen.direction === "grid-3col") {
    containerDisplay = "display: grid;";
    gridColsCss = "grid-template-columns: repeat(3, 1fr);";
    flexDirCss = "";
  }

  // Cross & main axis CSS
  let justifyCss = `justify-content: ${specimen.justify_content};`;
  let alignCss = `align-items: ${specimen.align_items};`;

  if (specimen.direction.startsWith("grid")) {
    // In grid, align-items aligns items along the block/vertical axis of their cell
    alignCss = `align-items: ${specimen.align_items};`;
    if (specimen.justify_content === "center") {
      justifyCss = "justify-items: center;";
    } else if (specimen.justify_content === "end") {
      justifyCss = "justify-items: end;";
    } else if (specimen.justify_content === "start") {
      justifyCss = "justify-items: start;";
    } else {
      justifyCss = "justify-items: stretch;";
    }
  }

  const gapCss = `gap: ${specimen.gap_px}px;`;
  const paddingCss = `padding: ${specimen.padding_px}px;`;

  // Generate child items
  const itemsHtml = Array.from({ length: specimen.item_count }, (_, i) => {
    const bg = itemBgs[i % itemBgs.length];
    const border = itemBorders[i % itemBorders.length];
    const dotColor = accentDots[i % accentDots.length];

    let itemHeightStyle = "";
    let itemWidthStyle = "";
    let label = `Item ${i + 1}`;
    let sub = "Standard";

    if (specimen.content_variant === "variable") {
      if (specimen.direction === "row") {
        // Vary heights to test row align-items
        const heights = [44, 72, 56, 84, 48];
        const widths = [85, 115, 95, 125, 90];
        itemHeightStyle = specimen.align_items === "stretch" ? "" : `height: ${heights[i % heights.length]}px;`;
        itemWidthStyle = `min-width: ${widths[i % widths.length]}px;`;
        label = ["Quick", "Optimized Core", "Metric Hub", "Realtime Sync", "Cache"][i % 5];
        sub = ["4ms", "99.98%", "Active", "Live", "Warm"][i % 5];
      } else if (specimen.direction === "column") {
        // Vary widths to test column align-items
        const widths = [130, 210, 160, 240];
        itemWidthStyle = specimen.align_items === "stretch" ? "width: 100%;" : `width: ${widths[i % widths.length]}px;`;
        itemHeightStyle = "min-height: 44px;";
        label = ["System Check", "Continuous Integration Service", "Build Node", "Deployment"][i % 4];
        sub = ["Healthy", "Passed", "Ready", "Standby"][i % 4];
      } else {
        // Grid variable
        const heights = [52, 68, 60, 76, 54, 70];
        itemHeightStyle = specimen.align_items === "stretch" ? "" : `min-height: ${heights[i % heights.length]}px;`;
        label = `Widget ${i + 1}`;
        sub = `${(i + 1) * 12}%`;
      }
    } else {
      // Uniform items
      if (specimen.direction === "row") {
        itemWidthStyle = "min-width: 82px;";
        itemHeightStyle = specimen.align_items === "stretch" ? "" : "height: 48px;";
      } else if (specimen.direction === "column") {
        itemWidthStyle = specimen.align_items === "stretch" ? "width: 100%;" : "width: 180px;";
        itemHeightStyle = "height: 44px;";
      } else {
        itemHeightStyle = specimen.align_items === "stretch" ? "" : "height: 52px;";
      }
    }

    // Flush items border treatment when gap is 0
    let flushRadius = "border-radius: 8px;";
    if (specimen.gap_px === 0 && specimen.item_count > 1) {
      if (specimen.direction === "row") {
        if (i === 0) flushRadius = "border-radius: 8px 0 0 8px;";
        else if (i === specimen.item_count - 1) flushRadius = "border-radius: 0 8px 8px 0;";
        else flushRadius = "border-radius: 0; border-left: none;";
      } else if (specimen.direction === "column") {
        if (i === 0) flushRadius = "border-radius: 8px 8px 0 0;";
        else if (i === specimen.item_count - 1) flushRadius = "border-radius: 0 0 8px 8px;";
        else flushRadius = "border-radius: 0; border-top: none;";
      }
    }

    return `
      <div class="item" style="background: ${bg}; border: 1px solid ${border}; ${flushRadius} ${itemWidthStyle} ${itemHeightStyle}">
        <div class="dot" style="background: ${dotColor};"></div>
        <div class="text-group">
          <span class="item-title">${label}</span>
          <span class="item-sub">${sub}</span>
        </div>
      </div>
    `;
  }).join("\n");

  return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    width: 560px;
    height: 380px;
    background: ${canvasBg};
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }
  .card {
    width: 480px;
    height: 300px;
    background: ${cardBg};
    border: 1px solid ${cardBorder};
    border-radius: 12px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
  .header {
    height: 42px;
    padding: 0 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid ${cardBorder};
    background: ${isDark ? "#0f1523" : "#f8fafc"};
    flex-shrink: 0;
  }
  .header-title {
    font-size: 13px;
    font-weight: 600;
    color: ${textColor};
    letter-spacing: -0.01em;
  }
  .header-tag {
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 9999px;
    background: ${isDark ? "#1e293b" : "#e2e8f0"};
    color: ${mutedColor};
    font-weight: 500;
  }
  .layout-stage {
    flex: 1;
    width: 100%;
    height: 100%;
    ${containerDisplay}
    ${flexDirCss}
    ${gridColsCss}
    ${justifyCss}
    ${alignCss}
    ${gapCss}
    ${paddingCss}
    overflow: hidden;
  }
  .item {
    display: flex;
    align-items: center;
    padding: 8px 12px;
    gap: 8px;
    box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.04);
  }
  .dot {
    width: 8px;
    height: 8px;
    border-radius: 9999px;
    flex-shrink: 0;
  }
  .text-group {
    display: flex;
    flex-direction: column;
    overflow: hidden;
    white-space: nowrap;
  }
  .item-title {
    font-size: 12px;
    font-weight: 600;
    color: ${textColor};
    line-height: 1.2;
    text-overflow: ellipsis;
    overflow: hidden;
  }
  .item-sub {
    font-size: 10px;
    color: ${mutedColor};
    line-height: 1.2;
    text-overflow: ellipsis;
    overflow: hidden;
  }
</style>
</head>
<body>
  <div class="card">
    <div class="header">
      <span class="header-title">${specimen.title}</span>
      <span class="header-tag">${specimen.tag}</span>
    </div>
    <div class="layout-stage">
      ${itemsHtml}
    </div>
  </div>
</body>
</html>`;
}

const PROMPT_TEXT = `Analyze the container layout in this UI screenshot.
The image shows a standardized UI card container rendered on a canvas with child elements laid out inside it.

Evaluate these 5 core layout attributes and respond ONLY with a valid JSON object matching this schema:
{
  "direction": "row" | "column" | "grid-2col" | "grid-3col",
  "justify_content": "start" | "center" | "end" | "space-between" | "space-around",
  "align_items": "start" | "center" | "end" | "stretch",
  "gap": "0px" | "4px" | "8px" | "12px" | "16px" | "24px" | "32px",
  "padding": "8px" | "16px" | "24px" | "32px"
}

Definitions:
- direction: the primary layout flow of items inside the container ("row", "column", "grid-2col", "grid-3col").
- justify_content: main-axis item distribution ("start", "center", "end", "space-between", "space-around").
- align_items: cross-axis item alignment ("start", "center", "end", "stretch").
- gap: spacing between neighboring child items ("0px", "4px", "8px", "12px", "16px", "24px", "32px").
- padding: internal padding inset between the container border and the outer child items ("8px", "16px", "24px", "32px").`;

async function main() {
  console.log(`Starting render of ${SPECIMENS.length} LayoutBench specimens...`);
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport: { width: 560, height: 380 },
    deviceScaleFactor: 2, // 2x Retina DPR
  });

  const manifestItems: LayoutBenchmarkManifestItem[] = [];

  for (let i = 0; i < SPECIMENS.length; i++) {
    const specimen = SPECIMENS[i];
    const filename = `${specimen.id}.png`;
    const outputPath = path.join(OUTPUT_DIR, filename);
    const html = generateLayoutHtml(specimen);

    await page.setContent(html);
    await page.screenshot({ path: outputPath, type: "png" });

    manifestItems.push({
      taskId: specimen.id,
      imagePath: outputPath,
      imageFilename: filename,
      groundTruth: {
        direction: specimen.direction,
        justify_content: specimen.justify_content,
        align_items: specimen.align_items,
        gap: specimen.gap,
        gap_px: specimen.gap_px,
        padding: specimen.padding,
        padding_px: specimen.padding_px,
        item_count: specimen.item_count,
        content_variant: specimen.content_variant,
        theme: specimen.theme,
      },
      prompt: PROMPT_TEXT,
    });

    if ((i + 1) % 20 === 0 || i === SPECIMENS.length - 1) {
      console.log(`Rendered ${i + 1}/${SPECIMENS.length} specimens...`);
    }
  }

  await browser.close();

  const manifest = {
    benchmark_id: "layoutbench-1",
    name: "LayoutBench-1",
    version: "1.0.0",
    description: "Visual layout direction, alignment, justification, gap spacing, and padding identification benchmark for multimodal vision-language models.",
    total_tasks: manifestItems.length,
    canonical_canvas: {
      width_px: 560,
      height_px: 380,
      card_width_px: 480,
      card_height_px: 300,
      dpr: 2,
    },
    tasks: manifestItems,
  };

  fs.writeFileSync(MANIFEST_PATH, JSON.stringify(manifest, null, 2));
  console.log(`✅ Finished rendering! Manifest written to ${MANIFEST_PATH}`);
}

main().catch((err) => {
  console.error("Render failed:", err);
  process.exit(1);
});
