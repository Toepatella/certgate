# out-e9a-rescore/ -- POST-HOC replay and rescoring of the label-shift power frontier

**Status: POST-HOC (2026-09-04).** The frozen arm
(`experiments/out/E9_bbse_frontier.csv`, E9 arm A) is unchanged and is
reproduced here before anything is written: every certified row's `rm_fresh`
is replayed on its frozen stream and must match to four decimals, and under
`--rho-point` the recovered BBSE box must match the frozen `[rho_lo, rho_hi]`
to six.

Produced by `experiments/rescore_e9a.py`:

    python -m experiments.rescore_e9a --rho-point

Files: `E9a_rescore.csv` (one row per certified frozen row: frozen and
replayed `rm_fresh`, the declared pool's prevalence `pi_target`, the fresh
pool's `pi_eval`, the class-reweighted `rm_rescored` and its exceed flag, the
declared-site and population odds ratios against the frozen box, and under
`--rho-point` the box's point estimate) and `E9a_rescore.json` (per-cell
frozen vs rescored exceedance with exact intervals, the exceeding rows, the
self-check block, `_run`).

What the rescoring is: the same certificate scored on the same fresh pool,
reweighted by class to the declared target pool's own oracle prevalence,
which is what the BBSE box was fitted to. It is a second estimand for the
same certificates, not a correction of the first; the manuscript reports both.
