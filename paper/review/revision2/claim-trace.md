# Revision-2 claim trace — every NEW numeric claim in `paper/draft.md` → artifact

Convention: display rounding of a higher-precision artifact value counts as traced
(the claim-audit rule); "summary" = the experiment's block in
`experiments/out/summary.md`; "subgroups summary" = the `EICU-SUBGROUPS` block in
`experiments/out-subgroups/EICU-SUMMARY.md`. ANALYTIC = mathematical statement,
no artifact. Artifacts land in `experiments/out/` via the `--only E8,E9` run
(deterministically identical to the gated scratch run whose values are quoted).

## §4.11 (comparator suite) + Figure 4 caption + abstract/contribution clauses

| claim | value | artifact |
|---|---|---|
| WSR certifies α=0.10 from 150 sites | certify_by_nsites [0,0,1,1,1,1] | summary E8 `comparators.wsr.0.1.certify_by_nsites` |
| WSR certifies α=0.05 from 300 (0.28) to 400 (1.0) | [0,0,0,0,0.28,1.0] | `comparators.wsr.0.05.certify_by_nsites` |
| Hoeffding certifies nothing | all-zero vectors | `comparators.hoeffding.*.certify_by_nsites` |
| MP-EB only α=0.10 at 400 | [0,0,0,0,0,1] | `comparators.mpeb.0.1.certify_by_nsites` |
| t / bootstrap grant every rung at every count incl. α=0.05 at 60 | all-ones vectors | `comparators.t/site_boot.*.certify_by_nsites` |
| t exceedance 0.0508; bootstrap 0.0492; WSR 0.0 | exact | `comparators.{t,site_boot,wsr}.0.05.rm_exceed_rate` |

## §4.12 (stress + heads) + Figure 4 caption

| claim | value | artifact |
|---|---|---|
| mean fresh-pool risk ≈ half the budget | 0.0567 vs 0.10 (pre-existing) | summary E1 |
| floor makes risk within ~0.03 of α uncertifiable | ln(1/δ)(1−α)/n ≈ 0.033 at 83 clusters | ANALYTIC (§3.4 formula) |
| risk at most permissive threshold 0.066 → 0.091 | 0.0655 → 0.0913 | summary E8 `noise.{0.01,0.04}.mean_risk_at_lowest_tau` |
| coverage 0.96 → 0.76 | 0.9629 → 0.7573 | `noise.{0.01,0.04}.0.1.mean_coverage` |
| certify 1.0 / 0.63 / 0.02 at η=0.01–0.03 / 0.035 / 0.04 | 1.0, 1.0, 0.9967, 0.63, 0.0233 | `noise.*.0.1.certify_rate` |
| exceedance zero at every η | 0.0 all | `noise.*.0.1.rm_exceed_rate` |
| heads: all certify, zero exceed | 1.0 / 0.0 | summary E8 `heads.*.0.1` |
| denied head coverage 0.88 vs 0.98 | 0.8799 vs 0.9839 | `heads.{degraded,linear}.0.1.mean_coverage` |
| monotone-miscalibration no-op | — | ANALYTIC (score = max(p̂,1−p̂)) |

## §4.13 (power frontiers) + Figure 5 caption + §4.3/§6.1 clauses

| claim | value | artifact |
|---|---|---|
| k40: 0.38 @900, 0.94 @1200; 0 @208/600 | exact | summary E9 `bbse_frontier.{n}|k40-boot.certify_rate` |
| ρ-box narrows 3.47 → 2.22 | 3.4687 → 2.2184 | `bbse_frontier.{208,1200}|k40-boot.median_box_width` |
| k40 zero exceedances | 0.0 where defined | `bbse_frontier.*|k40-boot.rm_exceed_rate` |
| single-site plateaus near 0.40; exceeds 0.10 @1200 | 0.4; 0.1 | `bbse_frontier.1200|single-site-cp.{certify_rate,rm_exceed_rate}` |
| 2 of 20; exact 95% CI 0.012–0.317 | Clopper–Pearson beta.ppf: [0.0123, 0.3170] | E9_bbse_frontier.csv (2 exceed rows of 20 certs); CI verified 2026-08-20 |
| E2 certify ≤5% under shift, 9% at null | 0.09/0.05/0.0/0.01/0.0 | summary E2 `shift_sweep_alpha0.10.*.bbse.certify_rate` (pre-existing artifact) |
| FNR truth ≈0.45 | 0.4499 | summary E9 `true_fnr_at_lowest_tau_mean` |
| FNR 0.4 never certifies; 0.55 @400 (0.285) and @600 (0.995); 0.6 from 208; 0.5 only 0.005 @600 | exact | `fnr_frontier.{budget}.{n}.certify_rate` |
| all issued FNR certificates held | fnr_exceed_rate 0.0 where defined | `fnr_frontier.*.*.fnr_exceed_rate` |
| eICU derived FNR 0.80–0.90 | 0.8044–0.904 | Table S7 ← panel_confusion_tables ← EICU_reliability_panel.json |
| BBSE positive certification near 900–1,200 sites (§6.1) | see k40 rows | same as above |
| no FNR budget below ~0.55 issuable at realistic counts (§6.1) | see fnr rows | same |

## §4.10 additions + Tables S7/S8

| claim | value | artifact |
|---|---|---|
| answered sens median 0.126 | 0.1255 | Table S7 ← `panel_confusion_tables` summary.answered.sensitivity.median |
| Table S7 all 10 rows | literal | `panel_confusion_tables` output (self-checked vs published-split TP57/FP6/FN537/TN12364) |
| age coverage 0.96→0.82, error 0.019→0.075 | 0.9631→0.8208; 0.0193→0.075 | subgroups summary `dims.age_band.*` |
| Table S8 all 10 rows | literal | subgroups summary `dims.*` / `experiments/out-subgroups/EICU_subgroups.csv` |
| 330 of 900 cells suppressed | exact | subgroups summary `n_cells_suppressed_whole` + CSV status counts |
| every unsuppressed cell under α | max answered_err_mean 0.084 < 0.10 | subgroups summary (verified over all dims) |

## Token appendix — Table S7/S8 literal cells (enumerated so the guard can verify presence)

Table S7 cells (← `python -m experiments.panel_confusion_tables` summary min/median/max,
derived from released `EICU_reliability_panel.json`; counts from the replicate-0 self-check):
0.096 0.1255 0.1956 0.9951 0.998 0.9995 0.6446 0.7667 0.9048 0.9447 0.9521 0.9661
0.8044 0.8745 0.904 0.3108 0.3689 0.446 0.7547 0.842 0.9002 0.5365 0.5882 0.6621
0.6391 0.6727 0.7857 0.554 0.6311 0.6892 57 6 537 12364

Table S8 cells (← `experiments/out-subgroups/EICU-SUMMARY.md` EICU-SUBGROUPS block
`dims.*.{n_mean, coverage_mean, coverage_min, answered_err_mean}`; age-band bounds are the
pinned `EICU_SUBGROUP_AGE_BANDS` constants):
2840 6555 4375 5498 8916 10345 656 1691 1624 246
0.9631 0.9203 0.0193 0.9192 0.8608 0.0391 0.8875 0.8063 0.0497 0.8208 0.6885 0.075
0.89 0.8034 0.0489 0.8908 0.8121 0.0468 0.9733 0.9435 0.02 0.9642 0.895 0.0261
0.7962 0.6826 0.0747 0.7396 0.6135 0.084
age-band bounds/labels: 18 44 45 64 65 74 75 (EICU_SUBGROUP_AGE_BANDS, pinned)
floor and suppression: 100 330 900 (subgroups summary + CSV status counts)
