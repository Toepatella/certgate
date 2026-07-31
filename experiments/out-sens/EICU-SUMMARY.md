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
    "utc": "2026-07-31T07:37:39+00:00",
    "replicates": 20,
    "arm": "apache-complete",
    "data_sha": "3744bf912e9196b44123a8d13c52faeb1a55e45a705250511c536ce7739ac26d"
  },
  "arm": "apache-complete",
  "replicates": 20,
  "n_records": 135127,
  "n_sites": 190,
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
      "certify_rate": 0.95,
      "n_certified": 19,
      "n_replicates": 20,
      "mean_tau": 0.8542,
      "mean_coverage": 0.8376,
      "mean_rm_fresh": 0.0374,
      "rm_exceed_rate": 0.0,
      "hard_violation_rate_diag": 0.0,
      "mean_per_site_exceed_frac": 0.0285,
      "deploy_modes": [
        "baseline"
      ],
      "mode_non_contribution": {
        "bbse:failsafe": 19,
        "baseline:failsafe|bbse:failsafe": 1
      }
    }
  },
  "failure_criteria": {
    "F-A": {
      "fired": false,
      "n_replicates": 20,
      "n_certified_replicates": 19,
      "n_rm_exceed": 0,
      "rm_exceed_rate": 0.0,
      "target": 0.05,
      "note": "BOUND-SHAPED OBSERVATION, never 'validity confirmed': 20 replicates cannot resolve a delta=0.05 rate, and the replicates share ONE hospital population, so they are not independent draws of the calibration site population."
    },
    "F-B": {
      "fired": false,
      "n_certified_replicates": 19,
      "mean_operative_coverage": 0.8376,
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
          "max_head_auc_oos": 0.870007,
          "what": "the head's OWN out-of-sample AUC on the site-disjoint calibration split. APACHE-IVa, a purpose-built day-1 score, reaches ~0.87 on this outcome; a 161-column logistic head that beats the ceiling FROM THE SAME INPUTS is a leak before it is a result."
        },
        "missingness_ablation": {
          "fired": false,
          "n_hits": 0,
          "max_drop": 0.05,
          "observed_max_drop": 0.003123,
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
    "utc": "2026-07-31T07:37:39+00:00",
    "replicates": 20,
    "arm": "apache-complete",
    "data_sha": "3744bf912e9196b44123a8d13c52faeb1a55e45a705250511c536ce7739ac26d"
  },
  "arm": "apache-complete",
  "n_pools": 480,
  "n_pool_too_small": 25,
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
      "n_certified": 431,
      "certify_rate": 0.8979,
      "mean_coverage": 0.8353,
      "answered_err": {
        "n": 431,
        "mean": 0.039702,
        "sd": 0.028096,
        "p10": 0.0141,
        "p50": 0.0348,
        "p90": 0.0662,
        "min": 0.0,
        "max": 0.2857
      },
      "hard_violation_rate_diag": 0.0046,
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
    "utc": "2026-07-31T07:37:39+00:00",
    "replicates": 20,
    "arm": "apache-complete",
    "data_sha": "3744bf912e9196b44123a8d13c52faeb1a55e45a705250511c536ce7739ac26d"
  },
  "arm": "apache-complete",
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
      "n_certified_replicates": 19,
      "mean_certgate_answered_err": 0.0384,
      "mean_certgate_answered_err_on_apache_subset": 0.0384,
      "mean_apache_iva_brier": 0.0368,
      "mean_apache_iva_auc": 0.806,
      "apache_available_share": 1.0,
      "note": "the APACHE-IVa columns are scored on the answered records that CARRY a comparator value; that coverage is site-correlated, so the subset-matched CertGate error is reported beside them rather than compared across different denominators."
    }
  }
}
```
