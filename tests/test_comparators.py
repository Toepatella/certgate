"""SPEC "Experiments" companion tests: experiments/comparators.py (E8 arm A).

What gets pinned:
  - the MP-EB arithmetic, byte-compatible with the old test-local reference
  - one-sided validity-side sanity for every bound
  - site-resampling determinism for the bootstrap
  - the inf-never-certifies edges

Refs: RP-2 (resamples sites, not records).
"""
import numpy as np

from experiments.comparators import (hoeffding_ucb, mpeb_ucb,
                                     site_bootstrap_ucb, t_ucb)


def test_mpeb_verbatim_regression():
    # Literal pin of the arithmetic on a fixed vector. Any drift in the
    # constants -- log(2/delta), the 7/3 tail term -- fails here.
    z = np.linspace(0.0, 1.0, 11)
    assert np.isclose(mpeb_ucb(z, 0.05), 1.6323588424413757)
    z2 = np.full(9, 0.04)
    z2[0] = 0.4
    assert np.isclose(mpeb_ucb(z2, 0.05), 1.2645712953758141)


def test_hoeffding_matches_closed_form():
    z = np.full(50, 0.1)
    expect = 0.1 + np.sqrt(np.log(1 / 0.05) / (2 * 50))
    assert np.isclose(hoeffding_ucb(z, 0.05), expect)


def test_degenerate_inputs_never_certify():
    one = np.array([0.02])
    assert hoeffding_ucb(one, 0.05) > 0.02          # widened, finite
    with np.errstate(divide="ignore"):
        assert not np.isfinite(mpeb_ucb(one, 0.05))  # n-1 division -> inf
    assert not np.isfinite(t_ucb(one, 0.05))
    assert not np.isfinite(
        site_bootstrap_ucb(one, 0.05, 100, np.random.default_rng(0)))


def test_bootstrap_resamples_sites_deterministically():
    z = np.random.default_rng(11).random(60) * 0.3
    a = site_bootstrap_ucb(z, 0.05, 500, np.random.default_rng(42))
    b = site_bootstrap_ucb(z, 0.05, 500, np.random.default_rng(42))
    c = site_bootstrap_ucb(z, 0.05, 500, np.random.default_rng(43))
    assert a == b
    assert a != c
    # percentile of resampled means stays inside the atom range
    assert 0.0 <= a <= 0.3 + 1e-12
