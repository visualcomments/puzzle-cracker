# Solving on Kaggle resources (GPU kernels)

The harness computes heavy solutions **on Kaggle**, not on the local machine.
The flow for the megaminx competition (general pattern for any of the
CayleyPy family):

```bash
# 1. push the solver kernel (GPU enabled, private)
kaggle kernels push -p kernels/megaminx-beam/

# 2. watch it
kaggle kernels status -k visualcomments/puzzle-cracker-megaminx-beam-cayleypy

# 3. collect the produced submission
kaggle kernels output -k visualcomments/puzzle-cracker-megaminx-beam-cayleypy \
        -p outputs/kernel
#    -> outputs/kernel/submission.csv

# 4. submit to the competition
kaggle competitions submit -c cayley-py-megaminx \
        -f outputs/kernel/submission.csv -m "puzzle-cracker beam"
```

## How data reaches the kernel

`competition_sources` does not mount for the agent credential on fresh
kernels, so the kernel consumes the data from a **private dataset** of the
same account:

```bash
mkdir -p /tmp/meg_data && cp data/cayley-py-megaminx/* /tmp/meg_data/
cat > /tmp/meg_data/dataset-metadata.json <<'EOF'
{ "id": "visualcomments/puzzle-cracker-cayleypy-megaminx",
  "title": "puzzle-cracker cayleypy megaminx", "isPrivate": true,
  "licenses": [{ "name": "other" }] }
EOF
kaggle datasets create -p /tmp/meg_data
```

Kernel metadata then lists `dataset_sources: [visualcomments/...megaminx]`.

## The solver kernel

`kernels/megaminx-beam/megaminx_beam.py`:

- loads `puzzle_info.json` + `test.csv` from `/kaggle/input/...`;
- per case: greedy best-first, then wide colour-guided beam
  (width 8192, per-case budget 30 s, wall budget 9 h, GPU instance);
- writes `initial_state_id,path` submission (dot-separated moves);
- env knobs: `PZ_DATA`, `PZ_OUT`, `PZ_BUDGET`, `PZ_WIDTH`, `PZ_LIMIT`
  (usable for local sanity runs with tiny budgets).

## Submission etiquette

- One real submission after the kernel completes (do not waste slots on
  dummy files).
- Unsolved cases are left with an empty path; the score counts solved
  cases only (per the CayleyPy family metric).