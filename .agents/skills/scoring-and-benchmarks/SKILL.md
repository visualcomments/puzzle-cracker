---
name: scoring-and-benchmarks
description: Measure solve rate and total moves, keep held-out scramble sets, write scorecards, run comparisons between solver strategies. Use for every run and every strategy comparison in the harness.
verified: 2026-08-01
---

# Scoring and Benchmarks skill

## Metric

For the CayleyPy competition family: **total path length** over scrambles
(the shorter, the better), with solve rate as the hard constraint.

Report for every run:

- solve rate (solved / total);
- total moves (sum over solved);
- mean solution length;
- score = 100 * solve_rate / (1 + mean_length) (harness default).

## Benchmark hygiene

- Held-out set: a fixed, seeded random-walk set (e.g. 50 scrambles of each
  length 10..40, seed fixed) - never tune a solver on the set you score on;
- baseline first: record the naive solver's score before any optimization;
- one change per run: same seed, same budget, one strategy change;
- if a run is not reproducible (nondeterministic solver, timers), say so.

## Scorecards

Append to `docs/scorecards/<puzzle>-<yyyymmdd>.md`:

```markdown
## <puzzle> <method> <date>
solve rate: 19/20 (95%)
total moves: 406
mean length: 21.4
command: <exact>
machine: <os/python>
notes: <one-two lines>
```

The harness's `distil()` writes the score into `strategy.py`; keep the
scorecard as the human record.

## When NOT to use

- Fine-tuning a specific solver search: that is a solver concern, not a
  scoring concern.