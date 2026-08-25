"""SPEC "Tests" for the BBSE label-shift mode.

Falsifiability first. The pure label shift is verified to push the baseline
answered risk above alpha, so the baseline walk certifies-and-violates, before
any BBSE behaviour is judged. Then the three declines and the affine-in-rho
property.
"""
import numpy as np
import pytest

from certgate.data import SimConfig, draw_cohort, split_sites
from certgate.model import fit_head, Head
from certgate.validate import Cohort
from certgate.certify import (influence_atoms, walk_order, fixed_sequence_walk,
                              certification_rng)
from certgate.shift import fit_bbse, certify_bbse, BBSEFit
from certgate.constants import (TAU_GRID, M_INFLUENCE, DELTA, MODE_BASELINE,
                                ALPHA_LADDER)

SRC_BASE = 0.095
TGT_BASE = 0.22
RHO_TRUE = (TGT_BASE / (1 - TGT_BASE)) / (SRC_BASE / (1 - SRC_BASE))


@pytest.fixture(scope="module")
def source():
    """A 260-site source split with a realistic, not near-perfect, head.

    sep=1.8 is good enough to certify in-distribution, weak enough that a real
    label shift bites the answered set. The target pool is one large site
    (size_lo=2000) so its Clopper-Pearson q interval is informative and the fit
    does not decline for target-pool noise; size affects only the site size,
    not the feature or label distributions (audit V2).
    """
    cfg = SimConfig(sep=1.8)
    rng = np.random.default_rng(20260721)
    src = draw_cohort(cfg, 260, rng)
    train, aux, cal = split_sites(src, rng)
    head = fit_head(train)
    tgt_cfg = SimConfig(sep=1.8, size_lo=2000, size_hi=5000)
    tgt = draw_cohort(tgt_cfg, 1, rng, label_base_rate=TGT_BASE,
                      site_label_prefix="tgt")
    return dict(cfg=cfg, head=head, aux=aux, cal=cal, tgt=tgt)


def _baseline_walk(head, cal, aux, alpha, label):
    score_aux = head.score(aux.x)
    err_aux = head.predict(aux.x) != aux.y
    order = walk_order(influence_atoms(score_aux, err_aux, aux.site_id,
                                       aux.n_sites, TAU_GRID, alpha,
                                       M_INFLUENCE))
    score_cal = head.score(cal.x)
    err_cal = head.predict(cal.x) != cal.y
    atoms = influence_atoms(score_cal, err_cal, cal.site_id, cal.n_sites,
                            TAU_GRID, alpha, M_INFLUENCE)
    return fixed_sequence_walk(atoms, order, alpha, DELTA, TAU_GRID,
                              rng=certification_rng(alpha, MODE_BASELINE, label))


def test_pure_label_shift_falsifiability_and_bbse(source):
    head, aux, cal, tgt = (source[k] for k in ("head", "aux", "cal", "tgt"))
    alpha = 0.10

    # 1. the BBSE rho interval must cover the true odds ratio.
    fit = fit_bbse(head, aux, tgt.x, np.random.default_rng(7))
    assert not fit.declined
    assert fit.rho_lo <= RHO_TRUE <= fit.rho_hi

    # 2. falsifiability: verify the shift moves the answered risk above alpha.
    certified, deployed = _baseline_walk(head, cal, aux, alpha, "tgt")
    assert deployed is not None                            # baseline certifies
    tau = TAU_GRID[deployed]
    ans_t = head.score(tgt.x) >= tau
    err_t = head.predict(tgt.x) != tgt.y
    target_risk = err_t[ans_t].mean()
    assert target_risk > alpha                             # ... and violates

    # 3. BBSE certifies or declines. Any certificate it does issue on this
    # draw must not be a certify-and-violate. Audit V6 found the old
    # reason-in-domain assertion vacuous: the set was certify_bbse's complete
    # return domain, so the predicate was identically true.
    from certgate.harness import hard_violation
    rb = certify_bbse(head, fit, cal, alpha)
    if rb["reason"] is None:
        ans_b = head.score(tgt.x) >= rb["tau"]
        assert not hard_violation(err_t[ans_b], alpha)
    else:
        # a decline issues nothing, so the certified fields must be empty
        # (verification N6, the same vacuous-assertion lesson as above)
        assert rb["tau"] is None and rb["tau_idx"] is None
        assert rb["certified"] == []


def test_degenerate_three_site_pool(source):
    """A 3-site pool with no positives at all must decline (audits F40, B-8).

    The point estimate is degenerate and every bootstrap resample is invalid,
    so no reduced-count quantile is taken.
    """
    head, tgt = source["head"], source["tgt"]
    d = source["cfg"].d
    rng = np.random.default_rng(3)
    xn = rng.normal(0, 1, (90, d))
    aux_neg = Cohort(x=xn, y=np.zeros(90, dtype=bool),
                     site_id=np.repeat(np.arange(3), 30),
                     site_labels=("a", "b", "c"))
    fit = fit_bbse(head, aux_neg, tgt.x, np.random.default_rng(1))
    assert fit.declined and fit.reason == "bbse-degenerate-bootstrap"


def test_weak_head_ill_conditioned(source):
    """A near-constant head cannot separate the classes, so c1 - c0 collapses
    below BBSE_GAP_FLOOR and the fit is ill-conditioned (audit B-9)."""
    head, aux, tgt = source["head"], source["aux"], source["tgt"]
    d = source["cfg"].d
    weak = Head(coef=np.zeros(d), intercept=-0.2, mu=np.zeros(d),
                sd=np.ones(d))
    fit = fit_bbse(weak, aux, tgt.x, np.random.default_rng(2))
    assert fit.declined and fit.reason == "bbse-ill-conditioned"


def test_q_t_outside_box_misspecified(source):
    """q_t forced above the box's [c0_lo, c1_hi] range is misspecified: the
    implied prevalence falls outside (0, 1) (audits F41, B-9)."""
    head, aux = source["head"], source["aux"]
    d = source["cfg"].d
    v = source["cfg"].direction()
    rng = np.random.default_rng(5)
    tgt_pos = np.tile(6.0 * v, (400, 1)) + rng.normal(0, 0.1, (400, d))
    assert head.predict(tgt_pos).mean() > 0.99             # q_t ~ 1
    fit = fit_bbse(head, aux, tgt_pos, np.random.default_rng(3))
    assert fit.declined and fit.reason == "bbse-misspecified"


def test_statistic_affine_in_rho():
    """The class-reweighted atom is affine in rho at a fixed normalization.

    The second difference over equally-spaced rho vanishes to ~1e-12. This is
    the fixed-wmax property only: the production walk uses a per-endpoint
    wmax=max(1,rho) under which the atom mean is not affine, and there the
    sign-carrier stays affine instead (see
    test_dual_endpoint_soundness_straddling_rho_one).
    """
    rng = np.random.default_rng(0)
    n = 4000
    site_id = rng.integers(0, 40, n)
    score = rng.random(n) * 0.5 + 0.5
    err = rng.random(n) < 0.1
    y = rng.random(n) < 0.2
    tau = np.array([0.6, 0.8])
    wmax = 5.0                                             # fixed normalization
    atoms = [influence_atoms(score, err, site_id, 40, tau, 0.05, 100,
                             weights=np.where(y, r, 1.0), wmax=wmax)
             for r in (1.0, 2.0, 3.0)]
    second_diff = (atoms[2] - atoms[1]) - (atoms[1] - atoms[0])
    assert np.abs(second_diff).max() < 1e-12


def test_dual_endpoint_soundness_straddling_rho_one():
    """Testing both endpoints of a rho interval covers every interior rho.

    On the production normalization wmax=max(1,rho) the atom mean is piecewise
    in rho with a kink at rho=1, so it is not affine. But the sign-carrier
    (mean - alpha) * max(1, rho) is affine, making the certifiable set
    {rho: E[Z] <= alpha} convex (R1, REDTEAM.md).
    """
    rng = np.random.default_rng(0)
    n = 4000
    site_id = rng.integers(0, 40, n)
    score = rng.random(n) * 0.5 + 0.5
    err = rng.random(n) < 0.1
    y = rng.random(n) < 0.2
    alpha = 0.05
    tau = np.array([0.6])
    rhos = np.array([0.5, 0.75, 1.0, 1.25, 1.5])   # equally spaced, straddles 1
    means = np.array([
        influence_atoms(score, err, site_id, 40, tau, alpha, 100,
                        weights=np.where(y, r, 1.0), wmax=max(1.0, r)).mean()
        for r in rhos])
    sign_carrier = (means - alpha) * np.maximum(1.0, rhos)   # == A + rho*B
    assert np.abs(np.diff(sign_carrier, 2)).max() < 1e-12    # affine in rho
    # the raw atom mean must show the kink, which guards against re-documenting
    # the old, false "atom mean is affine across rho=1" justification
    assert np.abs(np.diff(means, 2)).max() > 1e-6


def _flat_cohort(n_sites, n_pos_err, n_pos_ok, n_neg_err, n_neg_ok):
    """A d=1 cohort of n_sites identical sites for the identity head.

    With logit = x: x=-0.5 predicts negative, x=+0.5 predicts positive. Either
    way score = 0.622 >= TAU_GRID[0], so every record is answered at the first
    threshold. Positives carry BBSE weight rho, negatives weight 1.
    """
    per = ([(-0.5, True)] * n_pos_err      # y=1 predicted 0 -> error
           + [(+0.5, True)] * n_pos_ok    # y=1 predicted 1 -> correct
           + [(+0.5, False)] * n_neg_err  # y=0 predicted 1 -> error
           + [(-0.5, False)] * n_neg_ok)  # y=0 predicted 0 -> correct
    x = np.tile(np.array([p[0] for p in per], dtype=np.float64), n_sites)
    y = np.tile(np.array([p[1] for p in per], dtype=bool), n_sites)
    site_id = np.repeat(np.arange(n_sites, dtype=np.int64), len(per))
    return Cohort(x=x.reshape(-1, 1), y=y, site_id=site_id,
                  site_labels=tuple(f"d{s}" for s in range(n_sites)))


def _manual_fit(rho_lo, rho_hi, order=(0,)):
    """Hand-built non-declined BBSEFit with an explicit walk order."""
    return BBSEFit(declined=False, reason="", rho_lo=rho_lo, rho_hi=rho_hi,
                   rho_point=(rho_lo + rho_hi) / 2.0, diagnostics={},
                   walk_orders={a: np.array(list(order))
                                for a in ALPHA_LADDER})


def test_dual_endpoint_loop_requires_both_endpoints():
    """The dual-endpoint loop itself, not just the R1 math behind it.

    test_dual_endpoint_soundness_straddling_rho_one pins that math but never
    calls certify_bbse. Each scenario here makes one endpoint favorable and the
    other poisonous, so certify_bbse must decline (failsafe) in both
    orientations; a single-endpoint regression falsely certifies one of them.

    Collapsing the interval onto the favorable endpoint certifies, so the
    decline comes from the other endpoint, not lack of power. Fixed rng streams
    and identical sites keep it deterministic (REVIEW-FABLE B-1).
    """
    head = Head(coef=np.array([1.0]), intercept=0.0, mu=np.zeros(1),
                sd=np.ones(1))
    alpha = 0.10
    n_sites = 200

    # A: errors sit on positives (weight rho), so weighted answered risk rises
    #    with rho: rho=0.2 favorable (risk ~0.010), rho=3.0 poisonous (~0.136).
    cal_a = _flat_cohort(n_sites, n_pos_err=5, n_pos_ok=0,
                         n_neg_err=0, n_neg_ok=95)
    # B: errors sit on negatives (weight 1) under a large correct positive
    #    mass (weight rho), so risk falls with rho: rho=0.2 poisonous (~0.114),
    #    rho=3.0 favorable (~0.021).
    cal_b = _flat_cohort(n_sites, n_pos_err=0, n_pos_ok=70,
                         n_neg_err=5, n_neg_ok=25)

    for cal, favorable in ((cal_a, 0.2), (cal_b, 3.0)):
        r = certify_bbse(head, _manual_fit(0.2, 3.0), cal, alpha)
        assert r["reason"] == "failsafe"
        assert r["tau_idx"] is None and r["certified"] == []
        r_ok = certify_bbse(head, _manual_fit(favorable, favorable), cal,
                            alpha)
        assert r_ok["reason"] is None and r_ok["tau_idx"] == 0


# ---- audit V2/V14: the q_t confidence share and its decline paths ----------

def test_empty_target_declines(source):
    """An empty target pool must decline loudly as bbse-empty-target, never
    flow a NaN q_t through NaN-blind gates into an opaque downstream error
    (audit V14)."""
    from certgate.shift import fit_bbse
    head, aux = source["head"], source["aux"]
    d = source["cfg"].d
    fit = fit_bbse(head, aux, np.empty((0, d)), np.random.default_rng(9))
    assert fit.declined and fit.reason == "bbse-empty-target"


def test_fit_records_q_interval(source):
    """The fit's diagnostics carry a q interval bracketing q_t (audit V2)."""
    from certgate.shift import fit_bbse
    head, aux, tgt = source["head"], source["aux"], source["tgt"]
    fit = fit_bbse(head, aux, tgt.x, np.random.default_rng(7))
    q = fit.diagnostics["q_target"]
    q_lo, q_hi = fit.diagnostics["q_ci"]
    assert 0.0 <= q_lo <= q <= q_hi <= 1.0
    assert q_hi > q_lo                              # a real interval, not a point
    assert fit.diagnostics["n_target_sites"] == 1   # single-site CP path


def test_multi_site_q_interval_path(source):
    """At or above BBSE_MIN_TARGET_SITES, q takes the cluster-bootstrap path.

    The assertions are unconditional: an `if not declined` guard can leave a
    test with no reachable teeth (verification N6)."""
    from certgate.shift import fit_bbse
    head, aux, tgt = source["head"], source["aux"], source["tgt"]
    n = tgt.n
    sid = np.array([f"m{i % 12}" for i in range(n)], dtype=object)
    fit = fit_bbse(head, aux, tgt.x, np.random.default_rng(7),
                   target_site_id=sid)
    assert not fit.declined
    q = fit.diagnostics["q_target"]
    q_lo, q_hi = fit.diagnostics["q_ci"]
    assert q_lo <= q <= q_hi
    assert fit.diagnostics["n_target_sites"] == 12


def test_few_target_sites_decline_bbse_target_clustering(source):
    """2 <= K < BBSE_MIN_TARGET_SITES target sites must decline, never pretend.

    A percentile bootstrap over 2-9 sites cannot approach nominal coverage:
    rho-miss up to 46% at K=2 against a nominal 2.5%, and certify-and-violate
    at 3.4x delta where the bet has power (verification F1, critical).
    """
    from certgate.shift import fit_bbse
    from certgate.constants import BBSE_MIN_TARGET_SITES
    head, aux, tgt = source["head"], source["aux"], source["tgt"]
    n = tgt.n
    for k in (2, 3, BBSE_MIN_TARGET_SITES - 1):
        sid = np.array([f"k{i % k}" for i in range(n)], dtype=object)
        fit = fit_bbse(head, aux, tgt.x, np.random.default_rng(7),
                       target_site_id=sid)
        assert fit.declined and fit.reason == "bbse-target-clustering"
        assert fit.diagnostics["n_target_sites"] == k


def test_q_interval_propagation_regression():
    """Clopper-Pearson q intervals keep rho coverage at the nominal level.

    With the (c0, c1, pi_s) box held degenerate at truth, q intervals
    propagated through the 16-corner rho interval miss rho_true at most at the
    nominal per-parameter level plus MC tolerance; CP is conservative. The old
    point-q_t code, a zero-width q interval, misses at ~10x nominal on the same
    draws, so this test fails against it (audit V2).
    """
    from certgate.shift import _q_interval, rho_box_interval
    from certgate.constants import BBSE_DELTA_CONF, BBSE_BONFERRONI
    c0, c1, pi_s = 0.05, 0.60, 0.10
    pi_t = 0.25
    q_true = c0 * (1 - pi_t) + c1 * pi_t                      # 0.1875
    rho_true = (pi_t / (1 - pi_t)) / (pi_s / (1 - pi_s))      # 3.0
    lo = hi = np.array([c0, c1, pi_s])                        # degenerate box
    point = (c0, c1, pi_s)
    lvl = BBSE_DELTA_CONF / BBSE_BONFERRONI
    rng = np.random.default_rng(20260725)
    R, n_pool = 400, 100
    miss_interval = miss_point = 0
    for _ in range(R):
        pred = rng.random(n_pool) < q_true
        q_hat = float(pred.mean())
        q_lo, q_hi, _ = _q_interval(pred, None, lvl, rng)
        r_lo, r_hi, _ = rho_box_interval(q_lo, q_hi, q_hat, lo, hi, point)
        if not (r_lo <= rho_true <= r_hi):
            miss_interval += 1
        p_lo, p_hi, _ = rho_box_interval(q_hat, q_hat, q_hat, lo, hi, point)
        if not (p_lo <= rho_true <= p_hi):
            miss_point += 1
    # nominal per-parameter miss is lvl (two-sided); CP is conservative, so
    # allow only MC noise on top
    assert miss_interval / R <= lvl + 3.0 * np.sqrt(lvl / R) + 0.01
    # the point-q behaviour the audit demonstrated: an order of magnitude above
    # nominal on identical draws, the defect this test exists to catch
    assert miss_point / R > 10 * lvl


def test_bbse_walk_break_not_continue():
    """The BBSE fixed-sequence walk must stop at the first failing threshold.

    Fixture: errors score ~0.62, so they are answered only at low thresholds
    and threshold 0 is poisonous; correct records score ~0.95, so threshold 20
    alone would certify.

    Under walk order [0, 20] a `break` yields failsafe while a `continue`
    regression would certify threshold 20; a one-element order cannot tell them
    apart (audit V6 #8).
    """
    head = Head(coef=np.array([1.0]), intercept=0.0, mu=np.zeros(1),
                sd=np.ones(1))
    alpha = 0.10
    n_sites = 200
    # per site: 15 errors at x=+0.5 (pred pos, y neg -> error; score 0.622,
    # answered only for tau <= 0.61) + 85 correct at x=-3.0 (pred neg, y neg;
    # score 0.953, answered through tau <= 0.95 = TAU_GRID[20]).
    per_x = [0.5] * 15 + [-3.0] * 85
    per_y = [False] * 100
    x = np.tile(np.array(per_x, dtype=np.float64), n_sites).reshape(-1, 1)
    y = np.tile(np.array(per_y, dtype=bool), n_sites)
    site_id = np.repeat(np.arange(n_sites, dtype=np.int64), 100)
    cal = Cohort(x=x, y=y, site_id=site_id,
                 site_labels=tuple(f"w{s}" for s in range(n_sites)))
    # sanity: threshold 0 answers everything -> risk 15% > alpha; threshold 20
    # answers only the correct mass -> risk 0
    score = head.score(cal.x)
    assert 0.61 < float(score[0]) < 0.63          # error records
    assert float(score[15]) > 0.95                # correct records
    r = certify_bbse(head, _manual_fit(1.0, 1.0, order=(0, 20)), cal, alpha)
    assert r["reason"] == "failsafe"              # break, not continue
    assert r["certified"] == []
    # power check: order (20,) alone certifies -- the failure at 0 is real,
    # not lack of power
    r_ok = certify_bbse(head, _manual_fit(1.0, 1.0, order=(20,)), cal, alpha)
    assert r_ok["reason"] is None and r_ok["tau_idx"] == 20


def test_q_ci_is_clopper_pearson_at_the_bonferroni_level(source):
    """The per-parameter level must be BBSE_DELTA_CONF / BBSE_BONFERRONI.

    The single-site q interval is exact Clopper-Pearson, so its endpoints pin
    the level in closed form; a mutation dropping the Bonferroni division
    shifts them and fails here (audit V6 #4).
    """
    from scipy.stats import beta
    from certgate.constants import BBSE_DELTA_CONF, BBSE_BONFERRONI
    head, aux, tgt = source["head"], source["aux"], source["tgt"]
    fit = fit_bbse(head, aux, tgt.x, np.random.default_rng(7))
    assert not fit.declined
    k = int(head.predict(tgt.x).sum())
    n = int(tgt.n)
    lvl = BBSE_DELTA_CONF / BBSE_BONFERRONI
    exp_lo = float(beta.ppf(lvl / 2.0, k, n - k + 1)) if k > 0 else 0.0
    exp_hi = float(beta.ppf(1.0 - lvl / 2.0, k + 1, n - k)) if k < n else 1.0
    q_lo, q_hi = fit.diagnostics["q_ci"]
    assert q_lo == pytest.approx(exp_lo, abs=1e-12)
    assert q_hi == pytest.approx(exp_hi, abs=1e-12)


def test_q_interval_matches_the_scipy_reference_implementation():
    """The single-site q interval is exact Clopper-Pearson.

    The existing pin compares it to beta.ppf, the same construction the code
    uses, so it cannot catch a wrong quantile pairing. binomtest.proportion_ci
    is an independent path with its own k=0 and k=n handling."""
    from scipy.stats import binomtest
    from certgate.shift import _q_interval
    from certgate.constants import BBSE_DELTA_CONF, BBSE_BONFERRONI
    lvl = BBSE_DELTA_CONF / BBSE_BONFERRONI
    rng = np.random.default_rng(0)
    for k, n in ((0, 40), (7, 40), (40, 40), (19, 200), (1, 3)):
        pred = np.zeros(n, dtype=bool)
        pred[:k] = True
        q_lo, q_hi, n_sites = _q_interval(pred, None, lvl, rng)
        assert n_sites == 1                      # the finite-sample CP branch
        ref = binomtest(k, n).proportion_ci(confidence_level=1.0 - lvl,
                                            method="exact")
        assert q_lo == pytest.approx(float(ref.low), abs=1e-12), (k, n)
        assert q_hi == pytest.approx(float(ref.high), abs=1e-12), (k, n)


def test_fit_bbse_diagnostics_stable_key_set(source):
    """Full fits and every decline branch emit the same diagnostics key set.

    Whatever a branch did not compute comes back as None, so a consumer
    indexing any key gets None, never a KeyError. This extends the audit V25
    discipline to the bbse sub-dict (fixture audit 2026-07-25)."""
    from certgate.shift import bbse_diagnostics
    keys = set(bbse_diagnostics())
    head, aux, tgt = source["head"], source["aux"], source["tgt"]
    d = source["cfg"].d
    full = fit_bbse(head, aux, tgt.x, np.random.default_rng(7))
    assert not full.declined
    assert set(full.diagnostics) == keys
    assert full.diagnostics["rho_point"] is not None
    empty = fit_bbse(head, aux, np.empty((0, d)), np.random.default_rng(9))
    assert empty.reason == "bbse-empty-target"
    assert set(empty.diagnostics) == keys
    sid = np.array([f"k{i % 3}" for i in range(tgt.n)], dtype=object)
    clus = fit_bbse(head, aux, tgt.x, np.random.default_rng(7),
                    target_site_id=sid)
    assert clus.reason == "bbse-target-clustering"
    assert set(clus.diagnostics) == keys
    assert clus.diagnostics["q_target"] is None    # never computed there
    # unknown keys are rejected loudly, so the set cannot drift silently
    with pytest.raises(ValueError, match="unknown keys"):
        bbse_diagnostics(bogus=1)


def test_bootstrap_shortfall_declines_not_reduced_quantile(source, monkeypatch):
    """A bootstrap shortfall must decline, not quantile over a reduced count.

    When fewer than BBSE_BOOT valid resamples arrive within the attempt budget
    the fit returns bbse-degenerate-bootstrap. Fixture: positives live in one
    of three sites, so ~32% of site-resamples are invalid; with the budget
    pinched to 2100 the valid count lands far below 2000, and a mutation that
    proceeds with whatever arrived fails here (audits V6 #10, F40, B-8).
    """
    import certgate.shift as shift_mod
    head = source["head"]
    tgt = source["tgt"]
    d = source["cfg"].d
    rng = np.random.default_rng(12)
    x = rng.normal(0, 1, (90, d))
    y = np.array([True] * 30 + [False] * 60)     # positives only in site 'a'
    aux3 = Cohort(x=x, y=y, site_id=np.repeat(np.arange(3), 30).astype(np.int64),
                  site_labels=("a", "b", "c"))
    monkeypatch.setattr(shift_mod, "BBSE_BOOT_MAX_ATTEMPTS", 2100)
    fit = fit_bbse(head, aux3, tgt.x, np.random.default_rng(4))
    assert fit.declined and fit.reason == "bbse-degenerate-bootstrap"
    assert fit.diagnostics["n_boot"] < 2000      # the shortfall was real
