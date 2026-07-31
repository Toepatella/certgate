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
