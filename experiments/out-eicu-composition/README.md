# out-eicu-composition/ -- POST-HOC corrected eICU composition and exact S_aux margin

**Status: POST-HOC (2026-10-29).** Nothing in this directory is a certified quantity. No certificate, threshold, guarantee string or registered prediction descends from it, and the released eICU artifacts (`experiments/out/`) are unchanged.

Produced by `experiments/eicu_composition_margin.py` on the restricted eICU-CRD v2.0 extract (DUA holder only):

    python -m experiments.eicu_composition_margin --data <DATA_DIR> --replicates 20

It replays the released primary arm, re-split by re-split, exactly as `experiments/run_eicu.py` builds it (one `_build_and_gate` build; `site_split`, `impute`, `_build_cohorts`, `fit_head`, `run_certgate` on the 24-hospital pooled pool), and refuses to write unless the replay reproduces the release: the extract's `data_sha`, replicate 0's tau*, tau_idx, coverage, n_cal, BBSE rho_point and pi_s, feasibility and composition against `EICU_certificate.json`, and every replicate's BBSE, composition and pooled cells against `EICU_diagnostics.json` and `EICU_pooled.csv`, all by exact equality.

What is computed:

- **Corrected BBSE-implied answered positive fraction** (audit BBSE-1, contract C1). The released value re-weighted the head's odds by `rho_point = odds(pi_t)/odds(pi_s)` alone, dividing out the S_aux prior `pi_s`; the head's odds carry the S_train prior, so the corrected multiplier is `rho_point * odds(clip pi_s) / odds(pi_train)` with `pi_train = train.y.mean()`. Both are reported per replicate (`EICU_composition_corrected.csv`), beside the oracle fraction.
- **Exact S_aux atom-unit margin** (audit CORE-3): `max_tau (alpha - mean_c Z_c(tau))`, the quantity `walk_order` ranks by, beside the released record-pooled feasibility proxy (`pipeline._feasibility`) and the information floor `margin_floor(n_cal_carrying, DELTA, alpha)`, with both margin/floor ratios, for alpha = 0.05 and 0.10 (`EICU_margin_exact.csv`). The floor is a first-order heuristic, not an impossibility bound.

Files: `EICU_composition_margin.json` (per-replicate records, summaries across re-splits, the self-check, `_run` with UTC, git sha and the sha256 of every released file read, and the extract's `data_sha` and per-table sha256), `EICU_composition_corrected.csv`, `EICU_margin_exact.csv`. Aggregate quantities only: every write passed `run_eicu.assert_aggregate_only`.

The re-splits are re-splits of one hospital population on one extract, so the spread across them is split-to-split variation, not sampling uncertainty.

Headline: replicate 0 BBSE-implied answered positive fraction 0.0307 released -> 0.0323 corrected (oracle 0.0458; pi_train 0.0862, pi_s 0.0912); alpha=0.05: exact atom margin 0.0171 (x0.44 floor 0.0385) vs proxy 0.0166 (x0.43); alpha=0.1: exact atom margin 0.0458 (x1.26 floor 0.0364) vs proxy 0.0462 (x1.27)
