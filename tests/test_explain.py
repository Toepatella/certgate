"""SPEC "Tests" for the explainability layer.

Three contracts:
  - the additive attributions are exact: sum(phi) + base == logit
  - the abstention margin is > 0 exactly for declined cases
  - the composition object reports the three tagged views

Refs: audit F25.
"""
import numpy as np

from certgate.data import SimConfig, draw_cohort, split_sites
from certgate.model import fit_head
from certgate.explain import (local_attribution, abstention_explanation,
                              composition, gaussian_conditional_shapley_matrix)


def _head_and_pool():
    cfg = SimConfig()
    rng = np.random.default_rng(11)
    coh = draw_cohort(cfg, 40, rng)
    train, _, _ = split_sites(coh, rng)
    head = fit_head(train)
    pool = draw_cohort(cfg, 1, rng, site_label_prefix="p")
    return head, pool


def test_additive_attribution_is_exact():
    head, pool = _head_and_pool()
    for i in (0, 5, 17, 33):
        attr = local_attribution(head, pool.x[i])
        assert abs(attr["base"] + float(attr["phi"].sum())
                   - attr["logit"]) < 1e-10
        assert abs(attr["logit"] - float(head.logit(pool.x[i]))) < 1e-9


def _shapley_by_enumeration(value, k):
    """Exact Shapley values over k players, by enumerating all 2^k coalitions.

    This is the reference, not the implementation under test.
    """
    from itertools import combinations
    from math import factorial
    phi = np.zeros(k)
    for j in range(k):
        others = [i for i in range(k) if i != j]
        for r in range(k):
            for s in combinations(others, r):
                wt = factorial(r) * factorial(k - r - 1) / factorial(k)
                phi[j] += wt * (value(set(s) | {j}) - value(set(s)))
    return phi


def test_linear_attribution_equals_exhaustive_interventional_shapley():
    """phi_j = coef_j * z_j is the interventional Shapley value.

    The baseline is the S_train feature mean. Verified against exhaustive
    enumeration of all 2^8 coalitions on the 8-feature head, rather than
    asserted from the literature.
    """
    head, pool = _head_and_pool()
    k = head.coef.shape[0]
    assert k == 8
    for i in (0, 5, 17):
        z = (pool.x[i] - head.mu) / head.sd
        # interventional value function: absent features sit at the S_train
        # mean (z = 0), so v(S) = intercept + sum_{j in S} coef_j z_j
        def value(s, z=z):
            return float(head.intercept + sum(head.coef[j] * z[j] for j in s))
        phi_ref = _shapley_by_enumeration(value, k)
        assert np.allclose(phi_ref, local_attribution(head, pool.x[i])["phi"],
                           atol=1e-12)


def test_gaussian_conditional_shapley_matrix_pins():
    """Three pins on the matrix B (SPEC explain.py, 2026-08-21).

      - B == diag(w) under independence
      - columns sum to w, the efficiency identity
      - z @ B.T matches exhaustive enumeration of the Gaussian conditional
        value function on a correlated 6-feature block
    """
    rng = np.random.default_rng(3)
    w = rng.standard_normal(6)
    assert np.allclose(gaussian_conditional_shapley_matrix(w, np.eye(6)),
                       np.diag(w))
    a = rng.standard_normal((6, 6))
    cov = a @ a.T + 0.25 * np.eye(6)
    b = gaussian_conditional_shapley_matrix(w, cov)
    assert np.allclose(b.sum(axis=0), w)
    assert not np.allclose(b, np.diag(w))      # correlation moves the values
    z = rng.standard_normal(6)

    def value(s, z=z):
        s = sorted(s)
        sb = [i for i in range(6) if i not in s]
        if not s:
            return 0.0
        a_s = w[s] + (np.linalg.pinv(cov[np.ix_(s, s)])
                      @ (cov[np.ix_(s, sb)] @ w[sb]) if sb else 0.0)
        return float(a_s @ z[s])
    assert np.allclose(_shapley_by_enumeration(value, 6), b @ z, atol=1e-10)


def test_abstention_margin_positive_iff_declined():
    head, pool = _head_and_pool()
    tau_star = 0.8
    scores = head.score(pool.x)
    for i in range(0, pool.n, 7):
        exp = abstention_explanation(head, pool.x[i], tau_star)
        declined_by_score = bool(scores[i] < tau_star)
        assert exp["declined"] == declined_by_score
        assert (exp["margin_to_answer"] > 0) == declined_by_score


def test_composition_three_tagged_objects():
    head, pool = _head_and_pool()
    answered = head.score(pool.x) >= 0.7
    comp = composition(head, pool.x, answered, rho_point=2.0, oracle_y=pool.y)
    assert set(comp) == {"predicted_class", "bbse_true_class",
                         "oracle_true_class"}
    assert comp["predicted_class"]["tag"] == "estimated"
    assert "label-shift" in comp["bbse_true_class"]["tag"]
    assert "oracle" in comp["oracle_true_class"]["tag"]
    # predicted class object is self-consistent
    pc = comp["predicted_class"]
    assert pc["n_answered"] == int(answered.sum())


def test_composition_omits_untagged_views_when_inputs_absent():
    head, pool = _head_and_pool()
    answered = head.score(pool.x) >= 0.7
    comp = composition(head, pool.x, answered)               # no rho, no oracle
    assert set(comp) == {"predicted_class"}


def test_empty_population_gap_ranking_is_empty():
    """An empty answered or declined population gives an empty ranking.

    The gap is all-NaN there. Argsort of it returns the identity permutation,
    which fabricates feature 0 as the top abstention driver.

    Refs: audit V22.
    """
    from certgate.explain import cohort_abstention_profile
    head, pool = _head_and_pool()
    all_answered = np.ones(pool.n, dtype=bool)
    prof = cohort_abstention_profile(head, pool.x, all_answered)
    assert prof["gap_ranking"].size == 0
    assert prof["n_declined"] == 0
    none_answered = np.zeros(pool.n, dtype=bool)
    prof2 = cohort_abstention_profile(head, pool.x, none_answered)
    assert prof2["gap_ranking"].size == 0
    # the mixed case still ranks
    mixed = head.score(pool.x) >= np.median(head.score(pool.x))
    prof3 = cohort_abstention_profile(head, pool.x, mixed)
    assert prof3["gap_ranking"].size == pool.x.shape[1]


def test_counterfactual_min_l2_flips_deployed_rule_and_is_minimal():
    """The minimal-L2 delta flips the case under the deployed rule.

    That rule is head.score(x_cf) >= tau, with no tolerance. Shortening the
    delta to (1 - 1e-4) of it still declines.

    No standardized move of norm below the reported exact minimum flips in any
    direction, by Cauchy-Schwarz, spot-checked over random directions. The
    returned delta exceeds that minimum by exactly the documented headroom.

    Refs: SPEC "explain.py" counterfactual_to_answer.
    """
    from certgate.explain import _EPS_ANSWER_LOGIT, counterfactual_to_answer
    head, pool = _head_and_pool()
    tau_star = 0.8
    scores = head.score(pool.x)
    declined_idx = np.flatnonzero(scores < tau_star)
    assert declined_idx.size >= 1, "fixture must produce declined cases"
    coef_norm = np.linalg.norm(head.coef)
    rng = np.random.default_rng(3)
    for i in declined_idx[:5]:
        cf = counterfactual_to_answer(head, pool.x[i], tau_star)
        assert cf["declined"] and cf["flip_verified"]
        # the deployed rule answers the flipped point -- no tolerance
        x_cf = (pool.x[i] + cf["delta_x_min_l2"]).reshape(1, -1)
        assert float(head.score(x_cf)[0]) >= tau_star
        # flip outcome: current side's class, weakest answerable confidence
        assert cf["answered_class_on_flip"] == (cf["logit"] >= 0)
        assert tau_star <= cf["confidence_at_flip"] < tau_star + 1e-8
        # directional minimality under the deployed rule
        x_short = (pool.x[i]
                   + (1 - 1e-4) * cf["delta_x_min_l2"]).reshape(1, -1)
        assert float(head.score(x_short)[0]) < tau_star
        # the reported distance is the exact minimum m/||coef||, and the delta
        # carries exactly the documented headroom on top of it
        assert abs(cf["l2_distance_z"]
                   - cf["margin_to_answer"] / coef_norm) < 1e-12
        headroom = np.linalg.norm(cf["delta_z_min_l2"]) - cf["l2_distance_z"]
        assert abs(headroom - _EPS_ANSWER_LOGIT / coef_norm) < 1e-12
        # any-direction minimality: a standardized move of norm below the
        # exact minimum cannot reach the bar (Cauchy-Schwarz)
        for _ in range(20):
            d = rng.standard_normal(head.coef.shape[0])
            d *= (cf["l2_distance_z"] * (1 - 1e-6)) / np.linalg.norm(d)
            x_alt = (pool.x[i] + head.sd * d).reshape(1, -1)
            assert float(head.score(x_alt)[0]) < tau_star
        # the same-side minimum is visibly the minimum, and the opposite-side
        # formula is pinned, not just the ordering
        assert cf["opposite_side_distance_z"] >= cf["l2_distance_z"]
        assert abs(cf["opposite_side_distance_z"]
                   - (cf["L_star"] + abs(cf["logit"])) / coef_norm) < 1e-12


def test_counterfactual_flips_at_float_hostile_thresholds():
    """The headroom must clear every declined case at the two worst thresholds.

    At 6 of the 23 frozen grid thresholds sigmoid(L*) < tau in float64, so a
    delta landing exactly on the bar is still declined by the deployed rule.

    That gave 18.2% of the fixture head's declines a non-flipping
    "counterfactual" while the old tolerance-based flip_verified said True.

    Refs: boundary finding 2026-07-31.
    """
    from certgate.explain import counterfactual_to_answer
    head, pool = _head_and_pool()
    for tau_star in (0.63, 0.93):
        scores = head.score(pool.x)
        declined_idx = np.flatnonzero(scores < tau_star)
        assert declined_idx.size >= 1
        for i in declined_idx[:20]:
            cf = counterfactual_to_answer(head, pool.x[i], tau_star)
            x_cf = (pool.x[i] + cf["delta_x_min_l2"]).reshape(1, -1)
            assert float(head.score(x_cf)[0]) >= tau_star, (
                f"deployed rule still declines case {i} at tau={tau_star}")
            assert cf["flip_verified"]


def test_counterfactual_single_feature_flips_and_shorter_fails():
    """The top-ranked single-feature delta flips the case.

    It flips under the deployed rule, and (1 - 1e-4) of it still declines.
    The ranking is ascending in |delta_z| over the finite entries.
    """
    from certgate.explain import counterfactual_to_answer
    head, pool = _head_and_pool()
    tau_star = 0.8
    scores = head.score(pool.x)
    declined_idx = np.flatnonzero(scores < tau_star)
    for i in declined_idx[:5]:
        cf = counterfactual_to_answer(head, pool.x[i], tau_star)
        j = int(cf["single_feature_ranking"][0])
        x_cf = pool.x[i].copy()
        x_cf[j] += cf["single_feature_delta_x"][j]
        assert float(head.score(x_cf.reshape(1, -1))[0]) >= tau_star
        x_short = pool.x[i].copy()
        x_short[j] += (1 - 1e-4) * cf["single_feature_delta_x"][j]
        assert float(head.score(x_short.reshape(1, -1))[0]) < tau_star
        # ranking is ascending in |delta_z| and finite throughout
        dz = np.abs(cf["single_feature_delta_z"][cf["single_feature_ranking"]])
        assert np.all(np.isfinite(dz)) and np.all(np.diff(dz) >= 0)


def test_counterfactual_answered_case_returns_zero_deltas():
    from certgate.explain import counterfactual_to_answer
    head, pool = _head_and_pool()
    tau_star = 0.6
    scores = head.score(pool.x)
    answered_idx = np.flatnonzero(scores >= tau_star)
    assert answered_idx.size >= 1
    cf = counterfactual_to_answer(head, pool.x[answered_idx[0]], tau_star)
    assert not cf["declined"] and cf["flip_verified"]
    assert cf["l2_distance_z"] == 0.0
    assert np.all(cf["delta_z_min_l2"] == 0.0)
    assert np.all(cf["single_feature_delta_z"] == 0.0)
    # empty ranking, never the identity permutation over degenerate zeros,
    # and no fabricated flip fields (audit V22 pattern)
    assert cf["single_feature_ranking"].size == 0
    assert cf["confidence_at_flip"] is None
    assert cf["answered_class_on_flip"] is None


def test_counterfactual_dead_and_degenerate_heads():
    """Degenerate coefficients never produce a fabricated zero-cost flip.

    coef_j == 0 gives an infinite single-feature delta, excluded from the
    ranking. The all-zero head cannot flip a declined case at all: distance
    inf, flip_verified False.
    """
    from certgate.model import Head
    from certgate.explain import counterfactual_to_answer
    head = Head(coef=np.array([0.0, 2.0, -1.0]), intercept=0.1,
                mu=np.zeros(3), sd=np.ones(3))
    cf = counterfactual_to_answer(head, np.array([0.3, -0.1, 0.2]), 0.9)
    assert cf["declined"]
    assert np.isinf(cf["single_feature_delta_z"][0])
    assert 0 not in cf["single_feature_ranking"].tolist()
    assert cf["flip_verified"]

    dead = Head(coef=np.zeros(3), intercept=0.0,
                mu=np.zeros(3), sd=np.ones(3))
    cf2 = counterfactual_to_answer(dead, np.array([1.0, 2.0, 3.0]), 0.9)
    assert cf2["declined"]
    assert np.isinf(cf2["l2_distance_z"])
    assert not cf2["flip_verified"]
    assert cf2["single_feature_ranking"].size == 0
    assert cf2["confidence_at_flip"] is None
    assert cf2["answered_class_on_flip"] is None
