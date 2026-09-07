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
    "utc": "2026-09-05T16:43:39+00:00",
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
  ],
  "los_under_24h": {
    "unit": "hours",
    "threshold": 24.0,
    "what": "ICU stays (unitdischargeoffset, a DENYLISTED feature read as a diagnostic only) that ended inside the first 24 h, counted on the held-out target pool of each replicate and on its declined / answered halves at the deployed operative tau. The prediction is made at ICU hour 24, so a stay that ended before then is one the head would not have been asked about in deployment; the cohort keeps them and this block says how many there are. Means over replicates; no per-stay value is written.",
    "n_replicates": 20,
    "mean_n_pool": 19266.9,
    "mean_n_lt_24h_pool": 5781.15,
    "mean_frac_lt_24h_pool": 0.302,
    "mean_frac_lt_24h_of_declined": 0.2168,
    "mean_frac_lt_24h_of_answered": 0.3128,
    "mean_frac_declined_among_lt_24h": 0.0784,
    "mean_n_deaths_pool": 1690.8,
    "mean_n_deaths_lt_24h_pool": 518.7,
    "mean_frac_deaths_lt_24h_of_deaths": 0.3078,
    "mean_frac_deaths_lt_24h_of_pool": 0.0268,
    "mean_n_los_unavailable_pool": 0.0
  }
}
```

## EICU-PERSITE
```json
{
  "_run": {
    "mode": "FULL",
    "utc": "2026-09-05T16:43:39+00:00",
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
      "note": "per-hospital hard-violation is a DISPERSION diagnostic with NO delta target: the certificate bounds the site-population average, not individual hospitals (audit V1).",
      "share_75plus_vs_answered_err_spearman": null,
      "n_pools_in_spearman": 0,
      "share_75plus_note": "share_75plus is the share of a hospital's held-out stays aged 75 or over among stays with a recorded age; the Spearman correlation is against that hospital's answered error rate over every certified pool at this rung, so pools of the same hospital in different re-splits are not independent observations."
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
      "note": "per-hospital hard-violation is a DISPERSION diagnostic with NO delta target: the certificate bounds the site-population average, not individual hospitals (audit V1).",
      "share_75plus_vs_answered_err_spearman": 0.018746,
      "n_pools_in_spearman": 477,
      "share_75plus_note": "share_75plus is the share of a hospital's held-out stays aged 75 or over among stays with a recorded age; the Spearman correlation is against that hospital's answered error rate over every certified pool at this rung, so pools of the same hospital in different re-splits are not independent observations."
    }
  }
}
```

## EICU-COMPARATOR
```json
{
  "_run": {
    "mode": "FULL",
    "utc": "2026-09-05T16:43:39+00:00",
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
      "note": "the APACHE-IVa columns are scored on the answered records that CARRY a comparator value; that coverage is site-correlated, so the subset-matched CertGate error is reported beside them rather than compared across different denominators.",
      "mean_head_auc_pool": 0.8593,
      "mean_head_brier_pool": 0.0616,
      "mean_head_auc_answered": null,
      "mean_head_brier_answered": null,
      "mean_apache_iva_auc_pool": 0.8601,
      "mean_apache_iva_brier_pool": 0.063,
      "apache_available_share_pool": 0.8221,
      "n_rows_pool": 20,
      "pool_note": "*_pool fields score EVERY held-out stay of the replicate's target pool, certified rung or not: the head's on the full pool, APACHE-IVa's on the pool records that carry a comparator value. *_answered fields are on the answered set of a certified rung only."
    },
    "0.1": {
      "n_certified_replicates": 20,
      "mean_certgate_answered_err": 0.0478,
      "mean_certgate_answered_err_on_apache_subset": 0.0471,
      "mean_apache_iva_brier": 0.0437,
      "mean_apache_iva_auc": 0.8203,
      "apache_available_share": 0.8219,
      "note": "the APACHE-IVa columns are scored on the answered records that CARRY a comparator value; that coverage is site-correlated, so the subset-matched CertGate error is reported beside them rather than compared across different denominators.",
      "mean_head_auc_pool": 0.8593,
      "mean_head_brier_pool": 0.0616,
      "mean_head_auc_answered": 0.8098,
      "mean_head_brier_answered": 0.0428,
      "mean_apache_iva_auc_pool": 0.8601,
      "mean_apache_iva_brier_pool": 0.063,
      "apache_available_share_pool": 0.8221,
      "n_rows_pool": 20,
      "pool_note": "*_pool fields score EVERY held-out stay of the replicate's target pool, certified rung or not: the head's on the full pool, APACHE-IVa's on the pool records that carry a comparator value. *_answered fields are on the answered set of a certified rung only."
    }
  }
}
```

## EICU-RELIABILITY
```json
{
  "_run": {
    "mode": "FULL",
    "utc": "2026-09-05T16:43:39+00:00",
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
    "utc": "2026-09-05T16:43:39+00:00",
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
    },
    "aps_present": {
      "absent": {
        "n_mean": 727.5,
        "n_replicates": 20,
        "coverage_mean": 0.991,
        "coverage_min": 0.9492,
        "answered_err_mean": 0.0506,
        "answered_pos_mean": 0.0506,
        "n_answered_rates_suppressed": 0
      },
      "present": {
        "n_mean": 18539.4,
        "n_replicates": 20,
        "coverage_mean": 0.8862,
        "coverage_min": 0.7947,
        "answered_err_mean": 0.0478,
        "answered_pos_mean": 0.0526,
        "n_answered_rates_suppressed": 0
      }
    }
  },
  "n_cells_suppressed_whole": 330,
  "dim_notes": {
    "aps_present": "present = a day-1 apacheApsVar row exists for the stay; absent = no day-1 APACHE row: APACHE-ineligible admission types, stays that ended before the day-1 window closed, and hospitals that filed no APACHE rows. Absence is outcome-informative (audit E-9), which is why it is reported as a subgroup rather than imputed away."
  }
}
```

## EICU-FAITHFULNESS
```json
{
  "_run": {
    "mode": "FULL",
    "utc": "2026-09-05T16:43:39+00:00",
    "replicates": 20,
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
    },
    {
      "status": "ok",
      "replicate": 1,
      "k": 10,
      "n_coalitions": 1024,
      "n_answered": 20120,
      "n_declined": 2508,
      "top_driver_int": "aps_motor",
      "top_driver_cond": "aps_motor",
      "spearman_abs_gap_int_vs_cond": 0.842424,
      "max_abs_offdiag_corr_train": 0.801427,
      "max_abs_offdiag_corr_pair": [
        "aps_eyes",
        "aps_motor"
      ],
      "corr_train": [
        [
          1.0,
          0.8014,
          -0.0956,
          -0.4796,
          0.2006,
          0.0696,
          -0.3632,
          0.0368,
          -0.0797,
          0.0589
        ],
        [
          0.8014,
          1.0,
          -0.0688,
          -0.5229,
          0.1578,
          0.0437,
          -0.3974,
          0.0271,
          -0.0821,
          0.0644
        ],
        [
          -0.0956,
          -0.0688,
          1.0,
          0.1408,
          -0.0622,
          -0.2326,
          0.1794,
          0.098,
          0.0398,
          -0.0435
        ],
        [
          -0.4796,
          -0.5229,
          0.1408,
          1.0,
          -0.1365,
          -0.0169,
          0.7233,
          -0.0424,
          0.106,
          -0.0995
        ],
        [
          0.2006,
          0.1578,
          -0.0622,
          -0.1365,
          1.0,
          0.1175,
          -0.1307,
          0.0203,
          0.1144,
          0.0369
        ],
        [
          0.0696,
          0.0437,
          -0.2326,
          -0.0169,
          0.1175,
          1.0,
          -0.0124,
          -0.3658,
          -0.0468,
          0.0594
        ],
        [
          -0.3632,
          -0.3974,
          0.1794,
          0.7233,
          -0.1307,
          -0.0124,
          1.0,
          -0.0633,
          0.0896,
          -0.0875
        ],
        [
          0.0368,
          0.0271,
          0.098,
          -0.0424,
          0.0203,
          -0.3658,
          -0.0633,
          1.0,
          -0.0196,
          0.0521
        ],
        [
          -0.0797,
          -0.0821,
          0.0398,
          0.106,
          0.1144,
          -0.0468,
          0.0896,
          -0.0196,
          1.0,
          -0.0974
        ],
        [
          0.0589,
          0.0644,
          -0.0435,
          -0.0995,
          0.0369,
          0.0594,
          -0.0875,
          0.0521,
          -0.0974,
          1.0
        ]
      ],
      "max_abs_rel_gap_change": 0.666501
    },
    {
      "status": "ok",
      "replicate": 2,
      "k": 10,
      "n_coalitions": 1024,
      "n_answered": 17555,
      "n_declined": 4172,
      "top_driver_int": "aps_motor",
      "top_driver_cond": "aps_motor",
      "spearman_abs_gap_int_vs_cond": 0.030303,
      "max_abs_offdiag_corr_train": 0.955555,
      "max_abs_offdiag_corr_pair": [
        "aps_meanbp__missing",
        "aps_heartrate__missing"
      ],
      "corr_train": [
        [
          1.0,
          -0.4873,
          0.0012,
          -0.0,
          -0.0028,
          -0.1279,
          0.1875,
          0.0783,
          -0.004,
          0.8002
        ],
        [
          -0.4873,
          1.0,
          -0.0289,
          -0.0,
          -0.0283,
          0.1698,
          -0.1263,
          -0.014,
          0.0654,
          -0.5273
        ],
        [
          0.0012,
          -0.0289,
          1.0,
          0.7361,
          0.9556,
          -0.0003,
          0.001,
          -0.002,
          0.0016,
          0.0035
        ],
        [
          -0.0,
          -0.0,
          0.7361,
          1.0,
          0.7196,
          -0.0,
          0.0,
          -0.0,
          -0.0072,
          -0.0
        ],
        [
          -0.0028,
          -0.0283,
          0.9556,
          0.7196,
          1.0,
          0.0,
          0.0018,
          -0.0018,
          0.0009,
          0.0005
        ],
        [
          -0.1279,
          0.1698,
          -0.0003,
          -0.0,
          0.0,
          1.0,
          -0.0491,
          -0.2435,
          0.0478,
          -0.1063
        ],
        [
          0.1875,
          -0.1263,
          0.001,
          0.0,
          0.0018,
          -0.0491,
          1.0,
          0.107,
          0.0081,
          0.1525
        ],
        [
          0.0783,
          -0.014,
          -0.002,
          -0.0,
          -0.0018,
          -0.2435,
          0.107,
          1.0,
          0.0166,
          0.0522
        ],
        [
          -0.004,
          0.0654,
          0.0016,
          -0.0072,
          0.0009,
          0.0478,
          0.0081,
          0.0166,
          1.0,
          -0.0121
        ],
        [
          0.8002,
          -0.5273,
          0.0035,
          -0.0,
          0.0005,
          -0.1063,
          0.1525,
          0.0522,
          -0.0121,
          1.0
        ]
      ],
      "max_abs_rel_gap_change": 1.651462
    },
    {
      "status": "ok",
      "replicate": 3,
      "k": 10,
      "n_coalitions": 1024,
      "n_answered": 15912,
      "n_declined": 1998,
      "top_driver_int": "aps_motor",
      "top_driver_cond": "aps_motor",
      "spearman_abs_gap_int_vs_cond": 0.733333,
      "max_abs_offdiag_corr_train": 0.837765,
      "max_abs_offdiag_corr_pair": [
        "apv_oobintubday1",
        "apv_oobventday1"
      ],
      "corr_train": [
        [
          1.0,
          -0.1287,
          -0.4538,
          -0.3151,
          0.7971,
          0.0522,
          0.1675,
          0.7191,
          -0.3862,
          -0.0791
        ],
        [
          -0.1287,
          1.0,
          0.1656,
          0.2171,
          -0.1109,
          -0.2132,
          -0.0383,
          -0.1089,
          0.1175,
          0.4162
        ],
        [
          -0.4538,
          0.1656,
          1.0,
          0.699,
          -0.48,
          -0.021,
          -0.1398,
          -0.5546,
          0.8378,
          0.1259
        ],
        [
          -0.3151,
          0.2171,
          0.699,
          1.0,
          -0.3374,
          -0.0173,
          -0.1149,
          -0.3833,
          0.5856,
          0.1702
        ],
        [
          0.7971,
          -0.1109,
          -0.48,
          -0.3374,
          1.0,
          0.0355,
          0.1386,
          0.7722,
          -0.4181,
          -0.0763
        ],
        [
          0.0522,
          -0.2132,
          -0.021,
          -0.0173,
          0.0355,
          1.0,
          0.1015,
          0.0089,
          -0.0277,
          0.0288
        ],
        [
          0.1675,
          -0.0383,
          -0.1398,
          -0.1149,
          0.1386,
          0.1015,
          1.0,
          0.1118,
          -0.1253,
          -0.0432
        ],
        [
          0.7191,
          -0.1089,
          -0.5546,
          -0.3833,
          0.7722,
          0.0089,
          0.1118,
          1.0,
          -0.4774,
          -0.0793
        ],
        [
          -0.3862,
          0.1175,
          0.8378,
          0.5856,
          -0.4181,
          -0.0277,
          -0.1253,
          -0.4774,
          1.0,
          0.0662
        ],
        [
          -0.0791,
          0.4162,
          0.1259,
          0.1702,
          -0.0763,
          0.0288,
          -0.0432,
          -0.0793,
          0.0662,
          1.0
        ]
      ],
      "max_abs_rel_gap_change": 0.591667
    },
    {
      "status": "ok",
      "replicate": 4,
      "k": 10,
      "n_coalitions": 1024,
      "n_answered": 18525,
      "n_declined": 1816,
      "top_driver_int": "aps_motor",
      "top_driver_cond": "aps_motor",
      "spearman_abs_gap_int_vs_cond": 0.333333,
      "max_abs_offdiag_corr_train": 0.859367,
      "max_abs_offdiag_corr_pair": [
        "apv_oobintubday1",
        "apv_oobventday1"
      ],
      "corr_train": [
        [
          1.0,
          -0.0817,
          -0.3083,
          0.0687,
          0.1761,
          -0.476,
          0.065,
          -0.4158,
          0.7877,
          0.0323
        ],
        [
          -0.0817,
          1.0,
          0.1635,
          -0.227,
          -0.0451,
          0.1265,
          -0.0421,
          0.0858,
          -0.0541,
          0.0698
        ],
        [
          -0.3083,
          0.1635,
          1.0,
          0.0112,
          -0.1043,
          0.6414,
          -0.0671,
          0.5512,
          -0.3436,
          -0.0843
        ],
        [
          0.0687,
          -0.227,
          0.0112,
          1.0,
          0.0994,
          -0.0021,
          0.0461,
          -0.007,
          0.0486,
          -0.3772
        ],
        [
          0.1761,
          -0.0451,
          -0.1043,
          0.0994,
          1.0,
          -0.1157,
          0.0575,
          -0.1092,
          0.1414,
          0.0298
        ],
        [
          -0.476,
          0.1265,
          0.6414,
          -0.0021,
          -0.1157,
          1.0,
          -0.1048,
          0.8594,
          -0.522,
          -0.0568
        ],
        [
          0.065,
          -0.0421,
          -0.0671,
          0.0461,
          0.0575,
          -0.1048,
          1.0,
          -0.0959,
          0.0558,
          0.0482
        ],
        [
          -0.4158,
          0.0858,
          0.5512,
          -0.007,
          -0.1092,
          0.8594,
          -0.0959,
          1.0,
          -0.4635,
          0.0146
        ],
        [
          0.7877,
          -0.0541,
          -0.3436,
          0.0486,
          0.1414,
          -0.522,
          0.0558,
          -0.4635,
          1.0,
          0.0203
        ],
        [
          0.0323,
          0.0698,
          -0.0843,
          -0.3772,
          0.0298,
          -0.0568,
          0.0482,
          0.0146,
          0.0203,
          1.0
        ]
      ],
      "max_abs_rel_gap_change": 1.150387
    },
    {
      "status": "ok",
      "replicate": 5,
      "k": 10,
      "n_coalitions": 1024,
      "n_answered": 17772,
      "n_declined": 2992,
      "top_driver_int": "aps_motor",
      "top_driver_cond": "aps_motor",
      "spearman_abs_gap_int_vs_cond": 0.69697,
      "max_abs_offdiag_corr_train": 0.794472,
      "max_abs_offdiag_corr_pair": [
        "aps_motor",
        "aps_eyes"
      ],
      "corr_train": [
        [
          1.0,
          -0.0,
          0.0001,
          -0.4962,
          -0.1163,
          0.7945,
          0.0683,
          0.1645,
          -0.3361,
          -0.041
        ],
        [
          -0.0,
          1.0,
          0.7575,
          -0.0,
          -0.0,
          0.0,
          -0.0,
          -0.0,
          0.0,
          -0.0
        ],
        [
          0.0001,
          0.7575,
          1.0,
          -0.0215,
          -0.0012,
          0.0038,
          -0.0002,
          0.0008,
          -0.0194,
          -0.0015
        ],
        [
          -0.4962,
          -0.0,
          -0.0215,
          1.0,
          0.1482,
          -0.542,
          -0.0208,
          -0.1205,
          0.6742,
          0.017
        ],
        [
          -0.1163,
          -0.0,
          -0.0012,
          0.1482,
          1.0,
          -0.0996,
          -0.2311,
          -0.0413,
          0.1975,
          0.019
        ],
        [
          0.7945,
          0.0,
          0.0038,
          -0.542,
          -0.0996,
          1.0,
          0.0459,
          0.1318,
          -0.3654,
          -0.0411
        ],
        [
          0.0683,
          -0.0,
          -0.0002,
          -0.0208,
          -0.2311,
          0.0459,
          1.0,
          0.1108,
          -0.015,
          -0.0785
        ],
        [
          0.1645,
          -0.0,
          0.0008,
          -0.1205,
          -0.0413,
          0.1318,
          0.1108,
          1.0,
          -0.1066,
          -0.0844
        ],
        [
          -0.3361,
          0.0,
          -0.0194,
          0.6742,
          0.1975,
          -0.3654,
          -0.015,
          -0.1066,
          1.0,
          0.0286
        ],
        [
          -0.041,
          -0.0,
          -0.0015,
          0.017,
          0.019,
          -0.0411,
          -0.0785,
          -0.0844,
          0.0286,
          1.0
        ]
      ],
      "max_abs_rel_gap_change": 0.72112
    },
    {
      "status": "ok",
      "replicate": 6,
      "k": 10,
      "n_coalitions": 1024,
      "n_answered": 16491,
      "n_declined": 1603,
      "top_driver_int": "aps_motor",
      "top_driver_cond": "aps_motor",
      "spearman_abs_gap_int_vs_cond": 0.842424,
      "max_abs_offdiag_corr_train": 0.721215,
      "max_abs_offdiag_corr_pair": [
        "aps_intubated",
        "apv_oobintubday1"
      ],
      "corr_train": [
        [
          1.0,
          -0.1281,
          -0.4524,
          -0.336,
          0.0684,
          0.1825,
          -0.0589,
          -0.044,
          0.0515,
          -0.0395
        ],
        [
          -0.1281,
          1.0,
          0.1751,
          0.223,
          -0.2087,
          -0.0382,
          0.4293,
          0.016,
          0.0504,
          0.002
        ],
        [
          -0.4524,
          0.1751,
          1.0,
          0.7212,
          -0.0113,
          -0.1308,
          0.1348,
          0.0107,
          -0.0692,
          -0.2355
        ],
        [
          -0.336,
          0.223,
          0.7212,
          1.0,
          -0.0049,
          -0.1019,
          0.1765,
          0.0318,
          -0.0945,
          -0.1704
        ],
        [
          0.0684,
          -0.2087,
          -0.0113,
          -0.0049,
          1.0,
          0.0997,
          0.0339,
          -0.0861,
          -0.3793,
          -0.0238
        ],
        [
          0.1825,
          -0.0382,
          -0.1308,
          -0.1019,
          0.0997,
          1.0,
          -0.0344,
          -0.0851,
          0.0182,
          0.0508
        ],
        [
          -0.0589,
          0.4293,
          0.1348,
          0.1765,
          0.0339,
          -0.0344,
          1.0,
          -0.0272,
          -0.1567,
          -0.069
        ],
        [
          -0.044,
          0.016,
          0.0107,
          0.0318,
          -0.0861,
          -0.0851,
          -0.0272,
          1.0,
          -0.0179,
          0.149
        ],
        [
          0.0515,
          0.0504,
          -0.0692,
          -0.0945,
          -0.3793,
          0.0182,
          -0.1567,
          -0.0179,
          1.0,
          0.056
        ],
        [
          -0.0395,
          0.002,
          -0.2355,
          -0.1704,
          -0.0238,
          0.0508,
          -0.069,
          0.149,
          0.056,
          1.0
        ]
      ],
      "max_abs_rel_gap_change": 0.546233
    },
    {
      "status": "ok",
      "replicate": 7,
      "k": 10,
      "n_coalitions": 1024,
      "n_answered": 13649,
      "n_declined": 2230,
      "top_driver_int": "aps_motor",
      "top_driver_cond": "aps_motor",
      "spearman_abs_gap_int_vs_cond": 0.684848,
      "max_abs_offdiag_corr_train": 0.849298,
      "max_abs_offdiag_corr_pair": [
        "apv_oobventday1",
        "apv_oobintubday1"
      ],
      "corr_train": [
        [
          1.0,
          -0.4878,
          -0.1123,
          0.8114,
          0.0678,
          -0.312,
          0.1904,
          0.0734,
          -0.0376,
          -0.4196
        ],
        [
          -0.4878,
          1.0,
          0.1595,
          -0.522,
          -0.102,
          0.6904,
          -0.1506,
          -0.0331,
          -0.0002,
          0.8493
        ],
        [
          -0.1123,
          0.1595,
          1.0,
          -0.0924,
          -0.0438,
          0.2079,
          -0.0541,
          -0.227,
          0.0156,
          0.1152
        ],
        [
          0.8114,
          -0.522,
          -0.0924,
          1.0,
          0.0697,
          -0.3426,
          0.157,
          0.0548,
          -0.0347,
          -0.4555
        ],
        [
          0.0678,
          -0.102,
          -0.0438,
          0.0697,
          1.0,
          -0.086,
          0.0388,
          0.0562,
          -0.1435,
          -0.0924
        ],
        [
          -0.312,
          0.6904,
          0.2079,
          -0.3426,
          -0.086,
          1.0,
          -0.1274,
          -0.0247,
          0.0075,
          0.5863
        ],
        [
          0.1904,
          -0.1506,
          -0.0541,
          0.157,
          0.0388,
          -0.1274,
          1.0,
          0.1033,
          -0.0786,
          -0.1366
        ],
        [
          0.0734,
          -0.0331,
          -0.227,
          0.0548,
          0.0562,
          -0.0247,
          0.1033,
          1.0,
          -0.0738,
          -0.0309
        ],
        [
          -0.0376,
          -0.0002,
          0.0156,
          -0.0347,
          -0.1435,
          0.0075,
          -0.0786,
          -0.0738,
          1.0,
          0.0332
        ],
        [
          -0.4196,
          0.8493,
          0.1152,
          -0.4555,
          -0.0924,
          0.5863,
          -0.1366,
          -0.0309,
          0.0332,
          1.0
        ]
      ],
      "max_abs_rel_gap_change": 0.741245
    },
    {
      "status": "ok",
      "replicate": 8,
      "k": 10,
      "n_coalitions": 1024,
      "n_answered": 12369,
      "n_declined": 1298,
      "top_driver_int": "aps_motor",
      "top_driver_cond": "aps_motor",
      "spearman_abs_gap_int_vs_cond": 0.539394,
      "max_abs_offdiag_corr_train": 0.852509,
      "max_abs_offdiag_corr_pair": [
        "apv_oobventday1",
        "apv_oobintubday1"
      ],
      "corr_train": [
        [
          1.0,
          -0.3512,
          -0.1227,
          0.066,
          -0.4898,
          0.7904,
          0.0664,
          0.1834,
          -0.4209,
          -0.0
        ],
        [
          -0.3512,
          1.0,
          0.1724,
          -0.0207,
          0.6782,
          -0.3918,
          -0.0705,
          -0.1153,
          0.5782,
          0.0
        ],
        [
          -0.1227,
          0.1724,
          1.0,
          -0.2327,
          0.1377,
          -0.1031,
          -0.0478,
          -0.0496,
          0.1005,
          0.0
        ],
        [
          0.066,
          -0.0207,
          -0.2327,
          1.0,
          -0.0285,
          0.0448,
          0.058,
          0.1069,
          -0.0272,
          0.0
        ],
        [
          -0.4898,
          0.6782,
          0.1377,
          -0.0285,
          1.0,
          -0.5368,
          -0.0941,
          -0.1327,
          0.8525,
          0.0
        ],
        [
          0.7904,
          -0.3918,
          -0.1031,
          0.0448,
          -0.5368,
          1.0,
          0.069,
          0.1459,
          -0.4689,
          -0.0
        ],
        [
          0.0664,
          -0.0705,
          -0.0478,
          0.058,
          -0.0941,
          0.069,
          1.0,
          0.0268,
          -0.0839,
          0.0
        ],
        [
          0.1834,
          -0.1153,
          -0.0496,
          0.1069,
          -0.1327,
          0.1459,
          0.0268,
          1.0,
          -0.1218,
          0.0
        ],
        [
          -0.4209,
          0.5782,
          0.1005,
          -0.0272,
          0.8525,
          -0.4689,
          -0.0839,
          -0.1218,
          1.0,
          -0.0
        ],
        [
          -0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          -0.0,
          0.0,
          0.0,
          -0.0,
          1.0
        ]
      ],
      "max_abs_rel_gap_change": 0.697838
    },
    {
      "status": "ok",
      "replicate": 9,
      "k": 10,
      "n_coalitions": 1024,
      "n_answered": 15889,
      "n_declined": 1762,
      "top_driver_int": "aps_motor",
      "top_driver_cond": "aps_motor",
      "spearman_abs_gap_int_vs_cond": 0.806061,
      "max_abs_offdiag_corr_train": 0.785807,
      "max_abs_offdiag_corr_pair": [
        "aps_motor",
        "aps_eyes"
      ],
      "corr_train": [
        [
          1.0,
          0.1838,
          -0.4554,
          -0.1123,
          0.7858,
          0.0677,
          -0.3404,
          0.0673,
          0.0011,
          0.0357
        ],
        [
          0.1838,
          1.0,
          -0.1224,
          -0.0452,
          0.149,
          0.0976,
          -0.1141,
          0.0436,
          0.0001,
          0.0334
        ],
        [
          -0.4554,
          -0.1224,
          1.0,
          0.1585,
          -0.4993,
          -0.004,
          0.7156,
          -0.1093,
          -0.0253,
          -0.0681
        ],
        [
          -0.1123,
          -0.0452,
          0.1585,
          1.0,
          -0.0896,
          -0.2216,
          0.1936,
          -0.0559,
          -0.0007,
          0.0584
        ],
        [
          0.7858,
          0.149,
          -0.4993,
          -0.0896,
          1.0,
          0.0482,
          -0.3637,
          0.0682,
          0.0033,
          0.017
        ],
        [
          0.0677,
          0.0976,
          -0.004,
          -0.2216,
          0.0482,
          1.0,
          0.0162,
          0.0549,
          -0.0019,
          -0.3846
        ],
        [
          -0.3404,
          -0.1141,
          0.7156,
          0.1936,
          -0.3637,
          0.0162,
          1.0,
          -0.1034,
          -0.0208,
          -0.0993
        ],
        [
          0.0673,
          0.0436,
          -0.1093,
          -0.0559,
          0.0682,
          0.0549,
          -0.1034,
          1.0,
          0.0027,
          0.0537
        ],
        [
          0.0011,
          0.0001,
          -0.0253,
          -0.0007,
          0.0033,
          -0.0019,
          -0.0208,
          0.0027,
          1.0,
          0.0023
        ],
        [
          0.0357,
          0.0334,
          -0.0681,
          0.0584,
          0.017,
          -0.3846,
          -0.0993,
          0.0537,
          0.0023,
          1.0
        ]
      ],
      "max_abs_rel_gap_change": 0.738217
    },
    {
      "status": "ok",
      "replicate": 10,
      "k": 10,
      "n_coalitions": 1024,
      "n_answered": 21431,
      "n_declined": 2523,
      "top_driver_int": "aps_motor",
      "top_driver_cond": "aps_motor",
      "spearman_abs_gap_int_vs_cond": 0.515152,
      "max_abs_offdiag_corr_train": 0.803855,
      "max_abs_offdiag_corr_pair": [
        "aps_eyes",
        "aps_motor"
      ],
      "corr_train": [
        [
          1.0,
          -0.1219,
          0.0604,
          -0.3407,
          -0.4798,
          0.8039,
          0.164,
          0.0362,
          -0.066,
          -0.0186
        ],
        [
          -0.1219,
          1.0,
          -0.2239,
          0.2208,
          0.1707,
          -0.1005,
          -0.037,
          0.0732,
          0.389,
          0.0113
        ],
        [
          0.0604,
          -0.2239,
          1.0,
          -0.0028,
          -0.0132,
          0.0398,
          0.0895,
          -0.3532,
          0.0266,
          -0.0105
        ],
        [
          -0.3407,
          0.2208,
          -0.0028,
          1.0,
          0.7069,
          -0.3621,
          -0.1235,
          -0.091,
          0.159,
          0.0167
        ],
        [
          -0.4798,
          0.1707,
          -0.0132,
          0.7069,
          1.0,
          -0.5115,
          -0.137,
          -0.0638,
          0.1192,
          0.0196
        ],
        [
          0.8039,
          -0.1005,
          0.0398,
          -0.3621,
          -0.5115,
          1.0,
          0.1325,
          0.0274,
          -0.0591,
          -0.0215
        ],
        [
          0.164,
          -0.037,
          0.0895,
          -0.1235,
          -0.137,
          0.1325,
          1.0,
          0.0319,
          -0.0372,
          -0.0277
        ],
        [
          0.0362,
          0.0732,
          -0.3532,
          -0.091,
          -0.0638,
          0.0274,
          0.0319,
          1.0,
          -0.1389,
          -0.0424
        ],
        [
          -0.066,
          0.389,
          0.0266,
          0.159,
          0.1192,
          -0.0591,
          -0.0372,
          -0.1389,
          1.0,
          -0.0012
        ],
        [
          -0.0186,
          0.0113,
          -0.0105,
          0.0167,
          0.0196,
          -0.0215,
          -0.0277,
          -0.0424,
          -0.0012,
          1.0
        ]
      ],
      "max_abs_rel_gap_change": 0.867194
    },
    {
      "status": "ok",
      "replicate": 11,
      "k": 10,
      "n_coalitions": 1024,
      "n_answered": 19006,
      "n_declined": 1655,
      "top_driver_int": "aps_motor",
      "top_driver_cond": "aps_motor",
      "spearman_abs_gap_int_vs_cond": 0.466667,
      "max_abs_offdiag_corr_train": 0.802664,
      "max_abs_offdiag_corr_pair": [
        "aps_motor",
        "aps_eyes"
      ],
      "corr_train": [
        [
          1.0,
          -0.0885,
          -0.3304,
          -0.4823,
          0.0598,
          0.8027,
          0.0491,
          0.1736,
          -0.0604,
          -0.0342
        ],
        [
          -0.0885,
          1.0,
          0.193,
          0.1459,
          -0.2433,
          -0.0744,
          0.086,
          -0.0516,
          0.3939,
          0.0187
        ],
        [
          -0.3304,
          0.193,
          1.0,
          0.7006,
          -0.0244,
          -0.3574,
          -0.0913,
          -0.1235,
          0.1706,
          0.0189
        ],
        [
          -0.4823,
          0.1459,
          0.7006,
          1.0,
          -0.0294,
          -0.5189,
          -0.0626,
          -0.1421,
          0.124,
          0.0085
        ],
        [
          0.0598,
          -0.2433,
          -0.0244,
          -0.0294,
          1.0,
          0.0392,
          -0.3551,
          0.1185,
          0.0159,
          -0.0819
        ],
        [
          0.8027,
          -0.0744,
          -0.3574,
          -0.5189,
          0.0392,
          1.0,
          0.042,
          0.1431,
          -0.0559,
          -0.037
        ],
        [
          0.0491,
          0.086,
          -0.0913,
          -0.0626,
          -0.3551,
          0.042,
          1.0,
          0.0137,
          -0.1277,
          -0.0225
        ],
        [
          0.1736,
          -0.0516,
          -0.1235,
          -0.1421,
          0.1185,
          0.1431,
          0.0137,
          1.0,
          -0.0505,
          -0.0803
        ],
        [
          -0.0604,
          0.3939,
          0.1706,
          0.124,
          0.0159,
          -0.0559,
          -0.1277,
          -0.0505,
          1.0,
          -0.0226
        ],
        [
          -0.0342,
          0.0187,
          0.0189,
          0.0085,
          -0.0819,
          -0.037,
          -0.0225,
          -0.0803,
          -0.0226,
          1.0
        ]
      ],
      "max_abs_rel_gap_change": 0.741026
    },
    {
      "status": "ok",
      "replicate": 12,
      "k": 10,
      "n_coalitions": 1024,
      "n_answered": 15127,
      "n_declined": 2504,
      "top_driver_int": "aps_motor",
      "top_driver_cond": "aps_motor",
      "spearman_abs_gap_int_vs_cond": 0.50303,
      "max_abs_offdiag_corr_train": 0.852564,
      "max_abs_offdiag_corr_pair": [
        "apv_oobintubday1",
        "apv_oobventday1"
      ],
      "corr_train": [
        [
          1.0,
          -0.1048,
          -0.3323,
          0.0597,
          0.8104,
          -0.4908,
          -0.4229,
          0.1753,
          -0.0561,
          -0.0382
        ],
        [
          -0.1048,
          1.0,
          0.2064,
          -0.2272,
          -0.0887,
          0.1563,
          0.1071,
          -0.0449,
          0.403,
          0.0152
        ],
        [
          -0.3323,
          0.2064,
          1.0,
          0.0035,
          -0.3555,
          0.6573,
          0.5604,
          -0.1142,
          0.1594,
          0.0253
        ],
        [
          0.0597,
          -0.2272,
          0.0035,
          1.0,
          0.0387,
          -0.0106,
          -0.0146,
          0.0908,
          0.0412,
          -0.0792
        ],
        [
          0.8104,
          -0.0887,
          -0.3555,
          0.0387,
          1.0,
          -0.5342,
          -0.4662,
          0.142,
          -0.0499,
          -0.0402
        ],
        [
          -0.4908,
          0.1563,
          0.6573,
          -0.0106,
          -0.5342,
          1.0,
          0.8526,
          -0.1379,
          0.1122,
          0.0219
        ],
        [
          -0.4229,
          0.1071,
          0.5604,
          -0.0146,
          -0.4662,
          0.8526,
          1.0,
          -0.125,
          0.0635,
          0.0509
        ],
        [
          0.1753,
          -0.0449,
          -0.1142,
          0.0908,
          0.142,
          -0.1379,
          -0.125,
          1.0,
          -0.0311,
          -0.0814
        ],
        [
          -0.0561,
          0.403,
          0.1594,
          0.0412,
          -0.0499,
          0.1122,
          0.0635,
          -0.0311,
          1.0,
          -0.0257
        ],
        [
          -0.0382,
          0.0152,
          0.0253,
          -0.0792,
          -0.0402,
          0.0219,
          0.0509,
          -0.0814,
          -0.0257,
          1.0
        ]
      ],
      "max_abs_rel_gap_change": 0.668424
    },
    {
      "status": "ok",
      "replicate": 13,
      "k": 10,
      "n_coalitions": 1024,
      "n_answered": 24812,
      "n_declined": 2209,
      "top_driver_int": "aps_motor",
      "top_driver_cond": "aps_motor",
      "spearman_abs_gap_int_vs_cond": 0.842424,
      "max_abs_offdiag_corr_train": 0.790601,
      "max_abs_offdiag_corr_pair": [
        "aps_motor",
        "aps_eyes"
      ],
      "corr_train": [
        [
          1.0,
          -0.4707,
          0.7906,
          0.1844,
          -0.1335,
          0.0694,
          -0.367,
          0.0527,
          0.0472,
          0.0013
        ],
        [
          -0.4707,
          1.0,
          -0.516,
          -0.1413,
          0.1523,
          -0.0219,
          0.7138,
          -0.0946,
          -0.053,
          -0.024
        ],
        [
          0.7906,
          -0.516,
          1.0,
          0.1448,
          -0.1109,
          0.0539,
          -0.3929,
          0.0482,
          0.0303,
          0.0019
        ],
        [
          0.1844,
          -0.1413,
          0.1448,
          1.0,
          -0.042,
          0.1053,
          -0.1197,
          0.0415,
          0.0309,
          0.0001
        ],
        [
          -0.1335,
          0.1523,
          -0.1109,
          -0.042,
          1.0,
          -0.2362,
          0.1949,
          -0.0553,
          0.0862,
          -0.0003
        ],
        [
          0.0694,
          -0.0219,
          0.0539,
          0.1053,
          -0.2362,
          1.0,
          -0.015,
          0.0443,
          -0.3748,
          -0.0008
        ],
        [
          -0.367,
          0.7138,
          -0.3929,
          -0.1197,
          0.1949,
          -0.015,
          1.0,
          -0.0925,
          -0.076,
          -0.0208
        ],
        [
          0.0527,
          -0.0946,
          0.0482,
          0.0415,
          -0.0553,
          0.0443,
          -0.0925,
          1.0,
          0.0525,
          0.0004
        ],
        [
          0.0472,
          -0.053,
          0.0303,
          0.0309,
          0.0862,
          -0.3748,
          -0.076,
          0.0525,
          1.0,
          0.0004
        ],
        [
          0.0013,
          -0.024,
          0.0019,
          0.0001,
          -0.0003,
          -0.0008,
          -0.0208,
          0.0004,
          0.0004,
          1.0
        ]
      ],
      "max_abs_rel_gap_change": 0.621961
    },
    {
      "status": "ok",
      "replicate": 14,
      "k": 10,
      "n_coalitions": 1024,
      "n_answered": 14150,
      "n_declined": 1233,
      "top_driver_int": "aps_motor",
      "top_driver_cond": "aps_motor",
      "spearman_abs_gap_int_vs_cond": 0.757576,
      "max_abs_offdiag_corr_train": 0.867185,
      "max_abs_offdiag_corr_pair": [
        "apv_oobventday1",
        "apv_oobintubday1"
      ],
      "corr_train": [
        [
          1.0,
          -0.1151,
          -0.4848,
          0.163,
          0.7937,
          0.0753,
          -0.4266,
          -0.0469,
          -0.353,
          -0.0616
        ],
        [
          -0.1151,
          1.0,
          0.1489,
          -0.0384,
          -0.0948,
          -0.2401,
          0.1048,
          0.0162,
          0.192,
          0.4083
        ],
        [
          -0.4848,
          0.1489,
          1.0,
          -0.1335,
          -0.5364,
          -0.0099,
          0.8672,
          0.0196,
          0.6872,
          0.1114
        ],
        [
          0.163,
          -0.0384,
          -0.1335,
          1.0,
          0.135,
          0.0961,
          -0.1248,
          -0.086,
          -0.1145,
          -0.0446
        ],
        [
          0.7937,
          -0.0948,
          -0.5364,
          0.135,
          1.0,
          0.0482,
          -0.4791,
          -0.0444,
          -0.384,
          -0.0521
        ],
        [
          0.0753,
          -0.2401,
          -0.0099,
          0.0961,
          0.0482,
          1.0,
          -0.0159,
          -0.0809,
          -0.0005,
          0.0596
        ],
        [
          -0.4266,
          0.1048,
          0.8672,
          -0.1248,
          -0.4791,
          -0.0159,
          1.0,
          0.051,
          0.596,
          0.0638
        ],
        [
          -0.0469,
          0.0162,
          0.0196,
          -0.086,
          -0.0444,
          -0.0809,
          0.051,
          1.0,
          0.0368,
          -0.0351
        ],
        [
          -0.353,
          0.192,
          0.6872,
          -0.1145,
          -0.384,
          -0.0005,
          0.596,
          0.0368,
          1.0,
          0.1531
        ],
        [
          -0.0616,
          0.4083,
          0.1114,
          -0.0446,
          -0.0521,
          0.0596,
          0.0638,
          -0.0351,
          0.1531,
          1.0
        ]
      ],
      "max_abs_rel_gap_change": 1.139972
    },
    {
      "status": "ok",
      "replicate": 15,
      "k": 10,
      "n_coalitions": 1024,
      "n_answered": 15758,
      "n_declined": 2595,
      "top_driver_int": "aps_motor",
      "top_driver_cond": "aps_motor",
      "spearman_abs_gap_int_vs_cond": 0.357576,
      "max_abs_offdiag_corr_train": 0.835501,
      "max_abs_offdiag_corr_pair": [
        "apv_oobintubday1",
        "apv_oobventday1"
      ],
      "corr_train": [
        [
          1.0,
          -0.1106,
          -0.38,
          0.0677,
          -0.4795,
          -0.4094,
          0.1846,
          0.0436,
          0.7964,
          -0.05
        ],
        [
          -0.1106,
          1.0,
          0.2033,
          -0.2308,
          0.1637,
          0.106,
          -0.0425,
          0.0654,
          -0.085,
          0.4355
        ],
        [
          -0.38,
          0.2033,
          1.0,
          0.0123,
          0.7441,
          0.6217,
          -0.1083,
          -0.0922,
          -0.4134,
          0.1617
        ],
        [
          0.0677,
          -0.2308,
          0.0123,
          1.0,
          -0.0024,
          -0.0167,
          0.091,
          -0.3729,
          0.0367,
          0.026
        ],
        [
          -0.4795,
          0.1637,
          0.7441,
          -0.0024,
          1.0,
          0.8355,
          -0.1218,
          -0.0672,
          -0.5135,
          0.1251
        ],
        [
          -0.4094,
          0.106,
          0.6217,
          -0.0167,
          0.8355,
          1.0,
          -0.1159,
          0.0377,
          -0.4488,
          0.0665
        ],
        [
          0.1846,
          -0.0425,
          -0.1083,
          0.091,
          -0.1218,
          -0.1159,
          1.0,
          0.0219,
          0.1506,
          -0.0378
        ],
        [
          0.0436,
          0.0654,
          -0.0922,
          -0.3729,
          -0.0672,
          0.0377,
          0.0219,
          1.0,
          0.0324,
          -0.1329
        ],
        [
          0.7964,
          -0.085,
          -0.4134,
          0.0367,
          -0.5135,
          -0.4488,
          0.1506,
          0.0324,
          1.0,
          -0.0381
        ],
        [
          -0.05,
          0.4355,
          0.1617,
          0.026,
          0.1251,
          0.0665,
          -0.0378,
          -0.1329,
          -0.0381,
          1.0
        ]
      ],
      "max_abs_rel_gap_change": 1.119914
    },
    {
      "status": "ok",
      "replicate": 16,
      "k": 10,
      "n_coalitions": 1024,
      "n_answered": 14705,
      "n_declined": 1582,
      "top_driver_int": "aps_motor",
      "top_driver_cond": "aps_motor",
      "spearman_abs_gap_int_vs_cond": 0.745455,
      "max_abs_offdiag_corr_train": 0.802981,
      "max_abs_offdiag_corr_pair": [
        "aps_eyes",
        "aps_motor"
      ],
      "corr_train": [
        [
          1.0,
          -0.4587,
          0.803,
          -0.1122,
          0.1811,
          -0.3472,
          0.0612,
          0.0004,
          0.008,
          0.0599
        ],
        [
          -0.4587,
          1.0,
          -0.4925,
          0.1749,
          -0.1481,
          0.7252,
          -0.0293,
          -0.0259,
          0.0635,
          -0.0833
        ],
        [
          0.803,
          -0.4925,
          1.0,
          -0.0934,
          0.1397,
          -0.3739,
          0.0452,
          0.0028,
          -0.0009,
          0.0603
        ],
        [
          -0.1122,
          0.1749,
          -0.0934,
          1.0,
          -0.0491,
          0.2227,
          -0.2251,
          -0.0002,
          0.0355,
          -0.0388
        ],
        [
          0.1811,
          -0.1481,
          0.1397,
          -0.0491,
          1.0,
          -0.129,
          0.1075,
          0.001,
          0.0102,
          0.0367
        ],
        [
          -0.3472,
          0.7252,
          -0.3739,
          0.2227,
          -0.129,
          1.0,
          -0.0275,
          -0.0253,
          0.0677,
          -0.072
        ],
        [
          0.0612,
          -0.0293,
          0.0452,
          -0.2251,
          0.1075,
          -0.0275,
          1.0,
          -0.0009,
          0.0089,
          0.0593
        ],
        [
          0.0004,
          -0.0259,
          0.0028,
          -0.0002,
          0.001,
          -0.0253,
          -0.0009,
          1.0,
          -0.0063,
          0.0004
        ],
        [
          0.008,
          0.0635,
          -0.0009,
          0.0355,
          0.0102,
          0.0677,
          0.0089,
          -0.0063,
          1.0,
          -0.0973
        ],
        [
          0.0599,
          -0.0833,
          0.0603,
          -0.0388,
          0.0367,
          -0.072,
          0.0593,
          0.0004,
          -0.0973,
          1.0
        ]
      ],
      "max_abs_rel_gap_change": 0.667055
    },
    {
      "status": "ok",
      "replicate": 17,
      "k": 10,
      "n_coalitions": 1024,
      "n_answered": 18536,
      "n_declined": 1580,
      "top_driver_int": "aps_motor",
      "top_driver_cond": "aps_motor",
      "spearman_abs_gap_int_vs_cond": 0.539394,
      "max_abs_offdiag_corr_train": 0.854817,
      "max_abs_offdiag_corr_pair": [
        "apv_oobintubday1",
        "apv_oobventday1"
      ],
      "corr_train": [
        [
          1.0,
          -0.4281,
          0.1926,
          -0.1135,
          -0.3253,
          0.7864,
          0.0691,
          0.0871,
          -0.0001,
          -0.3697
        ],
        [
          -0.4281,
          1.0,
          -0.124,
          0.2016,
          0.7412,
          -0.4657,
          -0.0769,
          -0.0075,
          -0.027,
          0.8548
        ],
        [
          0.1926,
          -0.124,
          1.0,
          -0.0443,
          -0.105,
          0.1505,
          0.0249,
          0.1016,
          0.001,
          -0.1138
        ],
        [
          -0.1135,
          0.2016,
          -0.0443,
          1.0,
          0.2502,
          -0.0923,
          -0.0444,
          -0.207,
          -0.0,
          0.1484
        ],
        [
          -0.3253,
          0.7412,
          -0.105,
          0.2502,
          1.0,
          -0.3489,
          -0.0632,
          0.0085,
          -0.0247,
          0.6336
        ],
        [
          0.7864,
          -0.4657,
          0.1505,
          -0.0923,
          -0.3489,
          1.0,
          0.0709,
          0.0665,
          0.0018,
          -0.4099
        ],
        [
          0.0691,
          -0.0769,
          0.0249,
          -0.0444,
          -0.0632,
          0.0709,
          1.0,
          0.0575,
          0.0011,
          -0.0708
        ],
        [
          0.0871,
          -0.0075,
          0.1016,
          -0.207,
          0.0085,
          0.0665,
          0.0575,
          1.0,
          -0.002,
          -0.0164
        ],
        [
          -0.0001,
          -0.027,
          0.001,
          -0.0,
          -0.0247,
          0.0018,
          0.0011,
          -0.002,
          1.0,
          -0.0323
        ],
        [
          -0.3697,
          0.8548,
          -0.1138,
          0.1484,
          0.6336,
          -0.4099,
          -0.0708,
          -0.0164,
          -0.0323,
          1.0
        ]
      ],
      "max_abs_rel_gap_change": 1.084574
    },
    {
      "status": "ok",
      "replicate": 18,
      "k": 10,
      "n_coalitions": 1024,
      "n_answered": 18062,
      "n_declined": 1885,
      "top_driver_int": "aps_motor",
      "top_driver_cond": "aps_motor",
      "spearman_abs_gap_int_vs_cond": 0.515152,
      "max_abs_offdiag_corr_train": 0.852532,
      "max_abs_offdiag_corr_pair": [
        "apv_oobintubday1",
        "apv_oobventday1"
      ],
      "corr_train": [
        [
          1.0,
          -0.115,
          -0.4773,
          -0.3538,
          0.1758,
          0.0784,
          0.7946,
          -0.4129,
          -0.0435,
          -0.0669
        ],
        [
          -0.115,
          1.0,
          0.1401,
          0.1692,
          -0.0628,
          -0.2309,
          -0.0907,
          0.0929,
          0.0228,
          0.3954
        ],
        [
          -0.4773,
          0.1401,
          1.0,
          0.7378,
          -0.1401,
          -0.0174,
          -0.517,
          0.8525,
          0.0029,
          0.1174
        ],
        [
          -0.3538,
          0.1692,
          0.7378,
          1.0,
          -0.1395,
          -0.0054,
          -0.3865,
          0.629,
          0.0223,
          0.1494
        ],
        [
          0.1758,
          -0.0628,
          -0.1401,
          -0.1395,
          1.0,
          0.1166,
          0.1382,
          -0.1309,
          -0.0887,
          -0.046
        ],
        [
          0.0784,
          -0.2309,
          -0.0174,
          -0.0054,
          0.1166,
          1.0,
          0.05,
          -0.0195,
          -0.0926,
          0.0428
        ],
        [
          0.7946,
          -0.0907,
          -0.517,
          -0.3865,
          0.1382,
          0.05,
          1.0,
          -0.4541,
          -0.0411,
          -0.0543
        ],
        [
          -0.4129,
          0.0929,
          0.8525,
          0.629,
          -0.1309,
          -0.0195,
          -0.4541,
          1.0,
          0.0361,
          0.0629
        ],
        [
          -0.0435,
          0.0228,
          0.0029,
          0.0223,
          -0.0887,
          -0.0926,
          -0.0411,
          0.0361,
          1.0,
          -0.0201
        ],
        [
          -0.0669,
          0.3954,
          0.1174,
          0.1494,
          -0.046,
          0.0428,
          -0.0543,
          0.0629,
          -0.0201,
          1.0
        ]
      ],
      "max_abs_rel_gap_change": 0.922355
    },
    {
      "status": "ok",
      "replicate": 19,
      "k": 10,
      "n_coalitions": 1024,
      "n_answered": 20509,
      "n_declined": 1646,
      "top_driver_int": "aps_motor",
      "top_driver_cond": "aps_motor",
      "spearman_abs_gap_int_vs_cond": 0.866667,
      "max_abs_offdiag_corr_train": 0.856457,
      "max_abs_offdiag_corr_pair": [
        "apv_oobintubday1",
        "apv_oobventday1"
      ],
      "corr_train": [
        [
          1.0,
          0.1971,
          0.7893,
          0.0773,
          -0.1196,
          -0.4522,
          0.0849,
          -0.3646,
          -0.3919,
          0.0115
        ],
        [
          0.1971,
          1.0,
          0.1513,
          0.0506,
          -0.0559,
          -0.1347,
          0.1049,
          -0.136,
          -0.1218,
          0.0033
        ],
        [
          0.7893,
          0.1513,
          1.0,
          0.0759,
          -0.0942,
          -0.5017,
          0.0606,
          -0.3967,
          -0.4415,
          0.0131
        ],
        [
          0.0773,
          0.0506,
          0.0759,
          1.0,
          -0.0463,
          -0.0975,
          0.0689,
          -0.0809,
          -0.0876,
          -0.0057
        ],
        [
          -0.1196,
          -0.0559,
          -0.0942,
          -0.0463,
          1.0,
          0.1658,
          -0.2171,
          0.2017,
          0.1167,
          0.0035
        ],
        [
          -0.4522,
          -0.1347,
          -0.5017,
          -0.0975,
          0.1658,
          1.0,
          -0.0121,
          0.7546,
          0.8565,
          -0.0064
        ],
        [
          0.0849,
          0.1049,
          0.0606,
          0.0689,
          -0.2171,
          -0.0121,
          1.0,
          -0.0009,
          -0.0146,
          -0.0012
        ],
        [
          -0.3646,
          -0.136,
          -0.3967,
          -0.0809,
          0.2017,
          0.7546,
          -0.0009,
          1.0,
          0.6463,
          -0.0052
        ],
        [
          -0.3919,
          -0.1218,
          -0.4415,
          -0.0876,
          0.1167,
          0.8565,
          -0.0146,
          0.6463,
          1.0,
          -0.012
        ],
        [
          0.0115,
          0.0033,
          0.0131,
          -0.0057,
          0.0035,
          -0.0064,
          -0.0012,
          -0.0052,
          -0.012,
          1.0
        ]
      ],
      "max_abs_rel_gap_change": 0.825459
    }
  ],
  "n_replicates_ok": 20,
  "features": {
    "aps_albumin": {
      "n_replicates": 9,
      "coef_mean": -0.192476,
      "gap_int_mean": -0.083015,
      "gap_cond_mean": -0.090915,
      "rank_int_median": 7.0,
      "rank_cond_median": 7.0,
      "n_top1_int": 0,
      "n_top1_cond": 0
    },
    "aps_bilirubin": {
      "n_replicates": 1,
      "coef_mean": 0.149615,
      "gap_int_mean": -0.06562,
      "gap_cond_mean": -0.072256,
      "rank_int_median": 10.0,
      "rank_cond_median": 6.0,
      "n_top1_int": 0,
      "n_top1_cond": 0
    },
    "aps_bun": {
      "n_replicates": 7,
      "coef_mean": 0.191813,
      "gap_int_mean": -0.0661,
      "gap_cond_mean": -0.075545,
      "rank_int_median": 9.0,
      "rank_cond_median": 7.0,
      "n_top1_int": 0,
      "n_top1_cond": 0
    },
    "aps_eyes": {
      "n_replicates": 19,
      "coef_mean": -0.121718,
      "gap_int_mean": -0.100227,
      "gap_cond_mean": -0.172748,
      "rank_int_median": 6.0,
      "rank_cond_median": 2.0,
      "n_top1_int": 0,
      "n_top1_cond": 0
    },
    "aps_fio2": {
      "n_replicates": 20,
      "coef_mean": 0.179531,
      "gap_int_mean": -0.131605,
      "gap_cond_mean": -0.128956,
      "rank_int_median": 2.5,
      "rank_cond_median": 4.0,
      "n_top1_int": 0,
      "n_top1_cond": 0
    },
    "aps_heartrate": {
      "n_replicates": 1,
      "coef_mean": 0.232944,
      "gap_int_mean": -0.052389,
      "gap_cond_mean": -0.04584,
      "rank_int_median": 9.0,
      "rank_cond_median": 8.0,
      "n_top1_int": 0,
      "n_top1_cond": 0
    },
    "aps_heartrate__missing": {
      "n_replicates": 6,
      "coef_mean": -0.325741,
      "gap_int_mean": 0.084858,
      "gap_cond_mean": 0.067577,
      "rank_int_median": 8.5,
      "rank_cond_median": 8.0,
      "n_top1_int": 0,
      "n_top1_cond": 0
    },
    "aps_intubated": {
      "n_replicates": 19,
      "coef_mean": -0.188009,
      "gap_int_mean": -0.106899,
      "gap_cond_mean": -0.034893,
      "rank_int_median": 4.0,
      "rank_cond_median": 10.0,
      "n_top1_int": 0,
      "n_top1_cond": 0
    },
    "aps_meanbp__missing": {
      "n_replicates": 1,
      "coef_mean": 0.225948,
      "gap_int_mean": 0.072888,
      "gap_cond_mean": 0.023828,
      "rank_int_median": 5.0,
      "rank_cond_median": 10.0,
      "n_top1_int": 0,
      "n_top1_cond": 0
    },
    "aps_motor": {
      "n_replicates": 20,
      "coef_mean": -0.310011,
      "gap_int_mean": -0.313155,
      "gap_cond_mean": -0.315008,
      "rank_int_median": 1.0,
      "rank_cond_median": 1.0,
      "n_top1_int": 20,
      "n_top1_cond": 20
    },
    "aps_pao2": {
      "n_replicates": 9,
      "coef_mean": -0.091919,
      "gap_int_mean": -0.064328,
      "gap_cond_mean": -0.038101,
      "rank_int_median": 10.0,
      "rank_cond_median": 9.0,
      "n_top1_int": 0,
      "n_top1_cond": 0
    },
    "aps_pco2": {
      "n_replicates": 9,
      "coef_mean": -0.112821,
      "gap_int_mean": -0.070942,
      "gap_cond_mean": -0.047511,
      "rank_int_median": 8.0,
      "rank_cond_median": 9.0,
      "n_top1_int": 0,
      "n_top1_cond": 0
    },
    "aps_ph": {
      "n_replicates": 20,
      "coef_mean": -0.141234,
      "gap_int_mean": -0.100098,
      "gap_cond_mean": -0.123093,
      "rank_int_median": 6.0,
      "rank_cond_median": 4.0,
      "n_top1_int": 0,
      "n_top1_cond": 0
    },
    "aps_temperature": {
      "n_replicates": 20,
      "coef_mean": -0.195256,
      "gap_int_mean": -0.098129,
      "gap_cond_mean": -0.117533,
      "rank_int_median": 6.5,
      "rank_cond_median": 5.0,
      "n_top1_int": 0,
      "n_top1_cond": 0
    },
    "aps_verbal": {
      "n_replicates": 1,
      "coef_mean": -0.087367,
      "gap_int_mean": -0.066426,
      "gap_cond_mean": -0.092946,
      "rank_int_median": 8.0,
      "rank_cond_median": 7.0,
      "n_top1_int": 0,
      "n_top1_cond": 0
    },
    "apv_electivesurgery__missing": {
      "n_replicates": 1,
      "coef_mean": 0.237135,
      "gap_int_mean": 0.056138,
      "gap_cond_mean": 0.038826,
      "rank_int_median": 10.0,
      "rank_cond_median": 10.0,
      "n_top1_int": 0,
      "n_top1_cond": 0
    },
    "apv_oobintubday1": {
      "n_replicates": 20,
      "coef_mean": 0.200522,
      "gap_int_mean": -0.120279,
      "gap_cond_mean": -0.097485,
      "rank_int_median": 3.5,
      "rank_cond_median": 6.0,
      "n_top1_int": 0,
      "n_top1_cond": 0
    },
    "apv_oobventday1": {
      "n_replicates": 11,
      "coef_mean": 0.16491,
      "gap_int_mean": -0.075281,
      "gap_cond_mean": -0.051671,
      "rank_int_median": 9.0,
      "rank_cond_median": 8.0,
      "n_top1_int": 0,
      "n_top1_cond": 0
    },
    "hospitaladmitsource=PACU": {
      "n_replicates": 1,
      "coef_mean": -0.222476,
      "gap_int_mean": 0.057789,
      "gap_cond_mean": 0.061529,
      "rank_int_median": 10.0,
      "rank_cond_median": 8.0,
      "n_top1_int": 0,
      "n_top1_cond": 0
    },
    "pre_icu_hours": {
      "n_replicates": 2,
      "coef_mean": 0.137429,
      "gap_int_mean": -0.062948,
      "gap_cond_mean": -0.069187,
      "rank_int_median": 9.0,
      "rank_cond_median": 7.5,
      "n_top1_int": 0,
      "n_top1_cond": 0
    },
    "unitstaytype=stepdown/other": {
      "n_replicates": 3,
      "coef_mean": -0.209965,
      "gap_int_mean": 0.101895,
      "gap_cond_mean": 0.100881,
      "rank_int_median": 4.0,
      "rank_cond_median": 8.0,
      "n_top1_int": 0,
      "n_top1_cond": 0
    }
  },
  "max_abs_diff_vs_abstention_ranking": 0.0,
  "n_cross_checked": 200
}
```
