"""The positives-normalised false-negative atom (fix-pass sidecar, E9 arm B twin).

Four things get pinned here:
  - the atom stays in [0, 1] whether a site's positive count is below or
    above the cap M+, and a site with no positives is the neutral atom
  - the sign identity: at a budget equal to the fresh-pool FNR_M^+ the mean
    atom equals the budget exactly
  - the fresh-pool estimand against hand arithmetic, and its null
    equivalence with the pooled record-level FNR when no site hits the cap
  - the shipped arm reproduces the frozen E9_fnr.csv on draw 0, cell for cell

Refs: SPEC "Outcome-weighted atoms"; fix-pass plan WP2.
"""
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
    # the cap, one with n+ <= M+ gets its full count
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
