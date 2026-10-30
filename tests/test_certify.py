"""SPEC "Tests" for the certified-gate core.

Two non-negotiables, both live findings in v1:
  - the WSR boundary type-I level
  - the M-cap counterexample regression: a 17.5% record-weighted-risk
    configuration that a truncated-contribution reading falsely certifies,
    and that the influence-weighting path must refuse forever

Refs: audit Hole-1.
"""
import hashlib
import math

import numpy as np
import pytest

from certgate.certify import (influence_atoms, wsr_reject, margin_floor,
                              walk_order, fixed_sequence_walk,
                              certification_rng)
from certgate.constants import (TAU_GRID, SEED, ALPHA_LADDER, WSR_LAMBDA_CAP,
                                WSR_VAR_FLOOR)
from certgate.model import Head

ALPHA, DELTA = 0.05, 0.05


# The Maurer-Pontil reference arithmetic lives verbatim in
# experiments/comparators.py, so the truncation negative control below and the
# comparator bound can never drift. It stays out of the certgate/ library.
# Ref: revision-2, E8 arm A.
from experiments.comparators import mpeb_ucb as _mpeb_ucb  # noqa: E402


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
    # nothing answers: R_M is 0/0, every wealth factor is 1, and the test
    # cannot certify (audit 2026-10 CORE-16)
    assert not wsr_reject(z_hi[0], ALPHA, DELTA)
    # a site that carries no records (index 60 absent below) is neutral == alpha
    z2 = influence_atoms(score, err, site_id, 61, np.array([0.5]), ALPHA, M=100)
    assert np.isclose(z2[0, 60], ALPHA)


def test_mcap_counterexample_regression():
    """A configuration that influence weighting must refuse.

    140 clean sites (n=20, 0 errors) plus 10 heavy ones (n=2000, 20% errors)
    give a true record-weighted selective risk of 17.5%. A
    truncated-contribution reading certifies it, which is invalid. Its R_M at
    M = 100 is 200/3800 = 5.3%, also above budget (audit 2026-10 PAPER1-13).
    """
    sizes = np.array([20] * 140 + [2000] * 10)
    errs = np.array([0] * 140 + [400] * 10)
    assert np.isclose(errs.sum() / sizes.sum(), 0.17544, atol=1e-5)
    g = np.minimum(sizes, 100)                              # everything answered
    r_m = (g * errs / sizes).sum() / g.sum()
    assert np.isclose(r_m, 200 / 3800) and r_m > ALPHA
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

    The test is level 5%. The empirical rate must stay at or below the
    documented tolerance, 0.08.

    That tolerance is coarse. On {0,1} atoms the outcome hangs on the step at
    which an all-zero run first crosses 1/delta: at alpha=0.05 the test
    rejects exactly when the first 66 atoms are all 0, so its Bernoulli(alpha)
    level is 0.95**66 = 0.0339, and a 1/(2*delta) bar (level 0.0756) still
    scores 42/800 here. So the crossing steps are pinned exactly as well
    (rng=None): 66 and 33 for an all-zero run at alpha=0.05 and 0.10, no
    recovery from one loss among the first 66 atoms at alpha=0.05, and
    recovery at step 58 from a loss at step 20 at alpha=0.10.

    Refs: audit NUM-2.
    """
    rng = np.random.default_rng(1)
    rej = sum(wsr_reject(rng.random(80) < ALPHA, ALPHA, DELTA)
              for _ in range(800))
    assert rej / 800 <= 0.08
    for alpha, k in ((0.05, 66), (0.10, 33)):              # all-zero run
        assert not wsr_reject(np.r_[np.zeros(k - 1), np.ones(81 - k)],
                              alpha, DELTA)
        assert wsr_reject(np.r_[np.zeros(k), np.ones(80 - k)], alpha, DELTA)
    one_loss = np.eye(80)
    for j in range(66):                                    # never recovers
        assert not wsr_reject(one_loss[j], ALPHA, DELTA)
    z = one_loss[19]                                       # loss at step 20
    assert not wsr_reject(np.r_[z[:57], np.ones(23)], 0.10, DELTA)
    assert wsr_reject(np.r_[z[:58], np.ones(22)], 0.10, DELTA)


def test_wsr_power_under_clear_margin():
    """Power must exceed 0.9 on a clear margin below alpha.

    The atoms have mean 0.0 and tiny variance, at n=80.
    """
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


def test_nan_weight_raises():
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


def test_certification_rng_streams():
    """The stream depends on alpha, mode and endpoint only (audit V3).

    In particular, no target identifier may enter it.
    """
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
    # the default stream is the baseline stream: no identifier can perturb it
    assert np.allclose(a, certification_rng(0.05, 0, "").standard_normal(6))
    # weird stream values do not crash (no int() fast path)
    certification_rng(0.10, 1, "inf")
    certification_rng(0.10, 1, float("inf"))
    certification_rng(0.05, 0, "∞")


def test_mcap_supplies_ville_boundedness():
    """The M-cap is what keeps atoms in [0,1], the boundedness Ville requires.

    Site sizes here span 20..3000 against M=100. Remove np.minimum(sizes, M)
    and atoms leave [0,1]: each error-heavy 3000-record site (600 errors)
    contributes 0.01*(600*0.95 - 2400*0.05) + 0.05 = 4.55 uncapped. The
    shipped cap keeps every atom in range.

    Refs: audit V6 #1; audit 2026-10 NUM-11.
    """
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
    # the uncapped figure the docstring quotes (g_c = n_c, so g_c/(M n_c) = 1/M)
    z_unc = (np.bincount(site_id, weights=np.where(err, 1 - ALPHA, -ALPHA))
             / 100 + ALPHA)
    assert np.isclose(z_unc.max(), 4.55)


def test_threshold_tie_is_answered_in_atoms():
    """The statistic and the deploy mask share the score >= tau convention.

    A record scoring exactly tau is answered. A mutation to strict > silently
    drops boundary records from the statistic while the deploy mask keeps
    them, and fails here.

    Refs: audit V6 #11.
    """
    score = np.array([0.6])
    err = np.array([True])
    site_id = np.array([0])
    z = influence_atoms(score, err, site_id, 1, np.array([0.6]), ALPHA, M=100)
    # answered tie: Z = (g/(M*n))*(1-alpha) + alpha = (1/100)*0.95 + 0.05
    assert np.isclose(z[0, 0], 0.0095 + ALPHA)
    # under strict '>' the record would be unanswered and Z would collapse to
    # the neutral atom alpha
    assert not np.isclose(z[0, 0], ALPHA)


def test_margin_floor_is_a_first_order_lower_bound():
    """The floor is where delta*exp(n*m/(1-alpha)) reaches one, not a wall.

    It sits below m* = (1-alpha)*(delta**(-1/n) - 1), the smallest margin at
    which certification can be certain, and a rung whose sample margin is
    below the floor can still certify on a favourable draw.

    Refs: audit 2026-10 CORE-2.
    """
    for a in ALPHA_LADDER:
        for n in range(50, 401):
            f = margin_floor(n, DELTA, a)
            assert math.isclose(DELTA * math.exp(n * f / (1 - a)), 1.0,
                                rel_tol=1e-12)
            assert f < (1 - a) * (DELTA ** (-1.0 / n) - 1.0)
    z = np.array([0.0] * 40 + [0.2] * 34)          # sample margin 0.0081
    assert 0.10 - z.mean() < margin_floor(74, DELTA, 0.10)
    assert wsr_reject(z, 0.10, DELTA)              # crosses at t = 33


def test_neutral_atom_moves_bets_both_ways():
    """A neutral atom's own wealth factor is 1, yet it can flip the outcome.

    It counts toward n and enters the running (mu, s2) that set later bets, so
    one placed first can turn a refusal into a certificate, and ten placed
    last can turn a certificate into a refusal. Dropping neutral atoms would
    leave R_M unchanged, since they carry zero weight in it.

    Refs: audit 2026-10 CORE-4.
    """
    a = 0.10
    z = np.full(74, a - 0.04167)
    assert not wsr_reject(z, a, DELTA)
    assert wsr_reject(np.insert(z, 0, a), a, DELTA)
    z = np.full(74, a - 0.04184)
    assert wsr_reject(z, a, DELTA)
    assert not wsr_reject(np.append(z, np.full(10, a)), a, DELTA)

    rng = np.random.default_rng(4)
    n, n_sites, M, tau = 4000, 40, 100, 0.8
    site_id = rng.integers(0, n_sites, n)
    # sites 0..19 score below tau, so they answer nothing there
    score = np.where(site_id < 20, 0.5 + 0.2 * rng.random(n),
                     0.5 + 0.5 * rng.random(n))
    err = rng.random(n) < 0.08
    z = influence_atoms(score, err, site_id, n_sites, np.array([tau]), a,
                        M=M)[0]
    ans = score >= tau
    n_c = np.bincount(site_id, minlength=n_sites)
    n_ans = np.bincount(site_id, weights=ans, minlength=n_sites)
    silent = n_ans == 0
    assert silent.sum() >= 20 and np.all(z[silent] == a)
    g = np.minimum(n_c, M)
    a_c = n_ans / n_c
    e_c = np.divide(np.bincount(site_id, weights=ans & err, minlength=n_sites),
                    n_ans, out=np.zeros(n_sites), where=~silent)
    r_all = (g * a_c * e_c).sum() / (g * a_c).sum()
    r_ans = (g * a_c * e_c)[~silent].sum() / (g * a_c)[~silent].sum()
    assert np.isclose(r_all, r_ans, rtol=0, atol=1e-15)


def test_certification_rng_matches_documented_construction():
    """The walk streams are built exactly as METHODS 4 documents.

    SeedSequence([SEED, alpha index, mode index, w1, w2]), with (w1, w2) the
    first eight bytes of sha256(stream) read as two big-endian 32-bit words;
    the k-th threshold tested consumes the stream's k-th permutation.

    Refs: audit 2026-10 CORE-15.
    """
    for alpha in ALPHA_LADDER:
        for mode, stream in ((0, ""), (1, "lo"), (1, "hi")):
            h = hashlib.sha256(stream.encode()).digest()
            ref = np.random.default_rng(np.random.SeedSequence(
                [SEED, ALPHA_LADDER.index(alpha), mode,
                 int.from_bytes(h[:4], "big"), int.from_bytes(h[4:8], "big")]))
            assert np.array_equal(
                certification_rng(alpha, mode, stream).permutation(83),
                ref.permutation(83))
    # one permutation per call of wsr_reject, whether or not it crosses early
    r1, r2 = certification_rng(0.10, 0), certification_rng(0.10, 0)
    wsr_reject(np.zeros(83), 0.10, DELTA, rng=r1)
    r2.permutation(83)
    assert r1.bit_generator.state == r2.bit_generator.state

    class _Spy:
        def __init__(self, rng):
            self.rng, self.seen = rng, []

        def permutation(self, z):
            out = self.rng.permutation(z)
            self.seen.append(out)
            return out

    good = np.linspace(0.0, 0.04, 83)
    atoms = np.stack([good, good[::-1], np.full(83, 0.5), good])
    spy = _Spy(certification_rng(0.10, 0))
    certified, _ = fixed_sequence_walk(atoms, np.arange(4), 0.10, DELTA,
                                       np.array([0.9, 0.8, 0.7, 0.6]), rng=spy)
    assert certified == [0, 1] and len(spy.seen) == 3   # stopped at index 2
    ref = certification_rng(0.10, 0)
    for k in range(3):
        assert np.array_equal(spy.seen[k], ref.permutation(atoms[k]))


def _wsr_closed_form(z, alpha, delta, plug_in=True):
    """The bet rebuilt from the closed-form variance, independent of wsr_reject.

    plug_in=True: s2_{t-1} = (1/4 + sum_{i<t} (z_i - mu_i)**2) / t with
    mu_i = (1/2 + sum_{j<=i} z_j) / (i+1). plug_in=False: the plain running
    sample variance of the atoms seen so far (1/4 until two are seen), a
    reading the wsr_reject docstring rules out.
    """
    z = np.asarray(z, dtype=float)
    n = len(z)
    t = np.arange(1, n + 1)                               # 1-based step
    if plug_in:
        mu = (0.5 + np.cumsum(z)) / (t + 1)               # mu_i after z_i
        ss = np.concatenate([[0.0], np.cumsum((z - mu) ** 2)[:-1]])
        s2 = (0.25 + ss) / t
    else:
        c1 = np.concatenate([[0.0], np.cumsum(z)[:-1]])
        c2 = np.concatenate([[0.0], np.cumsum(z * z)[:-1]])
        m = np.maximum(t - 1, 1)
        s2 = np.where(t > 2, c2 / m - (c1 / m) ** 2, 0.25)
    lam = np.minimum(
        np.sqrt(2.0 * np.log(1.0 / delta) / (np.maximum(s2, WSR_VAR_FLOOR) * n)),
        WSR_LAMBDA_CAP / (1.0 - alpha))
    log_w = np.cumsum(np.log(np.maximum(1.0 + lam * (alpha - z), 1e-300)))
    return bool((log_w >= np.log(1.0 / delta)).any())


def test_wsr_variance_is_predictable_plugin():
    """wsr_reject's running variance is WSR's predictable plug-in.

    Its decisions match a closed-form reimplementation on 2000 seeded atom
    sets, near-boundary ones included, and differ from a plain
    running-sample-variance reading on some of them, so the test tells the
    two estimators apart.

    Refs: audit 2026-10 CORE-13.
    """
    rng = np.random.default_rng(5)
    decisions, flips = [], 0
    for r in range(2000):
        n = int(rng.integers(20, 120))
        alpha = (0.05, 0.10)[r % 2]
        kind = r % 4
        if kind == 0:
            z = np.clip(rng.normal(alpha - rng.uniform(0, 0.08),
                                   rng.uniform(0.01, 0.3), n), 0, 1)
        elif kind == 1:
            z = (rng.random(n) < alpha * rng.uniform(0.2, 1.2)).astype(float)
        elif kind == 2:
            z = rng.beta(1, 1 / max(alpha - rng.uniform(0, 0.05), 1e-3) - 1, n)
        else:
            z = rng.uniform(0, 2 * alpha * rng.uniform(0.3, 1.0), n)
        d = wsr_reject(z, alpha, DELTA)
        assert d == _wsr_closed_form(z, alpha, DELTA), r
        decisions.append(d)
        flips += d != _wsr_closed_form(z, alpha, DELTA, plug_in=False)
    assert 0 < sum(decisions) < len(decisions)
    assert flips > 0


def test_temperature_rescaling_keeps_labels_but_moves_grid_answered_sets():
    """Temperature keeps y_hat and the score order, not the grid's answered sets.

    TAU_GRID is fixed in score units, so grid point tau answers
    |logit p| >= T*logit(tau). SPEC E8 ARM C, corrected.

    Refs: audit 2026-10 synthetic-4.
    """
    rng = np.random.default_rng(0)
    x = rng.normal(size=(4000, 3))
    base = Head(coef=np.array([1.5, -0.8, 0.4]), intercept=-0.3,
                mu=np.zeros(3), sd=np.ones(3))
    n1 = np.array([(base.score(x) >= t).sum() for t in TAU_GRID])
    lg = np.abs(base.logit(x))
    for T in (0.5, 2.0):   # powers of two: the rescaled logit is exactly logit/T
        hT = Head(coef=base.coef / T, intercept=base.intercept / T,
                  mu=base.mu, sd=base.sd)
        assert np.array_equal(hT.predict(x), base.predict(x))
        sT = hT.score(x)
        for t in TAU_GRID:
            assert np.array_equal(sT >= t, lg >= T * np.log(t / (1.0 - t)))
        nT = np.array([(sT >= t).sum() for t in TAU_GRID])
        assert (nT < n1).any() if T > 1 else (nT > n1).any()
        assert (nT <= n1).all() if T > 1 else (nT >= n1).all()


def test_weight_cap_divides_atom_margin():
    """Weights normalised by a cap C scale every atom's signed margin by 1/C.

    The mechanism METHODS 9 cites for the covariate-shift scope cut: with
    w == 1 and wmax = C, Z_C - alpha == (Z_1 - alpha) / C, so the margin
    falls by C while the information floor does not depend on C.

    Refs: audit 2026-10 DOCS-11.
    """
    rng = np.random.default_rng(0)
    n = 3000
    site_id = rng.integers(0, 30, n)
    score = rng.random(n)
    err = rng.random(n) < 0.05
    tau = np.array([0.3, 0.6])
    z1 = influence_atoms(score, err, site_id, 30, tau, ALPHA, M=100)
    for C in (2.0, 5.0, 10.0):
        zc = influence_atoms(score, err, site_id, 30, tau, ALPHA, M=100,
                             weights=np.ones(n), wmax=C)
        assert np.allclose(zc - ALPHA, (z1 - ALPHA) / C, rtol=0, atol=1e-15)
        assert ((zc >= 0.0) & (zc <= 1.0)).all()


def test_walk_order_key_is_atom_margin():
    """The walk key is alpha minus the mean S_aux atom, not alpha - e_hat.

    alpha - mean_c Z_c = mean_c (g_c/M) a_c (alpha - e_c) weights each site's
    error gap by its influence and answered fraction, so the walk need not
    open at the highest threshold even where the record-pooled answered
    error is smallest there.

    Refs: audit 2026-10 CORE-1.
    """
    rng = np.random.default_rng(123)
    n, n_sites, M = 30000, 208, 100
    site_id = rng.integers(0, n_sites, n)
    score = 0.5 + 0.5 * rng.random(n)
    err = rng.random(n) < 0.4 * (1.0 - score)        # error falls with score
    atoms = influence_atoms(score, err, site_id, n_sites, TAU_GRID, ALPHA, M=M)
    n_c = np.bincount(site_id, minlength=n_sites)
    g = np.minimum(n_c, M)
    key, e_hat = [], []
    for t in TAU_GRID:
        ans = score >= t
        n_ans = np.bincount(site_id, weights=ans, minlength=n_sites)
        e_c = np.divide(np.bincount(site_id, weights=ans & err,
                                    minlength=n_sites),
                        n_ans, out=np.zeros(n_sites), where=n_ans > 0)
        key.append(np.mean(g / M * (n_ans / n_c) * (ALPHA - e_c)))
        e_hat.append((ans & err).sum() / ans.sum())
    assert np.allclose(ALPHA - atoms.mean(axis=1), key, rtol=0, atol=1e-12)
    top = len(TAU_GRID) - 1
    assert int(np.argmax(ALPHA - np.array(e_hat))) == top
    assert int(walk_order(atoms)[0]) != top
