# Polynomial complexity budgets (reference)

Everything the agent ships must obey `O(poly(n, d))`.  This table is the
default budget reference; when in doubt, use the formulas here.

Notation:

- `n` - the puzzle's size parameter (number of facelets for twisty puzzles,
  length of the permutation for graph puzzles, graph order, ...);
- `d` - scramble length / instance size;
- `B` - node budget of any search;
- `moves` - worst-case number of moves in the returned path.

## Default budgets

| solver | cost (runtime) | moves bound | notes |
| --- | --- | --- | --- |
| constructive pancake / reversals | O(n^2) | <= 2n | place element i with <=2 prefix flips |
| constructive transposition sort | O(n log n) compares | <= 2n transpositions | via cycles |
| staged cube tail (documented) | O(n^2) table smallness | poly | table sizes fixed constants for 3x3x3 |
| beam search | O(B * deg * movecost) | B | always set B = C * n^k |
| biBFS (small puzzles only) | O(S) with S = |reachable| | S small constant | allowed when S is genuinely small (2x2x2: 3.6M, reversals n<=9) |
| IDA* | O(B * deg * depth) | B | only with poly budget B |

## Enforcement in code

`puzzle_cracker/complexity.py` provides:

- `poly_budget(n, d, C=1.0, n_pow=2, d_pow=1, floor=512)` -> int budget;
- `ensure_poly(name, used, budget)` - hard assert, fail fast;
- `solve_pancake_poly(puzzle, state)` - constructive O(n^2) solver for
  prefix-reversal / segment-reversal puzzles (pancake), always returns a
  valid path of <= 2n moves;
- `scaling_check(fn, sizes)` - runs fn at 3 sizes and reports the cost
  growth exponent (must be ~1..3, not 2^(k)).

## NP-hardness guardrail

- Shortest path in a Cayley graph (and "solve with <= k moves" decision) is
  NP-hard in general - do not design for it under the contract.
- Any solution is fine for the contract; lengths are then reduced by local
  polynomial passes, never by exhaustive search.