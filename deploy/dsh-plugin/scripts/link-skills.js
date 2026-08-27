#!/usr/bin/env node
// Link this bundle's skills into the profile's skills dir (best effort).
import { existsSync, mkdirSync, readdirSync, symlinkSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "../..");
const skills = join(root, ".agents", "skills");
if (!existsSync(skills)) {
  process.exit(0);
}
const targets = [
  process.env.DSH_SKILLS_DIR,
  join(process.env.HOME || ".", ".config", "dsh", "skills"),
  join(process.env.HOME || ".", ".dsh", "skills"),
].filter(Boolean);
for (const t of targets) {
  try {
    mkdirSync(t, { recursive: true });
    for (const name of readdirSync(skills)) {
      if (name.startsWith(".")) continue;
      const p = join(t, name);
      if (!existsSync(p)) symlinkSync(join(skills, name), p, "dir");
    }
  } catch {
    /* best effort */
  }
}
process.exit(0);