"""Agent orchestration layer (multi-agent architecture).

Borrowed ideas, adapted to the puzzle harness:

* oh-my-opencode-slim (github.com/alvinunreal/oh-my-opencode-slim):
  a *pantheon* of specialized agents - Orchestrator plans a work graph,
  specialists run in the background, results are reconciled; a *council*
  runs several configurations in parallel on the same question and keeps
  the best answer.

* compound-engineering-plugin (github.com/everyinc/compound-engineering-plugin):
  the loop brainstorm -> plan -> build -> review -> CAPTURE: knowledge from
  each round is written where the next round reads it (docs/learnings/).

Here the "specialists" are solver configurations / harness runs; the
council is how the competition is actually won: several strategies (beam
widths, budgets, methods, constructive poly solvers) race in the
background on the same scramble set and the best is adopted, then the
improvement loop captures the lesson.
"""

from __future__ import annotations

import concurrent.futures
import os
import subprocess
import sys
import time
from typing import Callable, Dict, List, Optional

from . import scoring

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --------------------------------------------------------------------------- #
# role catalog (the "pantheon" of the puzzle harness)
# --------------------------------------------------------------------------- #

ROLES: Dict[str, dict] = {
    "orchestrator": {
        "alias": "@orchestrator",
        "mission": "plan the solve graph, dispatch specialists in the "
                   "background, reconcile their reports",
        "skills": ["scoring-and-benchmarks", "self-improvement"],
        "tools": ["harness", "council", "dispatch"],
    },
    "researcher": {
        "alias": "@researcher",
        "mission": "study CayleyPy papers, khoruzhii/cayleypy-cube, "
                   "DeepCubeA; propose solver improvements",
        "skills": ["cayley-graphs", "polynomial-time-algorithms"],
        "tools": ["web_search", "read"],
    },
    "solver": {
        "alias": "@solver",
        "mission": "run the harness on a competition/bundle with a given "
                   "strategy and return a scored report",
        "skills": ["kaggle-agent-competitions", "twisty-puzzles", "rubiks-cube"],
        "tools": ["harness"],
    },
    "analyst": {
        "alias": "@analyst",
        "mission": "analyze run results: strengths/weaknesses vs targets; "
                   "propose one safe change (self-improvement loop)",
        "skills": ["self-improvement", "scoring-and-benchmarks"],
        "tools": ["self_improve"],
    },
    "verifier": {
        "alias": "@verifier",
        "mission": "run the correctness oracle; never ship unverified claims",
        "skills": ["scoring-and-benchmarks"],
        "tools": ["verify"],
    },
    "distiller": {
        "alias": "@distiller",
        "mission": "turn the winning strategy into the simple elegant "
                   "artifact (strategy.py) + scorecard",
        "skills": ["algo-distillation"],
        "tools": ["distil"],
    },
}


def role_card(role: str) -> str:
    """Markdown role card (used for per-role agent files)."""
    r = ROLES[role]
    lines = [f"## @{role} - {r['mission']}", "", "- skills:",
             "\n".join(f"  - `{s}`" for s in r["skills"]) or "  - (none)",
             "- tools:", ", ".join(f"`{t}`" for t in r["tools"])]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# background dispatch
# --------------------------------------------------------------------------- #

def dispatch_python(args: List[str], cwd: str = REPO, timeout_s: float = 1800,
                    env: Optional[Dict[str, str]] = None) -> Dict:
    """Run a harness/script subprocess in the background (blocking wrapper);
    returns {returncode, stdout, stderr, elapsed}.  Used by the orchestrator
    to race solver configurations in parallel (see council)."""
    t0 = time.time()
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    res = subprocess.run([sys.executable, "-m"] + args, cwd=cwd,
                         capture_output=True, text=True, timeout=timeout_s,
                         env=full_env)
    return {"returncode": res.returncode, "stdout": res.stdout[-4000:],
            "stderr": res.stderr[-2000:], "elapsed": time.time() - t0}


def council(bundles: Dict[str, dict], strategies: Dict[str, dict],
            limit: int = 6, budget_s: float = 5.0,
            workers: int = 2) -> List[scoring.RunReport]:
    """Run several strategies in parallel on the same scramble slices (the
    'council' pattern) and return all reports, best first by score.

    ``strategies`` maps a name to harness kwargs, e.g.
    ``{"beam-w8": dict(method="beam"), "beam-w16": dict(method="beam", ...)}``
    Each strategy runs the two lightweight bundles (444 cube, megaminx) on
    the first ``limit`` cases, so a council round is fast and comparable.
    """
    from . import harness as H
    from . import kaggle_client as K

    plans = []
    for name, kw in strategies.items():
        for ref, bundle in bundles.items():
            if not bundle or bundle.get("moves_undefined") or bundle.get("puzzle") is None:
                continue
            plans.append((name, ref, bundle, kw))

    def run(plan):
        name, ref, bundle, kw = plan
        kw = dict(kw)
        method = kw.pop("method", "auto")
        rep = H.run_one(bundle["puzzle"], bundle["cases"][:limit], method,
                        kw.pop("budget_s", budget_s), None, None,
                        verbose=False)
        return name, rep

    reports: List[scoring.RunReport] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        for name, rep in ex.map(run, plans):
            rep.puzzle_name = f"{name}/{rep.puzzle_name}"
            reports.append(rep)
    reports.sort(key=lambda r: r.score, reverse=True)
    return reports


# --------------------------------------------------------------------------- #
# compound capture loop
# --------------------------------------------------------------------------- #

LEARNINGS = os.path.join(REPO, "docs", "learnings")


def capture(lesson: str, context: Optional[str] = None) -> str:
    """Append a lesson to docs/learnings/LESSONS.md - the file the next
    improvement round reads first (compound-engineering pattern)."""
    os.makedirs(LEARNINGS, exist_ok=True)
    path = os.path.join(LEARNINGS, "LESSONS.md")
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write("# Lessons learned\n\n"
                    "Read this first in every improvement round.  Each "
                    "entry: what was tried, what the results said, what "
                    "changed, what to remember.\n\n")
    stamp = time.strftime("%Y-%m-%d %H:%M")
    with open(path, "a") as f:
        f.write(f"\n## {stamp}\n\n{lesson}\n")
        if context:
            f.write(f"\n_Context: {context}_\n")
    return path


def lessons() -> str:
    """Return the current lessons file content (or an empty note)."""
    p = os.path.join(LEARNINGS, "LESSONS.md")
    if os.path.exists(p):
        return open(p).read()
    return "(no lessons yet - see agent-orchestration skill)"