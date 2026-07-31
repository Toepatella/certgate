# CertGate synthetic experiments -- summary

- mode: FULL (per-block stamps are authoritative; preserved sections are marked)
- seed: 20260721
- alpha ladder: (0.05, 0.1), delta: 0.05

## E1 (preserved from an earlier run)
```json
{
  "_run": {
    "mode": "FULL",
    "utc": "2026-07-30T17:53:08+00:00"
  },
  "R": 200,
  "eval_sites": 200,
  "conformance_metric": "rm_exceed_rate: fraction of certified draws whose influence-weighted answered risk R_M on a fresh 200-site pool exceeds alpha (target <= DELTA=0.05). hard_violation_rate_diag is a PER-SITE DISPERSION DIAGNOSTIC with no delta target -- the certificate bounds the site-population average, not individual sites (audit V1).",
  "s_u_protocol": 0.5,
  "0.05": {
    "certify_rate": 0.0,
    "n_certified": 0,
    "rm_exceed_rate": null,
    "mean_rm_fresh": null,
    "hard_violation_rate_diag": null,
    "exceedance_rate_diag": null,
    "mean_per_site_exceed_frac": null,
    "mean_coverage": 0.0
  },
  "0.1": {
    "certify_rate": 1.0,
    "n_certified": 200,
    "rm_exceed_rate": 0.0,
    "mean_rm_fresh": 0.0567,
    "hard_violation_rate_diag": 0.02,
    "exceedance_rate_diag": 0.08,
    "mean_per_site_exceed_frac": 0.055,
    "mean_coverage": 0.9828
  },
  "total_rm_exceed": 0,
  "su_sensitivity": [
    {
      "s_u": 0.5,
      "certify_rate": 1.0,
      "rm_exceed_rate": 0.0,
      "mean_rm_fresh": 0.0567,
      "hard_violation_rate_diag": 0.02,
      "mean_per_site_exceed_frac": 0.055
    },
    {
      "s_u": 1.0,
      "certify_rate": 1.0,
      "rm_exceed_rate": 0.0,
      "mean_rm_fresh": 0.0563,
      "hard_violation_rate_diag": 0.1,
      "mean_per_site_exceed_frac": 0.1285
    },
    {
      "s_u": 2.0,
      "certify_rate": 1.0,
      "rm_exceed_rate": 0.0,
      "mean_rm_fresh": 0.0519,
      "hard_violation_rate_diag": 0.095,
      "mean_per_site_exceed_frac": 0.1634
    }
  ],
  "exceedance_by_size": [
    {
      "size_bin": "[0,30)",
      "n": 2,
      "observed_exceedance": 0.0,
      "binomial_reference": 0.3937
    },
    {
      "size_bin": "[30,100)",
      "n": 24,
      "observed_exceedance": 0.125,
      "binomial_reference": 0.4822
    },
    {
      "size_bin": "[100,300)",
      "n": 54,
      "observed_exceedance": 0.0556,
      "binomial_reference": 0.4838
    },
    {
      "size_bin": "[300,inf)",
      "n": 120,
      "observed_exceedance": 0.0833,
      "binomial_reference": 0.4898
    }
  ]
}
```

## E2 (preserved from an earlier run)
```json
{
  "_run": {
    "mode": "FULL",
    "utc": "2026-07-30T18:00:01+00:00"
  },
  "R": 200,
  "target_base_rate": 0.22,
  "sep": 2.2,
  "R_sweep": 100,
  "baseline": {
    "0.05": {
      "certify_rate": 0.0,
      "n_certified": 0,
      "hard_violation_rate": null,
      "exceedance_rate": null,
      "rm_exceed_rate": null,
      "joint_certify_and_hard_rate": 0.0,
      "decline_rate": 1.0
    },
    "0.1": {
      "certify_rate": 1.0,
      "n_certified": 200,
      "hard_violation_rate": 0.395,
      "exceedance_rate": 0.585,
      "rm_exceed_rate": 0.975,
      "joint_certify_and_hard_rate": 0.395,
      "decline_rate": 0.0
    }
  },
  "bbse": {
    "0.05": {
      "certify_rate": 0.0,
      "n_certified": 0,
      "hard_violation_rate": null,
      "exceedance_rate": null,
      "rm_exceed_rate": null,
      "joint_certify_and_hard_rate": 0.0,
      "decline_rate": 1.0
    },
    "0.1": {
      "certify_rate": 0.0,
      "n_certified": 0,
      "hard_violation_rate": null,
      "exceedance_rate": null,
      "rm_exceed_rate": null,
      "joint_certify_and_hard_rate": 0.0,
      "decline_rate": 1.0
    }
  },
  "shift_sweep_alpha0.10": [
    {
      "target_base": 0.095,
      "R": 100,
      "baseline": {
        "certify_rate": 1.0,
        "n_certified": 100,
        "hard_violation_rate": 0.0,
        "exceedance_rate": 0.02,
        "rm_exceed_rate": 0.0,
        "joint_certify_and_hard_rate": 0.0,
        "decline_rate": 0.0
      },
      "bbse": {
        "certify_rate": 0.09,
        "n_certified": 9,
        "hard_violation_rate": 0.0,
        "exceedance_rate": 0.0,
        "rm_exceed_rate": 0.0,
        "joint_certify_and_hard_rate": 0.0,
        "decline_rate": 0.91
      }
    },
    {
      "target_base": 0.13,
      "R": 100,
      "baseline": {
        "certify_rate": 1.0,
        "n_certified": 100,
        "hard_violation_rate": 0.07,
        "exceedance_rate": 0.19,
        "rm_exceed_rate": 0.0,
        "joint_certify_and_hard_rate": 0.07,
        "decline_rate": 0.0
      },
      "bbse": {
        "certify_rate": 0.05,
        "n_certified": 5,
        "hard_violation_rate": 0.0,
        "exceedance_rate": 0.0,
        "rm_exceed_rate": 0.0,
        "joint_certify_and_hard_rate": 0.0,
        "decline_rate": 0.95
      }
    },
    {
      "target_base": 0.16,
      "R": 100,
      "baseline": {
        "certify_rate": 1.0,
        "n_certified": 100,
        "hard_violation_rate": 0.08,
        "exceedance_rate": 0.19,
        "rm_exceed_rate": 0.0,
        "joint_certify_and_hard_rate": 0.08,
        "decline_rate": 0.0
      },
      "bbse": {
        "certify_rate": 0.0,
        "n_certified": 0,
        "hard_violation_rate": null,
        "exceedance_rate": null,
        "rm_exceed_rate": null,
        "joint_certify_and_hard_rate": 0.0,
        "decline_rate": 1.0
      }
    },
    {
      "target_base": 0.19,
      "R": 100,
      "baseline": {
        "certify_rate": 1.0,
        "n_certified": 100,
        "hard_violation_rate": 0.21,
        "exceedance_rate": 0.43,
        "rm_exceed_rate": 0.17,
        "joint_certify_and_hard_rate": 0.21,
        "decline_rate": 0.0
      },
      "bbse": {
        "certify_rate": 0.01,
        "n_certified": 1,
        "hard_violation_rate": 0.0,
        "exceedance_rate": 0.0,
        "rm_exceed_rate": 0.0,
        "joint_certify_and_hard_rate": 0.0,
        "decline_rate": 0.99
      }
    },
    {
      "target_base": 0.22,
      "R": 200,
      "baseline": {
        "certify_rate": 1.0,
        "n_certified": 200,
        "hard_violation_rate": 0.395,
        "exceedance_rate": 0.585,
        "rm_exceed_rate": 0.975,
        "joint_certify_and_hard_rate": 0.395,
        "decline_rate": 0.0
      },
      "bbse": {
        "certify_rate": 0.0,
        "n_certified": 0,
        "hard_violation_rate": null,
        "exceedance_rate": null,
        "rm_exceed_rate": null,
        "joint_certify_and_hard_rate": 0.0,
        "decline_rate": 1.0
      }
    }
  ]
}
```

## E3 (preserved from an earlier run)
```json
{
  "_run": {
    "mode": "FULL",
    "utc": "2026-07-30T18:00:01+00:00"
  },
  "R": 200,
  "concept_intercept": 2.0,
  "sep": 2.2,
  "verified_mean_answered_risk_alpha0.10": 0.161,
  "tilt_pushes_risk_above_alpha": true,
  "0.05": {
    "certify_rate": 0.0,
    "n_certified": 0,
    "hard_violation_rate": null,
    "exceedance_rate": null,
    "rm_exceed_rate": null
  },
  "0.1": {
    "certify_rate": 1.0,
    "n_certified": 200,
    "hard_violation_rate": 0.7,
    "exceedance_rate": 0.845,
    "rm_exceed_rate": 1.0
  }
}
```

## E4 (preserved from an earlier run)
```json
{
  "_run": {
    "mode": "FULL",
    "utc": "2026-07-30T17:53:08+00:00"
  },
  "R": 200,
  "sweep": [
    60,
    100,
    150,
    208,
    300,
    400
  ],
  "grid": {
    "0.05": [
      {
        "n_sites": 60,
        "certify_rate": 0.0,
        "mean_coverage": 0.0
      },
      {
        "n_sites": 100,
        "certify_rate": 0.0,
        "mean_coverage": 0.0
      },
      {
        "n_sites": 150,
        "certify_rate": 0.0,
        "mean_coverage": 0.0
      },
      {
        "n_sites": 208,
        "certify_rate": 0.0,
        "mean_coverage": 0.0
      },
      {
        "n_sites": 300,
        "certify_rate": 0.285,
        "mean_coverage": 0.7296
      },
      {
        "n_sites": 400,
        "certify_rate": 1.0,
        "mean_coverage": 0.8516
      }
    ],
    "0.1": [
      {
        "n_sites": 60,
        "certify_rate": 0.0,
        "mean_coverage": 0.0
      },
      {
        "n_sites": 100,
        "certify_rate": 0.0,
        "mean_coverage": 0.0
      },
      {
        "n_sites": 150,
        "certify_rate": 1.0,
        "mean_coverage": 0.9372
      },
      {
        "n_sites": 208,
        "certify_rate": 1.0,
        "mean_coverage": 0.9818
      },
      {
        "n_sites": 300,
        "certify_rate": 1.0,
        "mean_coverage": 0.9754
      },
      {
        "n_sites": 400,
        "certify_rate": 1.0,
        "mean_coverage": 0.9641
      }
    ]
  },
  "gate_limited_n_sites": [
    60,
    100
  ],
  "gate_note": "points with n_sites < 125 are declined by the 50-record-carrying-cluster gate, not the betting test's information floor"
}
```

## E5
```json
{
  "_run": {
    "mode": "FULL",
    "utc": "2026-07-31T05:23:38+00:00"
  },
  "tau_star": 0.55,
  "n_answered": 200,
  "n_declined": 2,
  "top_gap_feature": 0,
  "replication": {
    "R": 200,
    "draws_certified": 200,
    "draws_with_declines": 186,
    "pooled_declined": 2644,
    "pooled_decline_rate": 0.0215,
    "gap_mean": [
      -0.2624,
      -0.2363,
      -0.2304,
      -0.208,
      -0.0002,
      -0.0006,
      -0.0006,
      0.0
    ],
    "gap_ci95": [
      0.0702,
      0.0493,
      0.0574,
      0.0579,
      0.0009,
      0.0008,
      0.0007,
      0.0009
    ],
    "top_gap_feature_counts": {
      "0": 47,
      "1": 40,
      "2": 51,
      "3": 48
    },
    "top_gap_feature_mode": 2,
    "top_gap_stability": 0.2742,
    "stable_driver": false,
    "counterfactual_eval": {
      "n_declined_evaluated": 2644,
      "n_unflippable": 0,
      "top_feature_flip_rate": 1.0,
      "random_feature_flip_rate": 0.115,
      "protocol": "top-ranked single-feature counterfactual delta vs an equal-|delta_z| most-favorable move on a uniformly random feature; both judged by the deployed rule score >= tau (R3-09 functionally-grounded)"
    }
  }
}
```

## E6 (preserved from an earlier run)
```json
{
  "_run": {
    "mode": "FULL",
    "utc": "2026-07-30T17:53:08+00:00"
  },
  "tau_star": 0.55,
  "size_bins": [
    {
      "size_bin": "[0,30)",
      "n_sites": 0,
      "mean_coverage": null,
      "mean_answered_err": null
    },
    {
      "size_bin": "[30,100)",
      "n_sites": 4,
      "mean_coverage": 0.9896,
      "mean_answered_err": 0.0523
    },
    {
      "size_bin": "[100,300)",
      "n_sites": 15,
      "mean_coverage": 0.98,
      "mean_answered_err": 0.067
    },
    {
      "size_bin": "[300,inf)",
      "n_sites": 21,
      "mean_coverage": 0.9856,
      "mean_answered_err": 0.0595
    }
  ],
  "predicted_positive_fraction": 0.063
}
```

## E7 (preserved from an earlier run)
```json
{
  "_run": {
    "mode": "FULL",
    "utc": "2026-07-30T17:53:08+00:00"
  },
  "R": 200,
  "record_sample": 2000,
  "comparator": "record unit = per-record atoms with M=1 on an 2000-record subsample \u2014 the plain record-level betting certifier, which treats within-site-correlated records as independent",
  "arms": {
    "0.5": {
      "0.05": {
        "site": {
          "certify_rate": 0.0,
          "rm_exceed_rate": null,
          "mean_rm_fresh": null,
          "mean_tau": null
        },
        "record": {
          "certify_rate": 1.0,
          "rm_exceed_rate": 0.035,
          "mean_rm_fresh": 0.0382,
          "mean_tau": 0.7239
        }
      },
      "0.1": {
        "site": {
          "certify_rate": 1.0,
          "rm_exceed_rate": 0.0,
          "mean_rm_fresh": 0.0573,
          "mean_tau": 0.5531
        },
        "record": {
          "certify_rate": 1.0,
          "rm_exceed_rate": 0.0,
          "mean_rm_fresh": 0.0576,
          "mean_tau": 0.55
        }
      }
    },
    "2.0": {
      "0.05": {
        "site": {
          "certify_rate": 0.0,
          "rm_exceed_rate": null,
          "mean_rm_fresh": null,
          "mean_tau": null
        },
        "record": {
          "certify_rate": 0.99,
          "rm_exceed_rate": 0.096,
          "mean_rm_fresh": 0.0379,
          "mean_tau": 0.828
        }
      },
      "0.1": {
        "site": {
          "certify_rate": 0.995,
          "rm_exceed_rate": 0.0,
          "mean_rm_fresh": 0.0522,
          "mean_tau": 0.7466
        },
        "record": {
          "certify_rate": 1.0,
          "rm_exceed_rate": 0.0,
          "mean_rm_fresh": 0.0807,
          "mean_tau": 0.5869
        }
      }
    }
  }
}
```
