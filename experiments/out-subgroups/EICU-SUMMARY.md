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
    "utc": "2026-08-20T16:20:51+00:00",
    "replicates": 20,
    "arm": "primary",
    "data_sha": "3744bf912e9196b44123a8d13c52faeb1a55e45a705250511c536ce7739ac26d"
  },
  "arm": "primary",
  "replicates": 20,
  "n_records": 164322,
  "n_sites": 207,
  "estimand": "the M=100 influence-weighted answered-set risk averaged over the SITE POPULATION the calibration hospitals were drawn from -- NOT any individual hospital's answered error rate (audit V1). per_site_exceed_frac measures what the certificate deliberately does not bound.",
  "rm_fresh_means": "R_M on the HELD-OUT 24-hospital target pool of this replicate -- hospitals that entered no fitting and no calibration split. It is not a second independent draw from the site population: the replicates share ONE hospital population, which is exactly why F-A is written as a bound-shaped observation.",
  "rungs": {
    "0.05": {
      "certify_rate": 0.0,
      "n_certified": 0,
      "n_replicates": 20,
      "mean_tau": null,
      "mean_coverage": null,
      "mean_rm_fresh": null,
      "rm_exceed_rate": null,
      "hard_violation_rate_diag": null,
      "mean_per_site_exceed_frac": null,
      "deploy_modes": [],
      "mode_non_contribution": {
        "baseline:failsafe|bbse:failsafe": 20
      }
    },
    "0.1": {
      "certify_rate": 1.0,
      "n_certified": 20,
      "n_replicates": 20,
      "mean_tau": 0.793,
      "mean_coverage": 0.8904,
      "mean_rm_fresh": 0.0478,
      "rm_exceed_rate": 0.0,
      "hard_violation_rate_diag": 0.0,
      "mean_per_site_exceed_frac": 0.0271,
      "deploy_modes": [
        "baseline"
      ],
      "mode_non_contribution": {
        "bbse:failsafe": 20
      }
    }
  },
  "failure_criteria": {
    "F-A": {
      "fired": false,
      "n_replicates": 20,
      "n_certified_replicates": 20,
      "n_rm_exceed": 0,
      "rm_exceed_rate": 0.0,
      "target": 0.05,
      "note": "BOUND-SHAPED OBSERVATION, never 'validity confirmed': 20 replicates cannot resolve a delta=0.05 rate, and the replicates share ONE hospital population, so they are not independent draws of the calibration site population."
    },
    "F-B": {
      "fired": false,
      "n_certified_replicates": 20,
      "mean_operative_coverage": 0.8904,
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
          "max_head_auc_oos": 0.867222,
          "what": "the head's OWN out-of-sample AUC on the site-disjoint calibration split. APACHE-IVa, a purpose-built day-1 score, reaches ~0.87 on this outcome; a 161-column logistic head that beats the ceiling FROM THE SAME INPUTS is a leak before it is a result."
        },
        "missingness_ablation": {
          "fired": false,
          "n_hits": 0,
          "max_drop": 0.05,
          "observed_max_drop": 0.006348,
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
    "utc": "2026-08-20T16:20:51+00:00",
    "replicates": 20,
    "arm": "primary",
    "data_sha": "3744bf912e9196b44123a8d13c52faeb1a55e45a705250511c536ce7739ac26d"
  },
  "arm": "primary",
  "n_pools": 480,
  "n_pool_too_small": 3,
  "min_answerable": 10,
  "reason_column": "EICU_per_site.csv 'reason' carries, in order of precedence: the STRUCTURAL gate ('pool-too-small' / 'insufficient-clusters'), else the rung's per-mode decline reasons, else -- on a CERTIFIED row -- the modes that did not back the deployed threshold ('bbse:<reason>'). Read it together with 'certified': a certified row carrying a reason is the BBSE non-contribution signal (P3), not a decline.",
  "rungs": {
    "0.05": {
      "n_pools": 480,
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
      "n_pools": 480,
      "n_certified": 477,
      "certify_rate": 0.9938,
      "mean_coverage": 0.8847,
      "answered_err": {
        "n": 477,
        "mean": 0.048226,
        "sd": 0.030693,
        "p10": 0.01882,
        "p50": 0.0448,
        "p90": 0.07762,
        "min": 0.0,
        "max": 0.2857
      },
      "hard_violation_rate_diag": 0.0147,
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
    "utc": "2026-08-20T16:20:51+00:00",
    "replicates": 20,
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
      "n_certified_replicates": 20,
      "mean_certgate_answered_err": 0.0478,
      "mean_certgate_answered_err_on_apache_subset": 0.0471,
      "mean_apache_iva_brier": 0.0437,
      "mean_apache_iva_auc": 0.8203,
      "apache_available_share": 0.8219,
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
    "utc": "2026-08-20T16:20:51+00:00",
    "replicates": 20,
    "arm": "primary",
    "data_sha": "3744bf912e9196b44123a8d13c52faeb1a55e45a705250511c536ce7739ac26d"
  },
  "post_hoc": "[MEASURE] POST-HOC (2026-08-01): the selective reliability panel is a DESCRIPTIVE diagnostic added AFTER the eICU-CRD v2.0 extract was read. It is NOT part of the pre-extract protocol freeze (commit 9f25b491b2554d0a4bd7aaaf44081c185d01715f), it alters no certified quantity, and it settles none of the frozen predictions P1-P7 or failure criteria F-A-F-E. Its bins, seed and bootstrap counts were fixed before it was run on this extract but AFTER the extract had been seen, so they carry NO pre-registration claim. Every figure and number derived from this panel must carry this label.",
  "arm": "primary",
  "replicates": 20,
  "n_panels": 20,
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
    "n": 20,
    "mean": 24.0,
    "sd": 0.0,
    "p10": 24.0,
    "p50": 24.0,
    "p90": 24.0,
    "min": 24.0,
    "max": 24.0
  },
  "coverage": {
    "n": 20,
    "mean": 0.89039,
    "sd": 0.030471,
    "p10": 0.855777,
    "p50": 0.901521,
    "p90": 0.920053,
    "min": 0.807981,
    "max": 0.925705
  },
  "ece_answered": {
    "n": 20,
    "mean": 0.00652,
    "sd": 0.002153,
    "p10": 0.003861,
    "p50": 0.006322,
    "p90": 0.010002,
    "min": 0.003216,
    "max": 0.010979
  },
  "ece_declined": {
    "n": 20,
    "mean": 0.030481,
    "sd": 0.012324,
    "p10": 0.014531,
    "p50": 0.031357,
    "p90": 0.046113,
    "min": 0.010239,
    "max": 0.052507
  },
  "calibration_slope_answered": {
    "n": 20,
    "mean": 0.979464,
    "sd": 0.062779,
    "p10": 0.902942,
    "p50": 0.96504,
    "p90": 1.071322,
    "min": 0.866421,
    "max": 1.09779
  },
  "calibration_status_answered_counts": {
    "ok": 20
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
    "n": 20,
    "mean": 0.042816,
    "sd": 0.005188,
    "p10": 0.034131,
    "p50": 0.044706,
    "p90": 0.048759,
    "min": 0.032759,
    "max": 0.050302
  },
  "brier_reference": {
    "n": 20,
    "mean": 0.043715,
    "sd": 0.005324,
    "p10": 0.036383,
    "p50": 0.044802,
    "p90": 0.04952,
    "min": 0.031744,
    "max": 0.050457
  },
  "brier_primary_matched": {
    "n": 20,
    "mean": 0.042196,
    "sd": 0.005271,
    "p10": 0.034055,
    "p50": 0.043587,
    "p90": 0.047885,
    "min": 0.031152,
    "max": 0.049588
  },
  "brier_difference": {
    "n": 20,
    "mean": 0.001519,
    "sd": 0.000913,
    "p10": 0.00057,
    "p50": 0.001507,
    "p90": 0.002468,
    "min": -0.000795,
    "max": 0.003387
  },
  "brier_available_share": {
    "n": 20,
    "mean": 0.821403,
    "sd": 0.043078,
    "p10": 0.77412,
    "p50": 0.828756,
    "p90": 0.871021,
    "min": 0.725911,
    "max": 0.881007
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
    "n": 20,
    "mean": 0.004557,
    "sd": 0.001345,
    "p10": 0.003545,
    "p50": 0.00422,
    "p90": 0.005848,
    "min": 0.00262,
    "max": 0.008366
  },
  "skill_margin_all": {
    "n": 20,
    "mean": 0.008428,
    "sd": 0.002536,
    "p10": 0.005875,
    "p50": 0.007889,
    "p90": 0.010601,
    "min": 0.004971,
    "max": 0.015655
  },
  "skill_contrast_answered_minus_all": {
    "n": 20,
    "mean": -0.003871,
    "sd": 0.001838,
    "p10": -0.006134,
    "p50": -0.003844,
    "p90": -0.001805,
    "min": -0.008189,
    "max": -0.001363
  },
  "skill_contrast_answered_minus_declined": {
    "n": 20,
    "mean": -0.037185,
    "sd": 0.017762,
    "p10": -0.054934,
    "p50": -0.040049,
    "p90": -0.013536,
    "min": -0.07775,
    "max": -0.012241
  },
  "ci_status_counts": {
    "ok": 440,
    "empty-bin": 100
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
    "max_abs_gap_panel_vs_pooled_answered_err": 4.9e-05,
    "n_compared": 20,
    "note": "panel skill.answered.model_error_rate vs the pooled row's answered_err_rate at the OPERATIVE rung. The panel's DECISION_THRESHOLD = 0.5 is Head.predict's own rule, so the two are the SAME quantity and the gap is pure rounding: the pooled row goes through _rate (4 dp) and the panel through the emit pass (6 dp), so anything up to 5e-05 is expected and is NOT a finding. A gap materially above that means the two are no longer measuring the same thing. REPORTED, never raised -- on real data this is a lead to chase, not a crash mid-run."
  }
}
```

## EICU-SUBGROUPS
```json
{
  "_run": {
    "mode": "FULL",
    "utc": "2026-08-20T16:20:51+00:00",
    "replicates": 20,
    "arm": "primary",
    "data_sha": "3744bf912e9196b44123a8d13c52faeb1a55e45a705250511c536ce7739ac26d"
  },
  "post_hoc": "[MEASURE] POST-HOC SUBGROUP DESCRIPTIVES (2026-08-20): computed after the extract was read; certifies nothing, settles no registered prediction or failure criterion, and no certified quantity descends from it. Rates in cells below the frozen EICU_MIN_OUTCOME_STRATUM record floor are suppressed as null, never 0.0.",
  "arm": "primary",
  "floor": 100,
  "dims": {
    "age_band": {
      "18-44": {
        "n_mean": 2839.8,
        "n_replicates": 20,
        "coverage_mean": 0.9631,
        "coverage_min": 0.9203,
        "answered_err_mean": 0.0193,
        "answered_pos_mean": 0.0201,
        "n_answered_rates_suppressed": 0
      },
      "45-64": {
        "n_mean": 6554.5,
        "n_replicates": 20,
        "coverage_mean": 0.9192,
        "coverage_min": 0.8608,
        "answered_err_mean": 0.0391,
        "answered_pos_mean": 0.0419,
        "n_answered_rates_suppressed": 0
      },
      "65-74": {
        "n_mean": 4374.6,
        "n_replicates": 20,
        "coverage_mean": 0.8875,
        "coverage_min": 0.8063,
        "answered_err_mean": 0.0497,
        "answered_pos_mean": 0.0555,
        "n_answered_rates_suppressed": 0
      },
      "75+": {
        "n_mean": 5498.0,
        "n_replicates": 20,
        "coverage_mean": 0.8208,
        "coverage_min": 0.6885,
        "answered_err_mean": 0.075,
        "answered_pos_mean": 0.0832,
        "n_answered_rates_suppressed": 0
      }
    },
    "gender": {
      "EMPTY": {
        "n_mean": 2.5,
        "n_replicates": 20,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "Female": {
        "n_mean": 8916.3,
        "n_replicates": 20,
        "coverage_mean": 0.89,
        "coverage_min": 0.8034,
        "answered_err_mean": 0.0489,
        "answered_pos_mean": 0.0531,
        "n_answered_rates_suppressed": 0
      },
      "Male": {
        "n_mean": 10344.8,
        "n_replicates": 20,
        "coverage_mean": 0.8908,
        "coverage_min": 0.8121,
        "answered_err_mean": 0.0468,
        "answered_pos_mean": 0.0516,
        "n_answered_rates_suppressed": 0
      },
      "OTHER": {
        "n_mean": 0.0,
        "n_replicates": 20,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "Other": {
        "n_mean": 0.1,
        "n_replicates": 20,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "Unknown": {
        "n_mean": 3.2,
        "n_replicates": 20,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      }
    },
    "ethnicity": {
      "African American": {
        "n_mean": 1940.7,
        "n_replicates": 20,
        "coverage_mean": 0.8982,
        "coverage_min": 0.8036,
        "answered_err_mean": 0.0422,
        "answered_pos_mean": 0.0457,
        "n_answered_rates_suppressed": 0
      },
      "Asian": {
        "n_mean": 311.4,
        "n_replicates": 20,
        "coverage_mean": 0.8748,
        "coverage_min": 0.7968,
        "answered_err_mean": 0.0466,
        "answered_pos_mean": 0.0514,
        "n_answered_rates_suppressed": 0
      },
      "Caucasian": {
        "n_mean": 15081.0,
        "n_replicates": 20,
        "coverage_mean": 0.8895,
        "coverage_min": 0.8062,
        "answered_err_mean": 0.0488,
        "answered_pos_mean": 0.0533,
        "n_answered_rates_suppressed": 0
      },
      "EMPTY": {
        "n_mean": 243.7,
        "n_replicates": 20,
        "coverage_mean": 0.8895,
        "coverage_min": 0.7736,
        "answered_err_mean": 0.0481,
        "answered_pos_mean": 0.0586,
        "n_answered_rates_suppressed": 4
      },
      "Hispanic": {
        "n_mean": 660.5,
        "n_replicates": 20,
        "coverage_mean": 0.8947,
        "coverage_min": 0.8123,
        "answered_err_mean": 0.0462,
        "answered_pos_mean": 0.0508,
        "n_answered_rates_suppressed": 0
      },
      "Native American": {
        "n_mean": 130.2,
        "n_replicates": 20,
        "coverage_mean": 0.8887,
        "coverage_min": 0.8489,
        "answered_err_mean": 0.0408,
        "answered_pos_mean": 0.0494,
        "n_answered_rates_suppressed": 0
      },
      "OTHER": {
        "n_mean": 0.0,
        "n_replicates": 20,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "Other/Unknown": {
        "n_mean": 899.5,
        "n_replicates": 20,
        "coverage_mean": 0.8902,
        "coverage_min": 0.818,
        "answered_err_mean": 0.0458,
        "answered_pos_mean": 0.0516,
        "n_answered_rates_suppressed": 0
      }
    },
    "hospitaladmitsource": {
      "Acute Care/Floor": {
        "n_mean": 416.1,
        "n_replicates": 20,
        "coverage_mean": 0.8581,
        "coverage_min": 0.688,
        "answered_err_mean": 0.0599,
        "answered_pos_mean": 0.0646,
        "n_answered_rates_suppressed": 0
      },
      "Chest Pain Center": {
        "n_mean": 30.6,
        "n_replicates": 20,
        "coverage_mean": 0.9914,
        "coverage_min": 0.9741,
        "answered_err_mean": 0.0323,
        "answered_pos_mean": 0.0323,
        "n_answered_rates_suppressed": 0
      },
      "Direct Admit": {
        "n_mean": 1285.0,
        "n_replicates": 20,
        "coverage_mean": 0.8806,
        "coverage_min": 0.792,
        "answered_err_mean": 0.0563,
        "answered_pos_mean": 0.0611,
        "n_answered_rates_suppressed": 0
      },
      "EMPTY": {
        "n_mean": 4797.2,
        "n_replicates": 20,
        "coverage_mean": 0.891,
        "coverage_min": 0.7769,
        "answered_err_mean": 0.0498,
        "answered_pos_mean": 0.0538,
        "n_answered_rates_suppressed": 0
      },
      "Emergency Department": {
        "n_mean": 7992.1,
        "n_replicates": 20,
        "coverage_mean": 0.8972,
        "coverage_min": 0.8187,
        "answered_err_mean": 0.0463,
        "answered_pos_mean": 0.0509,
        "n_answered_rates_suppressed": 0
      },
      "Floor": {
        "n_mean": 1624.2,
        "n_replicates": 20,
        "coverage_mean": 0.7962,
        "coverage_min": 0.6826,
        "answered_err_mean": 0.0747,
        "answered_pos_mean": 0.0852,
        "n_answered_rates_suppressed": 0
      },
      "ICU": {
        "n_mean": 6.1,
        "n_replicates": 20,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "ICU to SDU": {
        "n_mean": 7.8,
        "n_replicates": 20,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "OTHER": {
        "n_mean": 0.0,
        "n_replicates": 20,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "Observation": {
        "n_mean": 2.2,
        "n_replicates": 20,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "Operating Room": {
        "n_mean": 1691.4,
        "n_replicates": 20,
        "coverage_mean": 0.9642,
        "coverage_min": 0.895,
        "answered_err_mean": 0.0261,
        "answered_pos_mean": 0.0265,
        "n_answered_rates_suppressed": 0
      },
      "Other": {
        "n_mean": 0.9,
        "n_replicates": 20,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "Other Hospital": {
        "n_mean": 291.9,
        "n_replicates": 20,
        "coverage_mean": 0.8053,
        "coverage_min": 0.7017,
        "answered_err_mean": 0.066,
        "answered_pos_mean": 0.0753,
        "n_answered_rates_suppressed": 2
      },
      "Other ICU": {
        "n_mean": 38.0,
        "n_replicates": 20,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "PACU": {
        "n_mean": 181.8,
        "n_replicates": 20,
        "coverage_mean": 0.9727,
        "coverage_min": 0.9122,
        "answered_err_mean": 0.0162,
        "answered_pos_mean": 0.0165,
        "n_answered_rates_suppressed": 0
      },
      "Recovery Room": {
        "n_mean": 655.8,
        "n_replicates": 20,
        "coverage_mean": 0.9733,
        "coverage_min": 0.9435,
        "answered_err_mean": 0.02,
        "answered_pos_mean": 0.0206,
        "n_answered_rates_suppressed": 0
      },
      "Step-Down Unit (SDU)": {
        "n_mean": 245.7,
        "n_replicates": 20,
        "coverage_mean": 0.7396,
        "coverage_min": 0.6135,
        "answered_err_mean": 0.084,
        "answered_pos_mean": 0.0971,
        "n_answered_rates_suppressed": 1
      }
    },
    "unittype": {
      "CCU-CTICU": {
        "n_mean": 1708.7,
        "n_replicates": 20,
        "coverage_mean": 0.8998,
        "coverage_min": 0.766,
        "answered_err_mean": 0.0428,
        "answered_pos_mean": 0.0476,
        "n_answered_rates_suppressed": 0
      },
      "CSICU": {
        "n_mean": 756.0,
        "n_replicates": 20,
        "coverage_mean": 0.94,
        "coverage_min": 0.8657,
        "answered_err_mean": 0.0297,
        "answered_pos_mean": 0.0344,
        "n_answered_rates_suppressed": 0
      },
      "CTICU": {
        "n_mean": 585.2,
        "n_replicates": 20,
        "coverage_mean": 0.9275,
        "coverage_min": 0.7746,
        "answered_err_mean": 0.0396,
        "answered_pos_mean": 0.044,
        "n_answered_rates_suppressed": 0
      },
      "Cardiac ICU": {
        "n_mean": 1391.8,
        "n_replicates": 20,
        "coverage_mean": 0.8698,
        "coverage_min": 0.7692,
        "answered_err_mean": 0.0482,
        "answered_pos_mean": 0.0583,
        "n_answered_rates_suppressed": 0
      },
      "EMPTY": {
        "n_mean": 0.0,
        "n_replicates": 20,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "MICU": {
        "n_mean": 1763.2,
        "n_replicates": 20,
        "coverage_mean": 0.8497,
        "coverage_min": 0.7186,
        "answered_err_mean": 0.0603,
        "answered_pos_mean": 0.0676,
        "n_answered_rates_suppressed": 0
      },
      "Med-Surg ICU": {
        "n_mean": 10499.9,
        "n_replicates": 20,
        "coverage_mean": 0.8936,
        "coverage_min": 0.8281,
        "answered_err_mean": 0.0496,
        "answered_pos_mean": 0.0541,
        "n_answered_rates_suppressed": 0
      },
      "Neuro ICU": {
        "n_mean": 1315.8,
        "n_replicates": 20,
        "coverage_mean": 0.8888,
        "coverage_min": 0.8335,
        "answered_err_mean": 0.0443,
        "answered_pos_mean": 0.0461,
        "n_answered_rates_suppressed": 0
      },
      "OTHER": {
        "n_mean": 0.0,
        "n_replicates": 20,
        "coverage_mean": null,
        "coverage_min": null,
        "answered_err_mean": null,
        "answered_pos_mean": null,
        "n_answered_rates_suppressed": 0
      },
      "SICU": {
        "n_mean": 1246.2,
        "n_replicates": 20,
        "coverage_mean": 0.8954,
        "coverage_min": 0.7841,
        "answered_err_mean": 0.0481,
        "answered_pos_mean": 0.0518,
        "n_answered_rates_suppressed": 0
      }
    }
  },
  "n_cells_suppressed_whole": 330
}
```
