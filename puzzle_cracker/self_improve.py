"""The self-improvement loop.

After a scoring run the harness:

    1. analyzes strengths/weaknesses of the results (solve rate, mean
       length, budget usage, per-puzzle failures);
    2. produces a concrete improvement plan (deterministic knob changes);
    3. applies the *safest* change, benchmarks it against the previous run
       (small held-out regression), keeps or reverts;
    4. writes an improvement record to docs/improvements/;
    5. publishes the harness to GitHub when a token is provided by the
       user (env GITHUB_TOKEN / ~/.config/puzzle_cracker/secrets.env) -
       tokens are never stored in the repo.

The loop is deliberately small and deterministic so an agent can run it
after every competition result without risk: one config change per round,
measured, then published.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import subprocess
import sys
from typing import Dict, List, Optional

from . import scoring
from .config import Config, github_token

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMPROVE_DIR = os.path.join(REPO, "docs", "improvements")


# --------------------------------------------------------------------------- #
# 1. analysis
# --------------------------------------------------------------------------- #

def analyze(reports: List[scoring.RunReport], cfg: Config) -> Dict:
    """Summarize strengths/weaknesses against the configured targets."""
    solved = sum(r.solved for r in reports)
    total = sum(r.total for r in reports)
    moves = sum(r.total_moves for r in reports)
    rate = solved / total if total else 0.0
    mean = moves / solved if solved else float("inf")
    per = {r.puzzle_name: {"solved": r.solved, "total": r.total,
                           "rate": r.solve_rate,
                           "mean": r.mean_length} for r in reports}
    weak = []
    strong = []
    if rate < cfg.target_solve_rate:
        weak.append(f"solve rate {rate:.0%} < target {cfg.target_solve_rate:.0%}")
    elif rate >= cfg.target_solve_rate:
        strong.append(f"solve rate {rate:.0%} meets target")
    if mean > cfg.target_mean_length:
        weak.append(f"mean length {mean:.1f} > target {cfg.target_mean_length:.0f}")
    else:
        strong.append(f"mean length {mean:.1f} within target")
    worst = max(per.values(), key=lambda p: 0 if p["total"] == 0 else p["rate"])
    if worst["total"] and worst["rate"] < cfg.target_solve_rate:
        weak.append(f"weakest puzzle: {worst}")
    return {
        "solved": solved, "total": total, "solve_rate": rate,
        "total_moves": moves, "mean_length": mean, "per_puzzle": per,
        "strengths": strong or ["baseline recorded"],
        "weaknesses": weak or ["none within targets"],
    }


# --------------------------------------------------------------------------- #
# 2. plan + 3. apply
# --------------------------------------------------------------------------- #

def plan(analysis: Dict, cfg: Config) -> List[Dict]:
    """Concrete, deterministic candidate changes (ordered safest first)."""
    cands = []
    t = cfg.tuning
    if analysis["solve_rate"] < cfg.target_solve_rate:
        w = min(int(cfg.beam_width * t["beam_width_step"]), int(t["beam_width_cap"]))
        cands.append({"kind": "beam_width", "from": cfg.beam_width, "to": w,
                      "effect": "wider beam -> higher solve rate"})
        b = min(cfg.beam_per_case_budget_s * t["budget_step"], t["budget_cap"])
        cands.append({"kind": "beam_per_case_budget_s", "from": cfg.beam_per_case_budget_s,
                      "to": round(b, 1), "effect": "longer search -> more solved"})
    if analysis["mean_length"] > cfg.target_mean_length:
        mn = max(1_500_000, cfg.bibfs_max_nodes)
        cands.append({"kind": "bibfs_max_nodes", "from": cfg.bibfs_max_nodes,
                      "to": mn, "effect": "deeper optimal search -> shorter paths"})
    return cands


def apply_change(cfg: Config, change: Dict) -> Config:
    """Apply one change in-place; return cfg."""
    setattr(cfg, change["kind"], change["to"])
    return cfg


# --------------------------------------------------------------------------- #
# 4. regression benchmark
# --------------------------------------------------------------------------- #

def regress(cfg: Config, data_dir: str = "data", limit: int = 4,
            budget_s: float = 4.0) -> List[scoring.RunReport]:
    """Small held-out regression across puzzle kinds using the new config.
    Loads only the two lightweight competition bundles (444 cube, megaminx)
    - enough to detect a regression, cheap enough for every round."""
    from . import harness as H
    from . import kaggle_client as K
    reports: List[scoring.RunReport] = []
    for ref in ("cayley-py-444-cube", "cayley-py-megaminx"):
        try:
            bundle = K.load_competition(ref, data_dir)
        except Exception:
            continue
        if not bundle or bundle.get("moves_undefined") or bundle.get("puzzle") is None:
            continue
        cases = bundle["cases"][:limit]
        rep = H.run_one(bundle["puzzle"], cases, "auto", budget_s, None,
                        None, verbose=False)
        reports.append(rep)
    if not reports:
        raise RuntimeError("no local data for the regression benchmark "
                           "(run `make data`)")
    return reports


# --------------------------------------------------------------------------- #
# 5. publish to GitHub
# --------------------------------------------------------------------------- #

def publish(message: str, token: Optional[str] = None) -> Dict:
    """Commit harness changes and push to GitHub when a token is available.

    The token is supplied by the user at runtime (env / secrets file) and is
    never written into the repo.  Without a token the publish is a no-op that
    reports 'no token' - the improvement is still recorded locally.
    """
    tok = token if token is not None else github_token()
    if not tok:
        return {"published": False, "reason": "no GITHUB_TOKEN "
                "(set env GITHUB_TOKEN or secrets file)"}
    author = os.environ.get("GITHUB_AUTHOR", "visualcomments")
    email = os.environ.get("GITHUB_EMAIL", f"{author}@users.noreply.github.com")
    repo_url = os.environ.get("GITHUB_REPO", f"https://github.com/{author}/puzzle-cracker.git")
    extra = ("AUTHORIZATION: basic "
             + __import__("base64").b64encode(
                 f"x-access-token:{tok}".encode()).decode())
    cmds = [
        ["git", "add", "-A"],
        ["git", "-c", f"user.name={author}", "-c", f"user.email={email}",
         "commit", "-m", message],
        ["git", "-c", f"http.extraheader={extra}", "push", "-q", repo_url, "main"],
    ]
    for cmd in cmds:
        res = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
        if res.returncode != 0 and b"nothing to commit" not in res.stderr.encode() \
           and "nothing to commit" not in res.stderr:
            return {"published": False, "reason": res.stderr.strip()[:300]}
    return {"published": True, "commit": message}


# --------------------------------------------------------------------------- #
# the loop
# --------------------------------------------------------------------------- #

def improve_once(reports: List[scoring.RunReport], cfg: Optional[Config] = None,
                 data_dir: str = "data", allow_publish: bool = True) -> Dict:
    """One full improvement round: analyze -> plan -> apply -> regress ->
    record -> publish.  Returns a structured outcome."""
    cfg = cfg or Config.load()
    analysis = analyze(reports, cfg)
    cands = plan(analysis, cfg)
    outcome = {"analysis": analysis, "applied": None, "regression": None,
               "published": None, "record": None}

    if cands:
        change = cands[0]
        before = cfg.to_dict()
        apply_change(cfg, change)
        try:
            new_reports = regress(cfg, data_dir=data_dir)
            new_analysis = analyze(list(new_reports), cfg)
            keep = new_analysis["solve_rate"] >= analysis["solve_rate"] or \
                   new_analysis["mean_length"] <= analysis["mean_length"]
            if keep:
                cfg.save()
                outcome["applied"] = {**change, "kept": True,
                                      "new_solve_rate": new_analysis["solve_rate"]}
                outcome["regression"] = new_analysis
            else:
                _revert(cfg)  # revert to the saved config
                outcome["applied"] = {**change, "kept": False}
                outcome["regression"] = new_analysis
        except Exception as exc:
            _revert(cfg)
            outcome["applied"] = {**change, "kept": False, "error": str(exc)}
    else:
        outcome["applied"] = {"kept": False, "note": "no candidate changes"}

    record = write_record(outcome, cfg)
    outcome["record"] = record
    if allow_publish:
        outcome["published"] = publish(record)
    return outcome


def _revert(cfg: Config) -> None:
    """In-place revert: reload cfg from disk (or defaults)."""
    fresh = Config.load().to_dict()
    for k, v in fresh.items():
        setattr(cfg, k, v)


def write_record(outcome: Dict, cfg: Config) -> str:
    os.makedirs(IMPROVE_DIR, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    a = outcome["analysis"]
    lines = [f"# Improvement round {stamp}", ""]
    lines.append(f"- solved {a['solved']}/{a['total']} "
                 f"({100 * a['solve_rate']:.1f}%), total moves "
                 f"{a['total_moves']}, mean {a['mean_length']:.1f}")
    lines.append(f"- strengths: {', '.join(a['strengths'])}")
    lines.append(f"- weaknesses: {', '.join(a['weaknesses'])}")
    app = outcome["applied"] or {}
    lines.append(f"- applied: {app.get('kind', 'none')} "
                 f"{app.get('from')} -> {app.get('to')} "
                 f"(kept: {app.get('kept')})")
    rc = outcome.get("regression") or {}
    if rc and rc.get("solve_rate") is not None:
        lines.append(f"- regression: {100 * rc['solve_rate']:.1f}% "
                     f"solve, mean {rc.get('mean_length', 0):.1f}")
    pub = outcome.get("published") or {}
    lines.append(f"- publish: {pub.get('published', False)} "
                 f"({pub.get('reason', '')})")
    text = "\n".join(lines) + "\n"
    path = os.path.join(IMPROVE_DIR, f"round-{stamp}.md")
    with open(path, "w") as f:
        f.write(text)
    return f"improvement round {stamp} recorded -> docs/improvements/"


if __name__ == "__main__":
    # optional CLI: python -m puzzle_cracker.self_improve '{"solved":..}' 
    raw = sys.argv[1] if len(sys.argv) > 1 else None
    if raw:
        d = json.loads(raw)
        rep = scoring.RunReport("cli", [])
        rep.results = [scoring.CaseResult(str(i), True, [], len(v), 0.0)
                       for i, v in enumerate(d.get("lengths", []))]
        rep.results = rep.results[:0]
        print(json.dumps(improve_once([rep]), indent=2)[:2000])