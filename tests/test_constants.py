"""SPEC "Tests": literal equality for EVERY frozen constant (audit F13).

Any drift in ``constants.py`` fails here -- the lightweight, verifiable
stand-in for pre-registration.
"""
import ast
import hashlib
import json
import math
import pathlib
from collections import Counter

import numpy as np
import pytest

from certgate import constants as C
from certgate import reliability as RP


def test_seed():
    assert C.SEED == 20260721


def test_split_fractions():
    assert C.SPLIT_FRACTIONS == (0.40, 0.20, 0.40)


def test_alpha_ladder():
    assert C.ALPHA_LADDER == (0.05, 0.10)


def test_delta():
    assert C.DELTA == 0.05


def test_bbse_delta_shares_sum_to_delta():
    assert C.BBSE_DELTA_CONF == 0.025
    assert C.BBSE_DELTA_BET == 0.025
    assert C.BBSE_DELTA_CONF + C.BBSE_DELTA_BET == C.DELTA


def test_bbse_bonferroni():
    # audit V2: the box covers FOUR estimated parameters
    # (c0, c1, pi_source, q_target)
    assert C.BBSE_BONFERRONI == 4


def test_m_influence():
    assert C.M_INFLUENCE == 100


def test_tau_grid():
    assert len(C.TAU_GRID) == 23
    assert C.TAU_GRID[0] == 0.55
    assert C.TAU_GRID[-1] == 0.99
    assert np.allclose(C.TAU_GRID, np.linspace(0.55, 0.99, 23))


def test_wsr_constants():
    assert C.WSR_LAMBDA_CAP == 0.9
    assert C.WSR_VAR_FLOOR == 1e-8
    assert (C.WSR_MU0, C.WSR_S2_0) == (0.5, 0.25)


def test_min_cal_clusters():
    assert C.MIN_CAL_CLUSTERS == 50


def test_min_answerable():
    assert C.MIN_ANSWERABLE == 10


def test_bbse_gap_floor():
    assert C.BBSE_GAP_FLOOR == 0.10


def test_bbse_min_target_sites():
    # verification F1: the q cluster-bootstrap floor -- 2..9 declared target
    # sites decline "bbse-target-clustering" rather than run a bootstrap that
    # cannot approach nominal coverage
    assert C.BBSE_MIN_TARGET_SITES == 10


def test_bbse_boot_counts():
    assert C.BBSE_BOOT == 2000
    assert C.BBSE_BOOT_MAX_ATTEMPTS == 4000


def test_pi_clip():
    assert C.PI_CLIP == 1e-4


def test_sd_rel_tol():
    assert C.SD_REL_TOL == 1e-9


def test_head_hyperparams():
    assert C.HEAD_C == 1.0
    assert C.HEAD_MAX_ITER == 2000


def test_mode_indices():
    assert (C.MODE_BASELINE, C.MODE_BBSE) == (0, 1)


# ---- experiment-grid constants (audit V7: an undeclared generator parameter
# ---- made two headline numbers non-reproducible from the stated setup) ----

def test_experiment_grid_constants_pinned():
    from experiments import run_synthetic as rs
    assert rs.ANCHOR_SITES == 208
    assert rs.SHIFT_BASE == 0.22
    assert rs.CONCEPT_INTERCEPT == 2.0
    assert rs.QUICK_SWEEP == (60, 208, 400)
    assert rs.FULL_SWEEP == (60, 100, 150, 208, 300, 400)
    assert rs.E1_SU_SWEEP == (0.5, 1.0, 2.0)
    assert rs.E1_EVAL_SITES == 200
    # panel-driven additions (fixture audit follow-ups, 2026-07-30)
    assert rs.E2_SHIFT_SWEEP == (0.095, 0.13, 0.16, 0.19, 0.22)
    assert rs.SHIFT_BASE in rs.E2_SHIFT_SWEEP
    assert rs.E7_RECORD_SAMPLE == 2000
    assert rs.E7_SU_ARM == (0.5, 2.0)


def test_no_experiment_local_separation_override():
    """audit V7: E2/E3 ran at an undeclared sep=1.8 against a documented 2.2.
    Every experiment now runs the documented SimConfig generator; no
    experiment-local separation constant may exist."""
    from experiments import run_synthetic as rs
    assert not hasattr(rs, "SHIFT_SEP")


def test_simconfig_generator_defaults_pinned():
    """The generator defaults are protocol constants too (audit V7): the paper
    describes exactly these values."""
    from certgate.data import SimConfig
    cfg = SimConfig()
    assert cfg.d == 8
    assert cfg.sep == 2.2
    assert cfg.base_rate == 0.095
    assert cfg.s_u == 0.5
    assert (cfg.size_mu, cfg.size_sigma) == (6.0, 1.1)
    assert (cfg.size_lo, cfg.size_hi) == (20, 5000)


def test_e8_constants_pinned():
    """Revision-2 E8 arms (SPEC "E8"; design record
    paper/review/revision2/PHASE0-PROBES.md). Appended function: every
    pre-existing pin above stays byte-untouched."""
    from experiments import run_synthetic as rs
    assert rs.E8_COMPARATORS == ("wsr", "hoeffding", "mpeb", "t", "site_boot")
    assert rs.E8_BOOT == 1000
    assert rs.E8_NOISE_SWEEP == (0.01, 0.02, 0.03, 0.035, 0.04)
    assert rs.E8_NOISE_R == 300
    assert rs.E8_HEAD_ARMS == ("gbm", "degraded")
    assert rs.E8_GBM_MAX_ITER == 200
    assert rs.E8_DEGRADED_ZERO_FEATURES == 2


def test_e9_constants_pinned():
    """Revision-2 E9 arms (SPEC "E9" + "Outcome-weighted atoms"; frozen from
    the P0.2/P0.3 pilots in paper/review/revision2/PHASE0-PROBES.md)."""
    from experiments import run_synthetic as rs
    assert rs.E9_SOURCE_SWEEP == (208, 600, 900, 1200)
    assert rs.E9_TARGET_MODES == ("single-site-cp", "k40-boot")
    assert rs.E9_TARGET_K == 40
    assert rs.E9_R == 50
    assert rs.E9_FNR_LADDER == (0.4, 0.5, 0.55, 0.6)
    assert rs.E9_FNR_SWEEP == (208, 400, 600)
    assert rs.E9_FNR_R == 200


def test_experiment_registration_consistent():
    """EXPERIMENTS and _RUNNERS must agree (the --only validator checks one,
    the dispatch loop iterates the other -- registering in only one is a
    silent drop or a KeyError), and every name must stay single-digit: the
    summary-writer regex ``^## (E\\d)`` would silently alias an E10 block
    into E1's (CLAUDE.md gotcha, now pinned)."""
    import re
    from experiments import run_synthetic as rs
    assert set(rs.EXPERIMENTS) == set(rs._RUNNERS)
    assert all(re.fullmatch(r"E\d", n) for n in rs.EXPERIMENTS)


# ---- eICU real-data protocol constants (SPEC "Real-data protocol"). These are
# ---- PRE-REGISTRATION constants: they were frozen before a single eICU byte
# ---- was read, and pinning them literally is what makes that claim checkable.
# ---- A red assertion here is a protocol change and belongs in SPEC.md first.

def test_eicu_protocol_constants_pinned():
    from experiments import eicu_etl as etl

    # --- identity of the extract and of the unit of independence -----------
    assert etl.EICU_TABLES == ("patient", "hospital", "apacheApsVar",
                               "apachePredVar", "apachePatientResult")
    assert etl.EICU_SITE_PREFIX == "hosp-"
    assert etl.EICU_LABEL_COLUMN == "hospitaldischargestatus"
    assert etl.EICU_POSITIVE_LABEL == "Expired"
    assert etl.EICU_NEGATIVE_LABEL == "Alive"
    assert etl.EICU_POOLED_TARGET_LABEL == "eicu-target-pool"
    # `apache-linked` (2026-07-31 audit, E-9) restricts to stays whose day-1
    # APACHE window is COMPLETE, so the presence flags become constant and
    # information-free. It is the declared, immortal-time-selected escape from
    # the outcome-informative-missingness abort -- never the headline.
    assert etl.EICU_ARMS == ("primary", "apache-linked", "apache-complete")

    # --- the outcome-informative-missingness gates (E-9) -------------------
    # APACHE day-1 rows do not exist for a stay that ends BECAUSE THE PATIENT
    # DIED before the window closes, so aps_present/apv_present and the 43
    # __missing siblings are a partial OUTCOME proxy with no column name --
    # invisible to a name denylist. Measured on the mock: clean corpus 1.11;
    # outcome-correlated absence planted at p=0.20 gives 2.66, p=0.30 gives
    # 3.86, p=0.75 gives 14.51. Widening this cap is how the leak gets in.
    assert etl.EICU_MAX_OUTCOME_PREVALENCE_RATIO == 2.0
    assert etl.EICU_MIN_OUTCOME_STRATUM == 100
    assert etl.EICU_FEATURE_AUC_REVIEW == 0.75
    # E-15: the opposite direction of the -1 gate. A Postgres text-format
    # re-export writes '\N', which parses as `unparseable` and turns all 43
    # allowlisted APACHE numerics into 100% missing while build_raw succeeds.
    assert etl.EICU_MAX_UNPARSEABLE_SHARE == 0.01

    # --- cohort predicates -------------------------------------------------
    assert etl.EICU_MIN_AGE == 18
    # the HIPAA ceiling token, kept (not dropped): its share varies BY HOSPITAL,
    # so dropping it is a site-correlated exclusion
    assert etl.EICU_AGE_MASK_TOKEN == "> 89"
    assert etl.EICU_AGE_MASK_VALUE == 90.0

    # --- the UNDOCUMENTED APACHE sentinel and the imputation fallback ------
    assert etl.EICU_SENTINEL_MISSING == -1.0
    assert etl.EICU_IMPUTE_FALLBACK == 0.0
    assert etl.EICU_APACHE_VERSION_PREFERENCE == ("IVa", "IV")

    # --- the frozen vocabulary's drift cap and the T-5 disclosure cap ------
    assert etl.EICU_MAX_OTHER_SHARE == 0.05
    assert etl.EICU_MAX_CROSS_SITE_PATIENT_SHARE == 0.01

    # --- split arithmetic --------------------------------------------------
    assert etl.EICU_N_TARGET_SITES == 24        # >= 2 * BBSE_MIN_TARGET_SITES
    assert etl.EICU_SPLIT_NAMESPACE == 9        # SeedSequence([SEED, 9, replicate])
    assert etl.EICU_SPLIT_REPLICATES == 20
    assert etl.EICU_MIN_TOTAL_SITES == 149
    assert etl.EICU_N_TARGET_SITES >= 2 * C.BBSE_MIN_TARGET_SITES

    # EICU_MIN_TOTAL_SITES is a SUFFICIENT floor, not the tight one. The
    # int() truncation in the 40/20/40 split makes the calibration count
    # non-monotone in the total (148 sites yields 51 calibration clusters,
    # 149 yields 50), so the checkable property is: at and above the floor the
    # projection ALWAYS clears MIN_CAL_CLUSTERS, and some total below it does
    # not. The tight breakpoint is 146; the constant keeps three sites of slack.
    def _n_cal(total):
        rest = total - etl.EICU_N_TARGET_SITES
        return (rest - int(rest * C.SPLIT_FRACTIONS[0])
                - int(rest * C.SPLIT_FRACTIONS[1]))

    assert all(_n_cal(t) >= C.MIN_CAL_CLUSTERS
               for t in range(etl.EICU_MIN_TOTAL_SITES, 401))
    assert any(_n_cal(t) < C.MIN_CAL_CLUSTERS
               for t in range(1, etl.EICU_MIN_TOTAL_SITES))
    assert _n_cal(etl.EICU_MIN_TOTAL_SITES) == C.MIN_CAL_CLUSTERS == 50
    assert max(t for t in range(1, 401)
               if _n_cal(t) < C.MIN_CAL_CLUSTERS) == 145
    # and the released 208-hospital arithmetic the protocol advertises
    rest = 208 - etl.EICU_N_TARGET_SITES
    assert (int(rest * C.SPLIT_FRACTIONS[0]),
            int(rest * C.SPLIT_FRACTIONS[1])) == (73, 36)
    assert rest - 73 - 36 == 75

    # --- feature width: names and columns are built from ONE source --------
    assert etl.EICU_N_FEATURES == 161
    assert len(etl.FEATURE_NAMES) == etl.EICU_N_FEATURES
    assert etl.EICU_PATIENT_NUMERIC == ("age", "admissionheight",
                                        "admissionweight", "pre_icu_hours")
    assert len(etl.EICU_APS_NUMERIC) == 24
    assert len(etl.EICU_APV_NUMERIC) == 19
    assert etl.EICU_APS_NUMERIC == (
        "intubated", "vent", "dialysis", "eyes", "motor", "verbal", "meds",
        "urine", "wbc", "temperature", "respiratoryrate", "sodium", "heartrate",
        "meanbp", "ph", "hematocrit", "creatinine", "albumin", "pao2", "pco2",
        "bun", "glucose", "bilirubin", "fio2")
    assert etl.EICU_APV_NUMERIC == (
        "graftcount", "thrombolytics", "aids", "hepaticfailure", "lymphoma",
        "metastaticcancer", "leukemia", "immunosuppression", "cirrhosis",
        "electivesurgery", "activetx", "readmit", "ima", "midur", "ventday1",
        "oobventday1", "oobintubday1", "diabetes", "ejectfx")
    # 4*2 + 1 + (6+8+17+17+10+6) + 24*2 + 19*2 + 2 == 161
    assert (2 * len(etl.EICU_PATIENT_NUMERIC) + 1
            + sum(len(lv) for _, lv in etl.EICU_CATEGORICALS)
            + 2 * len(etl.EICU_APS_NUMERIC) + 2 * len(etl.EICU_APV_NUMERIC)
            + 2) == etl.EICU_N_FEATURES

    # --- the frozen categorical level tuples ------------------------------
    assert etl.EICU_LEVELS_GENDER == ("Female", "Male", "Other", "Unknown",
                                      "", "OTHER")
    assert etl.EICU_LEVELS_ETHNICITY == (
        "African American", "Asian", "Caucasian", "Hispanic",
        "Native American", "Other/Unknown", "", "OTHER")
    assert etl.EICU_LEVELS_ADMITSOURCE == (
        "Acute Care/Floor", "Chest Pain Center", "Direct Admit",
        "Emergency Department", "Floor", "ICU", "ICU to SDU", "Observation",
        "Operating Room", "Other", "Other Hospital", "Other ICU", "PACU",
        "Recovery Room", "Step-Down Unit (SDU)", "", "OTHER")
    assert etl.EICU_LEVELS_UNITTYPE == (
        "CCU-CTICU", "CSICU", "CTICU", "Cardiac ICU", "MICU", "Med-Surg ICU",
        "Neuro ICU", "SICU", "", "OTHER")
    assert etl.EICU_LEVELS_UNITSTAYTYPE == (
        "admit", "readmit", "stepdown/other", "transfer", "", "OTHER")
    # every tuple ends in the ETL's drift BUCKET, which is never a raw value
    for _col, levels in etl.EICU_CATEGORICALS:
        assert levels[-1] == "OTHER" and levels[-2] == ""
    assert [c for c, _ in etl.EICU_CATEGORICALS] == [
        "gender", "ethnicity", "hospitaladmitsource", "unitadmitsource",
        "unittype", "unitstaytype"]

    # --- plausibility windows and the two frozen unit normalisations ------
    assert etl.EICU_WINDOW_HEIGHT_CM == (100.0, 250.0)
    assert etl.EICU_WINDOW_WEIGHT_KG == (20.0, 300.0)
    assert etl.EICU_WINDOW_PRE_ICU_HRS == (0.0, 720.0)
    assert etl.EICU_WINDOW_FIO2_FRAC == (0.21, 1.0)
    assert etl.EICU_WINDOW_FIO2_PCT == (21.0, 100.0)
    assert etl.EICU_WINDOW_TEMP_C == (25.0, 45.0)
    assert etl.EICU_WINDOW_TEMP_F == (77.0, 113.0)
    # NON-OVERLAPPING by construction, so the convention mapping is unambiguous
    assert etl.EICU_WINDOW_FIO2_FRAC[1] <= etl.EICU_WINDOW_FIO2_PCT[0]
    assert etl.EICU_WINDOW_TEMP_C[1] <= etl.EICU_WINDOW_TEMP_F[0]
    # E-18: the fio2 windows are applied LOWER-CLOSED. fio2 == 0.21 (== 21) is
    # ROOM AIR -- a valid, modal observation on a ventilation-linked column,
    # and ventilation status is site-correlated, so discarding it would
    # manufacture the informative-missingness channel this protocol guards.
    # The temperature windows stay lower-OPEN: no convention value sits at
    # either endpoint, only implausible physiology.
    assert etl.EICU_ORDINAL_COLUMNS == ("intubated", "vent", "dialysis", "eyes",
                                        "motor", "verbal", "meds")
    assert etl.EICU_ORDINAL_RANGES == {
        "intubated": (0, 1), "vent": (0, 1), "dialysis": (0, 1),
        "eyes": (1, 4), "motor": (1, 6), "verbal": (1, 5), "meds": (0, 1)}

    # --- attrition ledger: frozen ORDER, and the three APACHE steps are the
    # --- site-selection diagnostic the primary arm measures but never applies
    assert etl.EICU_ATTRITION_STEPS == (
        "raw-unit-stays", "site-parseable", "outcome-known", "adult",
        "first-stay", "primary-cohort", "apache-aps-linked",
        "apache-result-linked", "apache-complete-arm")

    # --- extract identity (threat T-6) -------------------------------------
    assert etl.EICU_REFERENCE_ROW_COUNTS == {
        "patient": 200859, "hospital": 208, "apacheApsVar": 171177,
        "apachePredVar": 171177, "apachePatientResult": 297064}
    assert etl.EICU_REFERENCE_SITES == 208
    assert etl.EICU_REFERENCE_PATIENTS == 139367
    assert etl.EICU_REFERENCE_UNIT_STAYS == 200859

    # --- the leak denylist is 36 entries and every one carries a reason ----
    assert len(etl.EICU_LEAK_DENYLIST) == 36
    assert all(isinstance(c, str) and isinstance(r, str) and c and r
               for c, r in etl.EICU_LEAK_DENYLIST)
    assert len({c for c, _ in etl.EICU_LEAK_DENYLIST}) == 36

    # --- the compliance gate's own literals --------------------------------
    from experiments import run_eicu
    assert run_eicu.EICU_MAX_OUTPUT_LEN == 512      # > 208 sites, < any record array
    assert run_eicu.EICU_FORBIDDEN_OUT_KEYS == (
        "stay_id", "patient_id", "admission_id", "site_raw", "y_raw",
        "answered_mask", "x", "site_id", "comparator_predicted_mortality",
        "split_idx")
    # PIN AMENDMENT 2026-08-01 -- the ONE pre-existing pinned literal the
    # post-hoc reliability-panel work changes, recorded here so a later
    # `git log -p tests/test_constants.py` reads it as a dated design decision
    # rather than drift. It is written up in SPEC.md, "Real-data protocol",
    # under the heading "PIN AMENDMENT (2026-08-01)"; that paragraph is the
    # binding record, in the register the eICU protocol amendments A1-A6 use.
    # Ordering was SPEC first, then run_eicu.py, then this line -- never the
    # reverse, which would be editing a pin to match new code.
    #
    # Was a 5-tuple; "EICU-RELIABILITY" is APPENDED, never inserted or
    # re-ordered, so every EICU-SUMMARY.md written before that date --
    # experiments/out/ and out-sens/ included -- still parses and preserves.
    # This is an ENGINEERING pin, not a protocol amendment: EICU-PROTOCOL.md
    # SS2-13 are untouched and its A1-A6 log correctly does not mention it.
    # PIN AMENDMENT 2026-08-20 (SPEC first): "EICU-SUBGROUPS" APPENDED as the
    # seventh entry for the revision-2 post-hoc subgroup descriptives --
    # append-only, so every EICU-SUMMARY.md written under the 6-tuple still
    # parses and preserves.
    assert run_eicu.EICU_SUMMARY_SECTIONS == (
        "EICU-PREFLIGHT", "EICU-PREDICTIONS", "EICU-POOLED", "EICU-PERSITE",
        "EICU-COMPARATOR", "EICU-RELIABILITY", "EICU-SUBGROUPS")
    # the pre-declared failure criteria are literals in code, not prose
    assert run_eicu.EICU_FB_MIN_COVERAGE == 0.20
    assert run_eicu.EICU_FD_COVERAGE_ALARM == 0.90
    assert run_eicu.EICU_FD_RM_ALARM == 0.01
    assert run_eicu.EICU_FE_MIN_SITES == 200

    # E-10: F-D's two alpha- and coverage-INDEPENDENT legs. The old single-leg
    # form (alpha == 0.05 AND coverage > 0.90 AND R_M < 0.01) was demonstrated
    # to pass underneath an outcome-correlated-missingness leak that certified
    # alpha = 0.10 at coverage 0.86. Relaxing either literal below reopens it.
    assert run_eicu.EICU_LEAK_AUC_CEILING == 0.90
    assert run_eicu.EICU_LEAK_ABLATION_MAX_DROP == 0.05
    assert run_eicu.EICU_TIMING_UNVERIFIED == (
        "activetx", "thrombolytics", "graftcount", "electivesurgery",
        "ventday1", "oobventday1", "oobintubday1", "ima", "midur")
    # every timing-unverified flag is actually on the allowlist it qualifies
    assert set(run_eicu.EICU_TIMING_UNVERIFIED) <= set(etl.EICU_APV_NUMERIC)


def test_eicu_no_protocol_constant_leaked_into_the_core_package():
    """SPEC "Real-data protocol" B.0: the eICU path is an EXPERIMENT. No eICU
    constant may enter ``certgate/constants.py`` -- the core package must stay
    dataset-agnostic, exactly as it is for the synthetic grid."""
    assert not [n for n in dir(C) if n.startswith("EICU")]


def test_eicu_mock_constants_pinned():
    """Generator parameters, pinned for the same reason as SimConfig's (audit
    V7): an undeclared generator parameter made two headline numbers
    non-reproducible from the stated setup."""
    from experiments import eicu_mock as mock
    from experiments import eicu_etl as etl

    assert mock.EICU_MOCK_SEED == 20260801
    assert mock.EICU_MOCK_SMALL_SITES == 180
    assert mock.EICU_MOCK_SMALL_STAYS == 9000
    assert mock.EICU_MOCK_FULL_SITES == 208
    assert mock.EICU_MOCK_FULL_STAYS == 200859
    assert mock.EICU_MOCK_MIN_STAYS_PER_SITE == 12
    assert mock.EICU_MOCK_SITE_SIGMA == 1.1
    assert mock.EICU_MOCK_SITE_SIGMA_U == 0.5

    # The latent-severity slope. Its Bayes-optimal AUC is Phi(B/sqrt(2)) = 0.73
    # and the fitted head reaches ~0.60 out of sample. At the FROZEN corpus
    # sizes -- EICU_MOCK_SMALL_SITES = 180 (63 calibration clusters) and
    # EICU_MOCK_FULL_SITES = 208 (75) -- an ORACLE ranking's best margin 0.0354
    # sits below certify.margin_floor (0.0428 and 0.0359), so run_certgate
    # declines every rung and the default suite exercises the decline branch.
    #
    # SCOPE (2026-07-31 audit, E-20): margin_floor scales as 1/n_carrying, so
    # this comparison does NOT generalise to "any corpus size" -- the floor
    # first drops below 0.0354 at n_carrying = 77 (~217 hospitals), and a mock
    # at 900 or 1500 hospitals CERTIFIES alpha = 0.10 with this constant
    # untouched. `test_large_mock_reaches_the_certified_branch`
    # (CERTGATE_EICU_LARGE=1) exercises that branch. Raising this toward
    # synth_fixture's 2.0 is one option, not the only one, and either way it is
    # a SPEC + test_constants change, not one the generator may make on its own.
    assert mock.EICU_MOCK_SIGNAL_B == 0.85
    assert mock.EICU_MOCK_BASE_RATE == 0.095       # == SimConfig().base_rate
    _floor = __import__("certgate.certify", fromlist=["x"]).margin_floor
    assert _floor(63, C.DELTA, 0.10) > 0.0354      # small arm declines
    assert _floor(75, C.DELTA, 0.10) > 0.0354      # full arm declines
    assert _floor(77, C.DELTA, 0.10) < 0.0354      # ... and 77 does NOT
    assert min(n for n in range(50, 400)
               if _floor(n, C.DELTA, 0.10) < 0.0354) == 77

    # E-12/V7: EICU_MOCK_SIGNAL_LOAD is the per-feature loading dict that,
    # jointly with EICU_MOCK_SIGNAL_B, sets the mock's head AUC -- i.e. BOTH
    # headline numbers the comment above quotes. Leaving it unpinned let every
    # value be rewritten to 0.0 (head AUC 0.60 -> 0.48, a pure-noise outcome
    # model) with the whole suite still green: exactly the failure V7 was
    # raised about. Pinned as a digest plus the invariants that matter.
    _load = mock.EICU_MOCK_SIGNAL_LOAD
    assert isinstance(_load, dict) and len(_load) == 23
    assert set(_load) == {
        "age", "aps_urine", "aps_wbc", "aps_temperature", "aps_respiratoryrate",
        "aps_sodium", "aps_heartrate", "aps_meanbp", "aps_ph", "aps_hematocrit",
        "aps_creatinine", "aps_albumin", "aps_pao2", "aps_pco2", "aps_bun",
        "aps_glucose", "aps_bilirubin", "aps_fio2", "gcs", "aps_flag",
        "apv_flag", "apv_ejectfx", "comparator"}
    assert hashlib.sha256(
        json.dumps(sorted(_load.items()), separators=(",", ":"))
        .encode("ascii")).hexdigest() == (
        "c4610827e7c3b56f417a8d2900e50d1b8bb1f990de52d909bf0109fc2b38a3cb")
    # every keyed feature is either an ALLOWLISTED column or one of the three
    # named aggregates; not one leak column carries a loading (the leaks are
    # driven by the outcome directly, which is the point)
    _allow = ({f"aps_{c}" for c in etl.EICU_APS_NUMERIC}
              | {f"apv_{c}" for c in etl.EICU_APV_NUMERIC}
              | set(etl.EICU_PATIENT_NUMERIC)
              | {"gcs", "aps_flag", "apv_flag", "comparator"})
    assert set(_load) <= _allow
    assert all(isinstance(v, float) and math.isfinite(v)
               for v in _load.values())
    assert any(v != 0.0 for v in _load.values())

    assert mock.EICU_MOCK_MULTISTAY_RATE == 0.17
    assert mock.EICU_MOCK_AGE_MASK_RATE == 0.035   # 7081/200859
    assert mock.EICU_MOCK_STATUS_MISSING_RATE == 0.0087   # 1751/200859
    assert mock.EICU_MOCK_APS_SITE_BANDS == ((0.0048, 0.10), (0.0673, 0.40),
                                             (0.1490, 0.70), (0.7788, 0.92))
    assert mock.EICU_MOCK_RESULT_ZERO_SITE_SHARE == 0.0865
    assert mock.EICU_MOCK_SENTINEL_RATE == 0.18
    assert mock.EICU_MOCK_EMPTY_RATE == 0.04
    assert mock.EICU_MOCK_DUP_RATE == 0.002
    assert mock.EICU_MOCK_CROSS_SITE_PID_RATE == 0.004
    assert mock.EICU_MOCK_DIRTY_RATE == 0.02
    assert mock.EICU_MOCK_TABLES == ("patient", "hospital", "apacheApsVar",
                                     "apachePredVar", "apachePatientResult")
    assert mock.EICU_MOCK_HEADER_CASES == ("camel", "lower")

    # secondary generator rates
    assert mock.EICU_MOCK_AGE_BLANK_RATE == 0.004
    assert mock.EICU_MOCK_PEDIATRIC_RATE == 0.012
    assert mock.EICU_MOCK_UNLISTED_RATE == 0.02    # BELOW EICU_MAX_OTHER_SHARE
    assert mock.EICU_MOCK_DRIFT_RATE == 0.09       # --drift: ABOVE it
    assert mock.EICU_MOCK_ICU_DEATH_SHARE == 0.72
    assert mock.EICU_MOCK_RESULT_COVERAGE == (0.75, 0.98)
    assert mock.EICU_MOCK_SINGLE_VERSION_RATE == 0.11
    assert mock.EICU_MOCK_PRED_UNAVAILABLE_RATE == 0.09
    assert mock.EICU_MOCK_RECENT_PID_POOL == 512

    # the W16-vs-drift-gate relation is the whole point of those two rates
    from experiments import eicu_etl as etl
    assert mock.EICU_MOCK_UNLISTED_RATE < etl.EICU_MAX_OTHER_SHARE
    assert mock.EICU_MOCK_DRIFT_RATE > etl.EICU_MAX_OTHER_SHARE

    # the stdlib-only duplication of eicu_etl.EICU_MIN_TOTAL_SITES: eicu_mock
    # may not import numpy, so it may not import eicu_etl
    assert mock.EICU_MOCK_MIN_TOTAL_SITES == etl.EICU_MIN_TOTAL_SITES == 149

    # the small arm's split arithmetic, worked: 180 - 24 = 156 -> 62/31/63
    rest = mock.EICU_MOCK_SMALL_SITES - etl.EICU_N_TARGET_SITES
    n_tr = int(rest * C.SPLIT_FRACTIONS[0])
    n_aux = int(rest * C.SPLIT_FRACTIONS[1])
    assert (n_tr, n_aux, rest - n_tr - n_aux) == (62, 31, 63)
    assert rest - n_tr - n_aux >= C.MIN_CAL_CLUSTERS

    # the DDL schema: real column names, real DDL order, surrogate id FIRST
    assert tuple(mock.EICU_MOCK_SCHEMA) == mock.EICU_MOCK_TABLES
    assert {t: len(cols) for t, cols in mock.EICU_MOCK_SCHEMA.items()} == {
        "patient": 29, "hospital": 4, "apacheApsVar": 26,
        "apachePredVar": 51, "apachePatientResult": 23}
    for table, first in (("apacheApsVar", "apacheapsvarid"),
                         ("apachePredVar", "apachepredvarid"),
                         ("apachePatientResult", "apachepatientresultsid")):
        assert mock.EICU_MOCK_SCHEMA[table][0][0] == first
        assert mock.EICU_MOCK_SCHEMA[table][1][0] == "patientunitstayid"

    # the intercept is DERIVED from the base rate, never pinned independently,
    # so the advertised prevalence and the emitted prevalence cannot drift apart
    assert not hasattr(mock, "EICU_MOCK_SIGNAL_INTERCEPT_LITERAL")
    assert mock.EICU_MOCK_SIGNAL_INTERCEPT == pytest.approx(-2.649740738, rel=1e-9)


# ---------------------------------------------------------------------------
# POST-HOC selective reliability panel (SPEC "reliability.py", added 2026-08-01)
#
# Eighteen constants ported byte-exactly from the verified
# ``selective-reliability-panel/srp`` sandbox. They are pinned here for the same
# reason every other constant is -- a red pin is a design change, not a nuisance
# -- but they carry NO pre-registration claim: they were frozen AFTER the
# eICU-CRD v2.0 extract had been seen. That is exactly why they live in
# ``certgate/reliability.py`` and not in ``certgate/constants.py``.
# ---------------------------------------------------------------------------


def test_panel_schema_and_seed():
    # SCHEMA_VERSION is emitted verbatim AND hashed as the first bytes of
    # input_digest, which seeds every stream: renaming it (say to
    # "certgate/srp/1") moves EVERY confidence interval in the panel.
    assert RP.SCHEMA_VERSION == "srp/1"
    # srp's OWN root seed, RENAMED (never re-pointed) so it cannot be confused
    # with constants.SEED at an import site. Re-pointing it at C.SEED would
    # discard the byte-exact equivalence with the verified reference
    # implementation, which is the whole reason to port rather than re-derive.
    assert RP.PANEL_SEED == 20260731
    assert RP.PANEL_SEED != C.SEED


def test_panel_module_is_a_dag_leaf():
    """SPEC "reliability.py": the panel never sees a Head, a Cohort, or
    constants.SEED. NO ``from certgate ...`` import of any kind -- checked over
    the AST, not the text, because the module docstring says the words."""
    src = pathlib.Path(RP.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert not (node.module or "").startswith("certgate"), node.module
        elif isinstance(node, ast.Import):
            for a in node.names:
                assert not a.name.startswith("certgate"), a.name


def test_panel_bin_edges():
    # 7 bins. 1.01 is a SENTINEL above 1.0, never a bound: it is what lets
    # p == 1.0 land in the last bin under the strict `<` test (bin_bounds
    # clamps the EMITTED hi to 1.0). Replacing it with 1.0 silently drops every
    # p == 1.0 record and breaks "per-bin counts sum to n".
    assert RP.DEFAULT_BIN_EDGES == (0.0, 0.02, 0.05, 0.10, 0.20, 0.35, 0.55,
                                    1.01)
    edges = RP.DEFAULT_BIN_EDGES
    assert len(edges) == 8
    assert all(b > a for a, b in zip(edges[:-1], edges[1:]))
    assert edges[0] <= 0.0 and edges[-1] > 1.0
    # examples/explain_dashboard.py IMPORTS this tuple rather than restating
    # it; tests/test_reliability_panel.py::test_dashboard_bin_edges_match pins
    # that the dashboard and the panel actually BIN alike, not just that they
    # share a constant


def test_panel_curve_scopes():
    """The scopes the reliability CURVE is drawn for. `all` is deliberately
    absent -- reliability/ece/calibration are answered+declined only.

    Pinned because both consumers (`run_synthetic._e6_reliability_figure`,
    `run_eicu._reliability_figure`) `zip()` it against a fixed 2-element colour
    tuple: appending a third scope here would SILENTLY drop it from every
    figure rather than fail, since zip stops at the shorter operand.
    """
    assert RP.PANEL_CURVE_SCOPES == ("answered", "declined")
    # and it names real emitted blocks, in emitted order
    assert list(RP.PANEL_CURVE_SCOPES) == [
        s for s in ("answered", "declined") if s in RP.PANEL_CURVE_SCOPES]


def test_panel_decision_threshold():
    # yhat = (p >= this). It coincides with Head.predict's rule (p1 >= 0.5),
    # which is what makes skill.<scope>.model_error_rate the certgate answered
    # error rate on that scope -- a free cross-consistency check. It is
    # UNRELATED to the caller's gate tau and must not be confused with it.
    assert RP.DECISION_THRESHOLD == 0.5


def test_panel_irls_constants():
    # |logit(eps)| <= 13.815510557964274, so p == 0.0 and p == 1.0 remain
    # usable regression inputs. LOGIT_EPS and IRLS_TOL are also why `settings`
    # is EXEMPT from the emit-time round: both collapse to 0.0 at 6 dp.
    assert RP.LOGIT_EPS == 1e-6
    assert abs(math.log(1e-6 / (1 - 1e-6))) < 13.815510557964275
    assert RP.IRLS_MAX_ITER == 100          # -> 'not-converged', never a number
    assert RP.IRLS_TOL == 1e-8              # on the FULL Newton step
    # the REPORTING RANGE. |beta| past it is 'coef-out-of-range' (the MLE
    # exists but lies outside the range); 'separable' (the MLE does not exist)
    # is a DIFFERENT status decided before iterating. Collapsing the two claims
    # the wrong thing and implies the opposite operational action.
    assert RP.IRLS_MAX_ABS_COEF == 30.0
    assert RP.IRLS_MIN_WEIGHT == 1e-10      # invertible WITHOUT a ridge term
    assert RP.IRLS_MIN_RECORDS == 20


def test_panel_bootstrap_constants():
    assert RP.N_BOOT == 2000                # required VALID draws per statistic
    assert RP.CI_LEVEL == 0.95
    # the attempt budget at the production N_BOOT. BOOT_MAX_ATTEMPTS is NEVER
    # read at runtime: the enforced budget is the RELATION 2 * n_boot resolved
    # inside site_bootstrap_ci, so a lowered n_boot gets a proportionally
    # lowered budget and settings.boot_max_attempts echoes 2*n_boot.
    assert RP.BOOT_MAX_ATTEMPTS == 4000
    assert RP.BOOT_MAX_ATTEMPTS == 2 * RP.N_BOOT
    # cluster floor, checked against n_sites_carrying BEFORE any resampling
    # work (n_attempts == 0). Same measured lesson as BBSE_MIN_TARGET_SITES
    # (rho-miss up to 46% at K=2 against a nominal 2.5%).
    assert RP.MIN_SITES_FOR_CI == 10
    assert RP.MIN_SITES_FOR_CI == C.BBSE_MIN_TARGET_SITES


def test_panel_emit_constants():
    assert RP.ROUND_DP == 6                 # applied ONCE, at emit time
    assert RP.FIG_DPI == 110                # every existing experiment figure
    # the two EXHAUSTIVE status vocabularies; membership across the whole
    # adversarial fixture family is asserted in test_reliability_panel.py
    assert RP.CI_STATUSES == ("ok", "empty-bin", "too-few-sites",
                              "degenerate-resamples", "undefined-point",
                              "truncated-resamples")
    assert RP.FIT_STATUSES == ("ok", "too-few-records", "single-class",
                               "degenerate-design", "separable",
                               "coef-out-of-range", "not-converged",
                               "singular")
    # 'separable' and 'coef-out-of-range' are DISTINCT claims
    assert len(set(RP.FIT_STATUSES)) == len(RP.FIT_STATUSES) == 8
    assert len(set(RP.CI_STATUSES)) == len(RP.CI_STATUSES) == 6
    # The released EICU_reliability.csv column ORDER. Pinned literally
    # (2026-08-10) because every prior assertion was self-referential -- a
    # set-compare here and a `list(rp.PANEL_RELIABILITY_FIELDS)` header
    # assert in test_eicu_path.py -- so a reorder shipped a silently
    # rearranged published CSV with the suite fully green.
    assert RP.PANEL_RELIABILITY_FIELDS == (
        "scope", "index", "lo", "hi", "n", "n_sites_carrying",
        "mean_predicted", "observed", "ci_lo", "ci_hi",
        "ci_status", "n_boot_valid", "n_attempts")


def test_panel_post_hoc_label():
    """A6 register. The SUBSTANCE is pinned, the prose is not: wording may be
    improved without a false red, but the three load-bearing claims may not
    quietly leave."""
    label = RP.POST_HOC_LABEL
    assert isinstance(label, str)
    assert "POST-HOC" in label
    assert "9f25b491b2554d0a4bd7aaaf44081c185d01715f" in label
    assert "alters no certified quantity" in label
    assert label.startswith("[MEASURE]")     # the ETL's A6 register
    # the synthetic sibling: added-after-publication, not data-seen
    assert "POST-HOC" in RP.E6_POST_HOC_NOTE


def test_no_panel_constant_leaked_into_the_core_package():
    """SPEC "reliability.py": the ``constants.py`` block is the A-PRIORI
    pre-extract surface of the certified protocol. These eighteen values were
    frozen AFTER the extract was seen, so putting them there would place
    post-hoc values under a pre-registration claim they do not carry.
    ``harness.SIZE_BINS`` is the standing precedent for a module-local frozen
    tuple inside the core package."""
    assert not [n for n in dir(C)
                if n.startswith("PANEL") or n in (
                    "SCHEMA_VERSION", "DEFAULT_BIN_EDGES", "DECISION_THRESHOLD",
                    "N_BOOT", "BOOT_MAX_ATTEMPTS", "CI_LEVEL",
                    "MIN_SITES_FOR_CI", "ROUND_DP", "FIG_DPI", "CI_STATUSES",
                    "FIT_STATUSES", "LOGIT_EPS", "IRLS_MAX_ITER", "IRLS_TOL",
                    "IRLS_MAX_ABS_COEF", "IRLS_MIN_WEIGHT",
                    "IRLS_MIN_RECORDS", "POST_HOC_LABEL")]


def test_no_panel_regularisation_constant_exists():
    """The IRLS weight floor keeps the normal matrix invertible WITHOUT a ridge.
    NO ridge, NO shrinkage, NO penalty, NO prior, NO smoothing anywhere -- a
    fallback slope would report a number where the honest answer is a status."""
    banned = ("RIDGE", "SHRINK", "PENALT", "PRIOR", "SMOOTH", "LAMBDA_REG",
              "ALPHA_REG")
    assert not [n for n in dir(RP)
                if any(t in n.upper() for t in banned)]


def test_eicu_subgroup_posthoc_constants_pinned():
    """Revision-2 item 3b (SPEC PIN AMENDMENT 2026-08-20). POST-HOC pins:
    these constants carry NO pre-registration claim -- they were chosen after
    the extract was read and exist to keep the descriptive layer stable, the
    reliability-panel precedent. The cell floor deliberately REUSES the
    frozen eicu_etl.EICU_MIN_OUTCOME_STRATUM (no new threshold constant)."""
    from experiments import run_eicu
    from experiments import eicu_etl as etl
    assert run_eicu.EICU_SUBGROUP_DIMS == (
        "age_band", "gender", "ethnicity", "hospitaladmitsource", "unittype")
    assert run_eicu.EICU_SUBGROUP_AGE_BANDS == (
        (18, 45), (45, 65), (65, 75), (75, 200))
    assert "POST-HOC" in run_eicu.EICU_SUBGROUP_LABEL
    assert "certifies nothing" in run_eicu.EICU_SUBGROUP_LABEL
    assert etl.EICU_MIN_OUTCOME_STRATUM == 100
