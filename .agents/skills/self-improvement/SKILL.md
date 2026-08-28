---
name: self-improvement
description: Run the continuous improvement loop after every scoring result - analyze strengths and weaknesses, apply a safe deterministic change, benchmark it, and publish the improved harness to GitHub when the user supplies a token. Use after every competition run.
verified: 2026-08-01
---

# Self-Improvement Loop

After every scoring run the agent must close the loop: **results ->
analysis -> change -> regression -> publish**.  The harness ships this as
`puzzle_cracker/self_improve.improve_once(reports, ...)`.

## The loop (one round = one change)

1. **analyze** - `self_improve.analyze(reports, cfg)` compares solve rate
   and mean length against the configured targets and lists strengths and
   weaknesses (per-puzzle breakdown).
2. **plan** - `self_improve.plan(...)` produces deterministic candidate
   changes (wider beam, longer budgets, deeper optimal search) from the
   tuning table in `config/harness.json`.
3. **apply + regress** - the *safest* change is applied, benchmarked on a
   small held-out regression (2 puzzles x ~4 cases), and **kept only if it
   does not regress**; otherwise reverted.
4. **record** - the round is written to `docs/improvements/round-*.md`
   (analysis, change, regression, publish status).
5. **publish** - `self_improve.publish(message)` commits and pushes the
   improved harness to GitHub **when the user supplies a token**: env
   `GITHUB_TOKEN` or `~/.config/puzzle_cracker/secrets.env`.  Tokens are
   never written into the repo; without a token the improvement is still
   recorded locally.

## Rules

- One knob per round; measure before and after; revert on regression.
- Never commit credentials (AGENTS.md rule 6 applies).
- Publish messages start with `harness improvement:` and reference the
  round file.
- When the megaminx/other kernel results arrive: analyze the official score
  first, then run `make improve` against the new config.

## Commands

```bash
python -m puzzle_cracker.harness --ref ... --limit ... --improve   # loop on a run
make improve
```

## When NOT to use

- Before a first baseline (there must be results to analyze);
- When the change is architectural (new solver): that is a regular
  implementation task - the loop stays for the tuning adjustments around it.