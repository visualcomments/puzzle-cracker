---
name: agent-orchestration
description: Multi-agent architecture for the harness - role pantheon (Orchestrator/Researcher/Solver/Analyst/Verifier/Distiller), background dispatch, the council pattern (race strategies in parallel, keep the best), and the compound capture loop (write lessons where the next round reads them). Use when planning work, running parallel strategy comparisons, or after any round.
verified: 2026-08-01
---

# Agent Orchestration

Architecture borrowed from two open-source agent suites, adapted to puzzle
solving:

* **oh-my-opencode-slim** (github.com/alvinunreal/oh-my-opencode-slim) -
  a pantheon of specialized agents run by an Orchestrator that plans the
  work graph, dispatches specialists in the background and reconciles
  results; a *council* runs several configurations in parallel on the same
  question and keeps the best answer.
* **compound-engineering-plugin** (github.com/everyinc/compound-engineering
  -plugin) - the loop brainstorm -> plan -> build -> review -> **capture**:
  knowledge from each round is written where the next round reads it, and
  one plugin packaged for many agent hosts.

## The pantheon (puzzle edition)

| role | mission |
| --- | --- |
| `orchestrator` | plan the solve graph, dispatch specialists, reconcile reports |
| `researcher` | study CayleyPy / khoruzhii / DeepCubeA material, propose improvements |
| `solver` | run the harness on a bundle with a strategy, return a scored report |
| `analyst` | analyze results vs targets, propose one safe change |
| `verifier` | run the correctness oracle before anything is shipped |
| `distiller` | turn the winning strategy into `strategy.py` + scorecard |

Role cards ship in `deploy/opencode/agents/*.md` and in
`puzzle_cracker/agents.ROLES`.

## Council (parallel strategy race)

`agents.council(bundles, strategies, ...)` runs several solver strategies
in parallel (threads) on the same scramble slices and returns reports best-
first by score.  Use it before committing to a new default - a typical
race: `beam-w8k` vs `beam-w16k` vs `poly` vs `auto`.  The winner becomes
the harness config; the improvement loop then captures why.

## Background dispatch

`agents.dispatch_python([...])` runs a harness module in a subprocess with
a timeout - the orchestrator's way to parallelize across configurations
without blocking the conversation.

## Compound capture loop

After every round, write the lesson to `docs/learnings/LESSONS.md`
(`agents.capture(...)`); every improvement round reads it FIRST
(`agents.lessons()`).  This is what makes engineering compound: the next
change is easier because the previous one left its knowledge behind.

## Multi-host packaging

The same content (policy + skills + roles + docs) is wrapped for many hosts
via `deploy/marketplace/` (Claude/Cursor/Codex/OpenCode/OMP manifests) and
`deploy/dsh-plugin/` (DeepSeek Harness bundle) - compound-engineering
style.

## When NOT to use

- Single quick run: just the harness + improvement loop;
- The council adds value when strategies genuinely differ (beam width,
  method, budget); do not race identical configs.