import { afterEach, beforeEach, expect, test } from "bun:test";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { resolveRenderOutput } from "./render-output.ts";

let repository: string;

beforeEach(() => {
  repository = fs.mkdtempSync(path.join(os.tmpdir(), "layoutbench-output-"));
  fs.mkdirSync(path.join(repository, "releases"));
  fs.mkdirSync(path.join(repository, "dataset/release"), { recursive: true });
  fs.writeFileSync(path.join(repository, "releases/0.3.0.json"), JSON.stringify({ dataset_path: "dataset/release" }));
});

afterEach(() => fs.rmSync(repository, { recursive: true, force: true }));

test("default rendering uses a separate candidate without creating files", () => {
  const output = resolveRenderOutput(undefined, repository);
  expect(output).toBe(path.join(repository, "dataset/candidate-rendered"));
  expect(fs.existsSync(output)).toBe(false);
});

test("registered inputs reject exact, parent, and child output paths", () => {
  for (const output of [repository, "dataset", "dataset/release", "dataset/release/new-output"]) {
    expect(() => resolveRenderOutput(path.resolve(repository, output), repository)).toThrow("Frozen render output");
  }
});

test("both archived input directories remain protected without descriptors", () => {
  for (const output of ["dataset/layoutbench-1", "dataset/rendered", "dataset/rendered/new-output"]) {
    expect(() => resolveRenderOutput(path.join(repository, output), repository)).toThrow("Frozen render output");
  }
});

test("a similar filename prefix is not a frozen directory", () => {
  const output = path.join(repository, "dataset/release-copy");
  expect(resolveRenderOutput(output, repository)).toBe(output);
});

test("symlink aliases cannot route output into a frozen directory", () => {
  fs.symlinkSync(path.join(repository, "dataset/release"), path.join(repository, "alias"));
  expect(() => resolveRenderOutput(path.join(repository, "alias/new-output"), repository)).toThrow("Frozen render output");
  fs.symlinkSync(path.join(repository, "dataset"), path.join(repository, "parent-alias"));
  expect(() => resolveRenderOutput(path.join(repository, "parent-alias"), repository)).toThrow("Frozen render output");
});

test("qualitative CLI refuses released output before touching the manifest", () => {
  const root = path.resolve(import.meta.dir, "..");
  const manifest = path.join(root, "dataset/layoutbench-v0.3/manifest.json");
  const before = fs.readFileSync(manifest);
  const process = Bun.spawnSync(["bun", path.join(root, "src/render-qualitative.ts"), path.dirname(manifest)], { cwd: root });
  expect(process.exitCode).not.toBe(0);
  expect(process.stderr.toString()).toContain("Frozen render output");
  expect(fs.readFileSync(manifest).equals(before)).toBe(true);
});
