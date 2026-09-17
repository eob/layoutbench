import * as fs from "node:fs";
import * as path from "node:path";

function canonical(filename: string): string {
  const suffix: string[] = [];
  let existing = filename;
  while (!fs.existsSync(existing)) {
    // A dangling symlink must fail instead of being treated as a new directory.
    if (fs.lstatSync(existing, { throwIfNoEntry: false })?.isSymbolicLink()) {
      throw new Error(`Cannot resolve render output symlink: ${existing}`);
    }
    suffix.unshift(path.basename(existing));
    existing = path.dirname(existing);
  }
  return path.join(fs.realpathSync(existing), ...suffix);
}

function contains(parent: string, child: string): boolean {
  const relative = path.relative(parent, child);
  return relative === "" || (!relative.startsWith(`..${path.sep}`) && relative !== ".." && !path.isAbsolute(relative));
}

export function resolveRenderOutput(requested?: string, repository = path.resolve(import.meta.dir, "..")): string {
  const output = path.resolve(requested ?? path.join(repository, "dataset/candidate-rendered"));
  const frozen = ["dataset/layoutbench-1", "dataset/rendered"];
  for (const name of fs.readdirSync(path.join(repository, "releases"))) {
    if (!name.endsWith(".json")) continue;
    const release = JSON.parse(fs.readFileSync(path.join(repository, "releases", name), "utf8"));
    if (typeof release.dataset_path !== "string") throw new Error(`Missing dataset path in release ${name}`);
    frozen.push(release.dataset_path);
  }
  const realOutput = canonical(output);
  for (const relative of frozen) {
    const registered = path.resolve(repository, relative);
    const realRegistered = canonical(registered);
    if (contains(output, registered) || contains(registered, output)
        || contains(realOutput, realRegistered) || contains(realRegistered, realOutput)) {
      throw new Error(`Frozen render output: ${output} overlaps ${registered}`);
    }
  }
  return output;
}
