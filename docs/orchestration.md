# Orchestration architecture

## Roles (pantheon)

`puzzle_cracker/agents.py` defines six roles with per-role skills and
tools.  OpenCode agent files live in `deploy/opencode/agents/*.md`.

```
                 +--------------+
   user/kaggle ->| Orchestrator |---> Researcher (papers/ideas)
                 +--------------+---> Solver xN (background, council race)
                        |            ---> Analyst (weaknesses -> change)
                        v            ---> Verifier (oracle)
                 improvement loop    ---> Distiller (strategy.py + scorecard)
                        |
                        v
              capture -> docs/learnings/LESSONS.md
```

## Council example

```python
from puzzle_cracker import agents
from puzzle_cracker import competitions as C
bundles = C.load_all("data")
reports = agents.council(
    bundles,
    {"beam-w8k": dict(method="beam", budget_s=5.0),
     "beam-w16k": dict(method="beam", budget_s=5.0),
     "poly": dict(method="beam", budget_s=5.0)},
    limit=6, workers=4)
for r in reports[:2]:
    print(r.puzzle_name, r.solve_rate, r.total_moves)
```

## Capture loop

```python
agents.capture("per-case budgets must be timers from the case start",
               context="megaminx kernel v3")
print(agents.lessons())
```

## Multi-host install

- OpenCode: `deploy/opencode/agents/*.md` or
  `"plugin": ["puzzle-cracker@git+https://github.com/visualcomments/puzzle-cracker.git"]`;
- Claude/Cursor/Codex: marketplaces in `deploy/marketplace/`;
- DeepSeek Harness: `deploy/dsh-plugin/` bundle (`dsh plugin --profile web
  add file:...`);
- AGENTS.md-native hosts: run from the workspace root.

Attribution: orchestration pattern from
[oh-my-opencode-slim](https://github.com/alvinunreal/oh-my-opencode-slim);
capture loop + multi-host packaging from
[compound-engineering-plugin](https://github.com/everyinc/compound-engineering-plugin).