"""Frozen constants (SPEC section "Frozen constants").

Every value here is pinned literally by ``tests/test_constants.py`` so any
drift fails CI -- a lightweight, verifiable stand-in for pre-registration
(audit F13). These constants are the a-priori surface of the certified-gate
protocol; nothing downstream may redefine them.
"""

import numpy as np

SEED = 20260721
SPLIT_FRACTIONS = (0.40, 0.20, 0.40)     # S_train / S_aux / S_cal, site-disjoint
ALPHA_LADDER = (0.05, 0.10)
DELTA = 0.05
BBSE_DELTA_CONF = 0.025                  # BBSE box confidence share
BBSE_DELTA_BET = 0.025                   # BBSE betting-test share (sum = DELTA)
BBSE_BONFERRONI = 4                      # box covers (c0, c1, pi_source, q_target) — audit V2
M_INFLUENCE = 100
TAU_GRID = np.linspace(0.55, 0.99, 23)
WSR_LAMBDA_CAP = 0.9                     # lambda cap = 0.9 / (1 - alpha)
WSR_VAR_FLOOR = 1e-8
WSR_MU0, WSR_S2_0 = 0.5, 0.25
MIN_CAL_CLUSTERS = 50                    # RECORD-CARRYING calibration clusters (audit B-5)
MIN_ANSWERABLE = 10                      # registered target-pool floor (audit B-6)
BBSE_GAP_FLOOR = 0.10                    # worst-case (c1 - c0) below this -> decline
BBSE_MIN_TARGET_SITES = 10               # q cluster-bootstrap floor (verification F1):
                                         # 2 <= K < floor declines "bbse-target-clustering"
BBSE_BOOT = 2000                         # required VALID resamples
BBSE_BOOT_MAX_ATTEMPTS = 4000            # total attempts before declining (audit B-8)
PI_CLIP = 1e-4
SD_REL_TOL = 1e-9                        # guarded standardization (audit F06: relative, not ==0)
HEAD_C = 1.0
HEAD_MAX_ITER = 2000
MODE_BASELINE, MODE_BBSE = 0, 1
