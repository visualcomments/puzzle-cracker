"""Harness configuration (the improvement surface).

Solver knobs live here so the self-improvement loop can tune them
deterministically: analyze -> change -> benchmark -> keep-or-revert ->
publish.  Runtime config is `config/harness.json`; the committed default is
`config/harness.default.json`.

No credentials ever live here - the GitHub token is read at publish time
from env `GITHUB_TOKEN` or `~/.config/puzzle_cracker/secrets.env`.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional

DEFAULT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "config", "harness.default.json")
RUNTIME = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "config", "harness.json")


@dataclass
class Config:
    beam_width: int = 8192
    beam_per_case_budget_s: float = 30.0
    beam_max_nodes: int = 4_000_000
    bibfs_max_nodes: int = 1_500_000
    ida_max_nodes: int = 2_000_000
    default_method: str = "auto"
    target_solve_rate: float = 0.8
    target_mean_length: float = 60.0
    improve_max_step: str = "beam_width"  # which knob the improver tunes first
    tuning: Dict[str, float] = field(default_factory=lambda: {
        "beam_width_step": 1.5, "beam_width_cap": 32768,
        "budget_step": 1.25, "budget_cap": 90.0,
    })

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def load(cls, path: Optional[str] = None) -> "Config":
        p = path or (RUNTIME if os.path.exists(RUNTIME) else DEFAULT)
        with open(p) as f:
            d = json.load(f)
        cfg = cls()
        for k, v in d.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
        return cfg

    def save(self, path: Optional[str] = None) -> None:
        p = path or RUNTIME
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            json.dump(self.to_dict(), f, indent=2, sort_keys=True)


def github_token() -> Optional[str]:
    """The publish credential.  Supplied by the user at runtime - never by
    the repo.  Precedence: env GITHUB_TOKEN, then secrets file."""
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok:
        return tok
    for path in (os.path.expanduser("~/.config/puzzle_cracker/secrets.env"),
                 os.path.expanduser("~/.config/puzzle_cracker/.env")):
        if os.path.exists(path):
            for line in open(path):
                if line.startswith("GITHUB_TOKEN="):
                    return line.strip().split("=", 1)[1].strip("\"'")
    return None