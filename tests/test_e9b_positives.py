"""The positives-normalised false-negative atom (fix-pass sidecar, E9 arm B twin).

What gets pinned here:
  - the atom stays in [0, 1] whether a site's positive count is below or
    above the cap M+, a site with no positives is the neutral atom, and the
    site weight is the capped positive count
  - the sign identity: at a budget equal to the fresh-pool FNR_M^+ the mean
    atom equals the budget exactly, and likewise for the shipped atom at
    FNR_M on unequal site sizes, where the count form names another number
  - the fresh-pool estimand against hand arithmetic, and its null
    equivalence with the pooled record-level FNR when no site hits the cap
  - the shipped arm reproduces the frozen E9_fnr.csv on draw 0, cell for cell
  - b = 0.4 is not a null-true control: the six certificates issued there
    hold against the closed-form estimand
  - on this generator the two estimands take one value

Refs: SPEC "Outcome-weighted atoms"; fix-pass plan WP2; audits FNR-1,
FNR-2, FNR-5, FNR-8.
"""
import os
from types import SimpleNamespace

import numpy as np

from certgate.constants import TAU_GRID
from experiments import run_e9b_positives as e9b
from experiments.derive_fixpass_numbers import _read_csv


class _H:
    """Score from column 0, prediction from column 1 (>= 0.5)."""

    def score(self, x):
        return x[:, 0]

    def predict(self, x):
        return x[:, 1] >= 0.5


def _random_pool(rng, n_pos, n_neg):
    """Sites with the given positive and negative counts, random scores in
    [0.5, 1] and random predictions."""
    xs, ys, sids = [], [], []
    for s, (kp, kn) in enumerate(zip(n_pos, n_neg)):
        n = kp + kn
        sc = rng.uniform(0.5, 1.0, n)
        pred = rng.random(n) < 0.5
        xs.append(np.column_stack([sc, pred.astype(float)]))
        ys.append(np.array([True] * kp + [False] * kn))
        sids.append(np.full(n, s))
    x, y, sid = np.vstack(xs), np.concatenate(ys), np.concatenate(sids)
    sizes = np.bincount(sid, minlength=len(n_pos))
    return SimpleNamespace(x=x, y=y, site_id=sid, n_sites=len(n_pos),
                           site_sizes=sizes)


def test_positives_atoms_bounded_in_both_regimes():
    rng = np.random.default_rng(1)
    n_pos = (2, 5, 9, 10, 25, 40, 0)          # below M+, at and above, none
    n_neg = (30, 40, 10, 60, 100, 5, 20)
    pool = _random_pool(rng, n_pos, n_neg)
    head = _H()
    score, err = head.score(pool.x), head.predict(pool.x) != pool.y
    for budget in (0.4, 0.5, 0.55, 0.6):
        z = e9b._positives_atoms(score, err, pool.site_id, pool.n_sites,
                                 pool.y, budget)
        assert z.shape == (len(TAU_GRID), pool.n_sites)
        assert (z >= 0.0).all() and (z <= 1.0).all()
        # the site with no positives enters as the neutral atom b
        assert np.allclose(z[:, 6], budget)
        # the weight really is the positive count: a site with n+ > M+ gets
        # the cap, one with n+ <= M+ gets its full count, so
        # (Z_c - b) * M+ * n+ / min(n+, M+) is the site's inner sum
        # (audit FNR-8)
        npos = np.bincount(pool.site_id[pool.y],
                           minlength=pool.n_sites).astype(float)
        ans = score >= TAU_GRID[0]
        s = np.bincount(pool.site_id,
                        weights=(ans & pool.y) * (err.astype(float) - budget),
                        minlength=pool.n_sites)
        has = npos > 0
        cap = e9b.E9B_POS_M
        assert np.allclose((z[0, has] - budget) * cap * npos[has]
                           / np.minimum(npos[has], cap), s[has],
                           rtol=0, atol=1e-12)
    assert e9b.E9B_POS_M == 10


def test_positives_atoms_sign_identity_with_fresh_estimand():
    """E[Z] <= b iff FNR_M^+ <= b; at b == FNR_M^+ the mean atom is b.

    Everything answers at the lowest threshold, so the pool is its own
    calibration set and the identity is exact.
    """
    rng = np.random.default_rng(7)
    pool = _random_pool(rng, (15, 4, 8, 12), (30, 10, 20, 0))
    pool.x[:, 0] = 0.9                          # everything answers at tau 0.55
    head = _H()
    fnr_plus = e9b._fnr_pos_on_pool(head, pool, float(TAU_GRID[0]))
    assert 0.0 < fnr_plus < 1.0
    score, err = head.score(pool.x), head.predict(pool.x) != pool.y
    z = e9b._positives_atoms(score, err, pool.site_id, pool.n_sites, pool.y,
                             fnr_plus)
    assert abs(z[0].mean() - fnr_plus) < 1e-12
    # a budget above the truth puts the mean atom below it, and vice versa
    z_hi = e9b._positives_atoms(score, err, pool.site_id, pool.n_sites,
                                pool.y, fnr_plus + 0.1)
    z_lo = e9b._positives_atoms(score, err, pool.site_id, pool.n_sites,
                                pool.y, fnr_plus - 0.1)
    assert z_hi[0].mean() < fnr_plus + 0.1
    assert z_lo[0].mean() > fnr_plus - 0.1


def test_fnr_pos_on_pool_closed_form_and_null_equivalence():
    """Two-site toy: site 0 has three positives, two of them answered with
    one FN; site 1 has one answered positive and no FN, plus a negative.

    With M+ = 10 above both positive counts the weights are 1 and
    FNR_M^+ = 1/3 -- the pooled record-level FNR among answered positives,
    which is the null equivalence. With M+ = 1 site 0 carries weight
    min(3, 1)/3 = 1/3 on its positive COUNT, answered or not:
    (1/3 * 1) / (1/3 * 2 + 1) = 1/5.
    """
    x = np.array([[0.9, 0.0], [0.9, 1.0], [0.1, 1.0],
                  [0.9, 1.0], [0.9, 0.0]])
    y = np.array([True, True, True, True, False])
    pool = SimpleNamespace(x=x, y=y, site_id=np.array([0, 0, 0, 1, 1]),
                           n_sites=2, site_sizes=np.array([3, 2]))
    head = _H()
    got = e9b._fnr_pos_on_pool(head, pool, 0.5)
    assert np.isclose(got, 1.0 / 3.0)
    ans = head.score(pool.x) >= 0.5
    fn = (ans & (head.predict(pool.x) != y) & y).sum()
    ap = (ans & y).sum()
    assert np.isclose(got, fn / ap)                 # record-level FNR
    assert np.isclose(e9b._fnr_pos_on_pool(head, pool, 0.5, M=1), 0.2)
    # nothing answered -> NaN, never 0.0
    assert np.isnan(e9b._fnr_pos_on_pool(head, pool, 1.01))


def test_shipped_arm_reproduces_frozen_draw_zero():
    """The shipped rows of draw 0 at 208 sites equal the frozen CSV cells."""
    shipped, positives = e9b.run_draw(0, 0)
    frozen = _read_csv(e9b.FROZEN)
    assert e9b._check_shipped(shipped, frozen) == []
    assert [p["fnr_budget"] for p in positives] == \
        [s["fnr_budget"] for s in shipped] == list(e9b.E9_FNR_LADDER)
    # both estimands' truths travel with every row
    assert all(0.0 < p["true_fnr_at_lowest_tau"] < 1.0 for p in positives)
    assert all(0.0 < s["true_fnr_at_lowest_tau"] < 1.0 for s in shipped)


def test_shipped_fnr_atom_sign_identity():
    """SPEC "Outcome-weighted atoms": the unmodified weights=y atom has mean
    exactly b at b = FNR_M = E[g fn/n] / E[g ap/n], on unequal site sizes
    either side of the cap; the count form E[g fn] / E[g ap] is a different
    number.

    Refs: audits FNR-2, FNR-8.
    """
    from certgate.certify import influence_atoms
    from certgate.constants import M_INFLUENCE
    from experiments.run_synthetic import _fnr_on_pool
    rng = np.random.default_rng(3)
    pool = _random_pool(rng, (3, 40, 12, 0, 25), (20, 300, 150, 30, 1000))
    head = _H()
    score, err = head.score(pool.x), head.predict(pool.x) != pool.y
    yw = pool.y.astype(float)
    for tau in (float(TAU_GRID[0]), 0.75):
        b = _fnr_on_pool(head, pool, tau)
        z = influence_atoms(score, err, pool.site_id, pool.n_sites,
                            np.array([tau]), b, M_INFLUENCE, weights=yw,
                            wmax=1.0)[0]
        assert abs(z.mean() - b) < 1e-12
        for d in (0.05, -0.05):
            zd = influence_atoms(score, err, pool.site_id, pool.n_sites,
                                 np.array([tau]), b + d, M_INFLUENCE,
                                 weights=yw, wmax=1.0)[0]
            assert (zd.mean() - (b + d)) * d < 0
        ans = score >= tau
        fn = np.bincount(pool.site_id,
                         weights=(ans & err & pool.y).astype(float),
                         minlength=pool.n_sites)
        ap = np.bincount(pool.site_id, weights=(ans & pool.y).astype(float),
                         minlength=pool.n_sites)
        g = np.minimum(pool.site_sizes, M_INFLUENCE)
        assert abs((g * fn).sum() / (g * ap).sum() - b) > 1e-3


def _closed_form_fnr(head, cfg, taus):
    """(fn, ap) per positive at each tau, in closed form for a fixed head.

    x | y = 1 ~ N(mu_1, I) at every site, so the decision logit of a positive
    is Gaussian with mean m = intercept + a . (mu_1 - mu_head) and sd ||a||,
    a = coef / sd. An answered positive is a false negative when the logit
    is <= -logit(tau) and correct when it is >= logit(tau). Both FNR_M and
    FNR_M^+ equal fn / ap on this generator.
    """
    from scipy.stats import norm
    a = head.coef / head.sd
    s = float(np.linalg.norm(a))
    m = float(head.intercept + a @ (cfg.mu(1) - head.mu))
    L = np.log(taus / (1.0 - taus))
    fn = norm.cdf((-L - m) / s)
    return fn, fn + norm.sf((L - m) / s)


def test_b04_certificates_hold_against_closed_form_estimand():
    """b = 0.4 is not a null-true negative control (SPEC "Outcome-weighted
    atoms", corrected 2026-10-29).

    The ~0.45 truth is the false-negative rate at the LOWEST threshold; the
    rate falls as tau rises. For each of the six positives-arm certificates
    issued at b = 0.4 in the released out-e9b-positives/ run, the replayed
    head's closed-form rate is above 0.4 at tau = 0.55 and below it at the
    certified tau, so each certificate holds against its estimand. The
    shipped atom's population margin at 0.4 stays below the information
    floor at every grid tau: its 0 of 600 is a power limit. The one 600-site
    certificate that scored 0.400108 on its fresh pool has a closed-form
    estimand of 0.3902: a pool excursion, not an estimand exceedance.

    Refs: audit FNR-1.
    """
    from certgate.certify import margin_floor
    from certgate.constants import DELTA, SEED
    from certgate.data import SimConfig, draw_cohort
    from experiments.probe_bbse_coverage import population_prevalence
    from experiments.run_synthetic import (E1_EVAL_SITES, E9_FNR_SWEEP,
                                           _draw_split, _rng)
    cfg = SimConfig()
    released = os.path.join(e9b.OUT_DIR, "E9b_fnr_positives.csv")
    rows = [r for r in _read_csv(released)
            if r["arm"] == "positives" and r["fnr_budget"] == "0.4"
            and r["certified"] == "True"]
    assert len(rows) == 6
    kappa_bound = population_prevalence(0.095, 0.5)
    for r in rows:
        n_sites, draw = int(r["n_sites"]), int(r["draw"])
        n_idx = E9_FNR_SWEEP.index(n_sites)
        rng = _rng(9, 1, n_idx, draw)
        _, _, cal, head = _draw_split(cfg, n_sites, rng)
        fn, ap = _closed_form_fnr(head, cfg, TAU_GRID)
        fnr = fn / ap
        k = int(np.argmin(np.abs(TAU_GRID - float(r["tau"]))))
        assert np.all(np.diff(fnr) < 0)
        assert fnr[0] > 0.4 > fnr[k]
        # shipped atom margin: b - E[Z] <= E[pi_c] * P(ans|y=1) * (b - FNR)
        assert (kappa_bound * np.max(0.4 * ap - fn)
                < margin_floor(cal.n_sites, DELTA, 0.4))
        if (n_sites, draw) == (600, 80):
            assert r["fnr_fresh"] == "0.400108"
            assert abs(fnr[k] - 0.3902) < 5e-4
            evalp = draw_cohort(cfg, E1_EVAL_SITES, rng,
                                site_label_prefix=f"e9fv{n_idx}_{draw}")
            assert round(e9b._fnr_pos_on_pool(head, evalp,
                                              float(TAU_GRID[k])), 6) \
                == 0.400108
            # the closed form against simulated positives
            prng = np.random.default_rng([SEED, 20261029])
            x = prng.normal(size=(400_000, cfg.d)) + cfg.mu(1)
            ans = head.score(x) >= TAU_GRID[k]
            mc = float((ans & ~head.predict(x)).sum() / ans.sum())
            assert abs(mc - fnr[k]) < 0.003


def test_fnr_estimands_coincide_on_generator():
    """On this generator P(x | y) is the same at every site, so FNR_M and
    FNR_M^+ take one value, P(err | ans, y = 1), at every tau; the two atoms
    differ in power, not in the value certified. A negative control that
    makes the false-negative rate vary with site prevalence separates them.

    Refs: audit FNR-5.
    """
    from certgate.constants import SEED
    from certgate.data import SimConfig, draw_cohort, make_cohort
    from experiments.run_synthetic import _draw_split, _fnr_on_pool, _rng
    cfg = SimConfig()
    _, _, _, head = _draw_split(cfg, 208, _rng(9, 1, 0, 0))
    pool = draw_cohort(cfg, 1500, np.random.default_rng([SEED, 2]),
                       site_label_prefix="inv")
    for tau in (0.55, 0.75):
        s = _fnr_on_pool(head, pool, tau)
        p = e9b._fnr_pos_on_pool(head, pool, tau)
        fn, ap = _closed_form_fnr(head, cfg, np.array([tau]))
        assert abs(s - p) < 0.005
        assert abs(s - fn[0] / ap[0]) < 0.01
        assert abs(p - fn[0] / ap[0]) < 0.01
    # negative control: positives at high-prevalence sites move toward the
    # boundary, so the answered FNR varies by site and the weightings differ
    prev = (np.bincount(pool.site_id, weights=pool.y.astype(float))
            / pool.site_sizes)
    shift = (prev > np.median(prev))[pool.site_id] & pool.y
    x2 = pool.x.copy()
    x2[shift] -= 0.5 * cfg.direction()
    tilted = make_cohort(x2, pool.y, pool.site_id,
                         site_labels=pool.site_labels)
    for tau in (0.55, 0.75):
        assert abs(_fnr_on_pool(head, tilted, tau)
                   - e9b._fnr_pos_on_pool(head, tilted, tau)) > 0.02
