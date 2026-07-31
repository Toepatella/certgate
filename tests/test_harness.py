"""SPEC "Tests" for the validation instrumentation (audit V6 #6/#7).

``harness.py`` computes every violation number in the paper and had ZERO
tests: the audit showed that inverting ``wilson_lcb`` to the upper bound, or
making ``hard_violation`` use the raw rate, left the suite green. These tests
pin the instruments against closed forms and brute-force enumeration.
"""
import numpy as np
from scipy.stats import binom, norm

from certgate.harness import (wilson_lcb, hard_violation,
                              exceedance_reference, SIZE_BINS)


def test_wilson_lcb_matches_closed_form():
    z = float(norm.ppf(0.95))
    for k, n in ((0, 50), (3, 50), (10, 100), (25, 100), (100, 100)):
        phat = k / n
        z2 = z * z
        expected = ((phat + z2 / (2 * n)
                     - z * np.sqrt(phat * (1 - phat) / n + z2 / (4 * n * n)))
                    / (1 + z2 / n))
        expected = min(1.0, max(0.0, expected))
        assert abs(wilson_lcb(k, n) - expected) < 1e-12


def test_wilson_lcb_is_a_LOWER_bound_and_monotone():
    """The audit's mutation #6 replaced the lower bound with the upper: the
    LCB must sit strictly below the point estimate for interior k, and be
    monotone non-decreasing in k."""
    n = 200
    prev = -1.0
    for k in range(0, n + 1, 10):
        lcb = wilson_lcb(k, n)
        assert lcb >= prev
        prev = lcb
        if 0 < k < n:
            assert lcb < k / n          # LOWER bound, not upper
    assert wilson_lcb(0, 0) == 0.0      # empty: never a violation


def test_hard_violation_criterion():
    """Violated iff the one-sided 95% Wilson LOWER bound exceeds alpha -- the
    raw rate is deliberately not the criterion (mutation #7)."""
    alpha = 0.10
    assert not hard_violation(np.array([], dtype=bool), alpha)   # empty set
    # 3/20 = 15% raw > alpha, but the LCB is ~0.056 < alpha: NOT hard
    e = np.zeros(20, dtype=bool)
    e[:3] = True
    assert wilson_lcb(3, 20) < alpha
    assert not hard_violation(e, alpha)
    # 60/200 = 30%: LCB ~0.25 > alpha: hard
    e2 = np.zeros(200, dtype=bool)
    e2[:60] = True
    assert wilson_lcb(60, 200) > alpha
    assert hard_violation(e2, alpha)


def test_exceedance_reference_matches_brute_force():
    """P(K/n > alpha) at the boundary p = alpha, including the integer-
    boundary case alpha*n exactly integral (rate > alpha <=> K > alpha*n)."""
    for n, alpha in ((30, 0.10), (100, 0.10), (100, 0.05), (37, 0.10)):
        k_thresh = int(np.floor(alpha * n + 1e-9))
        brute = sum(binom.pmf(k, n, alpha) for k in range(k_thresh + 1, n + 1))
        assert abs(exceedance_reference(n, alpha) - brute) < 1e-10
    # n=100, alpha=0.10: K > 10 strictly (10/100 == alpha is NOT an exceedance)
    assert abs(exceedance_reference(100, 0.10)
               - float(binom.sf(10, 100, 0.10))) < 1e-12
    assert exceedance_reference(0, 0.10) == 0.0


def test_size_bins_cover_all_counts():
    lo_edges = [b[0] for b in SIZE_BINS]
    hi_edges = [b[1] for b in SIZE_BINS]
    assert lo_edges[0] == 0 and hi_edges[-1] == np.inf
    for i in range(1, len(SIZE_BINS)):
        assert lo_edges[i] == hi_edges[i - 1]      # contiguous, no gaps
