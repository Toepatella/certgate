"""SPEC "Tests" for report.py's OR-combination, _combine_alpha.

The OR-rule has two steps. Deploy the most conservative certified threshold
across modes. Then list only the modes whose own FWER-controlled certified
prefix contains the deployed index.

Until these tests it was exercised only through the in-distribution end-to-end
path, where baseline and BBSE agree. They pin the covered-mode selection
against divergent mode results, so a regression that listed a mode
unconditionally -- silently attaching an assumption tag it never earned --
fails here.

Refs: REVIEW-FABLE A-1 (skeptic-confirmed).
"""
import pytest

from certgate.report import _combine_alpha
from certgate.constants import TAU_GRID


def _mode(certified, tau_idx, reason=None):
    """A mode result in the exact shape pipeline.py step 6 produces."""
    return dict(certified=list(certified), tau_idx=tau_idx,
                tau=(None if tau_idx is None else float(TAU_GRID[tau_idx])),
                reason=reason)


def test_subset_prefixes_cover_both_modes():
    """Both modes are listed when one prefix contains the other's index.

    baseline certifies deeper and would deploy tau idx 2; bbse deploys the
    higher idx 5, so bbse wins deployment as the most conservative. baseline
    is covered too, because idx 5 sits inside its certified prefix.
    """
    out = _combine_alpha({
        "baseline": _mode([8, 5, 2], tau_idx=2),
        "bbse": _mode([8, 5], tau_idx=5),
    })
    assert out["status"] == "certified"
    assert out["deploy_mode"] == "bbse"
    assert out["tau_idx"] == 5
    assert out["tau"] == pytest.approx(float(TAU_GRID[5]))
    assert out["modes"] == ["baseline", "bbse"]
    assert out["mode_outcomes"] == {"baseline": "covering", "bbse": "covering"}


def test_declined_mode_never_listed():
    """A declined mode never appears in modes, whatever its reason says.

    A mode is declined when its tau_idx is None.
    """
    out = _combine_alpha({
        "baseline": _mode([4, 3], tau_idx=3),
        "bbse": _mode([], tau_idx=None, reason="bbse-ill-conditioned"),
    })
    assert out["status"] == "certified"
    assert out["deploy_mode"] == "baseline"
    assert out["tau_idx"] == 3
    assert out["modes"] == ["baseline"]
    # the certified row records why the non-deploying mode did not contribute:
    # the decline reason passes through instead of vanishing
    # (fixture audit 2026-07-25)
    assert out["mode_outcomes"] == {"baseline": "covering",
                                    "bbse": "bbse-ill-conditioned"}


def test_disjoint_prefixes_deploy_mode_alone():
    """A certifying mode that misses the deployed index is still excluded.

    baseline certifies idx 2 but not bbse's deployed idx 8, so it stays out of
    the OR-guarantee. Listing every certifying mode instead would mis-attach
    the exchangeability tag to a threshold baseline never certified.
    """
    out = _combine_alpha({
        "baseline": _mode([2], tau_idx=2),
        "bbse": _mode([8], tau_idx=8),
    })
    assert out["status"] == "certified"
    assert out["deploy_mode"] == "bbse"
    assert out["tau_idx"] == 8
    assert out["modes"] == ["bbse"]
    # certified something, but not the deployed threshold: distinguishable
    # from both "covering" and a statistical decline (fixture audit 2026-07-25)
    assert out["mode_outcomes"] == {"baseline": "certified-not-covering",
                                    "bbse": "covering"}


def test_no_certifying_mode_declines_with_reasons():
    out = _combine_alpha({
        "baseline": _mode([], tau_idx=None, reason="failsafe"),
        "bbse": _mode([], tau_idx=None, reason="bbse-misspecified"),
    })
    assert out["status"] == "declined"
    assert out["reasons"] == {"baseline": "failsafe",
                              "bbse": "bbse-misspecified"}


# ---- audit V6 #13/#14: the guarantee text is frozen as an exact string -----
# A token-presence check let a mutation invert the concept-shift clause into
# its exact opposite while the suite stayed green. Exact equality means any
# silent weakening -- or strengthening -- of a mandated clause fails here.
# Changing this text is a SPEC change: edit SPEC.md first, then this literal.
#
# There are three frozen variants because the estimand and the probability
# attribution are mode-dependent. Naming the calibration-population unweighted
# risk on a BBSE row emitted a demonstrably false certificate.
# Ref: verification G-1/G-3.

_FROZEN_BASELINE_010 = (
    "Under the tagged assumption (exchangeability), with probability >= 0.95 "
    "over the draw of calibration sites, the M=100 influence-weighted "
    "answered-set risk, averaged over the population of sites from which the "
    "calibration sites were drawn, is <= 0.1. This bounds a site-population "
    "average, NOT any individual site's answered error rate: under between-site "
    "heterogeneity individual sites can exceed alpha while the average stays "
    "within budget, at a rate this certificate does not measure or bound. It is "
    "NOT a bound on this batch's realized error count, which exceeds alpha at "
    "binomial-dispersion rates even under a valid certificate. In the "
    "exchangeable mode the certified thresholds are a function of the "
    "calibration draw alone -- one 1-0.05 event shared by every target pool the "
    "certificate is applied to. The operative rung is the strictest certified "
    "alpha, a data-driven selection over the {0.05, 0.1} ladder; the selected "
    "claim holds jointly at probability >= 0.90. Concept shift and combined "
    "shift are OUT OF SCOPE and undetectable from unlabeled data -- the "
    "certificate is void there.")

_FROZEN_BOTH_010 = (
    "With confidence >= 0.95, the M=100 influence-weighted answered-set risk is "
    "<= 0.1 under the tagged assumption (exchangeability or label shift): under "
    "exchangeability this is the risk averaged over the population of sites "
    "from which the calibration sites were drawn (probability over the "
    "calibration draw); under label shift it is that population risk reweighted "
    "to the target class prevalence identified by the BBSE correction "
    "(probability over the joint draw of the calibration sites, the auxiliary "
    "split and the target pool). This bounds a site-population average, NOT any "
    "individual site's answered error rate: under between-site heterogeneity "
    "individual sites can exceed alpha while the average stays within budget, "
    "at a rate this certificate does not measure or bound. It is NOT a bound on "
    "this batch's realized error count, which exceeds alpha at "
    "binomial-dispersion rates even under a valid certificate. The operative "
    "rung is the strictest certified alpha, a data-driven selection over the "
    "{0.05, 0.1} ladder; the selected claim holds jointly at probability >= "
    "0.90. Concept shift and combined shift are OUT OF SCOPE and undetectable "
    "from unlabeled data -- the certificate is void there. The [rho_lo, rho_hi] "
    "box covers FOUR estimated parameters (c0, c1, pi_source, q_target) at "
    "Bonferroni delta_conf=0.025, spent over the auxiliary (S_aux) site split "
    "and the target pool, not the calibration draw named above. The (c0, c1, "
    "pi_source) intervals are percentile cluster bootstraps -- asymptotic, with "
    "realized joint coverage at small cluster counts measurably below nominal "
    "(see METHODS); the q_target interval is finite-sample Clopper-Pearson for "
    "single-site pools and a cluster bootstrap for multi-site pools.")

_FROZEN_BBSE_010 = (
    "Under the tagged assumption (label shift), with probability >= 0.95 over "
    "the joint draw of the calibration sites, the auxiliary split and the "
    "target pool, the M=100 influence-weighted answered-set risk, averaged over "
    "the site population and reweighted to the target class prevalence "
    "identified by the BBSE correction, is <= 0.1. This bounds a "
    "site-population average, NOT any individual site's answered error rate: "
    "under between-site heterogeneity individual sites can exceed alpha while "
    "the average stays within budget, at a rate this certificate does not "
    "measure or bound. It is NOT a bound on this batch's realized error count, "
    "which exceeds alpha at binomial-dispersion rates even under a valid "
    "certificate. The operative rung is the strictest certified alpha, a "
    "data-driven selection over the {0.05, 0.1} ladder; the selected claim "
    "holds jointly at probability >= 0.90. Concept shift and combined shift are "
    "OUT OF SCOPE and undetectable from unlabeled data -- the certificate is "
    "void there. The [rho_lo, rho_hi] box covers FOUR estimated parameters (c0, "
    "c1, pi_source, q_target) at Bonferroni delta_conf=0.025, spent over the "
    "auxiliary (S_aux) site split and the target pool, not the calibration draw "
    "named above. The (c0, c1, pi_source) intervals are percentile cluster "
    "bootstraps -- asymptotic, with realized joint coverage at small cluster "
    "counts measurably below nominal (see METHODS); the q_target interval is "
    "finite-sample Clopper-Pearson for single-site pools and a cluster "
    "bootstrap for multi-site pools.")



def test_guarantee_statement_frozen_baseline():
    from certgate.report import _statement
    assert _statement(0.10, ("baseline",)) == _FROZEN_BASELINE_010


def test_guarantee_statement_frozen_both_modes():
    from certgate.report import _statement
    assert _statement(0.10, ("baseline", "bbse")) == _FROZEN_BOTH_010


def test_guarantee_statement_frozen_bbse_only():
    from certgate.report import _statement
    assert _statement(0.10, ("bbse",)) == _FROZEN_BBSE_010


def test_bbse_rows_never_claim_a_shared_event():
    """BBSE rows must not carry the shared-event clause (audit V3).

    The fit depends on the target pool through the q_t interval, so distinct
    targets get distinct boxes and no shared event exists.
    """
    from certgate.report import _statement
    for modes in (("baseline", "bbse"), ("bbse",)):
        s = _statement(0.10, modes)
        assert "shared by every target pool" not in s
        # and the estimand clause must name the reweighting (verification G-1)
        assert "reweighted to the target class prevalence" in s
    # baseline-only keeps the (narrowed, G-7) thresholds-shared clause
    sb = _statement(0.10, ("baseline",))
    assert "certified thresholds are a function of the calibration draw" in sb
    assert "reweighted" not in sb
