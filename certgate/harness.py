"""Validation instrumentation (SPEC section "harness.py", METHODS 7).

Numbers that must never be conflated (audit F29 lesson -- every label says
exactly what it computes; per-site scope corrected by audit V1):

  - ``hard_violation`` flags a single pool ONLY when the one-sided 95% Wilson
    lower bound on its answered error exceeds alpha. Applied to a single fresh
    site this is a PER-SITE DISPERSION DIAGNOSTIC with NO delta target
    (audit V1): the certificate bounds the site-population average, not
    individual sites, so per-site exceedances rise with between-site
    heterogeneity while the certified aggregate stays within budget. The
    conformance metric with the <= delta target is the aggregate R_M on a
    fresh multi-site pool (METHODS 7.1, computed in the experiment harness).
  - ``exceedance_reference`` is the binomial P(realized answered-error rate >
    alpha), a diagnostic against which the raw exceedance count is compared
    (small answered sets exceed alpha by luck at binomial-dispersion rates).

These are harness-only measurements over oracle labels; they never enter the
certified path.
"""

import numpy as np
from scipy.stats import binom, norm

SIZE_BINS = ((0, 30), (30, 100), (100, 300), (300, np.inf))


def wilson_lcb(k, n, level=0.95):
    """One-sided lower Wilson confidence bound on a binomial proportion
    (METHODS 7). ``level`` is the one-sided confidence (0.95 -> z ~= 1.645).
    Returns 0.0 for ``n <= 0``; result is clamped to [0, 1] and monotone
    non-decreasing in ``k``."""
    if n <= 0:
        return 0.0
    z = float(norm.ppf(level))
    phat = k / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = phat + z2 / (2.0 * n)
    half = z * np.sqrt(phat * (1.0 - phat) / n + z2 / (4.0 * n * n))
    lower = (center - half) / denom
    return float(min(1.0, max(0.0, lower)))


def hard_violation(err_answered, alpha):
    """A certificate is HARD-violated iff the one-sided 95% Wilson lower bound
    on the answered-set error exceeds ``alpha`` (METHODS 7). An empty answered
    set (``wilson_lcb == 0``) is never a violation."""
    err_answered = np.asarray(err_answered)
    n = int(err_answered.shape[0])
    k = int(np.count_nonzero(err_answered))
    return bool(wilson_lcb(k, n, 0.95) > alpha)


def exceedance_reference(n_answered, alpha):
    """Binomial reference probability that the realized answered-error RATE
    exceeds ``alpha`` (METHODS 7): ``P(K/n > alpha)`` for ``K ~ Binomial(n, p)``
    at the boundary ``p = alpha`` -- the dispersion curve of the worst valid
    certificate. Returns 0.0 for ``n_answered <= 0``."""
    if n_answered <= 0:
        return 0.0
    k_thresh = int(np.floor(alpha * n_answered + 1e-9))   # rate > alpha <=> K > alpha*n
    return float(binom.sf(k_thresh, n_answered, alpha))
