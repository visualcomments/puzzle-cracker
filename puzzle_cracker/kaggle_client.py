"""Kaggle competition data access for the CayleyPy puzzle family.

The competitions list that matters for this harness:

    santa-2023                                 (cube 2x2..33x33, globe, wreath)
    cayley-py-444-cube / -555 / -666 / -777    (NxNxN slice-cube)
    cayley-py-megaminx                         (megaminx, 120 facelets)
    cayleypy-reversals, cayleypy-transposons   (graphs_info server comps)
    cayleypy-ihes-cube, cayley-py-professor-tetraminx-solve-optimally,
    cayleypy-christophers-jewel, cayleypy-glushkov, cayleypy-rapapport-m2,
    lrx-oeis-a-186783-brainstorm-math-conjecture

Credentials are read, in order of precedence:

    1. env ``KAGGLE_USERNAME`` / ``KAGGLE_KEY`` (key form ``KGAT_...``);
    2. env ``KAGGLE_TOKEN`` (the bare ``KGAT_...`` value, username optional);
    3. ``~/.kaggle/kaggle.json`` (written by ``make install`` / setup).

The token is a Kaggle API credential: it authenticates (``/api/v1/...``
returns 401 without it) and gates the agent competitions this harness plays.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from typing import Dict, List, Optional

COMPETITIONS = [
    "santa-2023",
    "cayley-py-444-cube", "cayley-py-555-cube", "cayley-py-666-cube",
    "cayley-py-777-cube", "cayley-py-megaminx", "cayleypy-ihes-cube",
    "cayley-py-professor-tetraminx-solve-optimally",
    "cayleypy-reversals", "cayleypy-transposons", "cayleypy-christophers-jewel",
    "cayleypy-glushkov", "cayleypy-rapapport-m2",
    "lrx-oeis-a-186783-brainstorm-math-conjecture",
]


def token() -> Optional[str]:
    for var in ("KAGGLE_KEY", "KAGGLE_TOKEN"):
        v = os.environ.get(var)
        if v:
            return v
    path = os.path.expanduser("~/.kaggle/kaggle.json")
    if os.path.exists(path):
        try:
            return json.load(open(path)).get("key")
        except Exception:
            return None
    return None


def username() -> str:
    v = os.environ.get("KAGGLE_USERNAME")
    if v:
        return v
    try:
        path = os.path.expanduser("~/.kaggle/kaggle.json")
        return json.load(open(path)).get("username", "")
    except Exception:
        return ""
    return ""


def _kaggle_cli() -> Optional[str]:
    return shutil.which("kaggle")


def ensure_credentials() -> bool:
    """Ensure the token is available to the kaggle CLI."""
    if token() is None:
        return False
    if _kaggle_cli() is not None:
        os.environ.setdefault("KAGGLE_USERNAME", username() or "kaggle")
        os.environ.setdefault("KAGGLE_KEY", token() or "")
        return True
    return False


def list_competitions() -> List[str]:
    """List the competitions this credential can see (via the REST API)."""
    import urllib.request
    tok = token()
    if not tok:
        return []
    req = urllib.request.Request(
        "https://www.kaggle.com/api/v1/competitions/list",
        headers={"Authorization": f"Bearer {tok}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        return [c.get("url", "").rstrip("/").rsplit("/", 1)[-1]
                for c in data if c.get("category") in ("Featured", "Research",
                                                       "Playground")]
    except Exception:
        return []


def fetch_competition(ref: str, dest: str,
                      files: Optional[List[str]] = None) -> bool:
    """Download a competition's data files into ``dest`` (unzipped)."""
    os.makedirs(dest, exist_ok=True)
    if not ensure_credentials():
        print("[kaggle] no credentials - install with `make setup` or set "
              "KAGGLE_KEY")
        return False
    cli = _kaggle_cli()
    if cli is None:
        print("[kaggle] `kaggle` CLI not found - pip install kaggle")
        return False
    cmd = [sys.executable and cli or cli, "competitions", "download",
           "-c", ref, "-p", dest]
    if files:
        cmd += ["-f", ",".join(files)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[kaggle] download {ref} failed: {res.stderr.strip()}")
        return False
    # unzip any archives
    for name in sorted(os.listdir(dest)):
        if name.endswith(".zip"):
            try:
                import zipfile
                with zipfile.ZipFile(os.path.join(dest, name)) as z:
                    z.extractall(dest)
                os.remove(os.path.join(dest, name))
            except Exception:
                pass
    return True


def load_competition(ref: str, data_dir: str, **kw):
    """Load a competition directory into the harness format.

    Returns ``{"puzzle": Puzzle, "cases": [...]}`` (agent/santa style) or a
    graphs-style bundle, or raises FileNotFoundError when data is absent.
    """
    from . import puzzles as P
    d = os.path.join(data_dir, ref)
    if ref == "santa-2023":
        return P.load_santa_2023(d, **kw)
    info = os.path.join(d, "puzzle_info.json")
    if os.path.exists(info):
        return P.load_agent_competition(d, **kw)
    if os.path.exists(os.path.join(d, "graphs_info.json")) or \
       os.path.exists(os.path.join(d, "graphs_info.h5")):
        size = kw.pop("size", "12")
        return P.load_server_competition(d, size, **kw)
    raise FileNotFoundError(f"no data for {ref} in {d} "
                            "(run `make data` or kaggle_client.fetch_competition)")


def ensure_data(data_dir: str, refs: Optional[List[str]] = None, **kw) -> List[str]:
    """Download+load the wanted competitions.  Returns the refs that have
    usable local data."""
    ok = []
    for ref in refs or COMPETITIONS:
        d = os.path.join(data_dir, ref)
        probe = [f for f in ("puzzle_info.json", "puzzle_info.csv",
                             "graphs_info.json", "graphs_info.h5",
                             "test.csv") if os.path.exists(os.path.join(d, f))]
        if not probe:
            fetch_competition(ref, d)
        try:
            load_competition(ref, data_dir, **kw)
            ok.append(ref)
        except Exception as exc:
            print(f"[kaggle] {ref}: {exc}")
    return ok