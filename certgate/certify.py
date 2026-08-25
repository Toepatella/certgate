"""The statistical core of the certified gate.

The math is ported verbatim from the audited v1 reference at
../xAI-projtect-v1/testbed/certify.py, which survived adversarial review.
Where v1 and the SPEC disagree, the SPEC wins: its constants, its isfinite
guards on scores and weights, and its sha256-only seed rule.

What lives here:
  - influence_atoms       per-site atoms Z_c in [0, 1]
  - wsr_reject            one-sided Waudby-Smith-Ramdas betting test
  - margin_floor          information-theoretic feasibility floor
  - walk_order            S_aux-ordered fixed sequence, most conservative first
  - fixed_sequence_walk   learn-then-test threshold walk at full delta
  - certification_rng     deterministic, unchoosable permutation stream

Refs: SPEC "certify.py"; METHODS 3 (atoms), METHODS 4 (the rest).
"""

import hashlib

import numpy as np

from .constants import (SEED, ALPHA_LADDER, WSR_LAMBDA_CAP, WSR_VAR_FLOOR,
                        WSR_MU0, WSR_S2_0)


def influence_atoms(score, err, site_id, n_sites, tau_grid, alpha, M,
                    weights=None, wmax=1.0):
    """Per-site atoms Z_c in [0, 1], shape (n_tau, n_sites).

        Z_c = (g_c / (M*n_c)) * sum_{i in c} ans_i*(err_i - alpha) + alpha

    with the data-independent influence weight g_c = min(n_c, M). The whole
    point of that construction: E[Z] <= alpha exactly when R_M <= alpha.

    A site with no answered-eligible records enters as a neutral atom,
    Z_c = alpha. It is never dropped -- dropping would redefine the cluster
    population after the fact. A neutral atom costs power, never validity.

    Weighted mode (label-shift correction) scales each record's contribution by
    w_i / wmax, with w_i in [0, wmax]. The certified statistic is
    scale-invariant in w, so the normalization exists only to keep atoms in
    range.

    Raises on non-finite scores, and on weights that are non-finite or outside
    [0, wmax].

    Refs: METHODS 3; SPEC "certify.py" hardening; audits F36, F08.
    """
    score = np.asarray(score, dtype=float)
    if not np.isfinite(score).all():
        raise ValueError(
            "influence_atoms: score contains non-finite values "
            "(reason=nonfinite-score)")
    sizes = np.bincount(site_id, minlength=n_sites).astype(float)
    # empty (screened-out) sites -> zero influence -> neutral atom == alpha
    g_over_Mn = np.where(sizes > 0,
                         np.minimum(sizes, M) / (M * np.maximum(sizes, 1.0)),
                         0.0)
    base = np.where(err, 1.0 - alpha, -alpha)
    if weights is not None:
        w = np.asarray(weights, dtype=float)
        if (not np.isfinite(w).all()) or w.min() < 0.0 or w.max() > wmax + 1e-12:
            raise ValueError(
                "influence_atoms: weights must be finite and in [0, wmax] "
                "(reason=bad-weights)")
        base = base * (w / wmax)
    out = np.empty((len(tau_grid), n_sites))
    for t, tau in enumerate(tau_grid):
        ans = score >= tau
        s = np.bincount(site_id, weights=base * ans, minlength=n_sites)
        out[t] = g_over_Mn * s + alpha
    return out


def wsr_reject(z, alpha, delta, rng=None):
    """One-sided WSR betting test of H0: E[Z] >= alpha.

    Returns True (certify) when the wealth process

        K_t = prod (1 + lam_s (alpha - Z_s))

    sup-crosses 1/delta. Ville's inequality is what makes that a finite-sample
    level-delta test.

    lam_t is predictable and variance-adaptive: capped at
    WSR_LAMBDA_CAP/(1-alpha), variance floored at WSR_VAR_FLOOR, with the
    running (mu, s2) starting from (WSR_MU0, WSR_S2_0). rng supplies the
    prespecified permutation.

    Refs: METHODS 4; SPEC seed rule.
    """
    z = np.asarray(z, dtype=float)
    if rng is not None:
        z = rng.permutation(z)
    n = len(z)
    log_inv_delta = np.log(1.0 / delta)
    log_wealth = 0.0
    mu, s2, cnt = WSR_MU0, WSR_S2_0, 1.0
    lam_cap = WSR_LAMBDA_CAP / (1.0 - alpha)
    for t in range(n):
        lam = min(np.sqrt(2.0 * log_inv_delta / (max(s2, WSR_VAR_FLOOR) * n)),
                  lam_cap)
        log_wealth += np.log(max(1.0 + lam * (alpha - z[t]), 1e-300))
        if log_wealth >= log_inv_delta:
            return True                       # sup-crossing: Ville covers it
        cnt += 1.0
        mu += (z[t] - mu) / cnt
        s2 += ((z[t] - mu) ** 2 - s2) / cnt
    return False


def margin_floor(n, delta, alpha):
    """Smallest margin any valid level-delta test could certify (METHODS 4).

    No test of a [0,1]-bounded mean beats ln(1/delta) * (1 - alpha) / n. We
    report it as a diagnostic, never as a gate.
    """
    return np.log(1.0 / delta) * (1.0 - alpha) / n


def walk_order(atoms_aux):
    """Order the thresholds for the fixed-sequence walk, using S_aux only.

    Ascending mean atom, so the most conservative threshold -- largest
    estimated margin -- is tried first. The order never looks at S_cal, which
    is why it costs no multiplicity budget. (METHODS 4)
    """
    return np.argsort(atoms_aux.mean(axis=1))


def fixed_sequence_walk(atoms, order, alpha, delta, tau_grid, rng=None):
    """Learn-then-test threshold walk (METHODS 4).

    Tests thresholds in the prespecified order at full delta and stops at the
    first failure. Returns (certified tau-indices, deployed index or None),
    where deployed is the lowest tau in the certified prefix -- the one that
    answers the most cases.
    """
    certified = []
    for t in order:
        if wsr_reject(atoms[t], alpha, delta, rng=rng):
            certified.append(int(t))
        else:
            break
    if not certified:
        return [], None
    deployed = min(certified, key=lambda t: tau_grid[t])
    return certified, deployed


def certification_rng(alpha, mode_idx, stream=""):
    """A prespecified permutation stream nobody can choose after the fact.

    The stream discriminator is hashed with sha256, and its first eight bytes
    are spread across two 32-bit SeedSequence entries. There is no int() fast
    path, so nothing aliases numerically and odd inputs cannot raise
    OverflowError. Deterministic in the frozen inputs and the run identity.

    The target label is deliberately NOT part of the seed. Baseline atoms do
    not depend on the target, so seeding with the label gave every target a
    separately randomized test of the same calibration data. Two things broke:
    the deployed threshold moved with the spelling of a free-text identifier,
    and the shared-1-delta-event clause printed on the certificate was false.

    stream distinguishes only the BBSE endpoint walks ("lo" / "hi"). The
    baseline walk passes the default "".

    Refs: SPEC seed rule; METHODS 4; audits B-10, F43, F57, V3.
    """
    h = hashlib.sha256(str(stream).encode()).digest()
    return np.random.default_rng(np.random.SeedSequence(
        [SEED, ALPHA_LADDER.index(alpha), mode_idx,
         int.from_bytes(h[:4], "big"), int.from_bytes(h[4:8], "big")]))
