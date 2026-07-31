"""SPEC "Tests" for the explainability layer.

The additive attributions are exact (``sum(phi) + base == logit``); the
abstention margin is ``> 0`` exactly for declined cases; the composition object
reports the three tagged views (audit F25).
"""
import numpy as np

from certgate.data import SimConfig, draw_cohort, split_sites
from certgate.model import fit_head
from certgate.explain import (local_attribution, abstention_explanation,
                              composition)


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
    """audit V22: with every case answered (or every case declined) the gap is
    all-NaN and argsort of it returns the identity permutation -- which
    fabricated feature 0 as top abstention driver. The ranking must be EMPTY."""
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
    """SPEC explain.py counterfactual_to_answer: the minimal-L2 delta flips the
    case under the DEPLOYED rule ``head.score(x_cf) >= tau`` (no tolerance),
    (1 - 1e-4) of it still declines under the same rule, and no standardized
    move of norm below the reported exact minimum flips in ANY direction
    (Cauchy-Schwarz, spot-checked over random directions). The returned delta
    exceeds the reported exact minimum by exactly the documented headroom."""
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
        # the DEPLOYED rule answers the flipped point -- no tolerance
        x_cf = (pool.x[i] + cf["delta_x_min_l2"]).reshape(1, -1)
        assert float(head.score(x_cf)[0]) >= tau_star
        # flip outcome: current side's class, weakest answerable confidence
        assert cf["answered_class_on_flip"] == (cf["logit"] >= 0)
        assert tau_star <= cf["confidence_at_flip"] < tau_star + 1e-8
        # directional minimality under the deployed rule
        x_short = (pool.x[i]
                   + (1 - 1e-4) * cf["delta_x_min_l2"]).reshape(1, -1)
        assert float(head.score(x_short)[0]) < tau_star
        # reported distance is the EXACT minimum m/||coef||; the delta carries
        # exactly the documented headroom on top of it
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
        # FORMULA is pinned, not just the ordering
        assert cf["opposite_side_distance_z"] >= cf["l2_distance_z"]
        assert abs(cf["opposite_side_distance_z"]
                   - (cf["L_star"] + abs(cf["logit"])) / coef_norm) < 1e-12


def test_counterfactual_flips_at_float_hostile_thresholds():
    """Regression for the 2026-07-31 boundary finding: at 6 of the 23 frozen
    grid thresholds ``sigmoid(L*) < tau`` in float64, so a delta landing
    EXACTLY on the bar is still declined by the deployed rule -- 18.2% of the
    fixture head's declines got a non-flipping "counterfactual" while the old
    tolerance-based flip_verified reported True. The headroom must clear every
    declined case at the two worst thresholds."""
    from certgate.explain import counterfactual_to_answer
    head, pool = _head_and_pool()
    for tau_star in (0.63, 0.93):
        scores = head.score(pool.x)
        declined_idx = np.flatnonzero(scores < tau_star)
        assert declined_idx.size >= 1
        for i in declined_idx[:200]:
            cf = counterfactual_to_answer(head, pool.x[i], tau_star)
            x_cf = (pool.x[i] + cf["delta_x_min_l2"]).reshape(1, -1)
            assert float(head.score(x_cf)[0]) >= tau_star, (
                f"deployed rule still declines case {i} at tau={tau_star}")
            assert cf["flip_verified"]


def test_counterfactual_single_feature_flips_and_shorter_fails():
    """The top-ranked single-feature delta flips the case under the deployed
    rule; (1 - 1e-4) of it still declines. Ranking is ascending |delta_z| over
    finite entries."""
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
    # EMPTY ranking -- never the identity permutation over degenerate zeros
    # (audit V22 pattern) -- and no fabricated flip fields
    assert cf["single_feature_ranking"].size == 0
    assert cf["confidence_at_flip"] is None
    assert cf["answered_class_on_flip"] is None


def test_counterfactual_dead_and_degenerate_heads():
    """coef_j == 0 -> inf single-feature delta, excluded from the ranking; the
    all-zero head cannot flip a declined case: distance inf, flip_verified
    False -- never a fabricated zero-cost flip."""
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
