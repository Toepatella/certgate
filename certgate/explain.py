"""Attributions, abstention explanations, and answered-set composition.

For the linear head the additive attributions phi_j = coef_j * z_j, in
standardized space, are exact interventional Shapley values against the S_train
feature-mean baseline -- the Linear SHAP result. No sampling is involved, and
sum(phi) + intercept == logit to machine precision.

Naming the value function is load-bearing. Under correlated features the
conditional Shapley values differ from these, and the efficiency identity does
not tell the two apart, since both decompositions satisfy it.

Abstentions are explained against the answering bar L* = log(tau*/(1-tau*)).
In exact arithmetic answering requires |logit| >= L*, so the margin-to-answer
L* - |logit| is positive exactly for declined cases. The returned `declined`
flag is that logit-space test. In float64 it can disagree, in either
direction, with the deployed rule head.score(x) >= tau* when |logit| is
within rounding error of L* (summation order, sigmoid rounding; see
_EPS_ANSWER_LOGIT). Ref: audit 2026-10 explain-11.

Declined cases also carry an exact contrastive artifact,
counterfactual_to_answer: the closed-form minimal move, whole-vector or
single-feature, that would make the case answerable. It is a score-space
recourse statement, never a clinical recommendation.

Refs: SPEC "explain.py"; METHODS 6; audit V20.
"""
from __future__ import annotations

import numpy as np

from certgate.constants import PI_CLIP
from certgate.model import _sigmoid


def _standardize(head: "Head", x_row) -> np.ndarray:
    x_row = np.asarray(x_row, dtype=np.float64)
    return (x_row - head.mu) / head.sd


def global_importance(head: "Head") -> np.ndarray:
    """Standardized-space coefficients: direction and strength per feature.

    The head's coef already lives in standardized space, so it is the global
    importance vector.

    Refs: SPEC "explain.py"; METHODS 6 ("standardized coefficients").
    """
    return np.asarray(head.coef, dtype=np.float64)


def local_attribution(head: "Head", x_row) -> dict:
    """Exact additive attributions for one case (SPEC explain.py).

    Returns base (the intercept), phi (coef_j * z_j), logit and p1. By
    construction sum(phi) + base == logit exactly.

    phi are the interventional Shapley values of the linear logit against the
    S_train feature-mean baseline, i.e. Linear SHAP. They are exact for that
    value function, and differ from conditional Shapley values whenever
    features are correlated.

    Refs: audit V20.
    """
    z = _standardize(head, x_row)
    phi = head.coef * z
    base = float(head.intercept)
    logit = base + float(phi.sum())
    return {"base": base, "phi": phi, "logit": logit, "p1": float(_sigmoid(logit))}


def abstention_explanation(head: "Head", x_row, tau_star) -> dict:
    """Explain why a case is answered or declined at threshold tau_star.

    The answering bar is L* = log(tau*/(1-tau*)), so in exact arithmetic
    answering requires |logit| >= L*.

    Reports the signed margin-to-answer, declined = (margin > 0), and each
    feature's signed contribution toward or away from the decided-class
    confidence. declined is the logit-space test: within float64 rounding of
    |logit| = L* it can disagree, either way, with the deployed rule
    head.score(x) >= tau_star.

    Refs: SPEC "explain.py"; audit 2026-10 explain-11.
    """
    attr = local_attribution(head, x_row)
    logit = attr["logit"]
    l_star = float(np.log(tau_star / (1.0 - tau_star)))
    margin_to_answer = l_star - abs(logit)
    direction = 1.0 if logit >= 0 else -1.0
    toward_confidence = attr["phi"] * direction     # >0 builds confidence, <0 erodes it
    return {
        "tau_star": float(tau_star),
        "L_star": l_star,
        "logit": logit,
        "abs_logit": abs(logit),
        "margin_to_answer": margin_to_answer,
        "declined": bool(margin_to_answer > 0),
        "phi": attr["phi"],
        "toward_confidence": toward_confidence,
        "p1": attr["p1"],
    }


# Headroom added to the flip target in logit space. A delta landing exactly on
# |logit| = L* is declined by the deployed float64 rule head.score(x) >= tau on
# a measurable fraction of cases. Three float64 effects stack up:
#   - sigmoid(log(tau/(1-tau))) < tau for 6 of the 23 frozen TAU_GRID
#     thresholds, 1 ULP each;
#   - summation-order noise between the attribution sum and Head.logit's BLAS
#     dot reaches ~3e-14;
#   - the raw-space round trip adds ~1e-12.
# 1e-9 dominates every measured shortfall, and realized confidence moves by
# less than 3e-10.
# Ref: adversarial verification 2026-07-31 -- exact landings failed the
# deployed rule on 18.2% of fixture-head declines.
_EPS_ANSWER_LOGIT = 1e-9


def counterfactual_to_answer(head: "Head", x_row, tau_star) -> dict:
    """Minimal counterfactuals into the answer region (SPEC explain.py).

    The head is linear in standardized space, so "what is the smallest change
    that would make this case answerable?" has a closed-form answer. Take a
    declined case with margin m = L* - |logit| > 0 on its current side
    s = sign(logit), where a tie at 0 counts as +1. Two moves:

    - minimal standardized-L2 move: direction s*coef, exact minimal distance
      m/||coef||_2. By Cauchy-Schwarz no smaller-norm move flips it, in any
      direction.
    - single-feature counterfactual: delta_z_j = s*m/coef_j, in raw units
      delta_x_j = sd_j * delta_z_j, and inf where coef_j == 0.

    The reported distances are those exact minima. The returned delta vectors
    -- delta_*_min_l2 and single_feature_delta_* -- instead use
    m + _EPS_ANSWER_LOGIT, so the flip survives the deployed
    float64 rule head.score(x_cf) >= tau_star -- an exact landing on the bar
    provably does not. flip_verified re-evaluates that deployed rule with no
    tolerance.

    confidence_at_flip is the realized head.score at the flipped point: the
    weakest answerable answer, within ~3e-10 above tau_star.
    answered_class_on_flip is the current side's predicted class. Both are None
    unless the case was declined and the flip verified.

    These are score-space recourse statements about the gate, never causal or
    clinically achievable actions. Features are not independently manipulable
    -- a missingness indicator cannot "move 0.4" -- and the artifact answers
    what the gate would need, not what the clinician should do.

    Two degenerate cases. An answered case returns zero deltas, distance 0 and
    an empty ranking, never the argsort-of-degenerate identity permutation. An
    all-zero head cannot flip: distance inf, flip_verified False.

    declined is the logit-space test margin > 0, as in abstention_explanation,
    so within float64 rounding of the bar it can disagree with the deployed
    rule either way; flip_verified always reports the deployed rule at the
    returned point.

    Refs: _EPS_ANSWER_LOGIT; audit V22; audit 2026-10 explain-9, explain-11.
    """
    attr = local_attribution(head, x_row)
    logit = attr["logit"]
    l_star = float(np.log(tau_star / (1.0 - tau_star)))
    margin = l_star - abs(logit)
    declined = bool(margin > 0)
    m = max(margin, 0.0)
    m_eff = m + _EPS_ANSWER_LOGIT if declined else 0.0
    s = 1.0 if logit >= 0 else -1.0
    coef = np.asarray(head.coef, dtype=np.float64)
    sd = np.asarray(head.sd, dtype=np.float64)
    coef_norm2 = float(coef @ coef)

    if coef_norm2 > 0.0:
        delta_z_min = (s * m_eff / coef_norm2) * coef
        l2_distance_z = m / float(np.sqrt(coef_norm2))
        opposite_z = (l_star + abs(logit)) / float(np.sqrt(coef_norm2))
    else:
        delta_z_min = np.zeros_like(coef)
        l2_distance_z = float("inf") if declined else 0.0
        opposite_z = float("inf")

    if declined:
        with np.errstate(divide="ignore"):
            single_z = np.where(coef != 0.0, s * m_eff / coef, np.inf)
        finite = np.isfinite(single_z)
        order = np.argsort(np.abs(np.where(finite, single_z, np.inf)),
                           kind="stable")
        ranking = order[finite[order]]
    else:
        single_z = np.zeros_like(coef)
        ranking = np.array([], dtype=np.int64)
    single_x = sd * single_z
    delta_x_min = sd * delta_z_min

    # the deployed rule, exactly as pipeline.py compares it -- no tolerance
    x_cf = np.asarray(x_row, dtype=np.float64) + delta_x_min
    score_cf = float(head.score(x_cf.reshape(1, -1))[0])
    flip_verified = bool(score_cf >= tau_star)
    flipped = declined and flip_verified

    return {
        "tau_star": float(tau_star),
        "L_star": l_star,
        "logit": logit,
        "margin_to_answer": margin,
        "declined": declined,
        "direction": s,
        "delta_z_min_l2": delta_z_min,
        "delta_x_min_l2": delta_x_min,
        "l2_distance_z": l2_distance_z,
        "single_feature_delta_z": single_z,
        "single_feature_delta_x": single_x,
        "single_feature_ranking": ranking,
        "opposite_side_distance_z": opposite_z,
        "answered_class_on_flip": bool(s > 0) if flipped else None,
        "confidence_at_flip": score_cf if flipped else None,
        "flip_verified": flip_verified,
    }


def cohort_abstention_profile(head: "Head", x, answered_mask) -> dict:
    """Mean |phi_j| for answered and declined cases, plus a gap ranking.

    Identifies systematic abstention drivers: the features whose typical
    contribution magnitude differs most between the two populations.

    Refs: SPEC "explain.py".
    """
    x = np.asarray(x, dtype=np.float64)
    answered_mask = np.asarray(answered_mask, dtype=bool)
    z = (x - head.mu) / head.sd
    abs_phi = np.abs(z * head.coef)                 # (n, d)
    declined_mask = ~answered_mask
    d = head.coef.shape[0]
    mean_ans = abs_phi[answered_mask].mean(axis=0) if answered_mask.any() else np.full(d, np.nan)
    mean_dec = abs_phi[declined_mask].mean(axis=0) if declined_mask.any() else np.full(d, np.nan)
    gap = mean_ans - mean_dec
    # When either population is empty the gap is undefined, so the ranking is
    # empty. It is never argsort of all-NaN: that returns the identity
    # permutation and fabricates feature 0 as the top abstention driver.
    # Ref: audit V22.
    if np.isnan(gap).all():
        gap_ranking = np.array([], dtype=np.int64)
    else:
        gap_ranking = np.argsort(-np.abs(gap))
    return {
        "mean_abs_phi_answered": mean_ans,
        "mean_abs_phi_declined": mean_dec,
        "gap": gap,
        "gap_ranking": gap_ranking,
        "n_answered": int(answered_mask.sum()),
        "n_declined": int(declined_mask.sum()),
    }


def gaussian_conditional_shapley_matrix(coef, cov) -> np.ndarray:
    """(k, k) matrix B with phi_cond = z @ B.T (SPEC explain.py, 2026-08-21).

    Conditional Shapley values of the linear logit w . z under the Gaussian
    conditional value function of Aas, Jullum & Loland (2021), with
    z ~ N(0, cov).

    The conditional mean is linear, so every coalition value is c + a_S . z,
    with a_S[S] = w_S + cov_SS^{-1} cov_SSbar w_Sbar and a_S[Sbar] = 0. The
    Shapley sum over the 2^k coalitions then collapses to one k x k matrix,
    computed exactly by enumeration, no sampling. pinv handles a singular
    cov_SS: an S_train-constant column (z == 0 under the guarded sd), two
    exactly collinear columns (e.g. __missing indicators with one pattern),
    or a complete one-hot group. A feature beside its own __missing sibling
    is not a source: under S_train mean imputation and S_train
    standardization the two are uncorrelated on S_train, up to float
    rounding (z_j is 0 on every imputed row and sums to 0). Ref: audit
    2026-10 explain-10.

    Two checks on B. Its columns sum to w -- efficiency, sum_j phi_j = w . z.
    And B == diag(w) when cov is the identity, where conditional and
    interventional values coincide.
    """
    w = np.asarray(coef, dtype=np.float64).ravel()
    cov = np.asarray(cov, dtype=np.float64)
    k = w.shape[0]
    if cov.shape != (k, k):
        raise ValueError(f"gaussian_conditional_shapley_matrix: cov shape "
                         f"{cov.shape} != ({k}, {k})")
    fact = [1.0]
    for i in range(1, k + 1):
        fact.append(fact[-1] * i)
    # a_S for every coalition, indexed by bitmask
    a = np.zeros((1 << k, k), dtype=np.float64)
    idx = np.arange(k)
    for mask in range(1, 1 << k):
        in_s = ((mask >> idx) & 1).astype(bool)
        s_idx, sbar_idx = idx[in_s], idx[~in_s]
        a[mask, s_idx] = w[s_idx]
        if sbar_idx.size:
            a[mask, s_idx] += np.linalg.pinv(cov[np.ix_(s_idx, s_idx)]) @ (
                cov[np.ix_(s_idx, sbar_idx)] @ w[sbar_idx])
    b = np.zeros((k, k), dtype=np.float64)
    for mask in range(1 << k):
        size = bin(mask).count("1")
        weight = fact[size] * fact[k - size - 1] / fact[k] if size < k else 0.0
        if weight == 0.0:
            continue
        for j in range(k):
            if not (mask >> j) & 1:
                b[j] += weight * (a[mask | (1 << j)] - a[mask])
    return b


def composition(head: "Head", target_x, answered_mask, rho_point=None,
                oracle_y=None, *, pi_source=None, pi_train=None) -> dict:
    """Answered-set class composition, reported up to three tagged ways.

    - predicted_class (estimated): the fraction the head calls positive.
    - bbse_true_class (estimated, label-shift-tagged, only when rho_point is
      given): the label-shift-corrected true-positive fraction. A logistic
      head fit on S_train carries the S_train prevalence in its posterior
      odds (its unpenalized intercept makes the mean training probability
      pi_train at the optimum), so each record's odds are re-weighted by
      odds(pi_t)/odds(pi_train) = rho_point * odds(pi_source)/odds(pi_train),
      with pi_source the S_aux prevalence rho_point divides out (the fit's
      diagnostics key "pi_s", clipped here to [PI_CLIP, 1 - PI_CLIP] exactly
      as rho_box_interval clips it) and pi_train the S_train record
      prevalence, train.y.mean(). Re-weighting by rho_point alone left
      odds(pi_train)/odds(pi_source) in every record, so rho_point without
      both priors raises. The object records rho, the clipped pi_source,
      pi_train and the resulting odds_multiplier.
    - oracle_true_class (diagnostic, only when oracle_y is given): the realized
      true-positive fraction from oracle labels. This is what reveals a
      certificate earned by answering only easy negatives.

    Refs: SPEC "explain.py"; audit F25; audit 2026-10 BBSE-1.
    """
    target_x = np.asarray(target_x, dtype=np.float64)
    answered_mask = np.asarray(answered_mask, dtype=bool)
    n_ans = int(answered_mask.sum())
    pred = head.predict(target_x)

    pred_pos = int((np.asarray(pred, dtype=bool) & answered_mask).sum())
    out = {
        "predicted_class": {
            "tag": "estimated",
            "positive_fraction": (pred_pos / n_ans) if n_ans else float("nan"),
            "n_positive": pred_pos,
            "n_answered": n_ans,
        }
    }

    if rho_point is not None:
        if pi_source is None or pi_train is None:
            raise ValueError(
                "composition: rho_point needs pi_source (the S_aux prevalence "
                "BBSE divides out) and pi_train (the S_train prevalence the "
                "head's odds carry) (reason=missing-prior)")
        pi_train = float(pi_train)
        if not 0.0 < pi_train < 1.0:
            raise ValueError(
                f"composition: pi_train={pi_train!r} must lie in (0, 1) "
                f"(reason=bad-prior)")
        ps = float(np.clip(float(pi_source), PI_CLIP, 1.0 - PI_CLIP))
        mult = (float(rho_point) * (ps / (1.0 - ps))
                / (pi_train / (1.0 - pi_train)))
        p_h = np.asarray(head.predict_proba(target_x), dtype=np.float64)
        odds_h = p_h / np.clip(1.0 - p_h, 1e-12, None)
        odds_t = mult * odds_h
        p_t = odds_t / (1.0 + odds_t)
        out["bbse_true_class"] = {
            "tag": "estimated (label-shift assumption)",
            "positive_fraction": float(p_t[answered_mask].mean()) if n_ans else float("nan"),
            "expected_n_positive": float(p_t[answered_mask].sum()) if n_ans else float("nan"),
            "rho": float(rho_point),
            "odds_multiplier": float(mult),
            "pi_source": ps,
            "pi_train": pi_train,
            "n_answered": n_ans,
        }

    if oracle_y is not None:
        oracle_y = np.asarray(oracle_y, dtype=bool)
        opos = int((oracle_y & answered_mask).sum())
        out["oracle_true_class"] = {
            "tag": "diagnostic (oracle)",
            "positive_fraction": (opos / n_ans) if n_ans else float("nan"),
            "n_positive": opos,
            "n_answered": n_ans,
        }

    return out
