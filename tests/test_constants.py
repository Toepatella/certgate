"""SPEC "Tests": literal equality for EVERY frozen constant (audit F13).

Any drift in ``constants.py`` fails here -- the lightweight, verifiable
stand-in for pre-registration.
"""
import hashlib
import json
import math
from collections import Counter

import numpy as np
import pytest

from certgate import constants as C


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
    _sent = {"aps_fio2": etl._new_sentinel_counter(),
             "aps_temperature": etl._new_sentinel_counter()}
    _u, _w = Counter(), Counter()
    assert etl._parse_apache_cell("fio2", "0.21", "aps_fio2", _sent, _u, _w) == 0.21
    assert etl._parse_apache_cell("fio2", "21", "aps_fio2", _sent, _u, _w) == 0.21
    assert etl._parse_apache_cell("fio2", "1.0", "aps_fio2", _sent, _u, _w) == 1.0
    assert etl._parse_apache_cell("fio2", "100", "aps_fio2", _sent, _u, _w) == 1.0
    assert math.isnan(etl._parse_apache_cell(
        "temperature", "45", "aps_temperature", _sent, _u, _w))
    assert math.isnan(etl._parse_apache_cell(
        "temperature", "25", "aps_temperature", _sent, _u, _w))
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
    assert run_eicu.EICU_SUMMARY_SECTIONS == (
        "EICU-PREFLIGHT", "EICU-PREDICTIONS", "EICU-POOLED", "EICU-PERSITE",
        "EICU-COMPARATOR")
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
