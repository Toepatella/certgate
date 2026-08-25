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
    "utc": "2026-08-21T21:30:31+00:00",
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
    "utc": "2026-08-21T21:30:31+00:00",
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
    "utc": "2026-08-21T21:30:31+00:00",
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
    "utc": "2026-08-21T21:30:31+00:00",
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

## EICU-SUBGROUPS
```json
{
  "_run": {
    "mode": "FULL",
    "utc": "2026-08-21T21:30:31+00:00",
    "replicates": 1,
    "arm": "primary",
    "data_sha": "3744bf912e9196b44123a8d13c52faeb1a55e45a705250511c536ce7739ac26d"
  },
  "post_hoc": "[MEASURE] POST-HOC SUBGROUP DESCRIPTIVES (2026-08-20): computed after the extract was read; certifies nothing, settles no registered prediction or failure criterion, and no certified quantity descends from it. Rates in cells below the frozen EICU_MIN_OUTCOME_STRATUM record floor are suppressed as null, never 0.0.",
  "arm": "primary",
  "floor": 100,
  "dims": {
    "age_band": {
      "18-44": {
        "n_mean": 2136.0,
        "n_replicates": 1,
        "coverage_mean": 0.9625,
        "coverage_min": 0.9625,
        "answered_err_mean": 0.0204,
        "answered_pos_mean": 0.0209,
        "n_answered_rates_suppressed": 0
      },
      "45-64": {
        "n_mean": 5242.0,
        "n_replicates": 1,
        "coverage_mean": 0.9008,
        "coverage_min": 0.9008,
        "answered_err_mean": 0.0358,
        "answered_pos_mean": 0.0385,
        "n_answered_rates_suppressed": 0
      },
      "65-74": {
        "n_mean": 3457.0,
        "n_replicates": 1,
        "coverage_mean": 0.8542,
        "coverage_min": 0.8542,
        "answered_err_mean": 0.043,
        "answered_pos_mean": 0.0474,
        "n_answered_rates_suppressed": 0
      },
      "75+": {
        "n_mean": 4334.0,
        "n_replicates": 1,
        "coverage_mean": 0.746,
        "coverage_min": 0.746,
        "answered_err_mean": 0.0634,
        "answered_pos_mean": 0.0708,
        "n_answered_rates_suppressed": 0
      }
    },
    "gender": {
      "EMPTY": {
        "n_mean": 2.0,
        "n_replicates": 1,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "Female": {
        "n_mean": 6930.0,
        "n_replicates": 1,
        "coverage_mean": 0.8465,
        "coverage_min": 0.8465,
        "answered_err_mean": 0.0476,
        "answered_pos_mean": 0.0518,
        "n_answered_rates_suppressed": 0
      },
      "Male": {
        "n_mean": 8234.0,
        "n_replicates": 1,
        "coverage_mean": 0.8617,
        "coverage_min": 0.8617,
        "answered_err_mean": 0.0372,
        "answered_pos_mean": 0.0407,
        "n_answered_rates_suppressed": 0
      },
      "OTHER": {
        "n_mean": 0.0,
        "n_replicates": 1,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "Other": {
        "n_mean": 0.0,
        "n_replicates": 1,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "Unknown": {
        "n_mean": 3.0,
        "n_replicates": 1,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      }
    },
    "ethnicity": {
      "African American": {
        "n_mean": 1955.0,
        "n_replicates": 1,
        "coverage_mean": 0.8665,
        "coverage_min": 0.8665,
        "answered_err_mean": 0.0549,
        "answered_pos_mean": 0.059,
        "n_answered_rates_suppressed": 0
      },
      "Asian": {
        "n_mean": 260.0,
        "n_replicates": 1,
        "coverage_mean": 0.8154,
        "coverage_min": 0.8154,
        "answered_err_mean": 0.0425,
        "answered_pos_mean": 0.0425,
        "n_answered_rates_suppressed": 0
      },
      "Caucasian": {
        "n_mean": 11003.0,
        "n_replicates": 1,
        "coverage_mean": 0.8568,
        "coverage_min": 0.8568,
        "answered_err_mean": 0.0418,
        "answered_pos_mean": 0.0457,
        "n_answered_rates_suppressed": 0
      },
      "EMPTY": {
        "n_mean": 86.0,
        "n_replicates": 1,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "Hispanic": {
        "n_mean": 1268.0,
        "n_replicates": 1,
        "coverage_mean": 0.8241,
        "coverage_min": 0.8241,
        "answered_err_mean": 0.0306,
        "answered_pos_mean": 0.0354,
        "n_answered_rates_suppressed": 0
      },
      "Native American": {
        "n_mean": 17.0,
        "n_replicates": 1,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "OTHER": {
        "n_mean": 0.0,
        "n_replicates": 1,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "Other/Unknown": {
        "n_mean": 580.0,
        "n_replicates": 1,
        "coverage_mean": 0.8569,
        "coverage_min": 0.8569,
        "answered_err_mean": 0.0282,
        "answered_pos_mean": 0.0302,
        "n_answered_rates_suppressed": 0
      }
    },
    "hospitaladmitsource": {
      "Acute Care/Floor": {
        "n_mean": 329.0,
        "n_replicates": 1,
        "coverage_mean": 0.8298,
        "coverage_min": 0.8298,
        "answered_err_mean": 0.0916,
        "answered_pos_mean": 0.0916,
        "n_answered_rates_suppressed": 0
      },
      "Chest Pain Center": {
        "n_mean": 5.0,
        "n_replicates": 1,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "Direct Admit": {
        "n_mean": 986.0,
        "n_replicates": 1,
        "coverage_mean": 0.8773,
        "coverage_min": 0.8773,
        "answered_err_mean": 0.0705,
        "answered_pos_mean": 0.074,
        "n_answered_rates_suppressed": 0
      },
      "EMPTY": {
        "n_mean": 2747.0,
        "n_replicates": 1,
        "coverage_mean": 0.8682,
        "coverage_min": 0.8682,
        "answered_err_mean": 0.0323,
        "answered_pos_mean": 0.0348,
        "n_answered_rates_suppressed": 0
      },
      "Emergency Department": {
        "n_mean": 7171.0,
        "n_replicates": 1,
        "coverage_mean": 0.8572,
        "coverage_min": 0.8572,
        "answered_err_mean": 0.0413,
        "answered_pos_mean": 0.0456,
        "n_answered_rates_suppressed": 0
      },
      "Floor": {
        "n_mean": 1732.0,
        "n_replicates": 1,
        "coverage_mean": 0.7436,
        "coverage_min": 0.7436,
        "answered_err_mean": 0.0644,
        "answered_pos_mean": 0.0738,
        "n_answered_rates_suppressed": 0
      },
      "ICU": {
        "n_mean": 3.0,
        "n_replicates": 1,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "ICU to SDU": {
        "n_mean": 8.0,
        "n_replicates": 1,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "OTHER": {
        "n_mean": 0.0,
        "n_replicates": 1,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "Observation": {
        "n_mean": 1.0,
        "n_replicates": 1,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "Operating Room": {
        "n_mean": 1502.0,
        "n_replicates": 1,
        "coverage_mean": 0.9487,
        "coverage_min": 0.9487,
        "answered_err_mean": 0.0154,
        "answered_pos_mean": 0.0154,
        "n_answered_rates_suppressed": 0
      },
      "Other": {
        "n_mean": 1.0,
        "n_replicates": 1,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "Other Hospital": {
        "n_mean": 160.0,
        "n_replicates": 1,
        "coverage_mean": 0.7562,
        "coverage_min": 0.7562,
        "answered_err_mean": 0.0661,
        "answered_pos_mean": 0.0661,
        "n_answered_rates_suppressed": 0
      },
      "Other ICU": {
        "n_mean": 70.0,
        "n_replicates": 1,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "PACU": {
        "n_mean": 26.0,
        "n_replicates": 1,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "Recovery Room": {
        "n_mean": 283.0,
        "n_replicates": 1,
        "coverage_mean": 0.9435,
        "coverage_min": 0.9435,
        "answered_err_mean": 0.0075,
        "answered_pos_mean": 0.0075,
        "n_answered_rates_suppressed": 0
      },
      "Step-Down Unit (SDU)": {
        "n_mean": 145.0,
        "n_replicates": 1,
        "coverage_mean": 0.6414,
        "coverage_min": 0.6414,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 1
      }
    },
    "unittype": {
      "CCU-CTICU": {
        "n_mean": 0.0,
        "n_replicates": 1,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "CSICU": {
        "n_mean": 0.0,
        "n_replicates": 1,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "CTICU": {
        "n_mean": 1566.0,
        "n_replicates": 1,
        "coverage_mean": 0.8959,
        "coverage_min": 0.8959,
        "answered_err_mean": 0.0364,
        "answered_pos_mean": 0.0392,
        "n_answered_rates_suppressed": 0
      },
      "Cardiac ICU": {
        "n_mean": 1879.0,
        "n_replicates": 1,
        "coverage_mean": 0.8558,
        "coverage_min": 0.8558,
        "answered_err_mean": 0.0429,
        "answered_pos_mean": 0.0491,
        "n_answered_rates_suppressed": 0
      },
      "EMPTY": {
        "n_mean": 0.0,
        "n_replicates": 1,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "MICU": {
        "n_mean": 0.0,
        "n_replicates": 1,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "Med-Surg ICU": {
        "n_mean": 11572.0,
        "n_replicates": 1,
        "coverage_mean": 0.8493,
        "coverage_min": 0.8493,
        "answered_err_mean": 0.0422,
        "answered_pos_mean": 0.0458,
        "n_answered_rates_suppressed": 0
      },
      "Neuro ICU": {
        "n_mean": 0.0,
        "n_replicates": 1,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "OTHER": {
        "n_mean": 0.0,
        "n_replicates": 1,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "SICU": {
        "n_mean": 152.0,
        "n_replicates": 1,
        "coverage_mean": 0.8224,
        "coverage_min": 0.8224,
        "answered_err_mean": 0.064,
        "answered_pos_mean": 0.08,
        "n_answered_rates_suppressed": 0
      }
    }
  },
  "n_cells_suppressed_whole": 21
}
```

## EICU-FAITHFULNESS
```json
{
  "_run": {
    "mode": "FULL",
    "utc": "2026-08-21T21:30:31+00:00",
    "replicates": 1,
    "arm": "primary",
    "data_sha": "3744bf912e9196b44123a8d13c52faeb1a55e45a705250511c536ce7739ac26d"
  },
  "post_hoc": "[MEASURE] POST-HOC ATTRIBUTION VALUE-FUNCTION CONTRAST (2026-08-21): computed after the extract was read; certifies nothing, settles no registered prediction or failure criterion, and no certified quantity descends from it. Interventional (deployed) vs Gaussian-conditional Shapley values on the top-k abstention drivers; the Gaussian conditional is an APPROXIMATION for binary and __missing indicator features.",
  "arm": "primary",
  "k": 10,
  "replicates": [
    {
      "status": "ok",
      "replicate": 0,
      "k": 10,
      "n_coalitions": 1024,
      "n_answered": 12964,
      "n_declined": 2205,
      "top_driver_int": "aps_motor",
      "top_driver_cond": "aps_motor",
      "spearman_abs_gap_int_vs_cond": 0.575758,
      "max_abs_offdiag_corr_train": 0.852932,
      "max_abs_offdiag_corr_pair": [
        "apv_oobintubday1",
        "apv_oobventday1"
      ],
      "corr_train": [
        [
          1.0,
          -0.0937,
          0.0649,
          -0.355,
          0.0388,
          0.7988,
          -0.4787,
          0.175,
          -0.4146,
          -0.0562
        ],
        [
          -0.0937,
          1.0,
          -0.2319,
          0.1948,
          0.0874,
          -0.0769,
          0.1502,
          -0.057,
          0.1068,
          0.413
        ],
        [
          0.0649,
          -0.2319,
          1.0,
          -0.0137,
          -0.3608,
          0.0423,
          -0.0178,
          0.1161,
          -0.0238,
          0.039
        ],
        [
          -0.355,
          0.1948,
          -0.0137,
          1.0,
          -0.0873,
          -0.3916,
          0.717,
          -0.1347,
          0.6116,
          0.1678
        ],
        [
          0.0388,
          0.0874,
          -0.3608,
          -0.0873,
          1.0,
          0.0304,
          -0.0598,
          0.0139,
          0.0346,
          -0.1485
        ],
        [
          0.7988,
          -0.0769,
          0.0423,
          -0.3916,
          0.0304,
          1.0,
          -0.5167,
          0.1428,
          -0.4541,
          -0.0471
        ],
        [
          -0.4787,
          0.1502,
          -0.0178,
          0.717,
          -0.0598,
          -0.5167,
          1.0,
          -0.1445,
          0.8529,
          0.124
        ],
        [
          0.175,
          -0.057,
          0.1161,
          -0.1347,
          0.0139,
          0.1428,
          -0.1445,
          1.0,
          -0.1321,
          -0.0507
        ],
        [
          -0.4146,
          0.1068,
          -0.0238,
          0.6116,
          0.0346,
          -0.4541,
          0.8529,
          -0.1321,
          1.0,
          0.0697
        ],
        [
          -0.0562,
          0.413,
          0.039,
          0.1678,
          -0.1485,
          -0.0471,
          0.124,
          -0.0507,
          0.0697,
          1.0
        ]
      ],
      "max_abs_rel_gap_change": 0.912412
    }
  ],
  "n_replicates_ok": 1,
  "features": {
    "aps_eyes": {
      "n_replicates": 1,
      "coef_mean": -0.115928,
      "gap_int_mean": -0.07382,
      "gap_cond_mean": -0.141175,
      "rank_int_median": 6.0,
      "rank_cond_median": 2.0,
      "n_top1_int": 0,
      "n_top1_cond": 0
    },
    "aps_fio2": {
      "n_replicates": 1,
      "coef_mean": 0.195262,
      "gap_int_mean": -0.152379,
      "gap_cond_mean": -0.128726,
      "rank_int_median": 2.0,
      "rank_cond_median": 3.0,
      "n_top1_int": 0,
      "n_top1_cond": 0
    },
    "aps_intubated": {
      "n_replicates": 1,
      "coef_mean": -0.195205,
      "gap_int_mean": -0.109131,
      "gap_cond_mean": -0.02146,
      "rank_int_median": 4.0,
      "rank_cond_median": 10.0,
      "n_top1_int": 0,
      "n_top1_cond": 0
    },
    "aps_motor": {
      "n_replicates": 1,
      "coef_mean": -0.320479,
      "gap_int_mean": -0.245857,
      "gap_cond_mean": -0.246065,
      "rank_int_median": 1.0,
      "rank_cond_median": 1.0,
      "n_top1_int": 1,
      "n_top1_cond": 1
    },
    "aps_pao2": {
      "n_replicates": 1,
      "coef_mean": -0.081368,
      "gap_int_mean": -0.058155,
      "gap_cond_mean": -0.025103,
      "rank_int_median": 10.0,
      "rank_cond_median": 9.0,
      "n_top1_int": 0,
      "n_top1_cond": 0
    },
    "aps_pco2": {
      "n_replicates": 1,
      "coef_mean": -0.126074,
      "gap_int_mean": -0.077861,
      "gap_cond_mean": -0.047218,
      "rank_int_median": 5.0,
      "rank_cond_median": 7.0,
      "n_top1_int": 0,
      "n_top1_cond": 0
    },
    "aps_ph": {
      "n_replicates": 1,
      "coef_mean": -0.14355,
      "gap_int_mean": -0.116441,
      "gap_cond_mean": -0.126084,
      "rank_int_median": 3.0,
      "rank_cond_median": 4.0,
      "n_top1_int": 0,
      "n_top1_cond": 0
    },
    "aps_temperature": {
      "n_replicates": 1,
      "coef_mean": -0.177154,
      "gap_int_mean": -0.063872,
      "gap_cond_mean": -0.080629,
      "rank_int_median": 8.0,
      "rank_cond_median": 5.0,
      "n_top1_int": 0,
      "n_top1_cond": 0
    },
    "apv_oobintubday1": {
      "n_replicates": 1,
      "coef_mean": 0.141012,
      "gap_int_mean": -0.070734,
      "gap_cond_mean": -0.072234,
      "rank_int_median": 7.0,
      "rank_cond_median": 6.0,
      "n_top1_int": 0,
      "n_top1_cond": 0
    },
    "apv_oobventday1": {
      "n_replicates": 1,
      "coef_mean": 0.14746,
      "gap_int_mean": -0.060021,
      "gap_cond_mean": -0.046009,
      "rank_int_median": 9.0,
      "rank_cond_median": 8.0,
      "n_top1_int": 0,
      "n_top1_cond": 0
    }
  },
  "max_abs_diff_vs_abstention_ranking": 0.0,
  "n_cross_checked": 10
}
```
