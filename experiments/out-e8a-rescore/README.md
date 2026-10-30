# out-e8a-rescore/ -- POST-HOC replay and population rescoring of the E8 comparator arm

**Status: POST-HOC (2026-10-29).** Nothing in this directory is a certified
quantity. The released comparator arm (`experiments/out/E8_comparators.csv`,
E8 arm A) is unchanged; it is read, never written, and it is reproduced here
before anything is emitted.

Produced by `experiments/rescore_e8a.py` (about 20 minutes; the emission
recorded here took 1,149 s, `wall_clock_s` in E8a_rescore.json):

    python -m experiments.rescore_e8a

What is computed, and from what. Every arm-A draw is replayed on its frozen
stream (`_rng(8, 0, n_idx, r)` -> `_draw_split` -> the 200-site eval pool with
prefix `e8av{n_idx}_{r}`), and the five walks re-run in run_E8's order, with
the site bootstrap consuming `_rng(8, 0, n_idx, r, 1)` at alpha = 0.05 before
0.10. The script refuses to write unless all 12,000 frozen rows replay their
certified flag and all 6,056 certified rows replay their deployed tau
exactly, their coverage to four decimals, their `rm_fresh` to six and their
`rm_exceed` flag; the pooled fresh-pool counts (Student-t 61, site bootstrap
59 of 1,200 at alpha = 0.05, zero elsewhere) are pinned as well.

Each certified row is then scored a second way: against the site-population
R_M the certificate names, which this generator gives in closed form. Site
size is drawn independently of the site effect, so the influence weights
cancel and R_M = E_u[P_u(ans & err)] / E_u[P_u(ans)]; that is linear in the
site prevalence, evaluated at pibar = E[sigmoid(logit 0.095 + 0.5 Z)] =
0.1036567 (Gauss-Hermite quadrature), with the head's logit Gaussian within
each class. The pooled population counts are pinned (Student-t 46, site
bootstrap 45 of 1,200 at alpha = 0.05; WSR, MP-EB and Hoeffding zero), and
the closed form is checked against direct simulation at the pinned near-alpha
row (60 sites, draw 199, tau 0.61, closed form 0.049944) and the eight other
certified Student-t / bootstrap rows nearest alpha: a record-level Monte
Carlo (u -> y -> x | y, 20M records per row) and a fresh 4,000-site
`draw_cohort` pool scored by `_rm_on_pool`, each within five standard errors,
or nothing is written. The truth-check streams are `_rng(8, 90, ...)`, an
index family no experiment uses.

Files: `E8a_rescore.csv` (one row per certified frozen row: site count, draw,
alpha, method, tau, coverage, `rm_fresh`, `rm_population`, their difference,
and the two exceed flags) and `E8a_rescore.json` (pooled and per-site-count
counts under both scorings with exact Clopper-Pearson 95% intervals, the
concordance split with its exact McNemar p, the near-alpha pile-up, the
fresh-minus-population residual, pibar, the self-check, the truth check,
`_run` with the UTC time, git sha and sha256 of the frozen CSV).

How to read it. `rm_fresh` is Section 3.9's released metric and stays
correct as that metric; it also counts the 200-site pool's own sampling noise
in R_M (sd about 0.0015), which matters only for certificates whose risk
sits near alpha. `rm_population` is a second estimand for the same
certificates, not a correction of the first. Even an exactly calibrated
level-delta test realises less than delta under this fixed-sequence walk, so
neither column grades the asymptotic bounds as conservative, and no
per-site-count cell is labelled anti-conservative or conservative: every
per-site-count exact interval for Student-t and the site bootstrap at
alpha = 0.05 contains 0.05. The zero-exceedance cells of 200 certified rows
(Student-t and the site bootstrap at alpha = 0.10 at every site count, WSR at
alpha = 0.05 with 400 sites and at alpha = 0.10 with 150-400 sites, MP-EB at
alpha = 0.10 with 400 sites) have exact upper bound 0.018275 under both
scorings. That reflects the walk's sub-delta realised level, not a grading of
the bounds.
