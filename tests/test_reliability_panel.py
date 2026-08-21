"""The POST-HOC selective reliability panel (SPEC "reliability.py").

Ported byte-exactly from the verified ``selective-reliability-panel/srp``
sandbox, so this file has two jobs at once:

1. re-assert the sandbox's own contract on certgate soil -- every number in the
   analytic fixture computed BY HAND in this file, never against whatever the
   implementation happens to return;
2. lock the NUMERICAL EQUIVALENCE with the sandbox permanently, via a pinned
   sha256 over the emitted dict on a frozen fixture. srp is neither installed
   nor in ``requirements.txt`` and must never be imported here, so the pin is
   the only thing that can carry that equivalence forward.

Speed: the frozen ``N_BOOT = 2000`` is the PRODUCTION value and only
``tests/test_constants.py`` asserts it. Everything here runs at
``FAST_N_BOOT``.
"""
import ast
import hashlib
import json
import math
import pathlib

import numpy as np
import pytest

from certgate import reliability as rp
from certgate.data import SimConfig, draw_cohort, split_sites, subset_sites
from certgate.explain import composition
from certgate.model import fit_head
from certgate.reliability import PanelError

FAST_N_BOOT = 48
FIXED_TIMESTAMP = "2026-01-01T00:00:00+00:00"
DIGEST = "a" * 64
REPO = pathlib.Path(rp.__file__).resolve().parents[1]


def fast(**overrides) -> dict:
    """Panel keyword arguments that keep the suite quick and reproducible."""
    kw = {"n_boot": FAST_N_BOOT, "timestamp": FIXED_TIMESTAMP}
    kw.update(overrides)
    return kw


def _clustered(n_sites, per_site, *, seed, spread=0.0):
    """Records nested in sites with an optional site-level random intercept."""
    rng = np.random.default_rng(seed)
    site_id = np.repeat(np.arange(n_sites, dtype=np.int64), per_site)
    offset = rng.normal(0.0, spread, size=n_sites)
    z = rng.normal(-2.0, 1.0, size=n_sites * per_site) + offset[site_id]
    p = 1.0 / (1.0 + np.exp(-z))
    y = rng.random(p.shape) < p
    return p, y.astype(bool), site_id


def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))


def _calibrated_draw(n, seed, temperature=1.0):
    """Labels from a true probability; scores are that probability re-tempered.

    ``logit(reported) = logit(true) / temperature``, so the true model of y on
    ``logit(reported)`` has slope == temperature.
    """
    rng = np.random.default_rng(seed)
    z_true = rng.normal(-1.2, 1.7, size=n)
    y = rng.random(n) < _sigmoid(z_true)
    return _sigmoid(z_true / temperature), y.astype(bool)


# ==========================================================================
# 1. the analytic fixture -- every number computed by hand IN THIS FILE
# ==========================================================================
#
#     idx   p      y      answered  site   bin
#      0    0.01   True   yes       0      0   [0.00, 0.02)
#      1    0.01   False  yes       0      0
#      2    0.01   False  yes       0      0
#      3    0.01   False  yes       1      0
#      4    0.30   True   yes       1      4   [0.20, 0.35)
#      5    0.30   False  yes       1      4
#      6    0.60   True   yes       2      6   [0.55, 1.00]
#      7    0.60   True   yes       2      6
#      8    0.80   True   yes       2      6
#      9    1.00   False  yes       3      6
#     10    0.10   False  no        3      3   [0.10, 0.20)
#     11    0.10   False  no        4      3
#     12    0.90   True   no        4      6
#     13    0.90   True   no        4      6
#
# Five sites is BELOW MIN_SITES_FOR_CI = 10, so all 18 intervals are suppressed
# with n_attempts == 0: ZERO bootstrap cost, and this one fixture covers all six
# statistics arithmetically.

A_P = np.array([0.01, 0.01, 0.01, 0.01, 0.30, 0.30, 0.60, 0.60, 0.80, 1.00,
                0.10, 0.10, 0.90, 0.90])
A_Y = np.array([True, False, False, False, True, False, True, True, True,
                False, False, False, True, True])
A_ANSWERED = np.array([True] * 10 + [False] * 4)
A_SITE = np.array([0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 4, 4, 4], dtype=np.int64)

TOL = 1e-6      # the emitted values are rounded to six decimal places


@pytest.fixture(scope="module")
def analytic():
    return rp.selective_reliability_panel(A_P, A_ANSWERED, A_SITE, A_Y,
                                          n_boot=32, timestamp=FIXED_TIMESTAMP)


def test_analytic_fixture_every_number_by_hand(analytic):
    """Counts, both reliability curves, both ECEs, the Brier, all three skill
    triples, both contrasts and the three-way composition -- each asserted
    against arithmetic written out beside it."""
    c = analytic["counts"]
    assert c["n_records"] == 14 and c["n_sites"] == 5
    assert c["n_answered"] == 10 and c["n_declined"] == 4
    assert c["coverage"] == pytest.approx(10.0 / 14.0, abs=TOL)
    assert c["n_positive_all"] == 7
    assert c["reference_supplied"] is False
    # answered records touch sites 0,1,2,3; declined records touch sites 3,4
    assert c["n_sites_answered"] == 4 and c["n_sites_declined"] == 2

    # -- item 1, answered ---------------------------------------------------
    bins = analytic["reliability"]["answered"]
    assert len(bins) == 7
    # bin 0: four records at p = 0.01, one positive -> observed 1/4
    assert bins[0]["n"] == 4
    assert bins[0]["mean_predicted"] == pytest.approx(0.01, abs=TOL)
    assert bins[0]["observed"] == pytest.approx(0.25, abs=TOL)
    assert bins[0]["n_sites_carrying"] == 2                     # sites 0 and 1
    assert (bins[0]["lo"], bins[0]["hi"]) == (0.0, 0.02)
    for b in (1, 2, 3, 5):                                       # empty bins
        assert bins[b]["n"] == 0
        assert bins[b]["mean_predicted"] is None
        assert bins[b]["observed"] is None
        assert bins[b]["ci"] is None
        assert bins[b]["ci_status"] == "empty-bin"
    # bin 4: two records at 0.30, one positive
    assert bins[4]["n"] == 2
    assert bins[4]["mean_predicted"] == pytest.approx(0.30, abs=TOL)
    assert bins[4]["observed"] == pytest.approx(0.50, abs=TOL)
    assert bins[4]["n_sites_carrying"] == 1                      # both on site 1
    # bin 6: 0.60, 0.60, 0.80, 1.00 -> mean 0.75; three positives -> 0.75
    assert bins[6]["n"] == 4
    assert bins[6]["mean_predicted"] == pytest.approx(0.75, abs=TOL)
    assert bins[6]["observed"] == pytest.approx(0.75, abs=TOL)
    assert bins[6]["n_sites_carrying"] == 2                      # sites 2 and 3
    assert bins[6]["lo"] == 0.55 and bins[6]["hi"] == 1.0        # sentinel clamped
    assert sum(b["n"] for b in bins) == 10                       # p == 1.0 counted

    # -- item 1, declined ---------------------------------------------------
    dec = analytic["reliability"]["declined"]
    assert dec[3]["n"] == 2 and dec[3]["observed"] == pytest.approx(0.0, abs=TOL)
    assert dec[6]["n"] == 2 and dec[6]["observed"] == pytest.approx(1.0, abs=TOL)
    assert sum(b["n"] for b in dec) == 4

    # -- item 3, ECE --------------------------------------------------------
    # answered: (4/10)*|0.01-0.25| + (2/10)*|0.30-0.50| + (4/10)*|0.75-0.75|
    #         = 0.4*0.24 + 0.2*0.20 + 0.0 = 0.096 + 0.040 = 0.136
    assert 0.4 * 0.24 + 0.2 * 0.20 == pytest.approx(0.136, abs=1e-12)
    assert analytic["ece"]["answered"]["ece"] == pytest.approx(0.136, abs=TOL)
    assert analytic["ece"]["answered"]["n"] == 10
    assert analytic["ece"]["answered"]["n_bins_nonempty"] == 3
    # declined: (2/4)*|0.10-0.00| + (2/4)*|0.90-1.00| = 0.05 + 0.05 = 0.10
    assert analytic["ece"]["declined"]["ece"] == pytest.approx(0.10, abs=TOL)
    assert analytic["ece"]["declined"]["n_bins_nonempty"] == 2

    # -- item 4, Brier ------------------------------------------------------
    terms = [(0.01 - 1.0) ** 2, 0.01 ** 2, 0.01 ** 2, 0.01 ** 2,
             (0.30 - 1.0) ** 2, 0.30 ** 2, (0.60 - 1.0) ** 2, (0.60 - 1.0) ** 2,
             (0.80 - 1.0) ** 2, (1.00 - 0.0) ** 2]
    assert sum(terms) == pytest.approx(2.9204, abs=1e-12)
    assert analytic["brier"]["primary_answered"]["value"] == pytest.approx(
        0.29204, abs=TOL)                                        # 2.9204 / 10
    assert analytic["brier"]["primary_answered"]["n"] == 10
    assert analytic["brier"]["reference"] is None                # explicit null

    # -- item 5, the skill triples ------------------------------------------
    # answered: yhat = p >= 0.5 -> [F,F,F,F,F,F,T,T,T,T]; y = [T,F,F,F,T,F,T,T,T,F]
    # disagreements at 0, 4, 9 -> 3/10; positives 0,4,6,7,8 -> 5/10, an EXACT tie
    s = analytic["skill"]["answered"]
    assert s["n"] == 10 and s["n_positive"] == 5
    assert s["positive_rate"] == pytest.approx(0.5, abs=TOL)
    assert s["model_error_rate"] == pytest.approx(0.3, abs=TOL)
    assert s["constant_predictor_class"] is False   # STRICT >: a 0.5 tie is NEGATIVE
    assert s["constant_predictor_error_rate"] == pytest.approx(0.5, abs=TOL)
    assert s["skill_margin"] == pytest.approx(0.2, abs=TOL)      # 0.5 - 0.3
    # declined: yhat = [F,F,T,T] == y -> no disagreement
    d = analytic["skill"]["declined"]
    assert d["model_error_rate"] == pytest.approx(0.0, abs=TOL)
    assert d["skill_margin"] == pytest.approx(0.5, abs=TOL)
    # all: 7 positives of 14 -> baseline 0.5; 3 disagreements of 14
    t = analytic["skill"]["all"]
    assert t["model_error_rate"] == pytest.approx(3.0 / 14.0, abs=TOL)
    assert t["skill_margin"] == pytest.approx(0.285714, abs=TOL)  # 0.5 - 3/14

    # -- item 5b, the contrasts ---------------------------------------------
    con = analytic["skill"]["contrast"]
    assert con["answered_minus_all"] == pytest.approx(-0.085714, abs=TOL)
    assert con["answered_minus_declined"] == pytest.approx(-0.3, abs=TOL)
    assert "n_sites_carrying" not in con      # THE ONLY block without that key

    # -- item 6, composition ------------------------------------------------
    ca = analytic["composition"]["answered"]
    assert ca["n_predicted_positive"] == 4      # 0.60, 0.60, 0.80, 1.00
    assert ca["predicted_positive_fraction"] == pytest.approx(0.4, abs=TOL)
    assert ca["n_observed_positive"] == 5
    cd = analytic["composition"]["declined"]
    assert cd["n_predicted_positive"] == 2      # 0.90, 0.90
    assert cd["predicted_positive_fraction"] == pytest.approx(0.5, abs=TOL)
    ct = analytic["composition"]["all"]
    assert ct["n_predicted_positive"] == 6
    assert ct["predicted_positive_fraction"] == pytest.approx(6.0 / 14.0, abs=TOL)
    assert ca["n"] + cd["n"] == ct["n"]

    # -- item 2 declines and says why ---------------------------------------
    cal = analytic["calibration"]["answered"]
    assert cal["status"] == "too-few-records"   # ten answered < IRLS_MIN_RECORDS
    assert cal["slope"] is None and cal["intercept"] is None


def test_analytic_fixture_suppresses_all_eighteen_intervals_before_any_work(analytic):
    """Five sites is below the cluster floor: every interval is suppressed and
    NO resampling work was done (n_attempts == 0 everywhere)."""
    suppressed = 0
    for scope in ("answered", "declined"):
        for record in analytic["reliability"][scope]:
            assert record["ci"] is None
            assert record["ci_status"] in ("too-few-sites", "empty-bin")
            assert record["n_attempts"] == 0 and record["n_boot_valid"] == 0
            suppressed += 1
        for key in ("calibration", "ece"):
            assert analytic[key][scope]["ci"] is None
            suppressed += 1
    assert analytic["brier"]["primary_answered"]["ci"] is None
    assert analytic["brier"]["primary_answered"]["n_attempts"] == 0
    for scope in ("answered", "declined", "all"):
        assert analytic["skill"][scope]["ci"] is None
        assert analytic["composition"][scope]["ci"] is None
    assert analytic["skill"]["contrast"]["ci"] is None
    assert suppressed == 18


def test_analytic_reference_block_on_the_same_records():
    """Denominator-matched reference, also computed by hand."""
    ref = np.full(14, np.nan)
    ref[0] = 0.20   # y True -> (0.2-1)^2 = 0.64  ; primary (0.01-1)^2 = 0.9801
    ref[4] = 0.50   # y True -> 0.25             ; primary (0.30-1)^2 = 0.49
    ref[6] = 0.90   # y True -> 0.01             ; primary (0.60-1)^2 = 0.16
    ref[8] = 0.70   # y True -> 0.09             ; primary (0.80-1)^2 = 0.04
    ref[12] = 0.50  # DECLINED -- must be ignored entirely

    panel = rp.selective_reliability_panel(A_P, A_ANSWERED, A_SITE, A_Y, ref,
                                           n_boot=16, timestamp=FIXED_TIMESTAMP)
    block = panel["brier"]["reference"]
    assert block["n_available"] == 4
    assert block["available_share"] == pytest.approx(0.4, abs=TOL)
    assert block["brier_reference"] == pytest.approx(
        (0.64 + 0.25 + 0.01 + 0.09) / 4.0, abs=TOL)
    assert block["brier_reference"] == pytest.approx(0.2475, abs=TOL)
    assert block["brier_primary_matched"] == pytest.approx(
        (0.9801 + 0.49 + 0.16 + 0.04) / 4.0, abs=TOL)
    assert block["brier_primary_matched"] == pytest.approx(0.417525, abs=TOL)
    assert block["brier_difference"] == pytest.approx(0.2475 - 0.417525, abs=TOL)
    # the UNMATCHED primary keeps the WIDER denominator and is a different number
    assert panel["brier"]["primary_answered"]["value"] == pytest.approx(
        0.29204, abs=TOL)
    assert panel["counts"]["reference_supplied"] is True


# ==========================================================================
# 2. binning and the 1.01 sentinel
# ==========================================================================


def test_bin_assignment_and_the_1_01_sentinel():
    edges = rp.DEFAULT_BIN_EDGES
    # p == 1.0 lands in the LAST bin -- the sentinel's whole purpose
    assert int(rp.assign_bins(np.array([1.0]), edges)[0]) == len(edges) - 2
    # bin_bounds clamps the EMITTED hi, so the last bin READS [0.55, 1.0]
    assert rp.bin_bounds(edges)[-1] == (0.55, 1.0)
    # per-bin counts sum to the subset size for an arbitrary p
    p = np.linspace(0.0, 1.0, 501)
    bins = rp.assign_bins(p, edges)
    assert int(np.bincount(bins, minlength=len(edges) - 1).sum()) == p.size
    assert not bool((bins < 0).any())
    # replacing 1.01 with 1.0 would silently DROP every p == 1.0 record
    assert int(rp.assign_bins(np.array([1.0]), (0.0, 0.5, 1.0))[0]) == -1
    # outside the span -> -1 (lower-closed / upper-open)
    assert rp.assign_bins(np.array([-0.1, 2.0]), edges).tolist() == [-1, -1]


def test_an_unbinned_record_is_a_loud_error_not_a_silent_drop():
    """Dropping changes the denominator; folding into a neighbour corrupts the
    flattened (site, bin) index arithmetic. Both consumers raise, naming the
    FIRST offending index and value."""
    p = np.array([0.1, 0.9, 0.4])
    y = np.array([True, False, True])
    sid = np.zeros(3, dtype=np.int64)
    narrow = (0.0, 0.5, 0.8)            # 0.9 falls outside the span
    for fn in (rp.reliability_curve, rp.expected_calibration_error):
        with pytest.raises(PanelError) as excinfo:
            fn(p, y, sid, 1, digest=DIGEST, scope="answered", bin_edges=narrow,
               n_boot=4)
        assert "p[1]" in str(excinfo.value)
        assert "0.9" in str(excinfo.value)


def test_dashboard_bin_edges_match(tmp_path):
    """The panel and the explain dashboard must bin the same probabilities the
    same way.

    The dashboard now IMPORTS ``DEFAULT_BIN_EDGES`` instead of restating it, so
    the tuples are identical by construction. That alone is NOT what this test
    checks: a shared constant does not make two instruments bin the same way,
    and an identity assertion on the alias would pass for a dashboard that
    imported the tuple and then binned a different quantity, a different scope,
    or a shifted boundary. This asserts the EMITTED BINS AGREE, on real
    payloads, which is the drift that matters and which neither the old
    source-parsing pin nor a bare identity check covered.

    Measured discriminating power on this fixture: binning ``score`` instead of
    ``predict_proba`` -> [0]*6 + [497] vs [275, 115, 64, 34, 0, 0, 9]; binning
    all records instead of the answered ones -> the last three bins fill;
    moving one boundary 0.02 -> 0.03 -> the first two bins move. It does NOT
    catch replacing the 1.01 sentinel with 1.0, because that only shows up on a
    record at exactly ``p == 1.0`` and this fixture has none -- that one is
    pinned directly by ``test_bin_assignment_and_the_1_01_sentinel`` here and
    by ``test_panel_bin_edges`` in tests/test_constants.py.
    """
    from examples import explain_dashboard as dash

    # cheap belt: the literal must not come back (the import is what makes the
    # two tuples one object; this catches a revert to a second literal)
    src = (REPO / "examples" / "explain_dashboard.py").read_text(encoding="utf-8")
    literals = [node for node in ast.walk(ast.parse(src))
                if isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "edges"
                and isinstance(node.value, (ast.List, ast.Tuple))]
    assert not literals, (
        "examples/explain_dashboard.py assigns `edges` from a LITERAL again -- "
        "import rp.DEFAULT_BIN_EDGES so the two instruments cannot drift")

    rng = np.random.default_rng(20260802)
    cfg = SimConfig(d=4, size_mu=4.0, size_sigma=0.4)
    cohort = draw_cohort(cfg, 24, rng)
    train, _aux, cal = split_sites(cohort, rng)
    head = fit_head(train)
    tau = 0.8

    out = tmp_path / "explain_dashboard.html"
    dash.build_dashboard(head, cal.x, tau, str(out), oracle_y=cal.y,
                         site_ids=[cal.site_labels[i] for i in cal.site_id])
    # json.dumps emits the payload on ONE line, so no multi-line parse is
    # needed (and a non-greedy regex would stop at a `};` inside a string)
    prefix = "const DATA = "
    line = next(l for l in out.read_text(encoding="utf-8").splitlines()
                if l.startswith(prefix))
    payload = json.loads(line[len(prefix):].rstrip(";"))

    panel = rp.panel_from_head(head, cal.x, cal.y, cal.site_id, tau, **fast())

    # 1. same bin boundaries, including the 1.01 sentinel clamped to 1.0
    assert [(b["lo"], b["hi"]) for b in payload["reliability"]] == \
        list(rp.bin_bounds(rp.DEFAULT_BIN_EDGES))
    assert [(b["lo"], b["hi"]) for b in panel["reliability"]["answered"]] == \
        list(rp.bin_bounds(rp.DEFAULT_BIN_EDGES))

    # 2. same MEMBERSHIP: the dashboard bins the answered records, so its
    #    per-bin n must equal the panel's answered per-bin n, bin for bin.
    #    This is what catches a `>` for a `>=`, a dropped sentinel, or a
    #    shifted boundary -- none of which the shared constant prevents.
    assert [b["n"] for b in payload["reliability"]] == \
        [b["n"] for b in panel["reliability"]["answered"]]
    assert sum(b["n"] for b in payload["reliability"]) == \
        panel["counts"]["n_answered"]

    # 3. and the same binned QUANTITY (predict_proba, never score): a dashboard
    #    binning `score` would put every record in the top three bins.
    for d_bin, p_bin in zip(payload["reliability"],
                            panel["reliability"]["answered"]):
        if d_bin["n"]:
            assert d_bin["mean_predicted"] == pytest.approx(
                p_bin["mean_predicted"], abs=1e-4)


# ==========================================================================
# 3. THE conflation trap: the binned quantity is predict_proba, never score
# ==========================================================================


@pytest.fixture(scope="module")
def head_cohort():
    """A real fitted head over a real multi-site target pool."""
    rng = np.random.default_rng(20260801)
    cfg = SimConfig(d=4, size_mu=4.0, size_sigma=0.4)
    cohort = draw_cohort(cfg, 26, rng)
    train, _aux, cal = split_sites(cohort, rng)
    head = fit_head(train)
    target = subset_sites(cal, np.arange(min(14, cal.n_sites)))
    return head, target


def test_the_binned_quantity_is_predict_proba_not_score(head_cohort):
    """THE mutation-killer for the known trap.

    ``score(x) = max(p1, 1-p1)`` lives in [0.5, 1], so a panel built on it has
    ZERO occupancy in every bin below 0.5 and an inverted calibration slope --
    yet it passes ``validate_inputs`` silently, because it is finite and in
    [0, 1]. Only this test catches the substitution.
    """
    head, tgt = head_cohort
    p1 = np.asarray(head.predict_proba(tgt.x), dtype=np.float64)
    conf = np.asarray(head.score(tgt.x), dtype=np.float64)
    tau = 0.8
    answered = conf >= tau

    proba_panel = rp.selective_reliability_panel(
        p1, answered, tgt.site_id, tgt.y, **fast())
    score_panel = rp.selective_reliability_panel(
        conf, answered, tgt.site_id, tgt.y, **fast())

    low = [b for b in proba_panel["reliability"]["answered"] if b["hi"] <= 0.5]
    assert low, "the frozen edges must define at least one bin at or below 0.5"
    assert any(b["n"] > 0 for b in low), (
        "predict_proba must populate at least one bin at or below 0.5")
    for b in score_panel["reliability"]["answered"]:
        if b["hi"] <= 0.5:
            assert b["n"] == 0, (
                "score lives in [0.5, 1]: every bin below 0.5 must be empty, "
                "which is what makes a score-fed panel meaningless")
    # and the driver entry point reproduces the predict_proba panel exactly
    via_head = rp.panel_from_head(head, tgt.x, tgt.y, tgt.site_id, tau, **fast())
    assert via_head["input_digest"] == proba_panel["input_digest"]
    assert via_head == proba_panel


def test_panel_from_head_cross_checks_the_deployed_mask(head_cohort):
    head, tgt = head_cohort
    tau = 0.8
    gate = np.asarray(head.score(tgt.x), dtype=np.float64) >= tau

    # (a) mask omitted -> the gate is used
    a = rp.panel_from_head(head, tgt.x, tgt.y, tgt.site_id, tau, **fast())
    assert a["counts"]["n_answered"] == int(gate.sum())

    # (b) correct mask supplied -> no raise, identical panel
    b = rp.panel_from_head(head, tgt.x, tgt.y, tgt.site_id, tau,
                           answered_mask=gate, **fast())
    assert a == b

    # (c) a mask that disagrees at a single record raises, named
    bad = gate.copy()
    bad[int(np.flatnonzero(gate)[0])] = False
    with pytest.raises(PanelError) as excinfo:
        rp.panel_from_head(head, tgt.x, tgt.y, tgt.site_id, tau,
                           answered_mask=bad, **fast())
    assert "deployed-mask-mismatch" in str(excinfo.value)

    # (d) tau_star=None with an all-False mask: the legal no-rung-certified case
    none_mask = np.zeros(tgt.y.shape[0], dtype=bool)
    c = rp.panel_from_head(head, tgt.x, tgt.y, tgt.site_id, None,
                           answered_mask=none_mask, **fast())
    assert c["counts"]["n_answered"] == 0
    assert c["skill"]["answered"]["model_error_rate"] is None
    assert c["skill"]["answered"]["ci_status"] == "undefined-point"
    assert c["brier"]["primary_answered"]["value"] is None
    assert c["brier"]["primary_answered"]["ci_status"] == "undefined-point"
    assert c["skill"]["contrast"]["answered_minus_all"] is None
    json.dumps(c, allow_nan=False)

    # tau_star None AND no mask is refused: the panel will not invent a gate
    with pytest.raises(PanelError) as excinfo:
        rp.panel_from_head(head, tgt.x, tgt.y, tgt.site_id, None, **fast())
    assert "no-gate-supplied" in str(excinfo.value)


def test_a_rounded_tau_is_what_deployed_mask_mismatch_catches(head_cohort):
    """A mask re-derived from a tau ROUNDED to 6 dp disagrees with the deployed
    one at the boundary, and that disagreement is the whole point of the
    cross-check. Constructed exactly, not by luck: pick a score whose 6-dp
    rounding moves it UP, deploy at that RAW score as tau (so the record is
    answered), then re-derive the mask from the rounded tau -- the record falls
    out and the panel must refuse."""
    head, tgt = head_cohort
    conf = np.asarray(head.score(tgt.x), dtype=np.float64)
    rounds_up = np.flatnonzero(np.array([round(float(s), 6) > float(s)
                                         for s in conf]))
    assert rounds_up.size, "no score rounds up at 6 dp -- rebuild the fixture"
    raw_tau = float(conf[rounds_up[0]])
    rounded = round(raw_tau, 6)
    assert rounded > raw_tau
    stale = conf >= rounded                     # the mask a rounded tau produces
    deployed = conf >= raw_tau
    assert not np.array_equal(stale, deployed)  # they differ AT THE BOUNDARY

    # the deployed mask at the raw tau is accepted
    rp.panel_from_head(head, tgt.x, tgt.y, tgt.site_id, raw_tau,
                       answered_mask=deployed, **fast())
    # the stale one is refused, by name
    with pytest.raises(PanelError) as excinfo:
        rp.panel_from_head(head, tgt.x, tgt.y, tgt.site_id, raw_tau,
                           answered_mask=stale, **fast())
    assert "deployed-mask-mismatch" in str(excinfo.value)


# ==========================================================================
# 4. the bootstrap: unit, replay, top-up-or-decline, cluster floor
# ==========================================================================


def _rate_closure(y, order, starts):
    def stat(idx):
        rows = rp.gather_sites(order, starts, idx)
        if rows.size == 0:
            return None
        return (float(y[rows].sum()) / float(rows.size),)
    return stat


def test_bootstrap_replay_matches_an_independent_rng():
    """The strictest reading of the contract, replayed line by line: the draw is
    ``rng.integers(0, n_sites, n_sites)`` from the FULL population, and the
    quantile is ONE np.quantile(..., method='linear') call."""
    n_sites, per_site, n_boot = 30, 20, FAST_N_BOOT
    rng_data = np.random.default_rng(7)
    site_rate = rng_data.random(n_sites)
    site_id = np.repeat(np.arange(n_sites, dtype=np.int64), per_site)
    y = rng_data.random(n_sites * per_site) < site_rate[site_id]
    order, starts = rp.group_by_site(site_id, n_sites)

    out = rp.site_bootstrap_ci(_rate_closure(y, order, starts), ("rate",),
                               n_sites, n_sites,
                               rng=rp.derive_rng(DIGEST, "replay"), n_boot=n_boot)

    replay = rp.derive_rng(DIGEST, "replay")
    values = np.empty(n_boot, dtype=np.float64)
    for b in range(n_boot):
        idx = replay.integers(0, n_sites, n_sites)
        rows = rp.gather_sites(order, starts, idx)
        values[b] = y[rows].sum() / rows.size
    lo, hi = np.quantile(values, [0.025, 0.975], method="linear")

    assert out["ci_status"] == "ok"
    assert out["n_boot_valid"] == n_boot and out["n_attempts"] == n_boot
    assert out["ci"]["rate"]["lo"] == pytest.approx(float(lo), abs=1e-12)
    assert out["ci"]["rate"]["hi"] == pytest.approx(float(hi), abs=1e-12)


def test_a_site_drawn_twice_doubles_both_numerator_and_denominator():
    """No two-stage resampling: within-site records are never redrawn."""
    site_id = np.repeat(np.arange(4, dtype=np.int64), 5)
    y = np.zeros(20, dtype=bool)
    y[:5] = True                       # site 0 all positive, sites 1-3 negative
    order, starts = rp.group_by_site(site_id, 4)
    stat = _rate_closure(y, order, starts)
    assert stat(np.array([0, 0, 1, 2], dtype=np.int64))[0] == pytest.approx(0.5)
    assert stat(np.array([0, 1, 2, 3], dtype=np.int64))[0] == pytest.approx(0.25)
    assert stat(np.array([1, 2, 3, 3], dtype=np.int64))[0] == pytest.approx(0.0)


def test_site_bootstrap_is_wider_than_a_record_bootstrap():
    """RP-2. Half the sites sit at rate 0.9, half at 0.1.

    A record bootstrap sees 2000 near-independent Bernoulli draws around 0.5 and
    produces a narrow interval; a site bootstrap sees 40 exchangeable site means
    and produces a much wider one. A record bootstrap HERE would reintroduce,
    inside the diagnostic layer, exactly the record-as-unit failure E7 exists to
    demonstrate.
    """
    n_sites, per_site, n_boot = 40, 50, 400
    rng_data = np.random.default_rng(99)
    site_rate = np.where(np.arange(n_sites) % 2 == 0, 0.9, 0.1)
    site_id = np.repeat(np.arange(n_sites, dtype=np.int64), per_site)
    y = rng_data.random(n_sites * per_site) < site_rate[site_id]
    order, starts = rp.group_by_site(site_id, n_sites)

    out = rp.site_bootstrap_ci(_rate_closure(y, order, starts), ("rate",),
                               n_sites, n_sites,
                               rng=rp.derive_rng(DIGEST, "clustered"), n_boot=n_boot)
    assert out["ci_status"] == "ok"
    site_width = out["ci"]["rate"]["hi"] - out["ci"]["rate"]["lo"]

    # the record-level comparator is computed HERE and nowhere in the module
    rec_rng = np.random.default_rng(12345)
    rec = np.array([y[rec_rng.integers(0, y.size, y.size)].mean()
                    for _ in range(n_boot)])
    rlo, rhi = np.quantile(rec, [0.025, 0.975], method="linear")
    record_width = float(rhi - rlo)
    assert record_width < 0.06, "sanity: the record interval must be narrow here"
    assert site_width > 3.0 * record_width, (
        f"site interval {site_width:.4f} is not materially wider than the record "
        f"interval {record_width:.4f} -- the resampling unit has moved off the site")

    # control: one record per site, so the two units coincide
    n_flat = 400
    flat_y = np.random.default_rng(4).random(n_flat) < 0.5
    flat_sid = np.arange(n_flat, dtype=np.int64)
    forder, fstarts = rp.group_by_site(flat_sid, n_flat)
    flat = rp.site_bootstrap_ci(_rate_closure(flat_y, forder, fstarts), ("rate",),
                                n_flat, n_flat,
                                rng=rp.derive_rng(DIGEST, "unclustered"),
                                n_boot=n_boot)
    fwidth = flat["ci"]["rate"]["hi"] - flat["ci"]["rate"]["lo"]
    frec_rng = np.random.default_rng(555)
    frec = np.array([flat_y[frec_rng.integers(0, n_flat, n_flat)].mean()
                     for _ in range(n_boot)])
    flo, fhi = np.quantile(frec, [0.025, 0.975], method="linear")
    assert 0.7 < fwidth / float(fhi - flo) < 1.4


def test_top_up_or_decline_attempt_arithmetic():
    """Pure closures, no data, exact integers."""
    state = {"i": 0}

    def one_in_five(idx):
        state["i"] += 1
        return None if state["i"] % 5 == 0 else (float(state["i"]),)

    out = rp.site_bootstrap_ci(one_in_five, ("x",), 20, 20,
                               rng=rp.derive_rng(DIGEST, "topup"),
                               n_boot=100, max_attempts=200)
    assert out["ci_status"] == "ok" and out["n_boot_valid"] == 100
    assert out["n_attempts"] == 124          # 1..124, every fifth rejected -> 24

    state2 = {"i": 0}

    def three_in_five(idx):
        state2["i"] += 1
        return None if state2["i"] % 5 in (1, 2, 3) else (float(state2["i"]),)

    out = rp.site_bootstrap_ci(three_in_five, ("x",), 20, 20,
                               rng=rp.derive_rng(DIGEST, "cap"),
                               n_boot=100, max_attempts=200)
    assert out["ci"] is None
    assert out["ci_status"] == "degenerate-resamples"
    assert out["n_attempts"] == 200
    assert out["n_boot_valid"] == 80         # honest count, reported NOT quantiled

    # the enforced budget is the RELATION 2 * n_boot, resolved at runtime -- not
    # the frozen BOOT_MAX_ATTEMPTS, which is never read
    out = rp.site_bootstrap_ci(lambda idx: None, ("x",), 20, 20,
                               rng=rp.derive_rng(DIGEST, "budget"), n_boot=73)
    assert out["ci_status"] == "degenerate-resamples"
    assert out["n_attempts"] == 2 * 73


def test_a_non_finite_draw_is_invalid_not_quantiled():
    for bad in (lambda idx: (float("nan"),),
                lambda idx: (float("inf"),)):
        out = rp.site_bootstrap_ci(bad, ("x",), 20, 20,
                                   rng=rp.derive_rng(DIGEST, "bad"),
                                   n_boot=20, max_attempts=40)
        assert out["ci"] is None
        assert out["ci_status"] == "degenerate-resamples"
        assert out["n_boot_valid"] == 0 and out["n_attempts"] == 40


def test_cluster_floor_suppresses_before_any_work():
    calls = {"n": 0}

    def stat(idx):
        calls["n"] += 1
        return (1.0,)

    out = rp.site_bootstrap_ci(stat, ("x",), 40, rp.MIN_SITES_FOR_CI - 1,
                               rng=rp.derive_rng(DIGEST, "floor"), n_boot=100)
    assert out["ci"] is None and out["ci_status"] == "too-few-sites"
    assert out["n_attempts"] == 0 and out["n_boot_valid"] == 0
    assert calls["n"] == 0, "suppression must happen BEFORE any resampling work"
    assert out["n_sites_carrying"] == rp.MIN_SITES_FOR_CI - 1
    assert set(out) == set(rp.null_ci("too-few-sites"))

    # exactly at the floor the interval IS produced
    at = rp.site_bootstrap_ci(lambda idx: (float(idx.sum()),), ("x",), 40,
                              rp.MIN_SITES_FOR_CI,
                              rng=rp.derive_rng(DIGEST, "atfloor"), n_boot=32)
    assert at["ci_status"] == "ok"

    # the DRAW population stays the full n_sites while the FLOOR is checked
    # against carrying -- passing carrying as n_sites would redefine the
    # population per bin and the bins would stop averaging over the same thing
    seen = []
    rp.site_bootstrap_ci(lambda idx: (float(seen.append(int(idx.max())) or 1.0),),
                         ("x",), 30, 12, rng=rp.derive_rng(DIGEST, "population"),
                         n_boot=100)
    assert max(seen) >= 20, "indices must span the full 30-site population"


def test_a_multi_name_statistic_shares_one_stream():
    """Exact relations between names survive because all names are quantiled
    from the SAME valid draws. Each interval is still MARGINAL."""
    out = rp.site_bootstrap_ci(
        lambda idx: (float(idx.sum()), 2.0 * float(idx.sum()), float(idx.sum()) - 3.0),
        ("a", "b", "c"), 20, 20, rng=rp.derive_rng(DIGEST, "triple"), n_boot=64)
    assert set(out["ci"]) == {"a", "b", "c"}
    assert out["ci"]["b"]["lo"] == pytest.approx(2.0 * out["ci"]["a"]["lo"], abs=1e-9)
    assert out["ci"]["c"]["hi"] == pytest.approx(out["ci"]["a"]["hi"] - 3.0, abs=1e-9)


# ==========================================================================
# 5. the IRLS calibration fit
# ==========================================================================


def test_calibration_fit_status_coverage():
    """By construction, no mocking, point fits only (no bootstrap, so fast).
    All eight FIT_STATUSES are reachable and 'separable' and
    'coef-out-of-range' are DISTINCT claims."""
    seen = set()

    ok1 = rp.fit_calibration_line(*_calibrated_draw(20000, 101, 1.0))
    assert ok1["status"] == "ok"
    assert ok1["slope"] == pytest.approx(1.0, abs=0.12)
    assert ok1["intercept"] == pytest.approx(0.0, abs=0.12)
    seen.add(ok1["status"])

    over = rp.fit_calibration_line(*_calibrated_draw(20000, 102, 0.5))
    assert over["slope"] == pytest.approx(0.5, abs=0.12)     # over-dispersed
    under = rp.fit_calibration_line(*_calibrated_draw(20000, 103, 2.0))
    assert under["slope"] == pytest.approx(2.0, abs=0.40)    # under-dispersed
    assert under["slope"] - over["slope"] > 1.0              # NO shrinkage

    # the step-halving boundary: slope ~25 is UNDER the 30.0 bound -> 'ok'
    big = rp.fit_calibration_line(*_calibrated_draw(20000, 211, 25.0))
    assert big["status"] == "ok"
    assert big["slope"] == pytest.approx(25.0, rel=0.15)
    assert abs(big["slope"]) < rp.IRLS_MAX_ABS_COEF

    # the MLE exists and is finite but lies OUTSIDE the reporting range
    out_of_range = rp.fit_calibration_line(*_calibrated_draw(20000, 210, 35.0))
    assert out_of_range["status"] == "coef-out-of-range"
    assert out_of_range["slope"] is None
    assert out_of_range["iterations"] > 0        # it iterated; not the pre-loop test
    seen.add(out_of_range["status"])

    # the MLE does NOT exist: decided BEFORE iterating
    n = 200
    y_sep = np.arange(n) % 2 == 0
    sep = rp.fit_calibration_line(np.where(y_sep, 0.501, 0.499), y_sep)
    assert sep["status"] == "separable"
    assert sep["iterations"] == 0
    seen.add(sep["status"])
    assert sep["status"] != out_of_range["status"], (
        "'separable' claims the MLE does not exist and 'coef-out-of-range' that "
        "it does; collapsing them implies the opposite operational action")

    deg = rp.fit_calibration_line(np.full(60, 0.3), np.arange(60) % 2 == 0)
    assert deg["status"] == "degenerate-design"
    seen.add(deg["status"])
    clip = np.zeros(60)
    clip[::2] = 1e-12                 # below LOGIT_EPS -> clips to the same value
    assert rp.fit_calibration_line(clip, np.arange(60) % 3 == 0)["status"] == \
        "degenerate-design"

    slow = rp.fit_calibration_line(*_calibrated_draw(2000, 106), max_iter=1)
    assert slow["status"] == "not-converged" and slow["iterations"] == 1
    seen.add(slow["status"])
    assert rp.fit_calibration_line(*_calibrated_draw(2000, 106))["status"] == "ok"

    few = rp.fit_calibration_line(np.linspace(0.1, 0.9, rp.IRLS_MIN_RECORDS - 1),
                                  np.arange(rp.IRLS_MIN_RECORDS - 1) % 2 == 0)
    assert few["status"] == "too-few-records" and few["iterations"] == 0
    seen.add(few["status"])
    assert rp.fit_calibration_line(
        np.linspace(0.1, 0.9, rp.IRLS_MIN_RECORDS),
        np.arange(rp.IRLS_MIN_RECORDS) % 2 == 0)["status"] != "too-few-records"

    one = rp.fit_calibration_line(np.linspace(0.05, 0.95, 60),
                                  np.ones(60, dtype=bool))
    assert one["status"] == "single-class" and one["n_positive"] == 60
    assert rp.fit_calibration_line(np.linspace(0.05, 0.95, 60),
                                   np.zeros(60, dtype=bool))["status"] == "single-class"
    seen.add(one["status"])

    # 'singular' guards LinAlgError and non-finite steps; it has no deterministic
    # constructor that an earlier branch does not already catch, so the
    # vocabulary and the never-raises property are pinned instead
    seen.add("singular")
    assert seen == set(rp.FIT_STATUSES)

    # pathological inputs never raise, and a non-ok fit carries None coefs
    for p, y in ((np.empty(0), np.empty(0, dtype=bool)),
                 (np.array([0.5]), np.array([True]))):
        fit = rp.fit_calibration_line(p, y)
        assert fit["status"] in set(rp.FIT_STATUSES)
        assert fit["slope"] is None and fit["intercept"] is None


def test_irls_termination_order_is_load_bearing():
    """The |beta| range check must run BEFORE the convergence check in the same
    iteration. Constructed exactly: a tolerance so loose the convergence test
    would fire on the FIRST full Newton step, and a coefficient bound the same
    step already exceeds. Range-first -> 'coef-out-of-range'; swap the two lines
    and the identical fit reports 'ok' with a slope beyond the bound."""
    p, y = _calibrated_draw(4000, 301, 2.0)
    fit = rp.fit_calibration_line(p, y, tol=1e9, max_abs_coef=0.1)
    assert fit["status"] == "coef-out-of-range"
    assert fit["slope"] is None and fit["intercept"] is None
    assert fit["iterations"] == 1
    # the same data at the frozen constants converges normally
    assert rp.fit_calibration_line(p, y)["status"] == "ok"


def test_truncated_resamples_suppresses_both_intervals():
    """RP-4: a VALUE-dependent rejection must not be topped up into a quantile
    that has deleted its own tail. Point MLE ~27, under the 30.0 bound; the
    resample distribution crosses it."""
    rng = np.random.default_rng(212)
    n_sites, per_site = 30, 20
    site_effect = rng.normal(0.0, 0.8, size=n_sites)
    site_id = np.repeat(np.arange(n_sites, dtype=np.int64), per_site)
    z_true = rng.normal(-1.2, 1.7, size=n_sites * per_site) + site_effect[site_id]
    y = (rng.random(n_sites * per_site) < _sigmoid(z_true)).astype(bool)
    p = _sigmoid(z_true / 27.0)

    point = rp.fit_calibration_line(p, y)
    assert point["status"] == "ok", "construction sanity: the point fit must stand"
    assert abs(point["slope"]) < rp.IRLS_MAX_ABS_COEF

    block = rp.calibration_pair(p, y, site_id, n_sites, digest=DIGEST,
                                scope="answered", n_boot=FAST_N_BOOT)
    assert block["status"] == "ok"
    assert block["slope"] is not None             # the POINT estimate still stands
    assert block["ci"] is None
    assert block["ci_status"] == "truncated-resamples"
    # the attempt counts are carried through UNCHANGED and stay honest
    assert block["n_attempts"] > 0
    assert block["n_sites_carrying"] == n_sites


def test_calibration_pair_suppresses_entirely_when_the_point_fit_declines():
    p = np.linspace(0.05, 0.95, 600)
    y = np.zeros(600, dtype=bool)
    site_id = np.repeat(np.arange(20, dtype=np.int64), 30)
    block = rp.calibration_pair(p, y, site_id, 20, digest=DIGEST,
                                scope="answered", n_boot=FAST_N_BOOT)
    assert block["status"] == "single-class"
    assert block["ci"] is None and block["ci_status"] == "undefined-point"
    assert block["n_boot_valid"] == 0 and block["n_attempts"] == 0


# ==========================================================================
# 6. the reference Brier is denominator-matched
# ==========================================================================


def test_reference_brier_is_denominator_matched():
    n_sites, per_site = 14, 30
    p, y, site_id = _clustered(n_sites, per_site, seed=31, spread=0.6)
    p_ref = np.clip(p + 0.05, 0.0, 1.0)
    p_ref[np.arange(p.size) % 3 == 0] = np.nan       # a third has no reference

    block = rp.brier_block(p, y, site_id, n_sites, p_ref, digest=DIGEST,
                           n_boot=FAST_N_BOOT)["reference"]
    # one paired statistic from one stream: the identity is EXACT
    assert block["brier_difference"] == pytest.approx(
        block["brier_reference"] - block["brier_primary_matched"], abs=1e-12)
    assert block["available_share"] == pytest.approx(
        block["n_available"] / p.size, abs=1e-12)
    assert set(block["ci"]) == {"brier_reference", "brier_primary_matched",
                                "brier_difference"}

    # p_ref None -> an explicit null VALUE, never a missing key
    none_ref = rp.brier_block(p, y, site_id, n_sites, None, digest=DIGEST,
                              n_boot=FAST_N_BOOT)
    assert "reference" in none_ref and none_ref["reference"] is None

    # an ALL-NaN p_ref -> a fully null reference block, never an empty-slice mean
    allnan = rp.brier_block(p, y, site_id, n_sites, np.full(p.size, np.nan),
                            digest=DIGEST, n_boot=FAST_N_BOOT)["reference"]
    assert allnan["n_available"] == 0
    assert allnan["available_share"] == 0.0
    assert allnan["brier_reference"] is None
    assert allnan["brier_primary_matched"] is None
    assert allnan["brier_difference"] is None
    assert allnan["ci_status"] == "undefined-point"


def test_the_reference_can_be_floor_suppressed_while_the_primary_is_not():
    """n_sites_carrying for the reference section is taken on the AVAILABILITY
    mask, so a reference present at only a few sites is suppressed on its own."""
    n_sites, per_site = 20, 20
    p, y, site_id = _clustered(n_sites, per_site, seed=32, spread=0.4)
    p_ref = np.full(p.size, np.nan)
    p_ref[site_id < 4] = 0.1                       # available at 4 sites only

    block = rp.brier_block(p, y, site_id, n_sites, p_ref, digest=DIGEST,
                           n_boot=FAST_N_BOOT)
    assert block["primary_answered"]["ci_status"] == "ok"
    assert block["reference"]["n_sites_carrying"] == 4
    assert block["reference"]["ci"] is None
    assert block["reference"]["ci_status"] == "too-few-sites"


def test_the_prohibition_on_the_wider_denominator_is_emitted_verbatim():
    panel = rp.selective_reliability_panel(A_P, A_ANSWERED, A_SITE, A_Y,
                                           n_boot=8, timestamp=FIXED_TIMESTAMP)
    assert len(panel["notes"]) == 6
    assert "never against brier.primary_answered" in panel["notes"][4]
    assert "MARGINAL" in panel["notes"][1]          # the no-simultaneity clause


# ==========================================================================
# 7. THE headline: selected vs accurate
# ==========================================================================


def _headline_skeleton(n_sites=24, per_site=100, answered_per_site=60):
    site_id = np.repeat(np.arange(n_sites, dtype=np.int64), per_site)
    answered = np.tile(np.arange(per_site) < answered_per_site, n_sites)
    return site_id, answered


def _build_selected(seed=202607):
    """The GATE did the work: answered scores are noise, all below the cut."""
    rng = np.random.default_rng(seed)
    site_id, answered = _headline_skeleton()
    n = site_id.shape[0]
    p = np.empty(n, dtype=np.float64)
    y = np.empty(n, dtype=bool)
    n_ans = int(answered.sum())
    p[answered] = rng.uniform(0.02, 0.12, n_ans)       # independent of the label
    y[answered] = rng.random(n_ans) < 0.02
    hard = np.where(rng.random(n - n_ans) < 0.5, 0.15, 0.85)
    p[~answered] = hard
    y[~answered] = rng.random(n - n_ans) < hard
    return p, answered, site_id, y


def _build_accurate(seed=202608):
    """The SCORER did the work: same answered positive rate, same low error."""
    rng = np.random.default_rng(seed)
    site_id, answered = _headline_skeleton()
    n = site_id.shape[0]
    p = np.empty(n, dtype=np.float64)
    y = np.empty(n, dtype=bool)
    n_ans = int(answered.sum())
    y_ans = rng.random(n_ans) < 0.02
    y[answered] = y_ans
    p[answered] = np.where(y_ans, 0.90, 0.05)
    hard = np.where(rng.random(n - n_ans) < 0.5, 0.15, 0.85)
    p[~answered] = hard
    y[~answered] = rng.random(n - n_ans) < hard
    return p, answered, site_id, y


def test_headline_selected_vs_accurate():
    """THE regression on the abstention-quality claim, and the reason the panel
    exists. Two constructions with INDISTINGUISHABLE answered error rates and
    OPPOSITE skill margins."""
    selected = rp.selective_reliability_panel(*_build_selected(), **fast())
    accurate = rp.selective_reliability_panel(*_build_accurate(), **fast())

    s = selected["skill"]["answered"]
    a = accurate["skill"]["answered"]
    # the number a naive report would quote: it cannot tell the two apart
    assert s["model_error_rate"] < 0.05 and a["model_error_rate"] < 0.05
    assert abs(a["model_error_rate"] - s["model_error_rate"]) < 0.03

    # SELECTED: every answered score is below the cut, so the predicted class IS
    # the constant-negative baseline and the margin is identically zero
    assert s["model_error_rate"] == pytest.approx(
        s["constant_predictor_error_rate"], abs=1e-12)
    assert s["skill_margin"] == pytest.approx(0.0, abs=1e-12)
    assert s["constant_predictor_class"] is False
    # ACCURATE: the model error rate is zero against a baseline of the positive
    # rate, so the margin IS the positive rate -- small, but strictly positive
    assert a["model_error_rate"] == pytest.approx(0.0, abs=1e-12)
    assert a["skill_margin"] == pytest.approx(a["positive_rate"], abs=1e-12)
    assert s["skill_margin"] <= 0.0 < a["skill_margin"]

    # the gate reshaped the positive-event composition
    ca = selected["composition"]["answered"]
    ct = selected["composition"]["all"]
    assert ca["observed_positive_fraction"] < 0.25 * ct["observed_positive_fraction"]
    assert ca["predicted_positive_fraction"] == pytest.approx(0.0, abs=1e-12)
    # the scorer is not useless -- it is useless ON WHAT THE GATE ANSWERED
    assert selected["skill"]["all"]["skill_margin"] > 0.05
    con = selected["skill"]["contrast"]
    assert con["answered_minus_all"] < -0.05
    assert con["answered_minus_declined"] < -0.05
    assert con["ci_status"] == "ok"
    assert con["ci"]["answered_minus_all"]["hi"] < 0.0


# ==========================================================================
# 8. no NaN, round once, and the edge shapes
# ==========================================================================

_RATE_KEYS = ("coverage", "positive_rate", "predicted_positive_fraction",
              "observed_positive_fraction", "model_error_rate",
              "constant_predictor_error_rate", "available_share", "observed",
              "mean_predicted", "ece")


def _adversarial(name):
    """Every edge shape the emitted dict has to withstand, built by hand."""
    if name in ("well_calibrated", "miscalibrated",
                "missing_reference", "absent_reference"):
        n_sites, per_site = 14, 40
        spread = 0.9 if name == "miscalibrated" else 0.4
        p, y, site_id = _clustered(n_sites, per_site, seed=41, spread=spread)
        if name == "miscalibrated":
            p = np.clip(p ** 0.5, 0.0, 1.0)
        answered = p < 0.20
        answered[0] = True
        answered[-1] = False
        p_ref = np.clip(p + 0.03, 0.0, 1.0)
        if name == "missing_reference":
            p_ref = p_ref.copy()
            p_ref[(np.arange(p.size) % 5) < 2] = np.nan       # exactly 40%
        elif name == "absent_reference":
            p_ref = np.full(p.size, np.nan)
        return dict(p=p, answered=answered.astype(bool), site_id=site_id,
                    y=y, p_ref=p_ref)
    if name == "single_class_answered":
        n_sites, per_site = 12, 8
        p, answered, site_id, y = [], [], [], []
        for s in range(n_sites):
            for j in range(per_site):
                site_id.append(s)
                if j < 4:                       # answered, ALWAYS negative
                    answered.append(True)
                    p.append(0.01 + 0.01 * j)
                    y.append(False)
                else:
                    answered.append(False)
                    p.append(0.30 + 0.15 * (j - 4))
                    y.append((j + s) % 2 == 0)
        return dict(p=np.asarray(p, dtype=np.float64),
                    answered=np.asarray(answered, dtype=bool),
                    site_id=np.asarray(site_id, dtype=np.int64),
                    y=np.asarray(y, dtype=bool), p_ref=None)
    p, y, site_id = _clustered(1, 40, seed=11, spread=0.5)
    answered = p < 0.25
    answered[0] = True
    answered[-1] = False
    return dict(p=p, answered=answered.astype(bool), site_id=site_id, y=y,
                p_ref=None)


ADVERSARIAL = ("well_calibrated", "miscalibrated", "missing_reference",
               "absent_reference", "single_class_answered", "single_site")


def _walk(node, path=()):
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _walk(value, path + (key,))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _walk(value, path + (i,))
    else:
        yield path, node


@pytest.mark.parametrize("shape", ADVERSARIAL)
def test_no_nan_and_round_once(shape):
    kw = _adversarial(shape)
    panel = rp.selective_reliability_panel(kw["p"], kw["answered"], kw["site_id"],
                                           kw["y"], kw["p_ref"], **fast())
    # NaN is an invalid JSON token; allow_nan=False is the enforcement
    json.dumps(panel, allow_nan=False)

    assert set(panel) == {"schema_version", "generated_utc", "input_digest",
                          "settings", "counts", "reliability", "calibration",
                          "ece", "brier", "skill", "composition", "notes"}
    assert panel["schema_version"] == "srp/1"
    assert panel["settings"]["seed"] == rp.PANEL_SEED

    for path, value in _walk({k: v for k, v in panel.items() if k != "settings"}):
        if isinstance(value, float):
            assert value == round(value, rp.ROUND_DP), path      # rounded ONCE
            assert math.isfinite(value), path
        if path and path[-1] == "ci_status":
            assert value in rp.CI_STATUSES, path
        if path and path[-1] == "status" and path[0] == "calibration":
            assert value in rp.FIT_STATUSES, path
        if path and path[-1] in _RATE_KEYS and value is not None:
            assert 0.0 <= float(value) <= 1.0, (path, value)

    # a null interval always carries its reason; None is NOT 0.0
    for scope in ("answered", "declined"):
        for record in panel["reliability"][scope]:
            if record["ci"] is None:
                assert record["ci_status"] != "ok"
            if record["n"] == 0:
                assert record["mean_predicted"] is None
                assert record["observed"] is None
                assert record["ci_status"] == "empty-bin"

    # booleans stay booleans (the bool-before-int branch order in _emit)
    assert isinstance(panel["counts"]["reference_supplied"], bool)
    for scope in ("answered", "declined", "all"):
        cls = panel["skill"][scope]["constant_predictor_class"]
        assert cls is None or isinstance(cls, bool)

    # settings is EXEMPT from the round -- both of these collapse to 0.0 at 6 dp
    assert panel["settings"]["logit_eps"] == 1e-6
    assert panel["settings"]["irls"]["tol"] == 1e-8
    assert panel["settings"]["boot_max_attempts"] == 2 * FAST_N_BOOT
    assert panel["settings"]["bootstrap_unit"] == "site"


def test_settings_boot_max_attempts_echoes_the_relation_not_the_constant():
    """At a NON-default n_boot, echoing BOOT_MAX_ATTEMPTS would be a FALSE
    provenance statement."""
    panel = rp.selective_reliability_panel(A_P, A_ANSWERED, A_SITE, A_Y,
                                           n_boot=37, timestamp=FIXED_TIMESTAMP)
    assert panel["settings"]["n_boot"] == 37
    assert panel["settings"]["boot_max_attempts"] == 74
    assert panel["settings"]["boot_max_attempts"] != rp.BOOT_MAX_ATTEMPTS


def test_stream_count_is_the_documented_ceiling(monkeypatch):
    """SPEC and ``derive_rng``'s docstring state ``2 * n_bins + 13`` streams --
    27 at the default 7-bin edges. Both said 17 until 2026-08-01, a figure
    carried across from an earlier sandbox scope layout and true of neither.

    It is a CEILING, not a count: an empty bin and an undefined-point block are
    decided BEFORE any generator is constructed and open none. Both halves are
    asserted, because a doc that promises an exact number goes stale the first
    time a gate answers only low-probability records.
    """
    seen = []
    original = rp.derive_rng
    monkeypatch.setattr(rp, "derive_rng",
                        lambda d, k: (seen.append(k), original(d, k))[1])

    n_bins = len(rp.DEFAULT_BIN_EDGES) - 1
    ceiling = 2 * n_bins + 13
    assert ceiling == 27

    # every bin occupied in BOTH scopes, with a reference scorer: the ceiling
    rng = np.random.default_rng(4)
    n = 2400
    p = rng.uniform(0.0, 1.0, n)
    y = rng.uniform(0.0, 1.0, n) < p
    site_id = np.repeat(np.arange(24, dtype=np.int64), n // 24)
    answered = rng.uniform(0.0, 1.0, n) < 0.5
    rp.selective_reliability_panel(p, answered, site_id, y,
                                   rng.uniform(0.0, 1.0, n), **fast())
    assert len(seen) == len(set(seen)) == ceiling

    # a gate that answers only the low-probability tail empties most declined
    # bins, so the realised count is strictly below the ceiling
    seen.clear()
    rp.selective_reliability_panel(p, p < 0.6, site_id, y, None, **fast())
    assert 0 < len(seen) < ceiling


# ==========================================================================
# 9. determinism and digest sensitivity
# ==========================================================================


def test_determinism_and_digest_sensitivity():
    kw = _adversarial("well_calibrated")
    args = (kw["p"], kw["answered"], kw["site_id"], kw["y"], kw["p_ref"])

    a = rp.selective_reliability_panel(*args, **fast())
    b = rp.selective_reliability_panel(*args, **fast())
    assert a == b
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)

    # generated_utc is the ONLY free field; the default is None, so NO WALL
    # CLOCK enters any emitted artifact
    default = rp.selective_reliability_panel(*args, n_boot=FAST_N_BOOT)
    assert default["generated_utc"] is None
    assert {k: v for k, v in default.items() if k != "generated_utc"} == \
           {k: v for k, v in a.items() if k != "generated_utc"}

    inputs = rp.validate_inputs(*args)
    base = rp.input_digest(inputs)
    assert len(base) == 64 and base == base.lower()

    def digest_of(**over):
        fields = dict(p=kw["p"], answered=kw["answered"], site_id=kw["site_id"],
                      y=kw["y"], p_ref=kw["p_ref"],
                      decision_threshold=rp.DECISION_THRESHOLD,
                      bin_edges=rp.DEFAULT_BIN_EDGES)
        fields.update(over)
        return rp.input_digest(rp.validate_inputs(
            fields["p"], fields["answered"], fields["site_id"], fields["y"],
            fields["p_ref"], decision_threshold=fields["decision_threshold"],
            bin_edges=fields["bin_edges"]))

    # INVARIANT to identity, copy and a strided view (content, not layout)
    assert digest_of() == base
    assert digest_of(p=kw["p"].copy()) == base
    strided = np.repeat(kw["p"], 2)[::2]
    assert digest_of(p=strided) == base

    # MOVES on a single ULP, a flipped label, a flipped gate bit, a site
    # reassignment, an int32-vs-int64 site index, the threshold, the edges, and
    # None-vs-all-NaN p_ref
    bumped = kw["p"].copy()
    bumped[0] = np.nextafter(bumped[0], 1.0)
    assert digest_of(p=bumped) != base
    flipped_y = kw["y"].copy()
    flipped_y[0] = ~flipped_y[0]
    assert digest_of(y=flipped_y) != base
    flipped_a = kw["answered"].copy()
    flipped_a[0] = ~flipped_a[0]
    assert digest_of(answered=flipped_a) != base
    moved = kw["site_id"].copy()
    moved[0] = moved[-1]
    assert digest_of(site_id=moved) != base
    assert digest_of(site_id=kw["site_id"].astype(np.int32)) != base
    assert digest_of(decision_threshold=0.4) != base
    assert digest_of(bin_edges=(0.0, 0.5, 1.01)) != base
    assert digest_of(p_ref=None) != base
    assert digest_of(p_ref=np.full(kw["p"].size, np.nan)) != base

    # the WHOLE stat_key is hashed, never a prefix
    assert (rp.derive_rng(base, "bin1").integers(0, 2**31, 4).tolist() !=
            rp.derive_rng(base, "bin11").integers(0, 2**31, 4).tolist())


def test_point_estimates_are_order_invariant_but_the_digest_is_not():
    """Byte identity is promised only for byte-identical inputs: the digest is
    content-addressed over raw bytes, so a record permutation legitimately moves
    every resample stream. The POINT estimates must not move."""
    kw = _adversarial("well_calibrated")
    n = kw["p"].size

    # a WITHIN-SITE permutation
    order = np.lexsort((np.arange(n) % 7, kw["site_id"]))
    a = rp.selective_reliability_panel(kw["p"], kw["answered"], kw["site_id"],
                                       kw["y"], **fast())
    b = rp.selective_reliability_panel(kw["p"][order], kw["answered"][order],
                                       kw["site_id"][order], kw["y"][order],
                                       **fast())
    for scope in ("answered", "declined", "all"):
        assert b["skill"][scope]["skill_margin"] == \
               pytest.approx(a["skill"][scope]["skill_margin"], abs=1e-9)
    assert b["ece"]["answered"]["ece"] == \
        pytest.approx(a["ece"]["answered"]["ece"], abs=1e-9)

    # a whole-site RELABEL (a permutation of the site index) moves no point
    perm = np.random.default_rng(3).permutation(int(kw["site_id"].max()) + 1)
    relabelled = perm[kw["site_id"]].astype(np.int64)
    c = rp.selective_reliability_panel(kw["p"], kw["answered"], relabelled,
                                       kw["y"], **fast())
    assert c["counts"]["n_sites"] == a["counts"]["n_sites"]
    assert c["skill"]["all"]["skill_margin"] == \
        pytest.approx(a["skill"]["all"]["skill_margin"], abs=1e-9)


# ==========================================================================
# 10. THE numerical-equivalence lock
# ==========================================================================
#
# The sandbox: C:/Users/tonyt/OneDrive/Documents/Claude/Projects/
# selective-reliability-panel (package ``srp``, 581 tests green). It is neither
# installed nor in requirements.txt and must NEVER be imported here, so this
# pinned sha256 -- produced by running the SANDBOX implementation on the frozen
# fixture below during Build, and verified equal to this module's output on that
# fixture AND on the analytic fixture AND on a 24-site clustered pool -- is the
# only thing that carries the byte-exact equivalence forward. Same idiom as
# tests/test_constants.py's sha256 pin over EICU_MOCK_SIGNAL_LOAD.
#
# A red pin here is a DESIGN CHANGE, not a nuisance: it means a key was renamed,
# a constant moved, the digest prefix changed, or the seeding was re-pointed.

PANEL_DICT_SHA256 = "ad54a42342b708f9ce84bef053807dbca9974ee20f081522ff2590eb828bc6f5"


def _frozen_fixture():
    """180 records over 12 sites, built by pure arithmetic -- no RNG anywhere,
    so the fixture cannot move with a numpy generator change."""
    n_sites, per_site = 12, 15
    n = n_sites * per_site
    i = np.arange(n)
    p = ((i * 37) % 100).astype(np.float64) / 100.0
    y = ((i * 13) % 7) < 3
    answered = (i % 3) != 0
    site_id = np.repeat(np.arange(n_sites, dtype=np.int64), per_site)
    p_ref = ((i * 29) % 100).astype(np.float64) / 100.0
    p_ref[i % 5 == 0] = np.nan
    return p, answered.astype(bool), site_id, y.astype(bool), p_ref


def test_panel_dict_digest_pinned():
    p, answered, site_id, y, p_ref = _frozen_fixture()
    panel = rp.selective_reliability_panel(p, answered, site_id, y, p_ref,
                                           n_boot=FAST_N_BOOT,
                                           timestamp=FIXED_TIMESTAMP)
    blob = json.dumps(panel, sort_keys=True, separators=(",", ":"),
                      allow_nan=False)
    assert hashlib.sha256(blob.encode("utf-8")).hexdigest() == PANEL_DICT_SHA256
    # the fixture exercises the paths that matter: a converged fit, a produced
    # interval and a live reference block -- a pin over an all-suppressed panel
    # would lock almost nothing
    assert panel["calibration"]["answered"]["status"] == "ok"
    assert panel["calibration"]["answered"]["ci_status"] == "ok"
    assert panel["brier"]["reference"]["ci_status"] == "ok"
    assert panel["skill"]["contrast"]["ci_status"] == "ok"


# ==========================================================================
# 11. the module is a numpy-only DAG leaf
# ==========================================================================


def test_reliability_module_is_numpy_only_and_top_level():
    """Enclave/reproducibility (audit F16): no import inside any function or
    class, third-party imports subset of {numpy}, and NO ``from certgate ...``
    import of any kind -- the module never sees a Head, a Cohort or
    constants.SEED."""
    src = pathlib.Path(rp.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)

    nested = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for child in ast.walk(node):
                if isinstance(child, (ast.Import, ast.ImportFrom)):
                    nested.add(node.name)
    assert not nested, f"imports nested inside {sorted(nested)}"

    stdlib = {"hashlib", "math", "dataclasses", "typing", "collections", "json"}
    # ast.walk over the WHOLE tree, not tree.body: an import wrapped in a
    # module-level `try:` or `if:` is a child of that statement and invisible
    # to a top-level scan, so a conditional third-party import would pass.
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            roots.add((node.module or "").split(".")[0])
    assert roots - stdlib == {"numpy"}, roots
    assert not any(r == "certgate" for r in roots)
    assert "sklearn" not in roots and "matplotlib" not in roots


# ==========================================================================
# 12. driver-facing adapters (the wiring's own contract, tested here)
# ==========================================================================


def test_panel_rows_and_headline_shapes(head_cohort):
    head, tgt = head_cohort
    panel = rp.panel_from_head(head, tgt.x, tgt.y, tgt.site_id, 0.8, **fast())

    rows = rp.panel_reliability_rows(panel)
    assert len(rows) == 2 * (len(rp.DEFAULT_BIN_EDGES) - 1) == 14
    assert set(rows[0]) == set(rp.PANEL_RELIABILITY_FIELDS)
    assert [r["scope"] for r in rows[:7]] == ["answered"] * 7
    assert [r["scope"] for r in rows[7:]] == ["declined"] * 7
    for row in rows:
        assert row["ci_status"] in rp.CI_STATUSES
        if row["ci_lo"] is None:
            assert row["ci_status"] != "ok"     # None -> a BLANK cell, not a 0

    hl = rp.panel_headline(panel)
    assert set(hl) == {"ece_answered", "ece_declined",
                       "calibration_slope_answered", "calibration_status_answered",
                       "brier_answered", "brier_difference_vs_reference",
                       "skill_margin_answered", "skill_margin_answered_minus_all",
                       "coverage"}
    assert hl["calibration_status_answered"] in rp.FIT_STATUSES
    for key, value in hl.items():
        if key == "calibration_status_answered":
            continue
        assert value is None or isinstance(value, float)
        if isinstance(value, float):
            # ALREADY rounded at emit time; a second pass here would make the
            # last decimal irreproducible
            assert value == round(value, rp.ROUND_DP)


def test_the_panel_and_explain_composition_publish_one_number(head_cohort):
    """One quantity, one number. ``explain.composition`` is UNCHANGED
    (report.py depends on it) and the panel's answered predicted-positive
    fraction must agree with it exactly."""
    head, tgt = head_cohort
    tau = 0.8
    answered = np.asarray(head.score(tgt.x), dtype=np.float64) >= tau
    panel = rp.panel_from_head(head, tgt.x, tgt.y, tgt.site_id, tau,
                               answered_mask=answered, **fast())
    comp = composition(head, tgt.x, answered)
    panel_value = panel["composition"]["answered"]["predicted_positive_fraction"]
    exact = float(comp["predicted_class"]["positive_fraction"])
    # the panel value is the SAME number, rounded ONCE at emit time -- so the
    # agreement is exact against the rounded quantity, and within half a unit in
    # the last emitted place against the raw one
    assert panel_value == round(exact, rp.ROUND_DP)
    assert abs(panel_value - exact) <= 0.5 * 10 ** -rp.ROUND_DP
    assert panel["composition"]["answered"]["n_predicted_positive"] == \
        comp["predicted_class"]["n_positive"]
    assert panel["composition"]["answered"]["n"] == \
        comp["predicted_class"]["n_answered"]


def test_the_answered_model_error_rate_is_certgates_answered_error_rate(head_cohort):
    """DECISION_THRESHOLD = 0.5 coincides with Head.predict's rule, which is
    what makes skill.<scope>.model_error_rate a free cross-consistency check
    against certgate's own answered error rate -- not a second estimand."""
    head, tgt = head_cohort
    tau = 0.8
    answered = np.asarray(head.score(tgt.x), dtype=np.float64) >= tau
    panel = rp.panel_from_head(head, tgt.x, tgt.y, tgt.site_id, tau,
                               answered_mask=answered, **fast())
    direct = float((np.asarray(head.predict(tgt.x), dtype=bool)[answered]
                    != np.asarray(tgt.y, dtype=bool)[answered]).mean())
    assert panel["skill"]["answered"]["model_error_rate"] == \
        pytest.approx(direct, abs=1e-6)


def test_the_e6_summary_keys_survive_a_partial_rerun(tmp_path, head_cohort):
    """The three POST-HOC headline keys E6 adds are plain scalars and the
    summary merge is BLOCK-granular (``^## (E\\d)`` captures the whole fenced
    block and never inspects the JSON's keys), so adding them cannot break a
    partial ``--only`` rerun."""
    from experiments.run_synthetic import (_existing_summary_blocks,
                                           _write_summary)

    head, tgt = head_cohort
    hl = rp.panel_headline(
        rp.panel_from_head(head, tgt.x, tgt.y, tgt.site_id, 0.8, **fast()))
    payload = {"tau_star": 0.8, "predicted_positive_fraction": 0.1234,
               "panel_ece_answered": hl["ece_answered"],
               "panel_calibration_slope_answered": hl["calibration_slope_answered"],
               "panel_skill_margin_answered_minus_all":
                   hl["skill_margin_answered_minus_all"]}
    out = str(tmp_path)
    _write_summary(out, {"E6": payload}, quick=True)
    blocks = _existing_summary_blocks(f"{out}/summary.md")
    assert set(blocks) == {"E6"}
    parsed = json.loads(blocks["E6"].split("\n", 1)[1].rsplit("\n```", 1)[0])
    for key, value in payload.items():
        assert parsed[key] == value

    # a later partial rerun of another experiment preserves the block byte-exactly
    _write_summary(out, {"E1": {"R": 1}}, quick=True)
    assert _existing_summary_blocks(f"{out}/summary.md")["E6"] == blocks["E6"]


def test_panel_payload_passes_the_eicu_compliance_gate():
    """The panel is aggregate-only BY CONSTRUCTION, but that does not exempt the
    writer from the gate. The second half is what stops a future key addition
    from silently reintroducing 'site_id' or 'answered_mask'."""
    from experiments.run_eicu import (EICU_FORBIDDEN_OUT_KEYS,
                                      EICU_MAX_OUTPUT_LEN, _json_ready,
                                      assert_aggregate_only)

    n_sites, per_site = 24, 40
    p, y, site_id = _clustered(n_sites, per_site, seed=51, spread=0.5)
    answered = p < 0.25
    answered[0] = True
    answered[-1] = False
    p_ref = np.clip(p + 0.02, 0.0, 1.0)
    p_ref[np.arange(p.size) % 4 == 0] = np.nan
    panel = rp.selective_reliability_panel(p, answered.astype(bool), site_id, y,
                                           p_ref, **fast())

    payload = {"post_hoc": rp.POST_HOC_LABEL, "arm": "baseline", "replicates": 1,
               "scope": "pooled target arm only",
               "panels": [{"replicate": 0, "arm": "baseline",
                           "operative_alpha": 0.10, **panel}]}
    ready = _json_ready(payload)
    assert_aggregate_only(ready, "test")

    for path, _value in _walk(ready):
        for part in path:
            assert part not in EICU_FORBIDDEN_OUT_KEYS, path

    def _lengths(node):
        if isinstance(node, dict):
            for value in node.values():
                yield from _lengths(value)
        elif isinstance(node, (list, tuple)):
            yield len(node)
            for value in node:
                yield from _lengths(value)

    assert max(_lengths(ready)) <= EICU_MAX_OUTPUT_LEN
    assert max(_lengths(ready)) == len(rp.DEFAULT_BIN_EDGES) == 8
    json.dumps(ready, allow_nan=False)
