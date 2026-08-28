# CertGate synthetic experiments -- summary

- mode: FULL (per-block stamps are authoritative; preserved sections are marked)
- seed: 20260721
- alpha ladder: (0.05, 0.1), delta: 0.05

## E1
```json
{
  "_run": {
    "mode": "FULL",
    "utc": "2026-08-27T04:33:22+00:00"
  },
  "R": 200,
  "eval_sites": 200,
  "conformance_metric": "rm_exceed_rate: fraction of certified draws whose influence-weighted answered risk R_M on a fresh 200-site pool exceeds alpha (target <= DELTA=0.05). hard_violation_rate_diag is a PER-SITE DISPERSION DIAGNOSTIC with no delta target -- the certificate bounds the site-population average, not individual sites (audit V1).",
  "s_u_protocol": 0.5,
  "0.05": {
    "certify_rate": 0.0,
    "n_certified": 0,
    "rm_exceed_rate_ci95": null,
    "rm_exceed_rate": null,
    "mean_rm_fresh": null,
    "hard_violation_rate_diag_ci95": null,
    "hard_violation_rate_diag": null,
    "exceedance_rate_diag": null,
    "mean_per_site_exceed_frac": null,
    "mean_coverage": 0.0
  },
  "0.1": {
    "certify_rate": 1.0,
    "n_certified": 200,
    "rm_exceed_rate_ci95": [
      0.0,
      0.0183
    ],
    "rm_exceed_rate": 0.0,
    "mean_rm_fresh": 0.0567,
    "hard_violation_rate_diag_ci95": [
      0.0055,
      0.0504
    ],
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

## E2
```json
{
  "_run": {
    "mode": "FULL",
    "utc": "2026-08-27T04:33:22+00:00"
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
      "hard_violation_rate_ci95": null,
      "exceedance_rate": null,
      "rm_exceed_rate": null,
      "rm_exceed_rate_ci95": null,
      "joint_certify_and_hard_rate": 0.0,
      "decline_rate": 1.0
    },
    "0.1": {
      "certify_rate": 1.0,
      "n_certified": 200,
      "hard_violation_rate": 0.395,
      "hard_violation_rate_ci95": [
        0.3268,
        0.4664
      ],
      "exceedance_rate": 0.585,
      "rm_exceed_rate": 0.975,
      "rm_exceed_rate_ci95": [
        0.9426,
        0.9918
      ],
      "joint_certify_and_hard_rate": 0.395,
      "decline_rate": 0.0
    }
  },
  "bbse": {
    "0.05": {
      "certify_rate": 0.0,
      "n_certified": 0,
      "hard_violation_rate": null,
      "hard_violation_rate_ci95": null,
      "exceedance_rate": null,
      "rm_exceed_rate": null,
      "rm_exceed_rate_ci95": null,
      "joint_certify_and_hard_rate": 0.0,
      "decline_rate": 1.0
    },
    "0.1": {
      "certify_rate": 0.0,
      "n_certified": 0,
      "hard_violation_rate": null,
      "hard_violation_rate_ci95": null,
      "exceedance_rate": null,
      "rm_exceed_rate": null,
      "rm_exceed_rate_ci95": null,
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
        "hard_violation_rate_ci95": [
          0.0,
          0.0362
        ],
        "exceedance_rate": 0.02,
        "rm_exceed_rate": 0.0,
        "rm_exceed_rate_ci95": [
          0.0,
          0.0362
        ],
        "joint_certify_and_hard_rate": 0.0,
        "decline_rate": 0.0
      },
      "bbse": {
        "certify_rate": 0.09,
        "n_certified": 9,
        "hard_violation_rate": 0.0,
        "hard_violation_rate_ci95": [
          0.0,
          0.3363
        ],
        "exceedance_rate": 0.0,
        "rm_exceed_rate": 0.0,
        "rm_exceed_rate_ci95": [
          0.0,
          0.3363
        ],
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
        "hard_violation_rate_ci95": [
          0.0286,
          0.1389
        ],
        "exceedance_rate": 0.19,
        "rm_exceed_rate": 0.0,
        "rm_exceed_rate_ci95": [
          0.0,
          0.0362
        ],
        "joint_certify_and_hard_rate": 0.07,
        "decline_rate": 0.0
      },
      "bbse": {
        "certify_rate": 0.05,
        "n_certified": 5,
        "hard_violation_rate": 0.0,
        "hard_violation_rate_ci95": [
          0.0,
          0.5218
        ],
        "exceedance_rate": 0.0,
        "rm_exceed_rate": 0.0,
        "rm_exceed_rate_ci95": [
          0.0,
          0.5218
        ],
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
        "hard_violation_rate_ci95": [
          0.0352,
          0.1516
        ],
        "exceedance_rate": 0.19,
        "rm_exceed_rate": 0.0,
        "rm_exceed_rate_ci95": [
          0.0,
          0.0362
        ],
        "joint_certify_and_hard_rate": 0.08,
        "decline_rate": 0.0
      },
      "bbse": {
        "certify_rate": 0.0,
        "n_certified": 0,
        "hard_violation_rate": null,
        "hard_violation_rate_ci95": null,
        "exceedance_rate": null,
        "rm_exceed_rate": null,
        "rm_exceed_rate_ci95": null,
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
        "hard_violation_rate_ci95": [
          0.1349,
          0.3029
        ],
        "exceedance_rate": 0.43,
        "rm_exceed_rate": 0.17,
        "rm_exceed_rate_ci95": [
          0.1023,
          0.2582
        ],
        "joint_certify_and_hard_rate": 0.21,
        "decline_rate": 0.0
      },
      "bbse": {
        "certify_rate": 0.01,
        "n_certified": 1,
        "hard_violation_rate": 0.0,
        "hard_violation_rate_ci95": [
          0.0,
          0.975
        ],
        "exceedance_rate": 0.0,
        "rm_exceed_rate": 0.0,
        "rm_exceed_rate_ci95": [
          0.0,
          0.975
        ],
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
        "hard_violation_rate_ci95": [
          0.3268,
          0.4664
        ],
        "exceedance_rate": 0.585,
        "rm_exceed_rate": 0.975,
        "rm_exceed_rate_ci95": [
          0.9426,
          0.9918
        ],
        "joint_certify_and_hard_rate": 0.395,
        "decline_rate": 0.0
      },
      "bbse": {
        "certify_rate": 0.0,
        "n_certified": 0,
        "hard_violation_rate": null,
        "hard_violation_rate_ci95": null,
        "exceedance_rate": null,
        "rm_exceed_rate": null,
        "rm_exceed_rate_ci95": null,
        "joint_certify_and_hard_rate": 0.0,
        "decline_rate": 1.0
      }
    }
  ]
}
```

## E3
```json
{
  "_run": {
    "mode": "FULL",
    "utc": "2026-08-27T04:33:22+00:00"
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
    "hard_violation_rate_ci95": null,
    "exceedance_rate": null,
    "rm_exceed_rate": null,
    "rm_exceed_rate_ci95": null
  },
  "0.1": {
    "certify_rate": 1.0,
    "n_certified": 200,
    "hard_violation_rate": 0.7,
    "hard_violation_rate_ci95": [
      0.6314,
      0.7626
    ],
    "exceedance_rate": 0.845,
    "rm_exceed_rate": 1.0,
    "rm_exceed_rate_ci95": [
      0.9817,
      1.0
    ]
  }
}
```

## E4
```json
{
  "_run": {
    "mode": "FULL",
    "utc": "2026-08-27T04:33:22+00:00"
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
    "utc": "2026-08-27T04:33:22+00:00"
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

## E6
```json
{
  "_run": {
    "mode": "FULL",
    "utc": "2026-08-27T04:33:22+00:00"
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
  "predicted_positive_fraction": 0.063,
  "panel_post_hoc": "[MEASURE] POST-HOC (2026-08-01): added after the E1-E7 grid was published. Descriptive only -- it alters no certified quantity and no number in E1-E7 moves because of it (the panel self-seeds from a digest of its own inputs and consumes no _rng(6) draw).",
  "panel_ece_answered": 0.002914,
  "panel_calibration_slope_answered": 0.996989,
  "panel_skill_margin_answered_minus_all": 0.000204
}
```

## E7
```json
{
  "_run": {
    "mode": "FULL",
    "utc": "2026-08-27T04:33:22+00:00"
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

## E8
```json
{
  "_run": {
    "mode": "FULL",
    "utc": "2026-08-27T04:33:22+00:00"
  },
  "R": 200,
  "noise_R": 300,
  "sweep": [
    60,
    100,
    150,
    208,
    300,
    400
  ],
  "n_boot": 1000,
  "comparators": {
    "wsr": {
      "0.05": {
        "certify_rate": 0.2133,
        "rm_exceed_rate": 0.0,
        "mean_tau": 0.8712,
        "mean_coverage": 0.8272,
        "mean_rm_fresh": 0.0215,
        "certify_by_nsites": [
          0.0,
          0.0,
          0.0,
          0.0,
          0.28,
          1.0
        ]
      },
      "0.1": {
        "certify_rate": 0.6667,
        "rm_exceed_rate": 0.0,
        "mean_tau": 0.5852,
        "mean_coverage": 0.9733,
        "mean_rm_fresh": 0.0535,
        "certify_by_nsites": [
          0.0,
          0.0,
          1.0,
          1.0,
          1.0,
          1.0
        ]
      }
    },
    "hoeffding": {
      "0.05": {
        "certify_rate": 0.0,
        "rm_exceed_rate": null,
        "mean_tau": null,
        "mean_coverage": null,
        "mean_rm_fresh": null,
        "certify_by_nsites": [
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0
        ]
      },
      "0.1": {
        "certify_rate": 0.0,
        "rm_exceed_rate": null,
        "mean_tau": null,
        "mean_coverage": null,
        "mean_rm_fresh": null,
        "certify_by_nsites": [
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0
        ]
      }
    },
    "mpeb": {
      "0.05": {
        "certify_rate": 0.0,
        "rm_exceed_rate": null,
        "mean_tau": null,
        "mean_coverage": null,
        "mean_rm_fresh": null,
        "certify_by_nsites": [
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0
        ]
      },
      "0.1": {
        "certify_rate": 0.1667,
        "rm_exceed_rate": 0.0,
        "mean_tau": 0.7796,
        "mean_coverage": 0.8989,
        "mean_rm_fresh": 0.0321,
        "certify_by_nsites": [
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          1.0
        ]
      }
    },
    "t": {
      "0.05": {
        "certify_rate": 1.0,
        "rm_exceed_rate": 0.0508,
        "mean_tau": 0.666,
        "mean_coverage": 0.9472,
        "mean_rm_fresh": 0.0445,
        "certify_by_nsites": [
          1.0,
          1.0,
          1.0,
          1.0,
          1.0,
          1.0
        ]
      },
      "0.1": {
        "certify_rate": 1.0,
        "rm_exceed_rate": 0.0,
        "mean_tau": 0.55,
        "mean_coverage": 0.985,
        "mean_rm_fresh": 0.0576,
        "certify_by_nsites": [
          1.0,
          1.0,
          1.0,
          1.0,
          1.0,
          1.0
        ]
      }
    },
    "site_boot": {
      "0.05": {
        "certify_rate": 1.0,
        "rm_exceed_rate": 0.0492,
        "mean_tau": 0.6655,
        "mean_coverage": 0.9474,
        "mean_rm_fresh": 0.0445,
        "certify_by_nsites": [
          1.0,
          1.0,
          1.0,
          1.0,
          1.0,
          1.0
        ]
      },
      "0.1": {
        "certify_rate": 1.0,
        "rm_exceed_rate": 0.0,
        "mean_tau": 0.55,
        "mean_coverage": 0.985,
        "mean_rm_fresh": 0.0576,
        "certify_by_nsites": [
          1.0,
          1.0,
          1.0,
          1.0,
          1.0,
          1.0
        ]
      }
    }
  },
  "noise": {
    "0.01": {
      "0.05": {
        "certify_rate": 0.0,
        "rm_exceed_rate": null,
        "mean_tau": null,
        "mean_coverage": null,
        "mean_rm_fresh": null
      },
      "0.1": {
        "certify_rate": 1.0,
        "rm_exceed_rate": 0.0,
        "mean_tau": 0.6052,
        "mean_coverage": 0.9629,
        "mean_rm_fresh": 0.0584
      },
      "mean_risk_at_lowest_tau": 0.0655
    },
    "0.02": {
      "0.05": {
        "certify_rate": 0.0,
        "rm_exceed_rate": null,
        "mean_tau": null,
        "mean_coverage": null,
        "mean_rm_fresh": null
      },
      "0.1": {
        "certify_rate": 1.0,
        "rm_exceed_rate": 0.0,
        "mean_tau": 0.6823,
        "mean_coverage": 0.9235,
        "mean_rm_fresh": 0.0563
      },
      "mean_risk_at_lowest_tau": 0.0737
    },
    "0.03": {
      "0.05": {
        "certify_rate": 0.0,
        "rm_exceed_rate": null,
        "mean_tau": null,
        "mean_coverage": null,
        "mean_rm_fresh": null
      },
      "0.1": {
        "certify_rate": 0.9967,
        "rm_exceed_rate": 0.0,
        "mean_tau": 0.7695,
        "mean_coverage": 0.8558,
        "mean_rm_fresh": 0.0534
      },
      "mean_risk_at_lowest_tau": 0.0826
    },
    "0.035": {
      "0.05": {
        "certify_rate": 0.0,
        "rm_exceed_rate": null,
        "mean_tau": null,
        "mean_coverage": null,
        "mean_rm_fresh": null
      },
      "0.1": {
        "certify_rate": 0.63,
        "rm_exceed_rate": 0.0,
        "mean_tau": 0.8157,
        "mean_coverage": 0.8,
        "mean_rm_fresh": 0.0518
      },
      "mean_risk_at_lowest_tau": 0.0871
    },
    "0.04": {
      "0.05": {
        "certify_rate": 0.0,
        "rm_exceed_rate": null,
        "mean_tau": null,
        "mean_coverage": null,
        "mean_rm_fresh": null
      },
      "0.1": {
        "certify_rate": 0.0233,
        "rm_exceed_rate": 0.0,
        "mean_tau": 0.8357,
        "mean_coverage": 0.7573,
        "mean_rm_fresh": 0.0532
      },
      "mean_risk_at_lowest_tau": 0.0913
    }
  },
  "heads": {
    "linear": {
      "0.05": {
        "certify_rate": 0.0,
        "rm_exceed_rate": null,
        "mean_tau": null,
        "mean_coverage": null,
        "mean_rm_fresh": null
      },
      "0.1": {
        "certify_rate": 1.0,
        "rm_exceed_rate": 0.0,
        "mean_tau": 0.5535,
        "mean_coverage": 0.9839,
        "mean_rm_fresh": 0.0571
      }
    },
    "gbm": {
      "0.05": {
        "certify_rate": 0.0,
        "rm_exceed_rate": null,
        "mean_tau": null,
        "mean_coverage": null,
        "mean_rm_fresh": null
      },
      "0.1": {
        "certify_rate": 1.0,
        "rm_exceed_rate": 0.0,
        "mean_tau": 0.5622,
        "mean_coverage": 0.9823,
        "mean_rm_fresh": 0.0582
      }
    },
    "degraded": {
      "0.05": {
        "certify_rate": 0.0,
        "rm_exceed_rate": null,
        "mean_tau": null,
        "mean_coverage": null,
        "mean_rm_fresh": null
      },
      "0.1": {
        "certify_rate": 1.0,
        "rm_exceed_rate": 0.0,
        "mean_tau": 0.765,
        "mean_coverage": 0.8799,
        "mean_rm_fresh": 0.0537
      }
    }
  },
  "explain_supported": {
    "linear": true,
    "gbm": false,
    "degraded": false
  },
  "notes": "arm A: identical atoms and walk order across all five certifiers; two-sided reading pre-committed in SPEC. arm B: flips applied to every cohort alike, so exchangeability holds by construction. arm C: linear reference rows come from the gbm arm's draws; temperature miscalibration is analytically a no-op for the gate (monotone score transform) and is not simulated. explain_supported=False for the degraded head marks the deployed explanation path, not linear-algebra feasibility."
}
```

## E9
```json
{
  "_run": {
    "mode": "FULL",
    "utc": "2026-08-27T04:33:22+00:00"
  },
  "R": 50,
  "fnr_R": 200,
  "anchor_shift": 0.22,
  "bbse_frontier": {
    "208|single-site-cp": {
      "certify_rate": 0.0,
      "decline_reasons": {
        "failsafe": 50
      },
      "median_box_width": 4.9028,
      "mean_tau": null,
      "rm_exceed_rate": null
    },
    "208|k40-boot": {
      "certify_rate": 0.0,
      "decline_reasons": {
        "failsafe": 50
      },
      "median_box_width": 3.4687,
      "mean_tau": null,
      "rm_exceed_rate": null
    },
    "600|single-site-cp": {
      "certify_rate": 0.14,
      "decline_reasons": {
        "bbse-misspecified": 4,
        "failsafe": 39
      },
      "median_box_width": 4.2536,
      "mean_tau": 0.8586,
      "rm_exceed_rate": 0.0
    },
    "600|k40-boot": {
      "certify_rate": 0.0,
      "decline_reasons": {
        "failsafe": 50
      },
      "median_box_width": 2.8047,
      "mean_tau": null,
      "rm_exceed_rate": null
    },
    "900|single-site-cp": {
      "certify_rate": 0.26,
      "decline_reasons": {
        "failsafe": 35,
        "bbse-misspecified": 2
      },
      "median_box_width": 3.7739,
      "mean_tau": 0.8038,
      "rm_exceed_rate": 0.0
    },
    "900|k40-boot": {
      "certify_rate": 0.38,
      "decline_reasons": {
        "failsafe": 31
      },
      "median_box_width": 2.6004,
      "mean_tau": 0.9068,
      "rm_exceed_rate": 0.0
    },
    "1200|single-site-cp": {
      "certify_rate": 0.4,
      "decline_reasons": {
        "failsafe": 27,
        "bbse-misspecified": 3
      },
      "median_box_width": 4.2122,
      "mean_tau": 0.831,
      "rm_exceed_rate": 0.1
    },
    "1200|k40-boot": {
      "certify_rate": 0.94,
      "decline_reasons": {
        "failsafe": 3
      },
      "median_box_width": 2.2184,
      "mean_tau": 0.884,
      "rm_exceed_rate": 0.0
    }
  },
  "fnr_frontier": {
    "0.4": {
      "208": {
        "certify_rate": 0.0,
        "mean_tau": null,
        "mean_fnr_fresh": null,
        "fnr_exceed_rate": null
      },
      "400": {
        "certify_rate": 0.0,
        "mean_tau": null,
        "mean_fnr_fresh": null,
        "fnr_exceed_rate": null
      },
      "600": {
        "certify_rate": 0.0,
        "mean_tau": null,
        "mean_fnr_fresh": null,
        "fnr_exceed_rate": null
      }
    },
    "0.5": {
      "208": {
        "certify_rate": 0.0,
        "mean_tau": null,
        "mean_fnr_fresh": null,
        "fnr_exceed_rate": null
      },
      "400": {
        "certify_rate": 0.0,
        "mean_tau": null,
        "mean_fnr_fresh": null,
        "fnr_exceed_rate": null
      },
      "600": {
        "certify_rate": 0.005,
        "mean_tau": 0.55,
        "mean_fnr_fresh": 0.4194,
        "fnr_exceed_rate": 0.0
      }
    },
    "0.55": {
      "208": {
        "certify_rate": 0.0,
        "mean_tau": null,
        "mean_fnr_fresh": null,
        "fnr_exceed_rate": null
      },
      "400": {
        "certify_rate": 0.285,
        "mean_tau": 0.5504,
        "mean_fnr_fresh": 0.4382,
        "fnr_exceed_rate": 0.0
      },
      "600": {
        "certify_rate": 0.995,
        "mean_tau": 0.55,
        "mean_fnr_fresh": 0.45,
        "fnr_exceed_rate": 0.0
      }
    },
    "0.6": {
      "208": {
        "certify_rate": 0.04,
        "mean_tau": 0.55,
        "mean_fnr_fresh": 0.4164,
        "fnr_exceed_rate": 0.0
      },
      "400": {
        "certify_rate": 1.0,
        "mean_tau": 0.55,
        "mean_fnr_fresh": 0.4484,
        "fnr_exceed_rate": 0.0
      },
      "600": {
        "certify_rate": 1.0,
        "mean_tau": 0.55,
        "mean_fnr_fresh": 0.45,
        "fnr_exceed_rate": 0.0
      }
    }
  },
  "true_fnr_at_lowest_tau_mean": 0.4499,
  "notes": "arm A: pipeline in bbse mode only; certificates rescored on a fresh same-shift pool (E2's aggregate-estimand precedent); the single-site-declaration exceedance rate is a pre-declared question (SPEC E9). arm B: experimental secondary certificate on unmodified influence_atoms with weights=y; a frontier and a price, never a tight FNR guarantee; 0.4 is the built-in always-refuses negative control."
}
```
