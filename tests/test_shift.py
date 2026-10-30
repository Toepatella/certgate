"""SPEC "Tests" for the BBSE label-shift mode.

Falsifiability first. The pure label shift is verified to push the baseline
answered risk above alpha, so the baseline walk certifies-and-violates, before
any BBSE behaviour is judged. Then the six declines and the affine-in-rho
property.
"""
import numpy as np
import pytest

from certgate.data import SimConfig, draw_cohort, split_sites, _logit
from certgate.model import fit_head, Head, _sigmoid
from certgate.validate import Cohort
from certgate.certify import (influence_atoms, walk_order, fixed_sequence_walk,
                              certification_rng)
from certgate.shift import fit_bbse, certify_bbse, BBSEFit
from certgate.constants import (TAU_GRID, M_INFLUENCE, DELTA, MODE_BASELINE,
                                ALPHA_LADDER)

SRC_BASE = 0.095
TGT_BASE = 0.22


def _odds(p):
    return p / (1.0 - p)


def _population_prevalence(base, s_u, n_nodes=200):
    # E_u sigmoid(logit(base) + u), u ~ N(0, s_u^2), by probabilists'
    # Gauss-Hermite: the record-pooled source prevalence BBSE's pi_s
    # estimates, since site sizes are drawn independently of u (the same
    # integral as experiments/probe_bbse_coverage.population_prevalence).
    x, w = np.polynomial.hermite_e.hermegauss(n_nodes)
    return float((w * _sigmoid(_logit(base) + s_u * x)).sum()
                 / np.sqrt(2.0 * np.pi))


@pytest.fixture(scope="module")
def source():
    """A 260-site source split with a realistic, not near-perfect, head.

    sep=1.8 is good enough to certify in-distribution, weak enough that a real
    label shift bites the answered set. The target pool is one large site
    (size_lo=2000) so its Clopper-Pearson q interval is informative and the fit
    does not decline for target-pool noise; size affects only the site size,
    not the feature or label distributions (audit V2).

    The site still carries its own random effect u_t on the log-odds, so its
    prevalence pi_t = sigmoid(logit(TGT_BASE) + u_t) is not TGT_BASE; the
    fixture recovers u_t and returns pi_t for the coverage truth (audit round
    2026-10 NUM-4).
    """
    cfg = SimConfig(sep=1.8)
    rng = np.random.default_rng(20260721)
    src = draw_cohort(cfg, 260, rng)
    train, aux, cal = split_sites(src, rng)
    head = fit_head(train)
    tgt_cfg = SimConfig(sep=1.8, size_lo=2000, size_hi=5000)
    state = rng.bit_generator.state
    tgt = draw_cohort(tgt_cfg, 1, rng, label_base_rate=TGT_BASE,
                      site_label_prefix="tgt")
    # draw_cohort draws the site size, then the site's random effect u_t, then
    # the labels. Replaying that prefix recovers u_t, hence the declared site's
    # own prevalence pi_t; the exact label match fails loudly if the draw
    # order ever changes.
    replay = np.random.default_rng()
    replay.bit_generator.state = state
    replay.normal(tgt_cfg.size_mu, tgt_cfg.size_sigma, 1)
    u_t = float(replay.normal(0.0, tgt_cfg.s_u, 1)[0])
    pi_t = float(_sigmoid(_logit(TGT_BASE) + u_t))
    assert np.array_equal(replay.random(tgt.n) < pi_t, tgt.y)
    return dict(cfg=cfg, head=head, aux=aux, cal=cal, tgt=tgt, pi_t=pi_t)


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

    # 1. the BBSE rho interval must cover the true odds ratio: the declared
    # site's own prevalence pi_t against the record-pooled source prevalence,
    # the two quantities the single-site box is fitted to. The nominal
    # odds(TGT_BASE) / odds(SRC_BASE) = 2.687 is neither; on this draw
    # u_t = -0.257 and the truth is 1.886 (audit round 2026-10 NUM-4).
    fit = fit_bbse(head, aux, tgt.x, np.random.default_rng(7))
    assert not fit.declined
    pi_s = _population_prevalence(SRC_BASE, source["cfg"].s_u)
    rho_true = _odds(source["pi_t"]) / _odds(pi_s)
    assert fit.rho_lo <= rho_true <= fit.rho_hi

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


def test_degenerate_ten_site_pool(source, monkeypatch):
    """A 10-site pool with no positives at all must decline (audits F40, B-8).

    The per-class S_aux floor declines it first: no site carries a positive.
    With the floor lowered, so the fit reaches the bootstrap, it still
    declines there: the point estimate is degenerate and every resample is
    invalid, so no reduced-count quantile is taken. The bootstrap guard stays
    as defense in depth behind the floor (audit round 2026-10 NUM-1).
    """
    import certgate.shift as shift_mod
    head, tgt = source["head"], source["tgt"]
    d = source["cfg"].d
    rng = np.random.default_rng(3)
    xn = rng.normal(0, 1, (300, d))
    aux_neg = Cohort(x=xn, y=np.zeros(300, dtype=bool),
                     site_id=np.repeat(np.arange(10), 30),
                     site_labels=tuple("abcdefghij"))
    fit = fit_bbse(head, aux_neg, tgt.x, np.random.default_rng(1))
    assert fit.declined and fit.reason == "bbse-aux-clustering"
    monkeypatch.setattr(shift_mod, "BBSE_MIN_AUX_SITES", 0)
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
    and identical sites keep it deterministic (REVIEW-FABLE B-1, in git history).
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


def test_multi_site_q_interval_targets_the_site_population():
    """For ten or more declared sites q is the site population's rate (audit
    multisite-q; audit round 2026-10 BBSE-2).

    Clopper-Pearson on the pooled count covers the declared sites' own rate
    but misses the site-population rate in most pools, which is why a
    multi-site pool must declare its clustering; the cluster bootstrap is the
    path aimed at that rate. It is asymptotic, so only a loose ceiling is
    asserted, never nominal coverage.
    """
    from scipy.special import expit, logit
    from certgate.shift import _q_interval
    from certgate.constants import BBSE_DELTA_CONF, BBSE_BONFERRONI
    lvl = BBSE_DELTA_CONF / BBSE_BONFERRONI
    c0, c1, base, s_u, K, R = 0.02, 0.55, 0.22, 0.5, 10, 200
    x, w = np.polynomial.hermite_e.hermegauss(200)
    q_pop = c0 + (c1 - c0) * float(
        (w * expit(logit(base) + s_u * x)).sum() / w.sum())
    rng = np.random.default_rng(20261029)
    cp_pop = cp_own = boot_pop = 0
    for _ in range(R):
        n = np.clip(np.exp(rng.normal(6.0, 1.1, K)), 20, 5000).astype(int)
        q_site = c0 + (c1 - c0) * expit(logit(base) + rng.normal(0.0, s_u, K))
        sid = np.repeat(np.arange(K), n)
        pred = rng.random(sid.size) < q_site[sid]
        q_own = float((n * q_site).sum() / n.sum())
        lo, hi, _ = _q_interval(pred, None, lvl, rng)
        cp_pop += not (lo <= q_pop <= hi)
        cp_own += not (lo <= q_own <= hi)
        lo, hi, k = _q_interval(pred, sid, lvl, rng)
        assert k == K
        boot_pop += not (lo <= q_pop <= hi)
    assert cp_own / R <= 0.03
    assert cp_pop / R >= 0.30
    assert boot_pop / R <= 0.15


def test_q_interval_propagation_regression():
    """Clopper-Pearson q intervals keep rho coverage at the nominal level.

    With the (c0, c1, pi_s) box held degenerate at truth, q intervals
    propagated through the 16-corner rho interval miss rho_true at most at the
    nominal per-parameter level plus MC tolerance; CP is conservative. The old
    point-q_t code, a zero-width q interval at q_hat, misses on every draw here
    (q_true = 0.1875 is not a multiple of 1/n_pool, so q_hat never equals it),
    so this test fails against it (audit V2; audit round 2026-10 NUM-12).
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
    # nominal per-parameter miss is lvl (two-sided); CP is conservative (exact
    # miss 0.0044 here), so allow MC noise plus a fixed 0.01 margin on top
    assert miss_interval / R <= lvl + 3.0 * np.sqrt(lvl / R) + 0.01
    # the point-q behaviour the audit demonstrated: on these draws it misses
    # every time (160x nominal), the defect this test exists to catch
    assert miss_point / R > 10 * lvl
    assert miss_point == R                       # the lattice argument, exact


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
    the fit returns bbse-degenerate-bootstrap. Fixture: ten sites with
    positives in one of them, so ~35% of site-resamples are invalid
    (0.9**10 + 0.1**10); with the budget pinched to 2100 the valid count lands
    near 1,370, far below 2000, and a mutation that proceeds with whatever
    arrived fails here. One positive-carrying site is below the per-class
    S_aux floor, which would decline first (pinned in
    test_few_aux_sites_decline_bbse_aux_clustering), so the floor is lowered
    here to reach the bootstrap guard behind it (audits V6 #10, F40, B-8;
    audit round 2026-10 NUM-1).
    """
    import certgate.shift as shift_mod
    head = source["head"]
    tgt = source["tgt"]
    d = source["cfg"].d
    rng = np.random.default_rng(12)
    x = rng.normal(0, 1, (300, d))
    y = np.array([True] * 30 + [False] * 270)    # positives only in site 'a'
    aux10 = Cohort(x=x, y=y,
                   site_id=np.repeat(np.arange(10), 30).astype(np.int64),
                   site_labels=tuple("abcdefghij"))
    monkeypatch.setattr(shift_mod, "BBSE_MIN_AUX_SITES", 0)
    monkeypatch.setattr(shift_mod, "BBSE_BOOT_MAX_ATTEMPTS", 2100)
    fit = fit_bbse(head, aux10, tgt.x, np.random.default_rng(4))
    assert fit.declined and fit.reason == "bbse-degenerate-bootstrap"
    assert fit.diagnostics["n_boot"] < 2000      # the shortfall was real


def test_few_aux_sites_decline_bbse_aux_clustering(source):
    """Fewer than BBSE_MIN_AUX_SITES S_aux sites carrying a positive record,
    or fewer carrying a negative one, declines.

    With one site every valid resample equals the point estimate, so the
    (c0, c1, pi_s) box had zero width and the fit certified silently; a few
    sites cannot approach nominal coverage either. The floor is per class:
    c1 draws only on positive-carrying sites and c0 only on negative-carrying
    ones, so twelve record-carrying sites with positives (or negatives) in
    one still decline, and empty labels carry neither class,
    so a one-site S_aux padded with empty labels must not clear the floor
    (audit round 2026-10, NUM-1)."""
    from certgate.data import subset_sites
    from certgate.shift import BBSE_MIN_AUX_SITES, bbse_diagnostics
    head, aux, tgt = source["head"], source["aux"], source["tgt"]
    pos = np.bincount(aux.site_id, weights=aux.y.astype(float),
                      minlength=aux.n_sites)
    both = [s for s in range(aux.n_sites) if 0 < pos[s] < aux.site_sizes[s]]
    for k in (1, 3, BBSE_MIN_AUX_SITES - 1):
        fit = fit_bbse(head, subset_sites(aux, both[:k]), tgt.x,
                       np.random.default_rng(7))
        assert fit.declined and fit.reason == "bbse-aux-clustering"
        assert fit.diagnostics["n_boot"] is None     # no resampling work
        assert set(fit.diagnostics) == set(bbse_diagnostics())
    one = subset_sites(aux, both[:1])
    padded = Cohort(x=one.x, y=one.y, site_id=one.site_id,
                    site_labels=one.site_labels + tuple(
                        f"pad{i}" for i in range(BBSE_MIN_AUX_SITES)))
    fit = fit_bbse(head, padded, tgt.x, np.random.default_rng(7))
    assert fit.declined and fit.reason == "bbse-aux-clustering"
    # twelve record-carrying sites, positives in only one: c1 would rest on a
    # single cluster, so the per-class count declines it
    rng = np.random.default_rng(12)
    one_pos = Cohort(x=rng.normal(0, 1, (360, source["cfg"].d)),
                     y=np.array([True] * 30 + [False] * 330),
                     site_id=np.repeat(np.arange(12), 30).astype(np.int64),
                     site_labels=tuple(f"s{i}" for i in range(12)))
    fit = fit_bbse(head, one_pos, tgt.x, np.random.default_rng(7))
    assert fit.declined and fit.reason == "bbse-aux-clustering"
    # the mirror: twelve record-carrying sites, negatives in only one, so
    # eleven carry a positive; c0 would rest on a single cluster, and the
    # negative-side count declines it (a positive-only floor would let this
    # fit run on and decline as ill-conditioned instead)
    rng = np.random.default_rng(13)
    one_neg = Cohort(x=rng.normal(0, 1, (360, source["cfg"].d)),
                     y=np.array([False] * 30 + [True] * 330),
                     site_id=np.repeat(np.arange(12), 30).astype(np.int64),
                     site_labels=tuple(f"n{i}" for i in range(12)))
    fit = fit_bbse(head, one_neg, tgt.x, np.random.default_rng(7))
    assert fit.declined and fit.reason == "bbse-aux-clustering"
    fit = fit_bbse(head, subset_sites(aux, both[:BBSE_MIN_AUX_SITES]), tgt.x,
                   np.random.default_rng(7))
    assert not fit.declined                          # the floor admits ten


def test_rho_truth_is_the_declared_sites_own(source):
    """Step 1 of the pure-label-shift test scores the declared site's own
    odds ratio, 1.886 on this draw, never the nominal odds(0.22) / odds(0.095)
    = 2.687, which the box covers only because it is wide (audit round 2026-10
    NUM-4). The source side is the record-pooled prevalence, the same integral
    as the probe's population_prevalence."""
    from experiments.probe_bbse_coverage import population_prevalence
    pi_s = _population_prevalence(SRC_BASE, source["cfg"].s_u)
    assert pi_s == pytest.approx(population_prevalence(SRC_BASE,
                                                       source["cfg"].s_u),
                                 abs=1e-9)
    rho_true = _odds(source["pi_t"]) / _odds(pi_s)
    nominal = _odds(TGT_BASE) / _odds(SRC_BASE)
    assert rho_true == pytest.approx(1.8861, abs=1e-4)
    assert abs(rho_true - nominal) > 0.5


def test_rho_box_interval_clip_semantics():
    """What the PI_CLIP clip does and does not promise (audit round 2026-10
    CORE-14, PAPER2-3, PAPER2-4, BBSE-4).

    (a) On gated boxes the clipped rho is monotone in each box parameter, so
        the 16-corner extremes bound it at every point of the box.
    (b) The interval covers the true odds ratio odds(pi_t)/odds(pi_s) at every
        box point whose implied prevalences lie in [PI_CLIP, 1 - PI_CLIP].
    (c) The clip does not "only widen": a box point whose implied pi_t lies in
        (0, PI_CLIP) has a true odds ratio below rho_lo. This guards against
        re-documenting the false "only widens" claim.
    """
    from certgate.shift import rho_box_interval
    from certgate.constants import BBSE_GAP_FLOOR, PI_CLIP
    rng = np.random.default_rng(20261029)

    def clipped_rho(q, c0, c1, ps):
        pt = np.clip((q - c0) / (c1 - c0), PI_CLIP, 1.0 - PI_CLIP)
        ps = np.clip(ps, PI_CLIP, 1.0 - PI_CLIP)
        return _odds(pt) / _odds(ps)

    g = np.linspace(0.0, 1.0, 9)
    n_boxes = 0
    while n_boxes < 300:
        c0_lo = rng.uniform(0.0, 0.4)
        c0_hi = c0_lo + rng.uniform(0.0, 0.2)
        c1_lo = c0_hi + BBSE_GAP_FLOOR + rng.uniform(0.0, 0.4)
        c1_hi = c1_lo + rng.uniform(0.0, 0.2)
        if c1_hi >= 1.0:
            continue
        q_lo, q_hi = np.sort(rng.uniform(c0_lo, c1_hi, 2))
        ps_lo = rng.uniform(0.01, 0.5)
        ps_hi = ps_lo + rng.uniform(0.0, 0.3)
        lo = np.array([c0_lo, c1_lo, ps_lo])
        hi = np.array([c0_hi, c1_hi, ps_hi])
        point = (0.5 * (c0_lo + c0_hi), 0.5 * (c1_lo + c1_hi),
                 0.5 * (ps_lo + ps_hi))
        r_lo, r_hi, _ = rho_box_interval(q_lo, q_hi, 0.5 * (q_lo + q_hi),
                                         lo, hi, point)
        Q, C0, C1, PS = np.meshgrid(q_lo + g * (q_hi - q_lo),
                                    c0_lo + g * (c0_hi - c0_lo),
                                    c1_lo + g * (c1_hi - c1_lo),
                                    ps_lo + g * (ps_hi - ps_lo),
                                    indexing="ij")
        r = clipped_rho(Q, C0, C1, PS)
        tol = 1e-12 * max(1.0, r_hi)
        assert (r >= r_lo - tol).all() and (r <= r_hi + tol).all()   # (a)
        pt = (Q - C0) / (C1 - C0)
        inside = (pt >= PI_CLIP) & (pt <= 1.0 - PI_CLIP)
        true_rho = _odds(pt[inside]) / _odds(PS[inside])
        assert (true_rho >= r_lo - tol).all()                        # (b)
        assert (true_rho <= r_hi + tol).all()
        n_boxes += 1

    # (c) q in [0.030001, 0.05], c0 in [0.02, 0.03], c1 in [0.30, 0.40],
    # pi_s in [0.09, 0.10]: the corner (0.030001, 0.03, 0.40, 0.10) implies
    # pi_t ~ 2.7e-6, inside (0, PI_CLIP), and its true odds ratio sits below
    # the clipped rho_lo.
    lo = np.array([0.02, 0.30, 0.09])
    hi = np.array([0.03, 0.40, 0.10])
    r_lo, _, _ = rho_box_interval(0.030001, 0.05, 0.04, lo, hi,
                                  (0.025, 0.35, 0.095))
    pt = (0.030001 - 0.03) / (0.40 - 0.03)
    assert 0.0 < pt < PI_CLIP
    assert _odds(pt) / _odds(0.10) < r_lo


def test_clip_bound_endpoint_can_certify():
    """A clip-bound endpoint is tested like any other and can certify (audit
    round 2026-10 NUM-5, BBSE-4).

    rho_lo = odds(PI_CLIP) / odds(0.10) is the value a corner clipped at
    PI_CLIP produces. Errors sit on positives, so a tiny rho is favourable,
    and rho_hi = 0.2 is favourable too: both endpoints pass and the threshold
    certifies. The old docstring said a clipped endpoint fails to certify.
    """
    from certgate.constants import PI_CLIP
    head = Head(coef=np.array([1.0]), intercept=0.0, mu=np.zeros(1),
                sd=np.ones(1))
    cal = _flat_cohort(200, n_pos_err=5, n_pos_ok=0, n_neg_err=0, n_neg_ok=95)
    rho_clip = _odds(PI_CLIP) / _odds(0.10)
    r = certify_bbse(head, _manual_fit(rho_clip, 0.2), cal, 0.10)
    assert r["reason"] is None and r["tau_idx"] == 0


def test_bbse_reweighted_class_mix_is_influence_weighted():
    """rho's source odds are record-pooled; the estimand's mix is not (audit
    round 2026-10 BBSE-3).

    Two sites, every record answered, every second positive in error and no
    negative errors: n = 50 with 5 positives and n = 2000 with 400. The
    record-pooled source prevalence is pi_rec = 405/2050, so the odds ratio to
    a target at pi_t = 0.25 is rho* = odds(pi_t)/odds(pi_rec) = 1.353909. The
    atoms weight site c by g_c = min(n_c, M), so the class mix they certify has
    odds rho* . odds(pi_g), pi_g = sum g_c pi_c / sum g_c = 1/6: 0.270782,
    not the target's 1/3. It reaches pi_t exactly only where pi_g = pi_rec.
    """
    alpha, M, pi_t = 0.10, M_INFLUENCE, 0.25
    sizes, n_pos = np.array([50, 2000]), np.array([5, 400])
    site_id = np.repeat(np.arange(2), sizes)
    y = np.concatenate([np.arange(n) < p for n, p in zip(sizes, n_pos)])
    err = np.zeros(y.size, dtype=bool)
    pos_idx = np.flatnonzero(y)
    err[pos_idx[::2]] = True                          # every second positive
    score = np.ones(y.size)
    pi_rec = n_pos.sum() / sizes.sum()
    rho = _odds(pi_t) / _odds(pi_rec)
    assert rho == pytest.approx(1.353909, abs=1e-6)
    wmax = max(1.0, rho)
    z = influence_atoms(score, err, site_id, 2, np.array([0.5]), alpha, M,
                        weights=np.where(y, rho, 1.0), wmax=wmax)[0]
    # per-site closed form of Z_c
    g = np.minimum(sizes, M).astype(float)
    n_err = np.bincount(site_id, weights=err.astype(float), minlength=2)
    n_neg = sizes - n_pos
    signed = (rho * (n_err * (1.0 - alpha) - (n_pos - n_err) * alpha)
              - n_neg * alpha) / wmax
    z_closed = g / (M * sizes) * signed + alpha
    assert np.abs(z - z_closed).max() < 1e-12
    # the class mix behind those atoms: influence mass g_c/n_c per record,
    # class weight rho on positives
    pos_mass = (rho * g / sizes * n_pos).sum()
    neg_mass = (g / sizes * n_neg).sum()
    pi_g = (g * n_pos / sizes).sum() / g.sum()
    assert pi_g == pytest.approx(1.0 / 6.0, abs=1e-12)
    assert pos_mass / neg_mass == pytest.approx(rho * _odds(pi_g), abs=1e-12)
    assert pos_mass / neg_mass == pytest.approx(0.270782, abs=1e-6)
    assert abs(pos_mass / neg_mass - _odds(pi_t)) > 0.05


def test_gap_gate_is_worst_case_not_point():
    """The gap floor applies to the box's worst case lo_c1 - hi_c0, not to the
    point gap c1 - c0 (audit round 2026-10 BBSE-8).

    Identity head, ten equal S_aux sites, all with c1 = 0.45; five have
    c0 = 0.1 and five c0 = 0.5. The point gap is 0.15 >= BBSE_GAP_FLOOR, but
    the c0 upper limit sits near 0.46, so the worst-case gap is negative and
    the fit declines bbse-ill-conditioned.
    """
    from certgate.constants import BBSE_GAP_FLOOR
    head = Head(coef=np.array([1.0]), intercept=0.0, mu=np.zeros(1),
                sd=np.ones(1))
    xs = []
    ys = []
    for s in range(10):
        n_neg_pred_pos = 8 if s % 2 == 0 else 40           # c0 = 0.1 or 0.5
        xs += ([+0.5] * 9 + [-0.5] * 11                      # c1 = 9/20
               + [+0.5] * n_neg_pred_pos + [-0.5] * (80 - n_neg_pred_pos))
        ys += [True] * 20 + [False] * 80
    aux = Cohort(x=np.array(xs).reshape(-1, 1), y=np.array(ys),
                 site_id=np.repeat(np.arange(10, dtype=np.int64), 100),
                 site_labels=tuple(f"g{s}" for s in range(10)))
    tgt_x = np.array([+0.5] * 30 + [-0.5] * 70).reshape(-1, 1)
    fit = fit_bbse(head, aux, tgt_x, np.random.default_rng(11))
    d = fit.diagnostics
    assert d["c1"] - d["c0"] >= BBSE_GAP_FLOOR                # point gap passes
    assert d["gap_lo"] < BBSE_GAP_FLOOR                       # worst case fails
    assert fit.declined and fit.reason == "bbse-ill-conditioned"


def test_q_interval_partial_overlap_misspecified():
    """The q gate asks for the whole q interval inside [c0_lo, c1_hi]; a point
    estimate inside with an interval straddling c1_hi declines (audit round
    2026-10 BBSE-8).

    Identity head, ten identical S_aux sites with c0 = 0.1 and c1 = 0.5, so
    the box range is exactly [0.1, 0.5]. The target pool has q_hat = 19/40 =
    0.475, inside it, while its Clopper-Pearson upper limit is far above 0.5.
    """
    head = Head(coef=np.array([1.0]), intercept=0.0, mu=np.zeros(1),
                sd=np.ones(1))
    per_x = [+0.5] * 10 + [-0.5] * 10 + [+0.5] * 8 + [-0.5] * 72
    per_y = [True] * 20 + [False] * 80
    aux = Cohort(x=np.tile(np.array(per_x), 10).reshape(-1, 1),
                 y=np.tile(np.array(per_y), 10),
                 site_id=np.repeat(np.arange(10, dtype=np.int64), 100),
                 site_labels=tuple(f"p{s}" for s in range(10)))
    tgt_x = np.array([+0.5] * 19 + [-0.5] * 21).reshape(-1, 1)
    fit = fit_bbse(head, aux, tgt_x, np.random.default_rng(13))
    d = fit.diagnostics
    assert d["c0_ci"][0] == pytest.approx(0.1) and d["c1_ci"][1] == pytest.approx(0.5)
    assert d["c0_ci"][0] <= d["q_target"] <= d["c1_ci"][1]   # point inside
    assert d["q_ci"][1] > d["c1_ci"][1]                      # interval is not
    assert fit.declined and fit.reason == "bbse-misspecified"
