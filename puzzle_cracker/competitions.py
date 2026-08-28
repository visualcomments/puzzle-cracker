"""Manifest of every CayleyPy-family competition the harness plays.

Single source of truth for the agent: ref, kind, data files, loader,
and download status with the KGAT credential.  `fetch_all()` downloads
whatever the token can reach; `load_all()` loads every locally-available
competition into the harness format.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from . import kaggle_client

#: ref -> {kind, description, files, loader}
COMPETITIONS: Dict[str, dict] = {
    "santa-2023": {
        "kind": "santa",
        "desc": "Santa 2023: cubes 2x2x2..33x33x33, globe, wreath (classic)",
        "files": ["puzzle_info.csv", "puzzles.csv", "sample_submission.csv"],
    },
    "cayley-py-444-cube": {
        "kind": "agent", "desc": "4x4x4 slice-cube (96 facelets, 24 moves)",
        "files": ["puzzle_info.json", "test.csv", "sample_submission.csv"],
    },
    "cayley-py-555-cube": {
        "kind": "agent", "desc": "5x5x5 slice-cube (150 facelets)",
        "files": ["puzzle_info.json", "test.csv", "sample_submission.csv"],
    },
    "cayley-py-666-cube": {
        "kind": "agent", "desc": "6x6x6 slice-cube (216 facelets)",
        "files": ["puzzle_info.json", "test.csv", "sample_submission.csv"],
    },
    "cayley-py-777-cube": {
        "kind": "agent", "desc": "7x7x7 slice-cube (294 facelets)",
        "files": ["puzzle_info.json", "test.csv", "sample_submission.csv"],
    },
    "cayley-py-megaminx": {
        "kind": "agent", "desc": "Megaminx (120 facelets, 24 face turns)",
        "files": ["puzzle_info.json", "test.csv", "sample_submission.csv"],
    },
    "cayleypy-ihes-cube": {
        "kind": "agent", "desc": "IHES picture cube (72 facelets, 18 moves)",
        "files": ["puzzle_info.json", "test.csv", "sample_submission.csv"],
    },
    "cayley-py-professor-tetraminx-solve-optimally": {
        "kind": "agent", "desc": "Professor tetraminx (optimal material)",
        "files": ["puzzle_info.json", "test.csv", "sample_submission.csv"],
    },
    "cayleypy-reversals": {
        "kind": "graphs", "desc": "segment-reversal graphs per size (server comp)",
        "files": ["graphs_info.json", "graphs_info.h5", "sample_submission.csv"],
    },
    "cayleypy-transposons": {
        "kind": "graphs", "desc": "transposition-path graphs (server comp)",
        "files": ["graphs_info.json", "graphs_info.h5", "test.csv",
                  "sample_submission.csv"],
    },
    "cayleypy-christophers-jewel": {
        "kind": "agent", "desc": "Christopher's jewel (edge-turning jewel)",
        "files": ["puzzle_info.json", "test.csv", "sample_submission.csv"],
    },
    "cayleypy-glushkov": {
        "kind": "agent", "desc": "Glushkov graph-puzzle set",
        "files": ["test.csv", "sample_submission.csv"],
    },
    "cayleypy-rapapport-m2": {
        "kind": "agent", "desc": "Rapaport-Strasser M2 (1959 paper + data)",
        "files": ["test.csv", "sample_submission.csv",
                  "Rapaport_Strasser_1959_Cayley_color_groups_and_hamilton_lines.pdf"],
    },
    "lrx-oeis-a-186783-brainstorm-math-conjecture": {
        "kind": "agent", "desc": "LRX / OEIS A-186783 brainstorm",
        "files": ["test.csv", "sample_submission.csv"],
    },
}

ALL_REFS: List[str] = list(COMPETITIONS)


def status(data_dir: str) -> Dict[str, str]:
    """Data availability per competition: 'data' | 'missing' | 'forbidden'
    (forbidden = listable via the token but not downloadable)."""
    import os
    out: Dict[str, str] = {}
    cli_ok = kaggle_client.ensure_credentials()
    for ref in ALL_REFS:
        d = os.path.join(data_dir, ref)
        have = any(os.path.exists(os.path.join(d, f))
                   for f in ["puzzle_info.json", "puzzle_info.csv",
                             "graphs_info.json", "graphs_info.h5", "test.csv"])
        if have:
            has_moves = any(os.path.exists(os.path.join(d, f))
                            for f in ["puzzle_info.json", "puzzle_info.csv",
                                      "graphs_info.json", "graphs_info.h5"])
            out[ref] = "data" if has_moves else "moves-undefined"
            continue
        if not cli_ok:
            out[ref] = "no-credentials"
            continue
        files = kaggle_client._kaggle_cli() and _listable(ref)
        out[ref] = "forbidden" if files else "missing"
    return out


def _listable(ref: str) -> bool:
    import subprocess
    res = subprocess.run([kaggle_client._kaggle_cli(), "competitions", "files",
                          "-c", ref], capture_output=True, text=True)
    return res.returncode == 0 and "name" in res.stdout


def fetch_all(data_dir: str, refs: Optional[List[str]] = None) -> List[str]:
    """Download every reachable competition; returns the refs with data."""
    ok = []
    for ref in refs or ALL_REFS:
        if kaggle_client.fetch_competition(ref, _dir(data_dir, ref)):
            ok.append(ref)
    return ok


def _dir(data_dir: str, ref: str):
    import os
    return os.path.join(data_dir, ref)


def load_all(data_dir: str, verbose: bool = True) -> Dict[str, dict]:
    """Load every locally-available competition into the harness format."""
    loaded: Dict[str, dict] = {}
    for ref in ALL_REFS:
        try:
            bundle = kaggle_client.load_competition(ref, data_dir)
            loaded[ref] = bundle
            if verbose:
                n = _case_count(bundle)
                how = "moves-undefined" if bundle.get("moves_undefined") else "ready"
                print(f"  [load] {ref}: {n} cases [{how}]")
        except FileNotFoundError as exc:
            if verbose:
                print(f"  [skip] {ref}: {exc}")
        except Exception as exc:
            if verbose:
                print(f"  [err ] {ref}: {exc!r}")
    return loaded


def _case_count(bundle: dict) -> int:
    if "cases" in bundle:
        return len(bundle["cases"])
    return sum(len(b.get("cases", [])) for b in bundle.values()) if isinstance(bundle, dict) else 0