"""SPEC "Tests": first end-to-end exercise of the RAW loader (``from_raw``).

Draws synthetic multi-site data, then DE-STRUCTURES it back into the raw shapes a
real loader hands us -- string / int outcome labels and raw string site ids --
rebuilds every split through ``from_raw``, and drives ``run_certgate`` to a
certified rung. Covers the ``{1,2}`` int-label variant, the GAP-1 feature-width
gate, and the all-negative TARGET pool that can only flow via
``from_raw(require_both_classes=False)``. Also pins ``coerce_labels``' opt-in.

Until now ``from_raw`` had no test or experiment exercising it at all; this file
is the real-data readiness harness for the loader contract.
"""
import numpy as np
import pytest

from certgate.constants import SEED
from certgate.data import SimConfig, draw_cohort, split_sites
from certgate.validate import (CohortError, coerce_labels, from_raw,
                               assert_site_disjoint)
from certgate.pipeline import run_certgate


def _rec_site_labels(cohort) -> np.ndarray:
    """Per-record ORIGINAL site label -- robust to dense-id renumbering."""
    return np.array([cohort.site_labels[s] for s in cohort.site_id], dtype=object)


def _destructure_str(cohort):
    """Cohort -> raw (x, string y, raw string site ids), as a loader would deliver."""
    y_raw = np.where(cohort.y, "case", "control")
    site_ids_raw = [cohort.site_labels[s] for s in cohort.site_id]
    return cohort.x, y_raw, site_ids_raw


def _assert_equivalent(rebuilt, original) -> None:
    """Rebuilt cohort matches the original in x, y, and per-record site label."""
    assert np.array_equal(rebuilt.x, original.x)
    assert np.array_equal(rebuilt.y, original.y)
    assert np.array_equal(_rec_site_labels(rebuilt), _rec_site_labels(original))


@pytest.fixture(scope="module")
def raw_splits():
    """208 sites (keeps the 50-carrying calibration floor satisfied), split by
    site, then rebuilt from raw string forms. Same draw sequence as the
    established test_pipeline fixture so certification behaviour matches."""
    cfg = SimConfig()
    rng = np.random.default_rng(SEED)
    coh = draw_cohort(cfg, 208, rng)
    train, aux, cal = split_sites(coh, rng)
    target = draw_cohort(cfg, 1, rng, site_label_prefix="tgt")
    orig = dict(train=train, aux=aux, cal=cal, target=target)
    rebuilt = {}
    for name, c in orig.items():
        x, y_raw, sids = _destructure_str(c)
        rebuilt[name] = from_raw(x, y_raw, "case", sids)
    return dict(orig=orig, rebuilt=rebuilt)


def test_from_raw_roundtrip_equivalent_and_disjoint(raw_splits):
    orig, rb = raw_splits["orig"], raw_splits["rebuilt"]
    for name in ("train", "aux", "cal", "target"):
        _assert_equivalent(rb[name], orig[name])
    # site-disjointness holds on the rebuilt splits (must not raise)
    assert_site_disjoint(train=rb["train"], aux=rb["aux"], cal=rb["cal"])


def test_from_raw_end_to_end_certifies(raw_splits):
    rb = raw_splits["rebuilt"]
    rep = run_certgate(rb["train"], rb["aux"], rb["cal"], rb["target"].x,
                       target_label="realdata")
    row = next(r for r in rep["certified"] if r["alpha"] == 0.10)
    assert row["status"] == "certified"
    assert sum(rep["decline_partition"].values()) == rb["target"].n


def test_from_raw_int_labels_variant(raw_splits):
    """Raw labels as ints {1, 2} with positive_label=2 map identically."""
    tgt = raw_splits["orig"]["target"]
    y_int = np.where(tgt.y, 2, 1)
    sids = [tgt.site_labels[s] for s in tgt.site_id]
    rebuilt = from_raw(tgt.x, y_int, 2, sids)
    assert np.array_equal(rebuilt.y, tgt.y)
    assert np.array_equal(_rec_site_labels(rebuilt), _rec_site_labels(tgt))


def test_wrong_width_target_hits_gap1_gate(raw_splits):
    """A target matrix one column too wide is rejected loudly at the boundary
    (GAP 1) rather than surfacing as a raw numpy broadcast error in head.score."""
    rb = raw_splits["rebuilt"]
    bad = np.zeros((20, rb["train"].d + 1), dtype=np.float64)
    with pytest.raises(ValueError, match="feature-width-mismatch"):
        run_certgate(rb["train"], rb["aux"], rb["cal"], bad)


def test_all_negative_target_pool_flows(raw_splits):
    """A genuinely all-negative deployment batch: 'case' absent, only 'control'
    observed. Strict from_raw refuses (typo protection); the sanctioned opt-in
    admits it, and certification -- which never needs target labels -- proceeds."""
    rb, tgt = raw_splits["rebuilt"], raw_splits["orig"]["target"]
    y_all_control = np.array(["control"] * tgt.n)
    sids = [tgt.site_labels[s] for s in tgt.site_id]
    with pytest.raises(CohortError):
        from_raw(tgt.x, y_all_control, "case", sids)          # strict default refuses
    allneg = from_raw(tgt.x, y_all_control, "case", sids,
                      require_both_classes=False)              # opt-in admits it
    assert not allneg.y.any()
    rep = run_certgate(rb["train"], rb["aux"], rb["cal"], allneg.x,
                       target_label="allneg", oracle_target_y=allneg.y)
    row = next(r for r in rep["certified"] if r["alpha"] == 0.10)
    assert row["status"] == "certified"
    assert sum(rep["decline_partition"].values()) == allneg.n


# ---- coerce_labels opt-in unit contract (the resolved known API wall) ----

def test_coerce_labels_strict_default_raises_on_absent_positive():
    with pytest.raises(CohortError, match="not present"):
        coerce_labels(np.array([0, 0, 0]), 1)


def test_coerce_labels_optin_returns_all_false():
    out = coerce_labels(np.array([0, 0, 0]), 1, allow_absent_positive=True)
    assert out.dtype == bool
    assert out.shape == (3,)
    assert not out.any()


def test_coerce_labels_optin_maps_normally_when_positive_present():
    out = coerce_labels(np.array([2, 1, 1]), 2, allow_absent_positive=True)
    assert out.tolist() == [True, False, False]


def test_coerce_labels_optin_still_raises_on_multiple_distinct_when_absent():
    # positive absent AND >1 observed value -> ambiguous, still raises under opt-in
    with pytest.raises(CohortError, match="single observed value"):
        coerce_labels(np.array([0, 1, 1]), 9, allow_absent_positive=True)


def test_coerce_labels_optin_still_raises_on_three_distinct_when_present():
    # positive present but two other distinct values -> >2 distinct, still raises
    with pytest.raises(CohortError):
        coerce_labels(np.array([0, 1, 2]), 2, allow_absent_positive=True)


def test_coerce_labels_optin_still_raises_on_nan():
    with pytest.raises(CohortError):
        coerce_labels(np.array([np.nan, 0.0, 0.0]), 1.0,
                      allow_absent_positive=True)
