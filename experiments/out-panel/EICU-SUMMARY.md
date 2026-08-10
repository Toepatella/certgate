# CertGate eICU-CRD v2.0 -- real-data summary

- mode: FULL (per-block stamps are authoritative; preserved sections are marked)
- seed: 20260721
- alpha ladder: (0.05, 0.1), delta: 0.05
- estimand: site-population average, NOT a per-hospital guarantee (audit V1)
- the extract itself is NOT redistributable; every artifact here is aggregate-only (PhysioNet DUA 1.5.0)

## EICU-POOLED
```json
{
  "_run": {
    "mode": "FULL",
    "utc": "2026-08-01T05:40:25+00:00",
    "replicates": 1,
    "arm": "primary",
    "data_sha": "3744bf912e9196b44123a8d13c52faeb1a55e45a705250511c536ce7739ac26d"
  },
  "arm": "primary",
  "replicates": 1,
  "n_records": 164322,
  "n_sites": 207,
  "estimand": "the M=100 influence-weighted answered-set risk averaged over the SITE POPULATION the calibration hospitals were drawn from -- NOT any individual hospital's answered error rate (audit V1). per_site_exceed_frac measures what the certificate deliberately does not bound.",
  "rm_fresh_means": "R_M on the HELD-OUT 24-hospital target pool of this replicate -- hospitals that entered no fitting and no calibration split. It is not a second independent draw from the site population: the replicates share ONE hospital population, which is exactly why F-A is written as a bound-shaped observation.",
  "rungs": {
    "0.05": {
      "certify_rate": 0.0,
      "n_certified": 0,
      "n_replicates": 1,
      "mean_tau": null,
      "mean_coverage": null,
      "mean_rm_fresh": null,
      "rm_exceed_rate": null,
      "hard_violation_rate_diag": null,
      "mean_per_site_exceed_frac": null,
      "deploy_modes": [],
      "mode_non_contribution": {
        "baseline:failsafe|bbse:failsafe": 1
      }
    },
    "0.1": {
      "certify_rate": 1.0,
      "n_certified": 1,
      "n_replicates": 1,
      "mean_tau": 0.85,
      "mean_coverage": 0.8546,
      "mean_rm_fresh": 0.0415,
      "rm_exceed_rate": 0.0,
      "hard_violation_rate_diag": 0.0,
      "mean_per_site_exceed_frac": 0.0417,
      "deploy_modes": [
        "baseline"
      ],
      "mode_non_contribution": {
        "bbse:failsafe": 1
      }
    }
  },
  "failure_criteria": {
    "F-A": {
      "fired": false,
      "n_replicates": 1,
      "n_certified_replicates": 1,
      "n_rm_exceed": 0,
      "rm_exceed_rate": 0.0,
      "target": 0.05,
      "note": "BOUND-SHAPED OBSERVATION, never 'validity confirmed': 1 replicates cannot resolve a delta=0.05 rate, and the replicates share ONE hospital population, so they are not independent draws of the calibration site population."
    },
    "F-B": {
      "fired": false,
      "n_certified_replicates": 1,
      "mean_operative_coverage": 0.8546,
      "min_coverage": 0.2,
      "note": "feasibility failure: no rung certifies on the pooled arm, or the operative rung answers fewer than a fifth of cases -- a certificate at 5% coverage is a decline wearing a hat."
    },
    "F-C": {
      "fired": false,
      "checked": [
        "leak-denylist (assert_no_leak_columns)",
        "feature width == EICU_N_FEATURES",
        "categorical drift gate (build_raw strict_levels=True)",
        "finite x after impute (etl.impute)",
        "assert_site_disjoint(train, aux, cal)",
        "assert_aggregate_only on every write"
      ],
      "note": "protocol failure aborts the run and writes no certificate; reaching this payload means every gate above passed."
    },
    "F-D": {
      "fired": false,
      "legs": {
        "discrimination": {
          "fired": false,
          "n_hits": 0,
          "ceiling": 0.9,
          "max_head_auc_oos": 0.859523,
          "what": "the head's OWN out-of-sample AUC on the site-disjoint calibration split. APACHE-IVa, a purpose-built day-1 score, reaches ~0.87 on this outcome; a 161-column logistic head that beats the ceiling FROM THE SAME INPUTS is a leak before it is a result."
        },
        "missingness_ablation": {
          "fired": false,
          "n_hits": 0,
          "max_drop": 0.05,
          "observed_max_drop": 0.003636,
          "what": "AUC lost by ablating the 49 missingness/presence columns. APACHE day-1 rows do not exist for a stay that ends because the patient died, so whole-row absence is a partial OUTCOME proxy with no column name -- invisible to a name denylist. Measured on the mock: clean -0.016; outcome-correlated absence at p=0.30 +0.082; at p=0.75 +0.248."
        },
        "unfalsifiable_success": {
          "fired": false,
          "n_hits": 0,
          "alpha": 0.05,
          "coverage_alarm": 0.9,
          "rm_alarm": 0.01,
          "what": "the original leg: alpha=0.05 certifying at 208 hospitals with coverage > 0.90 and near-zero fresh-pool R_M contradicts E4's frontier."
        }
      },
      "n_hits": 0,
      "note": "the UNFALSIFIABLE-SUCCESS failure, in THREE legs. The first two depend on NEITHER alpha NOR coverage: the old single-leg form was demonstrated to pass underneath an outcome-correlated-missingness leak that certified alpha=0.10 at coverage 0.86 (2026-07-31 audit, E-10). If ANY leg fires the run is FAILED until the denylist, the first-stay/dedup logic and the APACHE presence channel are re-audited; it is never reported as a headline. Prediction P4 (presence flags in the top-3 abstention drivers) is the LEAK'S SIGNATURE, so P4 is settled as confirmed only when every leg here is clear."
    },
    "F-E": {
      "fired": false,
      "n_sites_primary_cohort": 207,
      "min_sites": 200,
      "note": "REPORTING obligation, not an abort: below this the certificate's site-population-average estimand refers to 'hospitals that survived our filters', not 'US hospitals in eICU', and every guarantee sentence must be re-scoped to the surviving population BY NAME."
    }
  },
  "site_selection": {
    "n_sites_primary_cohort": 207,
    "n_sites_apache_result_linked": 190,
    "n_sites_apache_complete_arm": 190,
    "note": "apache-result-linked vs primary-cohort is the site-selection statistic (threat T-4). The primary arm MEASURES it and never applies it: restricting the cohort would move the site population the estimand refers to."
  },
  "warnings": [
    "[MEASURE] POST-HOC (2026-08-01): the selective reliability panel is a DESCRIPTIVE diagnostic added AFTER the eICU-CRD v2.0 extract was read. It is NOT part of the pre-extract protocol freeze (commit 9f25b491b2554d0a4bd7aaaf44081c185d01715f), it alters no certified quantity, and it settles none of the frozen predictions P1-P7 or failure criteria F-A-F-E. Its bins, seed and bootstrap counts were fixed before it was run on this extract but AFTER the extract had been seen, so they carry NO pre-registration claim. Every figure and number derived from this panel must carry this label."
  ]
}
```

## EICU-PERSITE
```json
{
  "_run": {
    "mode": "FULL",
    "utc": "2026-08-01T05:40:25+00:00",
    "replicates": 1,
    "arm": "primary",
    "data_sha": "3744bf912e9196b44123a8d13c52faeb1a55e45a705250511c536ce7739ac26d"
  },
  "arm": "primary",
  "n_pools": 24,
  "n_pool_too_small": 0,
  "min_answerable": 10,
  "reason_column": "EICU_per_site.csv 'reason' carries, in order of precedence: the STRUCTURAL gate ('pool-too-small' / 'insufficient-clusters'), else the rung's per-mode decline reasons, else -- on a CERTIFIED row -- the modes that did not back the deployed threshold ('bbse:<reason>'). Read it together with 'certified': a certified row carrying a reason is the BBSE non-contribution signal (P3), not a decline.",
  "rungs": {
    "0.05": {
      "n_pools": 24,
      "n_certified": 0,
      "certify_rate": 0.0,
      "mean_coverage": null,
      "answered_err": {
        "n": 0,
        "mean": null,
        "sd": null,
        "p10": null,
        "p50": null,
        "p90": null,
        "min": null,
        "max": null
      },
      "hard_violation_rate_diag": null,
      "note": "per-hospital hard-violation is a DISPERSION diagnostic with NO delta target: the certificate bounds the site-population average, not individual hospitals (audit V1)."
    },
    "0.1": {
      "n_pools": 24,
      "n_certified": 24,
      "certify_rate": 1.0,
      "mean_coverage": 0.8479,
      "answered_err": {
        "n": 24,
        "mean": 0.043608,
        "sd": 0.02114,
        "p10": 0.0209,
        "p50": 0.04255,
        "p90": 0.06466,
        "min": 0.0142,
        "max": 0.1132
      },
      "hard_violation_rate_diag": 0.0,
      "note": "per-hospital hard-violation is a DISPERSION diagnostic with NO delta target: the certificate bounds the site-population average, not individual hospitals (audit V1)."
    }
  }
}
```

## EICU-COMPARATOR
```json
{
  "_run": {
    "mode": "FULL",
    "utc": "2026-08-01T05:40:25+00:00",
    "replicates": 1,
    "arm": "primary",
    "data_sha": "3744bf912e9196b44123a8d13c52faeb1a55e45a705250511c536ce7739ac26d"
  },
  "arm": "primary",
  "rungs": {
    "0.05": {
      "n_certified_replicates": 0,
      "mean_certgate_answered_err": null,
      "mean_certgate_answered_err_on_apache_subset": null,
      "mean_apache_iva_brier": null,
      "mean_apache_iva_auc": null,
      "apache_available_share": null,
      "note": "the APACHE-IVa columns are scored on the answered records that CARRY a comparator value; that coverage is site-correlated, so the subset-matched CertGate error is reported beside them rather than compared across different denominators."
    },
    "0.1": {
      "n_certified_replicates": 1,
      "mean_certgate_answered_err": 0.0419,
      "mean_certgate_answered_err_on_apache_subset": 0.0403,
      "mean_apache_iva_brier": 0.0381,
      "mean_apache_iva_auc": 0.8201,
      "apache_available_share": 0.8025,
      "note": "the APACHE-IVa columns are scored on the answered records that CARRY a comparator value; that coverage is site-correlated, so the subset-matched CertGate error is reported beside them rather than compared across different denominators."
    }
  }
}
```

## EICU-RELIABILITY
```json
{
  "_run": {
    "mode": "FULL",
    "utc": "2026-08-01T05:40:25+00:00",
    "replicates": 1,
    "arm": "primary",
    "data_sha": "3744bf912e9196b44123a8d13c52faeb1a55e45a705250511c536ce7739ac26d"
  },
  "post_hoc": "[MEASURE] POST-HOC (2026-08-01): the selective reliability panel is a DESCRIPTIVE diagnostic added AFTER the eICU-CRD v2.0 extract was read. It is NOT part of the pre-extract protocol freeze (commit 9f25b491b2554d0a4bd7aaaf44081c185d01715f), it alters no certified quantity, and it settles none of the frozen predictions P1-P7 or failure criteria F-A-F-E. Its bins, seed and bootstrap counts were fixed before it was run on this extract but AFTER the extract had been seen, so they carry NO pre-registration claim. Every figure and number derived from this panel must carry this label.",
  "arm": "primary",
  "replicates": 1,
  "n_panels": 1,
  "scope": "pooled target arm only (K = 24 hospitals >= MIN_SITES_FOR_CI = 10); the per-hospital arm is K = 1, where every interval would be floor-suppressed at 24x the cost",
  "settings": {
    "schema_version": "srp/1",
    "seed": 20260731,
    "n_boot": 2000,
    "ci_level": 0.95,
    "bin_edges": [
      0.0,
      0.02,
      0.05,
      0.1,
      0.2,
      0.35,
      0.55,
      1.01
    ],
    "decision_threshold": 0.5,
    "bootstrap_unit": "site"
  },
  "brier_difference_note": "brier.reference.brier_difference is a SINGLE paired statistic from ONE resample stream (reference minus primary on the IDENTICAL availability mask). It must never be reconstructed by differencing brier.primary_answered, whose denominator is the wider answered set (panel notes[4]).",
  "skill_margin_note": "skill_margin = constant-majority baseline error rate MINUS model error rate. At single-digit prevalence a low answered error rate is also what a constant always-negative rule achieves, so the margin -- not the error rate -- is what says whether the gate earned its answered set or merely selected an easy one.",
  "notes": [
    "Estimand: every reported quantity is a record-weighted ratio of sums over the fixed site population; a large site contributes proportionally more than a small one.",
    "Every interval is a MARGINAL two-sided percentile interval from an independent one-stage site resample. There is no joint-coverage claim: do not difference two interval endpoints -- differences that matter are computed as their own statistic inside a shared resample (skill.contrast, brier.reference.brier_difference).",
    "The expected calibration error is a plug-in estimate on fixed a-priori bins. It is positively biased and the bias grows as per-bin counts shrink; a percentile interval does not correct bias, so the interval covers the biased plug-in estimand, not true calibration error.",
    "The answered and declined subsets are selected by the caller's gate, so each is an average over a site population whose composition differs from the full record set. Compare skill.answered against skill.all before reading a low answered error rate as scorer accuracy.",
    "The reference-scorer Brier is computed on the answered records that carry a finite reference probability. Compare it ONLY against brier_primary_matched, which uses the identical denominator, never against brier.primary_answered.",
    "A null statistic means undefined or suppressed, never zero. A null interval carries its reason in the adjacent ci_status field."
  ],
  "replicate_spread_note": "sd / p10 / p50 / p90 below are taken ACROSS REPLICATES, which are re-splits of ONE hospital population on ONE extract and are therefore NOT independent draws. That spread is split-to-split variation, not sampling uncertainty. The cluster-bootstrap `ci` fields are the only intervals here with a coverage claim.",
  "n_sites": {
    "n": 1,
    "mean": 24.0,
    "sd": 0.0,
    "p10": 24.0,
    "p50": 24.0,
    "p90": 24.0,
    "min": 24.0,
    "max": 24.0
  },
  "coverage": {
    "n": 1,
    "mean": 0.854638,
    "sd": 0.0,
    "p10": 0.854638,
    "p50": 0.854638,
    "p90": 0.854638,
    "min": 0.854638,
    "max": 0.854638
  },
  "ece_answered": {
    "n": 1,
    "mean": 0.004757,
    "sd": 0.0,
    "p10": 0.004757,
    "p50": 0.004757,
    "p90": 0.004757,
    "min": 0.004757,
    "max": 0.004757
  },
  "ece_declined": {
    "n": 1,
    "mean": 0.02243,
    "sd": 0.0,
    "p10": 0.02243,
    "p50": 0.02243,
    "p90": 0.02243,
    "min": 0.02243,
    "max": 0.02243
  },
  "calibration_slope_answered": {
    "n": 1,
    "mean": 1.082649,
    "sd": 0.0,
    "p10": 1.082649,
    "p50": 1.082649,
    "p90": 1.082649,
    "min": 1.082649,
    "max": 1.082649
  },
  "calibration_status_answered_counts": {
    "ok": 1
  },
  "fit_statuses": [
    "ok",
    "too-few-records",
    "single-class",
    "degenerate-design",
    "separable",
    "coef-out-of-range",
    "not-converged",
    "singular"
  ],
  "brier_answered": {
    "n": 1,
    "mean": 0.038438,
    "sd": 0.0,
    "p10": 0.038438,
    "p50": 0.038438,
    "p90": 0.038438,
    "min": 0.038438,
    "max": 0.038438
  },
  "brier_reference": {
    "n": 1,
    "mean": 0.038079,
    "sd": 0.0,
    "p10": 0.038079,
    "p50": 0.038079,
    "p90": 0.038079,
    "min": 0.038079,
    "max": 0.038079
  },
  "brier_primary_matched": {
    "n": 1,
    "mean": 0.037104,
    "sd": 0.0,
    "p10": 0.037104,
    "p50": 0.037104,
    "p90": 0.037104,
    "min": 0.037104,
    "max": 0.037104
  },
  "brier_difference": {
    "n": 1,
    "mean": 0.000975,
    "sd": 0.0,
    "p10": 0.000975,
    "p50": 0.000975,
    "p90": 0.000975,
    "min": 0.000975,
    "max": 0.000975
  },
  "brier_available_share": {
    "n": 1,
    "mean": 0.80253,
    "sd": 0.0,
    "p10": 0.80253,
    "p50": 0.80253,
    "p90": 0.80253,
    "min": 0.80253,
    "max": 0.80253
  },
  "brier_reference_ci_replicate0": {
    "brier_reference": {
      "lo": 0.031912,
      "hi": 0.04327
    },
    "brier_primary_matched": {
      "lo": 0.030803,
      "hi": 0.042137
    },
    "brier_difference": {
      "lo": 0.000136,
      "hi": 0.001684
    }
  },
  "skill_margin_answered": {
    "n": 1,
    "mean": 0.003934,
    "sd": 0.0,
    "p10": 0.003934,
    "p50": 0.003934,
    "p90": 0.003934,
    "min": 0.003934,
    "max": 0.003934
  },
  "skill_margin_all": {
    "n": 1,
    "mean": 0.009955,
    "sd": 0.0,
    "p10": 0.009955,
    "p50": 0.009955,
    "p90": 0.009955,
    "min": 0.009955,
    "max": 0.009955
  },
  "skill_contrast_answered_minus_all": {
    "n": 1,
    "mean": -0.006021,
    "sd": 0.0,
    "p10": -0.006021,
    "p50": -0.006021,
    "p90": -0.006021,
    "min": -0.006021,
    "max": -0.006021
  },
  "skill_contrast_answered_minus_declined": {
    "n": 1,
    "mean": -0.041418,
    "sd": 0.0,
    "p10": -0.041418,
    "p50": -0.041418,
    "p90": -0.041418,
    "min": -0.041418,
    "max": -0.041418
  },
  "ci_status_counts": {
    "ok": 22,
    "empty-bin": 5
  },
  "ci_statuses": [
    "ok",
    "empty-bin",
    "too-few-sites",
    "degenerate-resamples",
    "undefined-point",
    "truncated-resamples"
  ],
  "consistency": {
    "max_abs_gap_panel_vs_pooled_answered_err": 1.5e-05,
    "n_compared": 1,
    "note": "panel skill.answered.model_error_rate vs the pooled row's answered_err_rate at the OPERATIVE rung. The panel's DECISION_THRESHOLD = 0.5 is Head.predict's own rule, so the two are the SAME quantity and the gap is pure rounding: the pooled row goes through _rate (4 dp) and the panel through the emit pass (6 dp), so anything up to 5e-05 is expected and is NOT a finding. A gap materially above that means the two are no longer measuring the same thing. REPORTED, never raised -- on real data this is a lead to chase, not a crash mid-run."
  }
}
```
