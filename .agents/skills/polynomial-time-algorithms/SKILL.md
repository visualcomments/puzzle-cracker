---
name: polynomial-time-algorithms
description: Design and ship puzzle solvers whose worst-case runtime is polynomial in the puzzle parameters (facelet count n, scramble length d) - constructive/staged algorithms, polynomial budgets for any search, solve-then-shorten. Use whenever the agent creates or extends a solver in this harness.
verified: 2026-08-01
---

# Polynomial-Time Algorithm Design

Every algorithm the agent creates for this harness must run in
**polynomial time**: worst-case `O(poly(n, d))` where `n` is the puzzle's
size parameter (facelets, graph order, reversal length...) and `d` is the
scramble length / instance size.  No exponential-in-the-state-space search
is allowed as a solver strategy without written justification.

This is not a performance preference - it is the *complexity contract* of
the harness (AGENTS.md golden rules): the competition graphs are
astronomically large (megaminx ~10^65, 4x4x4 ~10^45), so anything
exponential in the space silently becomes impossible, while a polynomial
algorithm always finishes.

## The three rules

1. **Analyse before you code.**  Write the asymptotic cost of the solver as
   a formula in `n` and `d` *before* implementing.  If it contains terms
   like `2^d`, `n!`, `d!`, `|state-space|^k` with unbounded parameters,
   redesign.  Exceptions must be justified in the code comment and in the
   PR/artifact notes.
2. **Any search needs a polynomial budget.**  Search (biBFS, IDA*, beam) is
   allowed only with an *explicit polynomial node budget* -
   `B = C * n^k * d^m` - enforced at runtime (see
   `puzzle_cracker/complexity.py`).  Failed searches must fail fast, not
   hang.
3. **Solve, then shorten.**  The competition metric is path length, but the
   contract is polynomial time.  The winning pattern: (a) a constructive
   polynomial solver that *always* returns a valid path; (b) local
   polynomial shortening passes (macro replacement, commutator cleanup,
   short bounded beam refinement) on the result.  Chasing optimal length by
   exponential search violates the contract.

## Why shortest paths are off the table

Finding a shortest path in a Cayley graph is NP-hard in general (and
"God's-number" table solvers are exponential precomputation).  So
"best possible score" is defined under the contract as: **guaranteed
polynomial solve + polynomial shortening**, measured in `docs/scorecards/`.

## Design patterns that stay polynomial

| pattern | example | cost |
| --- | --- | --- |
| **constructive stage-bys-stage** | pancake: place the largest element with <=2 reversals, repeat | O(n) moves, O(n^2) worst |
| **commutator macros** | megaminx LBL, big-cube reduction tails | O(1) moves per piece |
| **reduction** | 4x4x4 -> centres -> edges -> 3x3x3 staged tail | O(poly(n)) moves |
| **bounded local search** | beam width B = C*n^k over at most B states | O(B * deg) |
| **solve-then-shorten** | take the constructive path, greedily drop move sequences | linear in |path| |

## Verification (both required)

1. **Complexity table** in the skill note / scorecard: the formula in (n, d)
   and why it is polynomial.
2. **Empirical scaling check**: run the solver at n = n0, 2*n0, 4*n0 and
   confirm wall time grows polynomially (`make verify` keeps a scaling
   record in the scorecard).

## When NOT to use

- Exact-optimal small puzzles (2x2x2, reversals n<=9): the state space is a
  small *constant*-sized set - bounded search there is poly in d and is the
  right tool (`cayley-graphs` skill).
- Deep-optimal research runs that explicitly opt out of the contract and
  are operator-approved - documented as such in the scorecard.