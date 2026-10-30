# out-e9-exact/ -- POST-HOC closed-form named estimands for the E9 certificates

**Status: POST-HOC (2026-10-29).** Nothing in this directory is a certified
quantity, and no released artifact moves. The two E9 arms it reads
(`experiments/out/E9_bbse_frontier.csv`, `experiments/out/E9_fnr.csv`) and
the two earlier post-hoc sidecars (`out-e9a-rescore/`, `out-e9b-positives/`)
stay exactly as released. This directory scores each released certificate
against the estimand it names. On the synthetic generator that estimand has a
closed form. Audits FNR-1, FNR-5 and FNR-6 (2026-10).

Produced by `experiments/rescore_e9_exact.py`:

    python -m experiments.rescore_e9_exact

The run takes about 25 minutes, nearly all of it the arm-B walk replay.

## What is computed, and from what

The generator draws `x | y ~ N(mu_y, I)` at every site, and only the site's
prevalence varies. For a fitted head, the decision logit within each class is
therefore Gaussian. Write `e_y` for the probability that a class-`y` record
is answered and wrong at a given tau, and `a_y` for the probability that it is
answered. Both are normal tail probabilities. Site sizes are drawn
independently of the site effect, so the site weights cancel from every
estimand below.

- **Arm A, single declared site** (44 certificates over 40 draws). A
  single-site certificate's box is fitted to the declared site's own
  predicted-positive rate, an exact Clopper-Pearson interval. It therefore
  names `R(pi) = [pi e1 + (1-pi) e0] / [pi a1 + (1-pi) a0]` at the site's
  latent prevalence `pi_latent = sigmoid(logit 0.22 + u_t)`.
  - `u_t` is read from a deep copy of the draw's own generator, taken just
    before the target site is drawn. The copy's size draw must equal the
    target's record count.
  - The released `rm_rescored` (out-e9a-rescore/) reweights the fresh pool to
    the declared pool's realised prevalence instead, so it is a plug-in
    proxy. The CSV puts both side by side. Beside them it gives `R` at the
    realised prevalence and at the population target prevalence 0.23126, and
    whether the frozen box covers `rho* = odds(pi_latent)/odds(0.103657)` and
    the population parameter 2.601345.
- **Arm B, the FNR frontier** (600 draws, 2,428 certificates, shipped and
  positives-normalised atoms). On this generator both estimands equal
  `FNR(tau) = e1 / a1 = p_fn / p_ap`.
  - Every issued certificate is scored at its deployed tau.
  - Every draw's curve over `TAU_GRID` is recorded (`arm_b_draws` in the
    JSON).

## Self-check: the script refuses to write unless all of these hold

- **Arm A.** Each of the 40 replayed draws re-runs the pipeline in bbse mode
  on its frozen stream. It must equal `out/E9_bbse_frontier.csv` cell for
  cell at both alphas: 720 cells, covering the certified flag, tau,
  coverage, decline reason, box width, `rm_fresh` and `rm_exceed` as
  printed, and the unrounded `rho_lo`/`rho_hi` to 1e-12 relative (another
  platform's floating-point libraries can move their last bits).
- **Arm A, rescore file.** Each certified row must also reproduce
  `out-e9a-rescore/E9a_rescore.csv`'s `pi_target`, `pi_eval`, `pi_source`,
  `rm_fresh` and `rm_rescored` to six decimals.
- **Arm B.** `run_e9b_positives.run_draw` replays both arms' walks on all 600
  draws. The result must equal `out-e9b-positives/E9b_fnr_positives.csv`
  (52,800 cells) and `out/E9_fnr.csv` cell for cell.
- **Arm B, head refit.** The head is re-fitted here on the same stream. It
  must reproduce every row's fresh-pool values exactly.
- **Closed form against Monte Carlo.** On 10^6 simulated records per class,
  the closed form must agree to 0.003. This is checked for all 44 arm-A
  certificates (largest gap 0.00024) and for the six positives-atom
  certificates at b = 0.4 (largest gap 0.0011).
- **Population parameters.** These must equal `out-bbse-probe/BBSE_probe.json`.

## Results

- **Arm A.**
  - The named estimand is within budget in 44 of 44 certificates, with
    minimum slack 0.020.
  - The frozen box covers `rho*` in 44 of 44.
  - Three rows exceed their budget on the released fresh pool (1,200 sites;
    draw 29 at alpha 0.05 and 0.10, draw 48 at 0.10). Their named estimands
    are 0.0163, 0.0398 and 0.0792, against the released proxies 0.0175,
    0.0408 and 0.0586.
  - At the population prevalence the same three rows are 0.059, 0.111 and
    0.110, so those fresh-pool exceedances are real at the population level.
  - At 1,200 sites and alpha = 0.10 the box covers the population parameter
    in 16 of 20 certificates.
- **Arm B.**
  - The exact FNR at the deployed tau is within budget in all 2,428
    certificates, with minimum slack 0.0076.
  - The six positives-atom certificates at b = 0.4 score 0.370, 0.386,
    0.377, 0.390, 0.356 and 0.392. The one that scored 0.400108 on its fresh
    pool is the 0.390 certificate (600 sites, draw 80).
  - Certify-and-estimand-exceeds at 0.4 therefore occurred in 0 of 600
    draws, under either atom.
  - Exact FNR is below 0.4 at some grid tau in 529 of 600 draws (161, 185
    and 183 at 208, 400 and 600 sites).
  - FNR falls strictly in tau in 599 of 600 draws. The exception is 208/175,
    whose positives' mean logit is -0.004.
  - The mean is 0.4495 at tau = 0.55 and 0.364, 0.356 and 0.360 at
    tau = 0.99.

Files:
- `E9_exact.csv`: one row per certificate, arm A then arm B.
- `E9_exact.json`: summaries, the flagged rows, per-draw arm-B curves, the
  self-check block, and `_run` (UTC, git sha, sha256 of every input).

Pinned by `tests/test_sidecar_e9_exact.py`.
