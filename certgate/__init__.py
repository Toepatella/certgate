"""CertGate: finite-sample certified selective prediction for multi-site data.

Public surface re-exports the load-bearing entry points so callers can do
``from certgate import run_certgate, from_raw`` without reaching into modules.
The statistical contract lives in ``SPEC.md``; every constant is pinned by
``tests/test_constants.py``.
"""
from certgate import constants
from certgate.constants import (SEED, SPLIT_FRACTIONS, ALPHA_LADDER, DELTA,
                                M_INFLUENCE, TAU_GRID, MODE_BASELINE, MODE_BBSE)
from certgate.validate import (Cohort, CohortError, coerce_labels,
                               densify_sites, make_cohort, from_raw,
                               assert_site_disjoint)
from certgate.data import SimConfig, draw_cohort, split_sites, subset_sites
from certgate.model import Head, fit_head
from certgate.certify import (influence_atoms, wsr_reject, margin_floor,
                              walk_order, fixed_sequence_walk,
                              certification_rng)
from certgate.shift import BBSEFit, fit_bbse, certify_bbse
from certgate.explain import (global_importance, local_attribution,
                              abstention_explanation, counterfactual_to_answer,
                              cohort_abstention_profile, composition)
from certgate.harness import (wilson_lcb, hard_violation,
                              exceedance_reference, SIZE_BINS)
from certgate.report import provenance, build_report, render_text
from certgate.pipeline import run_certgate

__all__ = [
    "constants", "SEED", "SPLIT_FRACTIONS", "ALPHA_LADDER", "DELTA",
    "M_INFLUENCE", "TAU_GRID", "MODE_BASELINE", "MODE_BBSE",
    "Cohort", "CohortError", "coerce_labels", "densify_sites", "make_cohort",
    "from_raw", "assert_site_disjoint",
    "SimConfig", "draw_cohort", "split_sites", "subset_sites",
    "Head", "fit_head",
    "influence_atoms", "wsr_reject", "margin_floor", "walk_order",
    "fixed_sequence_walk", "certification_rng",
    "BBSEFit", "fit_bbse", "certify_bbse",
    "global_importance", "local_attribution", "abstention_explanation",
    "counterfactual_to_answer", "cohort_abstention_profile", "composition",
    "wilson_lcb", "hard_violation", "exceedance_reference", "SIZE_BINS",
    "provenance", "build_report", "render_text",
    "run_certgate",
]
