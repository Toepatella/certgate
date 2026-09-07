# out-bbse-probe/ -- POST-HOC coverage probe of the BBSE uncertainty box

**Status: POST-HOC (2026-09-04).** A diagnostic of the asymptotic bootstrap
intervals behind the label-shift mode, with the head held fixed. No certified
quantity descends from it; `BBSE_BOOT` is read and never changed; no frozen
file is read or written.

Produced by `experiments/probe_bbse_coverage.py`:

    python -m experiments.probe_bbse_coverage          # n_aux in {36, 42, 74}, 400 fits each

Files: `BBSE_probe.csv` (one row per fit: the four intervals, the truths, the
coverage flags, the propagated odds-ratio interval and its width, the decline
reason) and `BBSE_probe.json` (per-n_aux and pooled coverage with exact
intervals, decline rates, widths, the implied certificate level, the
Monte-Carlo resolution note, the fixed head's closed-form truths, `_run`).

Design: one 208-site cohort on stream `_rng(9, 2)` fixes the head; its
population confusion rates are closed-form under the class-conditional
Gaussian generator and checked against Monte Carlo. Each fit draws a fresh
auxiliary cohort of `n_aux` sites and one declared target site at the
registered shift (base rate 0.22) whose random effect is drawn in the open, so
its prevalence is known exactly; `fit_bbse` runs as the pipeline runs it.
Coverage is scored per parameter, jointly over the three bootstrap parameters
and over all four, and for the propagated odds-ratio interval against the
declared site's odds ratio and the population's. The implied certificate level
is `1 - (measured box miss + delta_bet)`, with the panel's decomposition
(three-bootstrap miss + q share + delta_bet) beside it and the exact interval
of a 400-fit estimate on both. Only the single-declared-site target mode is
probed; the multi-site bootstrap mode would need per-site effects drawn in the
open and is left for a later sidecar.
