"""SPEC "Tests" for the certified-gate core.

The two non-negotiables (both were live findings in v1): the WSR boundary
type-I level, and the M-cap counterexample regression -- a 17.5%-true-risk
configuration that a truncated-contribution reading falsely certifies and the
influence-weighting path must refuse forever (audit Hole-1).
"""
import numpy as np
import pytest

from certgate.certify import (influence_atoms, wsr_reject, margin_floor,
                              walk_order, fixed_sequence_walk,
                              certification_rng)
from certgate.constants import TAU_GRID

ALPHA, DELTA = 0.05, 0.05


def _mpeb_ucb(z, delta):
    """Maurer-Pontil empirical-Bernstein UCB (range 1) -- test-local reference
    arithmetic ONLY (the truncation negative control; never in the library)."""
    z = np.asarray(z, dtype=float)
    n = len(z)
    v = z.var(ddof=1) if n > 1 else 0.25
    L = np.log(2.0 / delta)
    return z.mean() + np.sqrt(2.0 * v * L / n) + 7.0 * L / (3.0 * (n - 1))


def test_atom_range_and_empty_site_neutral():
    rng = np.random.default_rng(0)
    n = 5000
    site_id = rng.integers(0, 60, n)
    score = rng.random(n) * 0.5 + 0.5
    err = rng.random(n) < 0.08
    z = influence_atoms(score, err, site_id, 60, TAU_GRID, ALPHA, M=100)
    assert z.min() >= 0.0 and z.max() <= 1.0
    # zero-coverage boundary: every site is a neutral atom exactly == alpha
    z_hi = influence_atoms(score, err, site_id, 60, np.array([1.01]),
                           ALPHA, M=100)
    assert np.allclose(z_hi, ALPHA)
    # a site that carries no records (index 60 absent below) is neutral == alpha
    z2 = influence_atoms(score, err, site_id, 61, np.array([0.5]), ALPHA, M=100)
    assert np.isclose(z2[0, 60], ALPHA)


def test_mcap_counterexample_regression():
    """140 clean (n=20, 0 err) + 10 heavy (n=2000, 20% err): true
    record-weighted selective risk 17.5%. A truncated-contribution reading
    certifies (INVALID); influence weighting must refuse."""
    sizes = np.array([20] * 140 + [2000] * 10)
    errs = np.array([0] * 140 + [400] * 10)
    T = errs * (1 - ALPHA) - (sizes - errs) * ALPHA
    x01 = (np.minimum(T, 1.0) + 1.0) / 2.0
    assert _mpeb_ucb(x01, DELTA) * 2.0 - 1.0 <= 0.0        # truncation: certifies

    site_id = np.repeat(np.arange(150), sizes)
    err = np.zeros(int(sizes.sum()), dtype=bool)
    start = 0
    for n_c, e_c in zip(sizes, errs):
        err[start:start + e_c] = True
        start += n_c
    score = np.ones(int(sizes.sum()))                      # everything answered
    z = influence_atoms(score, err, site_id, 150, np.array([0.5]),
                        ALPHA, M=100)[0]
    assert z.mean() > ALPHA                                # estimand > budget
    assert not wsr_reject(z, ALPHA, DELTA,
                          rng=np.random.default_rng(7))    # refuses


def test_wsr_boundary_type_I_at_n80():
    """Boundary null Bernoulli(alpha) at n=80, 800 reps, fixed seed.
    Level 5%; empirical rate must stay <= 0.08 (documented tolerance)."""
    rng = np.random.default_rng(1)
    rej = sum(wsr_reject(rng.random(80) < ALPHA, ALPHA, DELTA)
              for _ in range(800))
    assert rej / 800 <= 0.08


def test_wsr_power_under_clear_margin():
    """A clear margin below alpha (mean 0.0, tiny variance) at n=80: power
    must exceed 0.9."""
    rng = np.random.default_rng(2)
    hits = sum(
        wsr_reject(np.clip(rng.normal(0.0, 0.01, 80), 0.0, 1.0), ALPHA, DELTA)
        for _ in range(200))
    assert hits / 200 > 0.9


def test_walk_stops_at_first_failure_and_deploys_max_coverage():
    tau = np.array([0.9, 0.8, 0.7, 0.6])
    good = np.full(130, ALPHA - 0.03)
    bad = np.full(130, ALPHA + 0.03)
    atoms = np.stack([good, good, bad, good])              # order hits index 2
    order = np.array([0, 1, 2, 3])
    certified, deployed = fixed_sequence_walk(atoms, order, ALPHA, DELTA, tau)
    assert certified == [0, 1]                             # stopped at 2
    assert deployed == 1                                   # lowest tau certified


def test_walk_order_is_margin_sorted():
    atoms = np.array([[0.06] * 5, [0.01] * 5, [0.04] * 5])
    assert list(walk_order(atoms)) == [1, 2, 0]


def test_nan_weight_and_nan_score_raise():
    rng = np.random.default_rng(0)
    n = 200
    site_id = rng.integers(0, 10, n)
    score = rng.random(n) * 0.5 + 0.5
    err = rng.random(n) < 0.1
    w = np.ones(n)
    w[0] = np.nan
    with pytest.raises(ValueError, match="bad-weights"):
        influence_atoms(score, err, site_id, 10, np.array([0.6]), ALPHA,
                        M=100, weights=w, wmax=1.0)
    score_bad = score.copy()
    score_bad[1] = np.nan
    with pytest.raises(ValueError, match="nonfinite-score"):
        influence_atoms(score_bad, err, site_id, 10, np.array([0.6]), ALPHA,
                        M=100)


def test_certification_rng_streams():
    """audit V3: the permutation stream depends on (alpha, mode, endpoint
    stream) and on NOTHING else -- in particular, no target identifier."""
    a = certification_rng(0.05, 0).standard_normal(6)
    c = certification_rng(0.05, 0).standard_normal(6)
    assert np.allclose(a, c)                               # identical repeats
    b_alpha = certification_rng(0.10, 0).standard_normal(6)
    b_mode = certification_rng(0.05, 1).standard_normal(6)
    b_lo = certification_rng(0.05, 0, "lo").standard_normal(6)
    b_hi = certification_rng(0.05, 0, "hi").standard_normal(6)
    assert not np.allclose(a, b_alpha)                     # distinct per alpha
    assert not np.allclose(a, b_mode)                      # distinct per mode
    assert not np.allclose(a, b_lo)                        # distinct endpoint
    assert not np.allclose(b_lo, b_hi)                     # lo != hi
    # the default stream IS the baseline stream: no identifier can perturb it
    assert np.allclose(a, certification_rng(0.05, 0, "").standard_normal(6))
    # weird stream values do not crash (no int() fast path)
    certification_rng(0.10, 1, "inf")
    certification_rng(0.10, 1, float("inf"))
    certification_rng(0.05, 0, "∞")


def test_mcap_supplies_ville_boundedness():
    """audit V6 #1: the M-cap is what keeps atoms in [0,1] -- the boundedness
    Ville's inequality REQUIRES. With site sizes spanning 20..3000 against
    M=100, removing ``np.minimum(sizes, M)`` drives atoms outside [0,1]
    (an error-heavy 3000-record site contributes ~3.05 uncapped) and this
    test fails; the shipped cap keeps every atom in range."""
    sizes = np.array([20] * 40 + [3000] * 10)
    site_id = np.repeat(np.arange(50), sizes)
    n = int(sizes.sum())
    err = np.zeros(n, dtype=bool)
    start = 0
    for n_c in sizes:
        if n_c == 3000:
            err[start:start + 600] = True          # 20% errors on huge sites
        start += n_c
    score = np.ones(n)                             # everything answered
    z = influence_atoms(score, err, site_id, 50, np.array([0.5]),
                        ALPHA, M=100)[0]
    assert z.min() >= 0.0 and z.max() <= 1.0       # Ville's precondition
    # and the capped statistic still sees the bad news (never censors it)
    assert z.mean() > ALPHA


def test_threshold_tie_is_answered_in_atoms():
    """audit V6 #11 killer: the certified statistic and the deployed answered
    mask share the ``score >= tau`` convention. A record scoring EXACTLY tau is
    answered; a mutation to strict ``>`` silently drops boundary records from
    the statistic while the deploy mask keeps them, and fails here."""
    score = np.array([0.6])
    err = np.array([True])
    site_id = np.array([0])
    z = influence_atoms(score, err, site_id, 1, np.array([0.6]), ALPHA, M=100)
    # answered tie: Z = (g/(M*n))*(1-alpha) + alpha = (1/100)*0.95 + 0.05
    assert np.isclose(z[0, 0], 0.0095 + ALPHA)
    # under strict '>' the record would be unanswered and Z would collapse to
    # the neutral atom alpha
    assert not np.isclose(z[0, 0], ALPHA)
