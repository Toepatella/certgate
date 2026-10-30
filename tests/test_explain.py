"""SPEC "Tests" for the explainability layer.

Three contracts:
  - the additive attributions are exact: sum(phi) + base == logit
  - the abstention margin is > 0 exactly for the declined cases of a fixture
    with no case within float64 rounding of the bar
  - the composition object reports the three tagged views

Refs: audit F25; audit 2026-10 explain-11.
"""
import numpy as np
import pytest

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
    comp = composition(head, pool.x, answered, rho_point=2.0, oracle_y=pool.y,
                       pi_source=0.1, pi_train=0.1)
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


def test_composition_bbse_divides_out_the_train_prior():
    """The BBSE view shifts the head's own prior, S_train's, not S_aux's.

    rho_point = odds(pi_t)/odds(pi_aux), but a logistic head with an
    unpenalized intercept carries the S_train prevalence in its odds. With
    pi_t equal to pi_train the view over S_train itself must return the
    head's mean training probability, whatever S_aux's prevalence; the
    rho-only multiplier returned 0.161 against 0.128 here.

    Ref: audit 2026-10 BBSE-1.
    """
    cfg = SimConfig()
    rng = np.random.default_rng(11)
    train, aux, _ = split_sites(draw_cohort(cfg, 40, rng), rng)
    head = fit_head(train)
    pi_train, pi_aux = float(train.y.mean()), float(aux.y.mean())
    assert abs(pi_train - pi_aux) > 0.01
    odds = lambda p: p / (1.0 - p)
    rho = odds(pi_train) / odds(pi_aux)
    every = np.ones(train.n, dtype=bool)
    bt = composition(head, train.x, every, rho_point=rho, pi_source=pi_aux,
                     pi_train=pi_train)["bbse_true_class"]
    assert abs(bt["odds_multiplier"] - 1.0) < 1e-12
    assert bt["pi_source"] == pi_aux and bt["pi_train"] == pi_train
    assert abs(bt["positive_fraction"]
               - float(head.predict_proba(train.x).mean())) < 1e-12
    assert abs(bt["positive_fraction"] - pi_train) < 1e-3


def test_composition_bbse_view_requires_both_priors():
    """rho_point without both priors raises; pi_source is clipped.

    pi_source is clipped to [PI_CLIP, 1 - PI_CLIP] exactly as
    rho_box_interval clips it, and the clipped value is the one recorded.

    Ref: audit 2026-10 BBSE-1.
    """
    from certgate.constants import PI_CLIP
    head, pool = _head_and_pool()
    answered = head.score(pool.x) >= 0.7
    for kw in ({}, {"pi_source": 0.1}, {"pi_train": 0.1}):
        with pytest.raises(ValueError, match=r"\(reason=missing-prior\)$"):
            composition(head, pool.x, answered, rho_point=2.0, **kw)
    for bad in (0.0, 1.0):
        with pytest.raises(ValueError, match="bad-prior"):
            composition(head, pool.x, answered, rho_point=2.0,
                        pi_source=0.1, pi_train=bad)
    bt = composition(head, pool.x, answered, rho_point=2.0, pi_source=0.0,
                     pi_train=0.1)["bbse_true_class"]
    assert bt["pi_source"] == PI_CLIP
    want = 2.0 * (PI_CLIP / (1.0 - PI_CLIP)) / (0.1 / 0.9)
    assert bt["odds_multiplier"] == pytest.approx(want, rel=1e-15)


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
    """The headroom must flip every declined case at every float-hostile grid threshold.

    At 6 of the 23 frozen grid thresholds sigmoid(L*) < tau in float64, each by
    1 ULP, so a delta landing exactly on the bar is still declined by the
    deployed rule. The hostile set is computed from TAU_GRID itself: the
    literal 0.93 is not a grid value (TAU_GRID[19] == 0.9299999999999999) and
    is not hostile.

    That gave 18.2% of the fixture head's declines a non-flipping
    "counterfactual" while the old tolerance-based flip_verified said True.

    Refs: boundary finding 2026-07-31; audit 2026-10 explain-12, NUM-10.
    """
    from certgate.constants import TAU_GRID
    from certgate.model import _sigmoid
    from certgate.explain import counterfactual_to_answer
    head, pool = _head_and_pool()
    hostile = [float(t) for t in TAU_GRID
               if float(_sigmoid(np.log(t / (1.0 - t)))) < t]
    assert hostile, "no float-hostile grid threshold on this platform"
    scores = head.score(pool.x)
    for tau_star in hostile:
        declined_idx = np.flatnonzero(scores < tau_star)
        assert declined_idx.size >= 1
        for i in declined_idx:
            cf = counterfactual_to_answer(head, pool.x[i], tau_star)
            x_cf = (pool.x[i] + cf["delta_x_min_l2"]).reshape(1, -1)
            assert float(head.score(x_cf)[0]) >= tau_star, (
                f"deployed rule still declines case {i} at tau={tau_star!r}")
            assert cf["flip_verified"]


def test_counterfactual_single_feature_flips_and_shorter_fails():
    """The top-ranked single-feature delta flips the case.

    It flips under the deployed rule, and (1 - 1e-4) of it still declines.
    The ranking is ascending in |delta_z| over the finite entries. The
    single-feature deltas carry the same _EPS_ANSWER_LOGIT headroom as the
    minimal-L2 delta (audit 2026-10 explain-9).
    """
    from certgate.explain import _EPS_ANSWER_LOGIT, counterfactual_to_answer
    head, pool = _head_and_pool()
    tau_star = 0.8
    scores = head.score(pool.x)
    declined_idx = np.flatnonzero(scores < tau_star)
    for i in declined_idx[:5]:
        cf = counterfactual_to_answer(head, pool.x[i], tau_star)
        dz_all = cf["single_feature_delta_z"]
        fin = np.isfinite(dz_all)
        assert np.all(np.abs(cf["direction"] * head.coef[fin] * dz_all[fin]
                             - (cf["margin_to_answer"] + _EPS_ANSWER_LOGIT))
                      < 1e-12)
        assert not np.any(np.isneginf(dz_all))
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
    assert cf["single_feature_delta_z"][0] == np.inf     # +inf, never -inf
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


def test_single_feature_ranking_is_abs_coef_order_and_off_top_equal_budget_never_flips():
    """The ranking is the descending-|coef| order; equal budget off the top fails.

    For the linear head every declined case gets the same ranking, the
    descending-|coef| order. Spending the top feature's |delta_z| in the
    favourable direction on any other feature shifts the logit by only
    |coef_j|/|coef_top| of the padded margin, so it cannot flip a case whose
    margin is far above the 1e-9 headroom. E5's random-feature control rate
    therefore measures 1/d, not the ranking's informativeness.

    Ref: audit 2026-10 synthetic-8.
    """
    from certgate.explain import counterfactual_to_answer
    head, pool = _head_and_pool()
    tau_star = 0.8
    nz = np.flatnonzero(head.coef != 0.0)
    want = nz[np.argsort(-np.abs(head.coef[nz]), kind="stable")]
    scores = head.score(pool.x)
    n_checked = 0
    for i in np.flatnonzero(scores < tau_star)[:20]:
        cf = counterfactual_to_answer(head, pool.x[i], tau_star)
        if cf["margin_to_answer"] <= 1e-6:
            continue
        rank = cf["single_feature_ranking"]
        assert np.array_equal(rank, want)
        top = int(rank[0])
        budget = abs(cf["single_feature_delta_z"][top])
        for j in rank[1:]:
            x_alt = pool.x[i].copy()
            x_alt[j] += (head.sd[j] * cf["direction"]
                         * np.sign(head.coef[j]) * budget)
            assert float(head.score(x_alt.reshape(1, -1))[0]) < tau_star
        n_checked += 1
    assert n_checked >= 5


def test_cohort_gap_factorises_as_abs_standardized_coef():
    """w_j is the standardized coefficient, so phi_j = w_j z_j (explain-1).

    With sd far from 1, phi equals coef * z and (coef / sd) * (x - mu), base
    is the logit at the training mean, and the cohort gap factorises as
    |coef_j| times the difference in mean |z_j| -- not |coef_j / sd_j| times
    it.

    Ref: audit 2026-10 explain-1, PAPER1-14, NUM-7, DOCS-5.
    """
    from certgate.model import Head
    from certgate.explain import cohort_abstention_profile
    head = Head(coef=np.array([0.9, -0.6, 0.35, 1.2]), intercept=-0.4,
                mu=np.array([0.2, 50.0, 7.3, -1.0]),
                sd=np.array([1.0, 12.0, 0.15, 3.0]))
    rng = np.random.default_rng(7)
    x = head.mu + head.sd * rng.standard_normal((400, 4))
    z = (x - head.mu) / head.sd
    for i in (0, 1, 2):
        attr = local_attribution(head, x[i])
        assert np.allclose(attr["phi"], head.coef * z[i], rtol=0, atol=1e-12)
        assert np.allclose(attr["phi"], (head.coef / head.sd) * (x[i] - head.mu),
                           rtol=0, atol=1e-12)
    assert local_attribution(head, head.mu)["base"] == float(
        head.logit(head.mu))
    answered = head.score(x) >= 0.75
    assert answered.any() and (~answered).any()
    prof = cohort_abstention_profile(head, x, answered)
    dmean = (np.abs(z[answered]).mean(axis=0)
             - np.abs(z[~answered]).mean(axis=0))
    assert np.allclose(prof["gap"], np.abs(head.coef) * dmean,
                       rtol=0, atol=1e-12)
    assert not np.allclose(prof["gap"], np.abs(head.coef / head.sd) * dmean,
                           rtol=0, atol=1e-6)


def test_counterfactual_formulas_use_standardized_coef_under_nonunit_sd():
    """The closed-form moves use the standardized coef, w = head.coef.

    Under sd far from 1 the minimal standardized move is s*m_eff*w/||w||^2 at
    distance m/||w||, and the single-feature move is s*m_eff/w_j, i.e.
    sd_j times that in raw units. Reading w as the raw-space coefficient
    coef/sd gives a standardized move that falls short of the bar.

    Ref: audit 2026-10 NUM-7, DOCS-5, explain-1.
    """
    from certgate.model import Head
    from certgate.explain import _EPS_ANSWER_LOGIT, counterfactual_to_answer
    head = Head(coef=np.array([0.9, -0.6, 0.35, 1.2]), intercept=-0.4,
                mu=np.array([0.2, 50.0, 7.3, -1.0]),
                sd=np.array([1.0, 10.0, 0.2, 3.0]))
    tau = 0.8
    x0 = head.mu.copy()                           # logit = intercept = -0.4
    cf = counterfactual_to_answer(head, x0, tau)
    assert cf["declined"] and cf["flip_verified"]
    s, m = cf["direction"], cf["margin_to_answer"]
    w = head.coef
    m_eff = m + _EPS_ANSWER_LOGIT
    assert np.allclose(cf["delta_z_min_l2"], s * m_eff * w / (w @ w),
                       rtol=0, atol=1e-15)
    assert abs(cf["l2_distance_z"] - m / np.linalg.norm(w)) < 1e-15
    assert np.allclose(cf["single_feature_delta_z"], s * m_eff / w,
                       rtol=1e-15, atol=0)
    assert np.allclose(cf["single_feature_delta_x"],
                       head.sd * cf["single_feature_delta_z"],
                       rtol=1e-15, atol=0)
    a = w / head.sd                               # the raw-space coefficient
    dz_raw_reading = s * m * a / (a @ a)
    x_wrong = (x0 + head.sd * dz_raw_reading).reshape(1, -1)
    assert float(head.score(x_wrong)[0]) < tau


def test_declined_flag_is_the_logit_test_at_the_float64_bar():
    """`declined` is the logit-space test, not the deployed score rule.

    On the bar itself, |logit| == L* exactly, the margin is 0 and the flag is
    False, while at the float-hostile threshold 0.63 the deployed rule
    head.score(x) >= tau still declines (sigmoid(L*) < tau by 1 ULP). The
    documented band where the two can disagree is pinned here.

    Ref: audit 2026-10 explain-11.
    """
    from certgate.constants import TAU_GRID
    from certgate.model import Head
    from certgate.explain import counterfactual_to_answer
    head = Head(coef=np.array([1.0]), intercept=0.0, mu=np.array([0.0]),
                sd=np.array([1.0]))
    tau = float(TAU_GRID[4])
    assert abs(tau - 0.63) < 1e-12
    x = np.array([np.log(tau / (1.0 - tau))])
    exp = abstention_explanation(head, x, tau)
    assert exp["margin_to_answer"] == 0.0
    assert exp["declined"] is False
    assert float(head.score(x.reshape(1, -1))[0]) < tau
    cf = counterfactual_to_answer(head, x, tau)
    assert cf["declined"] is False
    assert cf["flip_verified"] is False


def test_value_and_missing_sibling_are_uncorrelated_on_s_train():
    """Mean imputation plus S_train standardization decorrelates a feature
    from its __missing sibling, up to float rounding, so the pair is not what
    makes cov_SS singular in gaussian_conditional_shapley_matrix.

    Ref: audit 2026-10 explain-10.
    """
    rng = np.random.default_rng(29)
    n = 500
    v = rng.lognormal(0.0, 1.0, n)
    missing = v > np.quantile(v, 0.7)             # MNAR: large values missing
    x0 = np.where(missing, v[~missing].mean(), v)
    xs = np.column_stack([x0, missing.astype(np.float64)])
    z = (xs - xs.mean(axis=0)) / xs.std(axis=0)
    assert abs(float((z.T @ z / n)[0, 1])) < 1e-12


def test_sigmoid_is_silent_and_exact_at_extreme_logits():
    """Both np.where branches are evaluated; the discarded one must not leak a
    RuntimeWarning or, under a strict error state, a FloatingPointError, and
    silencing must not move a bit. Ref: audit 2026-10 NUM-13."""
    import math
    import warnings
    from certgate import model
    z = np.array([-np.inf, -1e4, -800.0, -709.79, -40.0, -0.0, 0.0, 40.0,
                  709.79, 800.0, 1e4, np.inf])
    head = model.Head(coef=np.array([1.0]), intercept=0.0, mu=np.zeros(1),
                      sd=np.ones(1))
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with np.errstate(all="raise"):
            p = model._sigmoid(z)
            p0 = model._sigmoid(800.0)           # the 0-d path local_attribution uses
            s = head.score(np.array([[1e3], [-1e3], [5.0]]))
    assert p[:3].tolist() == [0.0, 0.0, 0.0]
    assert 0.0 < p[3] < 1e-308                   # gradual underflow, neither 0 nor NaN
    assert abs(p[4] / math.exp(-40.0) - 1.0) < 1e-15
    assert p[5:7].tolist() == [0.5, 0.5]
    assert p[7:].tolist() == [1.0] * 5
    assert float(p0) == 1.0
    assert s[:2].tolist() == [1.0, 1.0]
    assert abs(s[2] - 1.0 / (1.0 + math.exp(-5.0))) < 1e-15
    rng = np.random.default_rng(13)
    w = np.concatenate([rng.normal(0.0, 5.0, 4096), rng.uniform(-750.0, 750.0, 4096)])
    with np.errstate(all="ignore"):
        ref = np.where(w >= 0, 1.0 / (1.0 + np.exp(-w)), np.exp(w) / (1.0 + np.exp(w)))
    assert np.array_equal(model._sigmoid(w).view(np.uint64), ref.view(np.uint64))


def test_dashboard_histogram_and_explorer_follow_the_deployed_rule(tmp_path):
    """The dashboard's histogram follows the deployed rule exactly; the
    threshold explorer counts at its 2-dp bars.

    Both are computed in build_dashboard on the same float64 scores as the
    answered mask, never re-derived from 4-dp scores in the page, and the
    payload no longer carries all_scores. The histogram splits by
    score >= tau. The explorer is an intuition aid whose entries count
    score >= k/100, k = 55..99, so at a deployed grid tau one ulp off its 2-dp
    value (TAU_GRID[14] = 0.8300000000000001) its opening reading can differ
    from the answered count by scores inside that ulp.

    Ref: audit 2026-10 explain-5.
    """
    import json
    from certgate.constants import SEED, TAU_GRID
    from examples.explain_dashboard import build_dashboard
    rng = np.random.default_rng(SEED)
    cfg = SimConfig()
    coh = draw_cohort(cfg, 40, rng)
    train = split_sites(coh, rng)[0]
    head = fit_head(train)
    pool = draw_cohort(cfg, 4, rng, site_label_prefix="demo")
    scores = head.score(pool.x)
    prefix = "const DATA = "
    for tau in (0.77, float(TAU_GRID[15]), float(TAU_GRID[18]), 0.83):
        out = tmp_path / f"dash_{tau!r}.html"
        build_dashboard(head, pool.x, tau, str(out))
        line = next(l for l in out.read_text(encoding="utf-8").splitlines()
                    if l.startswith(prefix))
        payload = json.loads(line[len(prefix):].rstrip(";"))
        assert "all_scores" not in payload
        ha = np.array(payload["hist"]["answered"])
        hd = np.array(payload["hist"]["declined"])
        assert ha.sum() == int((scores >= tau).sum())
        assert hd.sum() == int((scores < tau).sum())
        k = int(round((tau - 0.5) * 100))
        assert ha[:k].sum() == 0 and hd[k:].sum() == 0
        assert payload["explore_answered"] == [
            int((scores >= j / 100).sum()) for j in range(55, 100)]
