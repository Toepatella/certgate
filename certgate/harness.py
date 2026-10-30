"""Instrumentation for validating the gate.

Nothing here touches the certified path. These read oracle labels and only
ever measure.

Two numbers look alike and mean different things, so keep them apart:

  - hard_violation flags one pool when the one-sided 95% Wilson lower bound on
    its answered error exceeds alpha. On a single fresh site that is a
    DISPERSION diagnostic with no delta target. The certificate bounds the
    average across sites, not any one site, so per-site exceedances climb with
    between-site heterogeneity while the certified average stays in budget.
  - exceedance_reference is the binomial P(realized answered-error rate >
    alpha) for a batch whose records err independently with probability
    exactly alpha. It is the yardstick for the raw exceedance count: such a
    batch clears alpha on luck alone at this rate, and a homogeneous batch
    below alpha at a lower one. It is not a bound for a single-site batch
    under between-site heterogeneity, whose rate is a mixture over site risks
    and can sit on either side of it even when the certified average is
    exactly alpha.

The rate that carries the <= delta target is aggregate conformance (METHODS
7.1), computed in the experiment harness: the share of certified draws whose
influence-weighted R_M on a fresh multi-site pool exceeds alpha. That pool R_M
is a finite-sample estimate of the population R_M the certificate bounds, and
the share is conditional on certification; the betting test itself bounds the
joint probability of certifying while the population R_M is at or above
alpha.

Refs: SPEC "harness.py"; METHODS 7; audits F29 (every label says exactly what
it computes), V1 (per-site scope), 2026-10 synthetic-2 and synthetic-3.
"""

import numpy as np
from scipy.stats import binom, norm

SIZE_BINS = ((0, 30), (30, 100), (100, 300), (300, np.inf))


def wilson_lcb(k, n, level=0.95):
    """One-sided lower Wilson confidence bound on a binomial proportion.

    level is the one-sided confidence (0.95 -> z ~= 1.645). Returns 0.0 when
    n <= 0. The result is clamped to [0, 1] and rises monotonically with k.

    Refs: METHODS 7.
    """
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
    """True when the answered-set error is high enough to call a hard violation.

    The bar is the one-sided 95% Wilson lower bound exceeding alpha. An empty
    answered set gives wilson_lcb == 0, so it is never a violation.

    Refs: METHODS 7.
    """
    err_answered = np.asarray(err_answered)
    n = int(err_answered.shape[0])
    k = int(np.count_nonzero(err_answered))
    return bool(wilson_lcb(k, n) > alpha)


def exceedance_reference(n_answered, alpha):
    """How often a batch erring at exactly alpha still exceeds alpha by luck.

    P(K/n > alpha) for K ~ Binomial(n, p) evaluated at p = alpha: the
    exceedance rate of a homogeneous batch whose records err independently at
    the budget. It oscillates with the integer lattice for small n and tends
    to 1/2 as n grows. Under between-site heterogeneity a single-site batch,
    drawn from a site population whose influence-weighted average risk R_M is
    exactly alpha, exceeds at the mixture rate E_c[P(Bin(n, p_c) > alpha n)],
    which tends to P(p_c > alpha) rather than 1/2. Returns 0.0 when
    n_answered <= 0.

    Refs: METHODS 7; audit 2026-10 synthetic-3.
    """
    if n_answered <= 0:
        return 0.0
    k_thresh = int(np.floor(alpha * n_answered + 1e-9))   # rate > alpha <=> K > alpha*n
    return float(binom.sf(k_thresh, n_answered, alpha))
