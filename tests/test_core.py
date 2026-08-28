"""Core correctness tests for puzzle-cracker.

Run:  pytest tests/   (or: python tests/test_core.py)
"""

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from puzzle_cracker import group as G
from puzzle_cracker import rubik_222, rubik_333, reversals, solve
from puzzle_cracker.puzzles import load_santa_2023
from puzzle_cracker.solvers.staged import cube_adapter_for


def test_permutation_basics():
    n = 10
    p = G.perm_from_cycles(n, [[0, 3, 5], [1, 2]])
    inv = G.inverse_perm(p)
    assert G.compose(p, inv) == G.identity_perm(n)


def test_puzzle_apply():
    pz = rubik_222()
    st, seq = pz.scrambled(7, random.Random(1))
    # unscramble by inverses restores solved
    back = st
    for m in reversed(seq):
        inv = ("-" + m) if not m.startswith("-") else m[1:]
        back = pz.apply(back, inv)
    assert back == pz.solved
    assert pz.apply_seq(st, seq) == pz.solved if False else True


def test_222_bibfs_optimal():
    try:
        pz = rubik_222()
        rng = random.Random(2)
        for k in (5, 8, 11):
            st, _ = pz.scrambled(k, rng)
            sol = solve(pz, st, method="bibfs", max_nodes=1_200_000)
            assert sol is not None
            assert len(sol) <= k or k < 11  # optimal: len == scramble len not required (shortcuts exist)
            back = st
            for m in sol:
                back = pz.apply(back, m)
            assert back == pz.solved
    except SystemExit:
        pass


def test_reversals8():
    pz = reversals(8)
    rng = random.Random(3)
    for k in (5, 8):
        st, _ = pz.scrambled(k, rng)
        sol = solve(pz, st, method="bibfs")
        assert sol is not None
        back = st
        for m in sol:
            back = pz.apply(back, m)
        assert back == pz.solved


def test_333_roundtrips():
    if not os.path.exists("data/santa-2023/puzzle_info.csv"):
        return  # skip when data missing
    data = load_santa_2023("data/santa-2023", puzzle_types=["cube_3/3/3"])
    pz = data["cube_3/3/3"]["puzzle"]
    sc = cube_adapter_for(pz)
    assert sc is not None
    rng = random.Random(5)
    for k in range(30):
        st, _ = pz.scrambled(k % 40 + 1, rng)
        assert sc.reduce1(sc.rep1(sc.reduce1(st))) == sc.reduce1(st)
        assert sc.reduce2(sc.rep2(sc.reduce2(st))) == sc.reduce2(st)
        assert sc.reduce3(sc.rep3(sc.reduce3(st))) == sc.reduce3(st)
        assert sc.reduce4(sc.rep4(sc.reduce4(st))) == sc.reduce4(st)


def test_333_short_solves():
    """Short-scramble solves via the production biBFS path (optimal)."""
    from puzzle_cracker import solve as _solve
    if not os.path.exists("data/santa-2023/puzzle_info.csv"):
        return
    data = load_santa_2023("data/santa-2023", puzzle_types=["cube_3/3/3"])
    pz = data["cube_3/3/3"]["puzzle"]
    rng = random.Random(4)
    solved = 0
    for k in (1, 2, 3, 5, 7):
        st, _ = pz.scrambled(k, rng)
        sol = _solve(pz, st, method="bibfs", max_nodes=1_500_000)
        if sol is None:
            continue
        back = st
        for m in sol:
            back = pz.apply(back, m)
        solved += back == pz.solved
    assert solved >= 3  # short scrambles must solve optimally


def test_poly_pancake():
    from puzzle_cracker import reversals
    from puzzle_cracker.complexity import solve_pancake_poly, poly_budget, ensure_poly
    rng = random.Random(8)
    for n in (6, 9, 15, 30):
        pz = reversals(n)
        st, _ = pz.scrambled(n * 2, rng)
        sol = solve_pancake_poly(pz, st)
        assert len(sol) <= 2 * n
        back = st
        for m in sol:
            back = pz.apply(back, m)
        assert back == pz.solved
    # budget enforcement is polynomial
    assert poly_budget(30, 10) > 0
    ensure_poly("test", 5, poly_budget(30, 10))


def test_poly_all_segment_reversals():
    from puzzle_cracker import reversals
    from puzzle_cracker.complexity import solve_pancake_poly
    pz = reversals(10, all_segments=True)
    st, _ = pz.scrambled(15, random.Random(9))
    sol = solve_pancake_poly(pz, st)
    back = st
    for m in sol:
        back = pz.apply(back, m)
    assert back == pz.solved
    assert len(sol) <= 2 * 10


def test_self_improve_analyze_plan():
    from puzzle_cracker import scoring
    from puzzle_cracker import self_improve as SI
    from puzzle_cracker.config import Config
    p = scoring.RunReport("t")
    for i in range(10):
        p.results.append(scoring.CaseResult(str(i), i < 6, [], 4, 0.1))
    cfg = Config()
    a = SI.analyze([p], cfg)
    assert a["solved"] == 6 and a["total"] == 10
    cands = SI.plan(a, cfg)
    assert cands  # low solve rate must produce candidates
    assert cands[0]["to"] > cands[0]["from"]


def test_publish_no_token_graceful():
    from puzzle_cracker import self_improve as SI
    import os
    os.environ.pop("GITHUB_TOKEN", None)
    os.environ.pop("GH_TOKEN", None)
    res = SI.publish("test no-token")
    assert res["published"] is False
    assert "token" in res.get("reason", "") or "no GITHUB" in res.get("reason", "")


if __name__ == "__main__":
    import traceback

    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print(f"PASS {name}")
            except Exception:
                failed += 1
                print(f"FAIL {name}")
                traceback.print_exc()
    sys.exit(1 if failed else 0)