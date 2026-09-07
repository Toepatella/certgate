# out-e9b-positives/ -- POST-HOC second arm of the false-negative frontier

**Status: POST-HOC (2026-09-04).** The frozen arm (`experiments/out/E9_fnr.csv`,
E9 arm B) is unchanged. This directory re-runs it row for row on the frozen
streams -- the shipped rows must equal the frozen CSV cell for cell before
anything is written -- and runs a second arm on the same draws with a
positives-normalised atom. An experimental secondary certificate, never the
deployed report.

Produced by `experiments/run_e9b_positives.py`:

    python -m experiments.run_e9b_positives            # full grid, R = 200
    python -m experiments.run_e9b_positives --quick    # 20 draws per site count

Files: `E9b_fnr_positives.csv` (one row per draw, budget and arm, each
certificate scored on the fresh pool under its own estimand and under the
other's), `E9b_fnr_positives.json` (frontier per arm, truths, the shipped-row
check, `_run`), `E9b_fnr_positives.png` (certify rate versus FNR budget at
208, 400 and 600 sites, both arms, in the style of `E9_frontiers.png`; the
Supplementary Information's Figure S10).

## The two estimands

- **shipped**: `influence_atoms` with `weights = y` and the site weight
  `g_c = min(n_c, 100)` on the full site size (SPEC "Outcome-weighted atoms").
  Estimand `FNR_M = E[g_c fn_c / n_c] / E[g_c ap_c / n_c]`.
- **positives**: the same `influence_atoms` on each site's positive records,
  with `g_c+ = min(n_c+, 10)` on the positive count. Estimand
  `FNR_M+ = E[g_c+ fn_c / n_c+] / E[g_c+ ap_c / n_c+]`.

## Why the positives-normalised atom is valid (the SPEC's objection, answered)

SPEC.md, "Outcome-weighted atoms", paragraph "Validity", keeps `g_c` on the
full site size because "renormalizing by per-site answered positives would
make the weight outcome-dependent and void the outcome-independence
requirement on g_c". The atom here does not renormalise by *answered*
positives. Its weight is a function of the site's positive **count** `n_c+`:
fixed by the site's labels before any threshold is chosen, identical at every
rung of the tau grid, and never a function of the head's errors or of which
records answer. The requirement exists so that the certified quantity is one
fixed functional of the site distribution that the certificate can name; a
threshold-dependent weight would make the estimand move with tau. `n_c+` is
tau-independent, so the estimand `FNR_M+` is fixed, a ratio of expectations
over the site draw exactly parallel to `R_M`.

Under Assumption 1 the sites are exchangeable draws, so `(n_c+, the
positives' scores and errors)` are i.i.d. across sites and the per-site atoms
`Z_c = b + (g_c+ / (M+ n_c+)) sum_{i in c, y_i = 1} ans_i (err_i - b)` are
i.i.d. and bounded: the inner sum lies in `[-b n_c+, (1 - b) n_c+]`, the
prefactor scales it into `[-b, 1 - b]`, and the shift lands it in `[0, 1]`.
A site with no positives, or none answered, enters as the neutral atom
`Z_c = b`, exactly as record-less sites do for `R_M`. The sign identity
`E[Z] <= b iff FNR_M+ <= b` holds exactly as for the shipped atom (pinned in
`tests/test_e9b_positives.py`). What changes is the estimand -- sites count by
their positives, capped at ten, rather than by their records capped at a
hundred -- and the manuscript reports both, because a certificate is a
statement about one named estimand and the choice between them is a
modelling decision, not a free lunch.
