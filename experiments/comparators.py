"""Alternative one-sided upper confidence bounds for E8 arm A (SPEC:
"Experiments" companion `experiments/comparators.py`).

Pure arithmetic over per-site atoms in [0, 1]; a DAG leaf over numpy/scipy —
``certgate/`` never imports this module. Each bound answers the question the
betting test answers inside the walk ("is the atom mean provably <= alpha at
level delta?"), decided as ``ucb(atoms, delta) <= alpha`` inside E8's local
fixed-sequence walk. The validity classes differ, and stating them is the
point of the comparison:

    hoeffding_ucb       finite-sample, distribution-free for [0,1] variables
    mpeb_ucb            finite-sample, variance-adaptive (Maurer-Pontil
                        empirical Bernstein; moved verbatim from the
                        test-local reference in ``tests/test_certify.py``,
                        which now imports it, so the truncation negative
                        control and this comparator can never drift)
    t_ucb               exact only under normality of the site atoms —
                        included as the practitioners' default, not as a
                        finite-sample-valid certificate
    site_bootstrap_ucb  asymptotic percentile bootstrap; resamples SITES
                        (atoms), never records (RP-2)

Every bound returns ``inf`` where it is undefined (fewer than two atoms),
which can never certify.
"""
import numpy as np
from scipy import stats


def hoeffding_ucb(z, delta):
    """One-sided Hoeffding UCB for the mean of [0,1] variables."""
    z = np.asarray(z, dtype=float)
    n = len(z)
    if n < 1:
        return float("inf")
    return float(z.mean() + np.sqrt(np.log(1.0 / delta) / (2.0 * n)))


def mpeb_ucb(z, delta):
    """Maurer-Pontil empirical-Bernstein UCB (range 1).

    Verbatim arithmetic of the truncation-negative-control reference that
    lived in ``tests/test_certify.py`` (audit Hole-1); the ``log(2/delta)``
    constant is the paper's own (delta/2 to the variance concentration), so
    this is the conservative one-sided form.
    """
    z = np.asarray(z, dtype=float)
    n = len(z)
    v = z.var(ddof=1) if n > 1 else 0.25
    L = np.log(2.0 / delta)
    return z.mean() + np.sqrt(2.0 * v * L / n) + 7.0 * L / (3.0 * (n - 1))


def t_ucb(z, delta):
    """One-sided Student-t UCB — exact only under normal atoms."""
    z = np.asarray(z, dtype=float)
    n = len(z)
    if n < 2:
        return float("inf")
    sd = z.std(ddof=1)
    return float(z.mean() + stats.t.ppf(1.0 - delta, n - 1) * sd / np.sqrt(n))


def site_bootstrap_ucb(z, delta, n_boot, rng):
    """Percentile-bootstrap UCB for the atom mean; resamples SITES, never
    records (RP-2). Asymptotic — its miscoverage at small site counts is one
    of the things E8 arm A measures."""
    z = np.asarray(z, dtype=float)
    n = len(z)
    if n < 2:
        return float("inf")
    idx = rng.integers(0, n, size=(int(n_boot), n))
    means = z[idx].mean(axis=1)
    return float(np.quantile(means, 1.0 - delta))
