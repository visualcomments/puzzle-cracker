// Puzzle Cracker - DeepSeek Harness plugin bundle.
//
// A `dsh.bundle.patch` export that adds the puzzle-cracker skills and the
// make targets to the profile.  Load with:
//
//     dsh plugin add file:/path/to/deploy/dsh-plugin
//
// Then the agent in the harness profile automatically has the skills
// (AGENTS.md root + .agents/skills) and the run/verify/demo commands.

export function patch(profile) {
  const ctx = profile.ctx || (profile.ctx = {});
  ctx.puzzleCracker = {
    description:
      "Puzzle Cracker: solve Rubik's cube / Megaminx / CayleyPy Kaggle competitions. " +
      "Commands: `make run REF=... METHOD=...`, `make verify`, `make demo`.",
    commands: ["make run", "make verify", "make demo", "make scorecard"],
  };
  return profile;
}

export default patch;