# Revision-2 Phase-0 design probes (2026-08-20)

Read-only, unreleased probes on probe-only RNG streams (leading parts 9101–9107,
disjoint from every published stream). These freeze the E8/E9 designs before any
SPEC or code lands. Probe scripts are session scratch; results recorded here are
the design inputs, not published numbers.

## P0.1 → E8-B redesigned: the boundary arm becomes a label-noise stress frontier

Original plan (pin true answered risk just below α=0.10 via a uniform concept
intercept) is **infeasible for two reasons the probe surfaced**:

1. **The walk adapts.** Raising ambient risk (intercepts 0.5→1.1) just moves the
   deployed threshold up (mean τ 0.638→0.748) while deployed R_M stays ≈0.053–0.058
   — the gate escapes the stress by buying coverage down (coverage 0.947→0.862).
2. **The information floor forbids near-α certification.** At ~83 calibration
   clusters `ln(1/δ)(1−α)/n ≈ 0.033`, so risk within ~0.03 of α cannot certify at
   208 sites by construction; a "window at (0.08, 0.10)" would only ever measure
   declines.

**Redesign (B1 probe, R=12/arm):** flip labels of every cohort (train/aux/cal/eval)
at rate η — an exchangeable aleatoric floor no threshold can screen. Result:

| η | certify rate | mean deployed R_M | mean τ | exceed |
|---|---|---|---|---|
| 0.01 | 1.0 | 0.0582 | 0.605 | 0 |
| 0.02 | 1.0 | 0.0554 | 0.687 | 0 |
| 0.03 | 1.0 | 0.0536 | 0.763 | 0 |
| 0.04 | 0.0 | — | — | 0 |

A sharp certify-cliff between η=0.03 and 0.04, zero exceedances throughout, and
the mechanism visible (τ escalation = coverage spent to stay valid). The released
arm sweeps `E8_NOISE_SWEEP = (0.01, 0.02, 0.03, 0.035, 0.04)` at R=300 and reports
certify rate, coverage, deployed R_M distribution, and exceedance vs δ — the
claim: **as aleatoric risk approaches the floor-adjusted boundary, the certifier
declines rather than violates**, which is the stressed-validity evidence the
review asked for. (η is applied identically to all cohorts, so exchangeability —
Assumption 1 — holds by construction and validity must too; an exceedance > δ
here survives the estimand/stream triage as a genuine finding.)

## P0.3 + B2 → E9-B frozen: the FNR frontier is real and sits at ~400 sites

True influence-weighted FN-rate among answered positives (validity-grid world,
lowest grid τ): mean 0.448 (range 0.411–0.482, R=40). Walks on outcome-weighted
atoms (`weights=y`, zero library change):

| sites | budget | certify rate | fresh FNR | exceed |
|---|---|---|---|---|
| 208 | 0.5 / 0.55 / 0.6 | 0.0 | — | 0 |
| 400 | 0.5 | 0.0 | — | 0 |
| 400 | 0.55 | 0.25 | 0.431 | 0 |
| 400 | 0.6 | 1.0 | 0.449 | 0 |

At 208 sites nothing ≤0.6 certifies (per-site FNR variance starves the bet even
though the raw margin at 0.5 exceeds the floor); at 400 the frontier turns on
between 0.5 and 0.6. **Frozen design:** `E9_FNR_LADDER = (0.4, 0.5, 0.55, 0.6)`
(0.4 = always-refuses negative control), `E9_FNR_SWEEP = (208, 400, 600)`, R=200.
The paper's claim: a class-conditional certificate is *issuable* on the same
atoms, and its frontier — no FNR budget below ~0.55 at any realistic site count —
is the honest price of the symmetric-loss operating point (eICU derived answered
FNR: median 0.87 across the 20 re-splits, from the released panel).

## P0.5 → E8-C frozen: heads = (gbm, degraded); temperature miscalibration is a no-op by construction

R=10 pilot at 208 sites, α=0.10, all through the identical atoms + walk:

| head | certify rate | mean τ | mean coverage | mean R_M | exceed |
|---|---|---|---|---|---|
| linear (reference) | 1.0 | 0.552 | 0.984 | 0.058 | 0 |
| GBM (HistGradientBoosting, 200 iter) | 1.0 | 0.564 | 0.981 | 0.059 | 0 |
| temperature-sharpened linear (T=0.5) | 1.0 | 0.572 | 0.989 | 0.060 | 0 |
| **degraded** (features 0–1 zeroed, R=8) | 1.0 | **0.745** | **0.892** | 0.056 | 0 |

Two design findings:

1. **Temperature miscalibration cannot stress this gate**: the score is
   `max(p, 1−p)` and a temperature transform is monotone in it, so the answered
   sets along the grid are unchanged — the walk simply certifies a different τ
   label for the same sets. This is an *analytic* property worth one paragraph
   (the certificate is insensitive to monotone miscalibration by construction);
   the "miscalibrated head" arm is therefore replaced.
2. **The degraded head (denied the first two informative features) carries the
   S2-26/S2-27 demonstration**: certification survives, validity holds
   (exceed 0), and the walk prices the lost quality visibly — τ up 0.55→0.75,
   coverage down 0.98→0.89. GBM ≈ linear here because the generator's signal is
   linear (stated as such; the point of the GBM row is that a nonlinear
   black-box passes the same gate unchanged, with the attribution layer
   explicitly not surviving — the scoped Contribution-3 statement).

Frozen: `E8_HEAD_ARMS = ("gbm", "degraded")`, `E8_GBM_MAX_ITER = 200`,
`E8_DEGRADED_ZERO_FEATURES = 2`.

## Still pending

- **P0.2** BBSE power pilot (source-site counts 600–1600 × two target modes) —
  queued behind the P0.0 control grid rerun; freezes `E9_SOURCE_SWEEP`/`E9_R`.
- **P0.4** full `run_eicu` wall-clock — gates the subgroup re-run (3b).
- **P0.0** control-rerun byte-diff vs released `experiments/out/` — grid running.
