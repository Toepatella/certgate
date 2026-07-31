# CertGate eICU-CRD v2.0 -- real-data summary

- mode: FULL (per-block stamps are authoritative; preserved sections are marked)
- seed: 20260721
- alpha ladder: (0.05, 0.1), delta: 0.05
- estimand: site-population average, NOT a per-hospital guarantee (audit V1)
- the extract itself is NOT redistributable; every artifact here is aggregate-only (PhysioNet DUA 1.5.0)

## EICU-PREFLIGHT (preserved from an earlier run)
```json
{
  "_run": {
    "mode": "PREFLIGHT",
    "utc": "2026-07-31T07:13:52+00:00",
    "replicates": 0,
    "arm": null,
    "data_sha": "3744bf912e9196b44123a8d13c52faeb1a55e45a705250511c536ce7739ac26d"
  },
  "data_dir_basename": "eicu-extract",
  "tables": {
    "patient": {
      "rows": 200859,
      "reference_rows": 200859,
      "rows_match_reference": true,
      "header_case_as_read": "lower"
    },
    "hospital": {
      "rows": 208,
      "reference_rows": 208,
      "rows_match_reference": true,
      "header_case_as_read": "lower"
    },
    "apacheApsVar": {
      "rows": 171177,
      "reference_rows": 171177,
      "rows_match_reference": true,
      "header_case_as_read": "lower"
    },
    "apachePredVar": {
      "rows": 171177,
      "reference_rows": 171177,
      "rows_match_reference": true,
      "header_case_as_read": "lower"
    },
    "apachePatientResult": {
      "rows": 297064,
      "reference_rows": 297064,
      "rows_match_reference": true,
      "header_case_as_read": "lower"
    }
  },
  "n_hospitals": 208,
  "n_uniquepid": 139367,
  "n_healthsystemstays": 164322,
  "attrition": [
    {
      "step": "raw-unit-stays",
      "n_stays": 200859,
      "n_sites": 208,
      "n_positive": 18004,
      "prevalence": 0.08963501759941053
    },
    {
      "step": "site-parseable",
      "n_stays": 200859,
      "n_sites": 208,
      "n_positive": 18004,
      "prevalence": 0.08963501759941053
    },
    {
      "step": "outcome-known",
      "n_stays": 199108,
      "n_sites": 207,
      "n_positive": 18004,
      "prevalence": 0.09042328786387287
    },
    {
      "step": "adult",
      "n_stays": 198490,
      "n_sites": 207,
      "n_positive": 17982,
      "prevalence": 0.09059398458360622
    },
    {
      "step": "first-stay",
      "n_stays": 164322,
      "n_sites": 207,
      "n_positive": 14603,
      "prevalence": 0.08886819780674529
    },
    {
      "step": "primary-cohort",
      "n_stays": 164322,
      "n_sites": 207,
      "n_positive": 14603,
      "prevalence": 0.08886819780674529
    },
    {
      "step": "apache-aps-linked",
      "n_stays": 157403,
      "n_sites": 207,
      "n_positive": 14285,
      "prevalence": 0.09075430582644549
    },
    {
      "step": "apache-result-linked",
      "n_stays": 138496,
      "n_sites": 190,
      "n_positive": 12270,
      "prevalence": 0.08859461645101664
    },
    {
      "step": "apache-complete-arm",
      "n_stays": 135127,
      "n_sites": 190,
      "n_positive": 11959,
      "prevalence": 0.08850192781605452
    }
  ],
  "site_selection": {
    "n_sites_primary_cohort": 207,
    "n_sites_apache_result_linked": 190,
    "note": "apache-result-linked vs primary-cohort is the headline site-selection statistic (threat T-4): restricting to APACHE-covered stays MOVES the site population the certificate's site-population-average estimand refers to. The primary arm never applies it."
  },
  "categorical_drift": {
    "gender": {
      "other_share": 0.0,
      "exceeds_cap": false
    },
    "ethnicity": {
      "other_share": 0.0,
      "exceeds_cap": false
    },
    "hospitaladmitsource": {
      "other_share": 0.0,
      "exceeds_cap": false
    },
    "unitadmitsource": {
      "other_share": 0.0,
      "exceeds_cap": false
    },
    "unittype": {
      "other_share": 0.0,
      "exceeds_cap": false
    },
    "unitstaytype": {
      "other_share": 0.0,
      "exceeds_cap": false
    }
  },
  "cross_site_patients": {
    "n_uniquepid": 137773,
    "n_uniquepid_multi_hospital": 3996,
    "share": 0.029004231598353813,
    "cap": 0.01
  },
  "reference_check": {
    "expect_reference": true,
    "ok": true,
    "mismatches": [],
    "split_projection": {
      "n_sites": 207,
      "n_target": 24,
      "rest": 183,
      "n_train": 73,
      "n_aux": 36,
      "n_cal": 74,
      "min_cal_clusters": 50,
      "cal_ok": true,
      "min_total_sites": 149,
      "total_sites_ok": true
    },
    "invalid_conditions": []
  },
  "sentinel_site_dispersion_reported": true,
  "warnings": [
    "[MEASURE] T-5: 3996 uniquepid (0.0290 > cap 0.01) appear at more than one hospitalid; assert_site_disjoint compares site LABELS only, so these are correlated records across splits. This is a LOWER bound (de-identification may split one person across several uniquepid) and is disclosed, never filtered -- a filter would itself be site-correlated",
    "[MEASURE] T-8: 148532 stays carry >1 apachePatientResult row (297,064 != 2 x 171,177 in the released extract); dedup is min(apachepatientresultsid) within (stay, version) with version preference ('IVa', 'IV'), counted in meta['dedup_counts'] -- a naive join would silently duplicate records and inflate the cluster sizes feeding the influence cap",
    "[MEASURE] T-4: 17 hospitals have ZERO apachePatientResult rows. The primary arm draws NO feature from that table: restricting to APACHE-covered stays would delete those hospitals and CHANGE THE SITE POPULATION the site-population-average estimand refers to (audit V1)",
    "[MEASURE] E-9: OUTCOME-informative missingness -- 2 indicator(s) show an absent:present outcome prevalence ratio over the cap 2.0; worst [('apv_ejectfx__missing', 4.333), ('apv_electivesurgery__missing', 2.6552)]. APACHE day-1 rows do not exist for a stay that ends because the patient died, so this channel is a LEAK, not the site channel T-3 describes, and prediction P4 being satisfied is its SIGNATURE rather than a confirmation",
    "[MEASURE] T-2/A6: apacheApsVar carries negative mass NOT at exactly -1.0 in {'urine': 1}, BELOW the 0.01 abort threshold: the cells map to missing and the run proceeds (amendment A6, POST-HOC). Inspect the column's support before trusting it",
    "[MEASURE] T-10/E-18: apacheApsVar.fio2 has 1670 of 39072 observed values outside BOTH frozen windows (0.0427); those become missing. The fio2 windows are lower-CLOSED so room air (0.21 / 21) is kept; a large residue here means a third unit convention, and the fix is a SPEC + constants diff, not a silent loss",
    "[MEASURE] T-10/E-18: apachePredVar.fio2 has 1670 of 39072 observed values outside BOTH frozen windows (0.0427); those become missing. The fio2 windows are lower-CLOSED so room air (0.21 / 21) is kept; a large residue here means a third unit convention, and the fix is a SPEC + constants diff, not a silent loss"
  ],
  "certifies_nothing": true
}
```

## EICU-PREDICTIONS (preserved from an earlier run)
```json
{
  "_run": {
    "mode": "PREFLIGHT",
    "utc": "2026-07-31T07:13:52+00:00",
    "replicates": 0,
    "arm": null,
    "data_sha": "3744bf912e9196b44123a8d13c52faeb1a55e45a705250511c536ce7739ac26d"
  },
  "registered_before_any_certificate": true,
  "predictions": [
    {
      "id": "P1",
      "prediction": "At 208 hospitals (75 calibration sites), alpha = 0.10 certifies on the pooled arm and alpha = 0.05 does not, in >= 15 of the 20 replicates. Basis: E4's synthetic frontier -- alpha=0.10 certifies from ~150 sites, alpha=0.05 first appears ~300 and is reliable only by 400.",
      "settled_by": "EICU_pooled.csv `certified` by `alpha`"
    },
    {
      "id": "P2",
      "prediction": "The per-site dispersion diagnostic on the pooled target pool at the deployed tau (_per_site_exceed_frac) is > 0.02 and lands in [0.05, 0.30] -- real hospitals are more heterogeneous than the synthetic generator at s_u = 0.5 (which gave 0.02) and closer to its s_u = 2.0 arm (0.10).",
      "settled_by": "EICU_pooled.csv `per_site_exceed_frac`"
    },
    {
      "id": "P3",
      "prediction": "BBSE contributes no certificate: it declines on >= 90% of the 25 pools per replicate, with bbse-misspecified or bbse-ill-conditioned the modal reason. Basis: E2's 200/200 declines, plus the coarse 2000-draw q_t tail widening the 16-corner box. Falsified if BBSE certifies a tau the baseline walk does not.",
      "settled_by": "`decline_reason` / `mode_outcomes` columns"
    },
    {
      "id": "P4",
      "prediction": "APACHE-absence features (aps_present, apv_present, or an aps_*__missing / apv_*__missing sibling) appear in the top 3 of the abstention gap_ranking on the pooled arm. Basis: absence is site-correlated by the dataset authors' own account.",
      "settled_by": "EICU_diagnostics.json `abstention_gap_ranking`"
    },
    {
      "id": "P5",
      "prediction": "The per-hospital arm returns pool-too-small for >= 1 and <= 6 of the 24 target hospitals (heavy-tailed hospital sizes; ~78% of hospitals have < 500 stays).",
      "settled_by": "EICU_per_site.csv `reason`"
    },
    {
      "id": "P6",
      "prediction": "Mean coverage at the operative rung on the pooled arm is in [0.60, 0.95].",
      "settled_by": "EICU_pooled.csv `coverage`"
    },
    {
      "id": "P7",
      "prediction": "Primary-cohort size lands in [130 000, 175 000] stays across 208 sites, and apache-result-linked retains <= 195 sites -- i.e. the APACHE-result restriction visibly deletes >= 13 hospitals.",
      "settled_by": "EICU_attrition.csv"
    }
  ]
}
```

## EICU-POOLED
```json
{
  "_run": {
    "mode": "FULL",
    "utc": "2026-07-31T07:27:13+00:00",
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
  "warnings": []
}
```

## EICU-PERSITE
```json
{
  "_run": {
    "mode": "FULL",
    "utc": "2026-07-31T07:27:13+00:00",
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
    "utc": "2026-07-31T07:27:13+00:00",
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
