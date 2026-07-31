"""SPEC "Tests": every loud rejection in the Cohort input contract.

NaN x; float y; ``{1,2}`` labels; NaN raw labels; gappy site ids +
``densify_sites`` round-trip; length mismatch; the disjointness assertion; and
the ``site_sizes == bincount`` invariant (audit F38).
"""
import numpy as np
import pytest

from certgate.validate import (Cohort, CohortError, coerce_labels,
                               densify_sites, make_cohort, assert_site_disjoint)


def _ok_kwargs(n=6, d=3, n_sites=3):
    x = np.arange(n * d, dtype=np.float64).reshape(n, d)
    y = (np.arange(n) % 2 == 0)                  # alternating, both classes, len n
    site_id = np.repeat(np.arange(n_sites), n // n_sites)
    return dict(x=x, y=y, site_id=site_id)


def test_nan_x_rejected():
    kw = _ok_kwargs()
    kw["x"] = kw["x"].copy()
    kw["x"][0, 0] = np.nan
    with pytest.raises(CohortError, match="non-finite"):
        make_cohort(**kw)


def test_float_y_rejected_pointing_at_coerce():
    kw = _ok_kwargs()
    kw["y"] = kw["y"].astype(np.float64)
    with pytest.raises(CohortError, match="coerce_labels"):
        make_cohort(**kw)


def test_int_labels_rejected_by_make_cohort_but_mapped_by_coerce():
    kw = _ok_kwargs()
    raw = np.array([1, 2, 1, 2, 1, 2])
    with pytest.raises(CohortError):
        make_cohort(x=kw["x"], y=raw, site_id=kw["site_id"])
    mapped = coerce_labels(raw, 2)
    assert mapped.dtype == bool
    assert mapped.tolist() == [False, True, False, True, False, True]


def test_nan_raw_labels_raise():
    with pytest.raises(CohortError):
        coerce_labels(np.array([1.0, np.nan, 2.0]), 2.0)


def test_gappy_site_ids_rejected():
    kw = _ok_kwargs()
    kw["site_id"] = np.array([0, 0, 2, 2, 2, 2])          # index 1 missing
    with pytest.raises(CohortError, match="dense"):
        make_cohort(**kw)


def test_densify_sites_round_trip():
    dense, labels = densify_sites([10, 10, 3, 3, 7])
    # canonical order = np.unique of str() forms: '10' < '3' < '7'
    assert labels == ("10", "3", "7")
    assert dense.tolist() == [0, 0, 1, 1, 2]
    # dense ids are exactly 0..K-1 with every index present
    assert set(dense.tolist()) == set(range(len(labels)))


def test_length_mismatch_rejected():
    with pytest.raises(CohortError, match="length"):
        make_cohort(x=np.zeros((5, 2)), y=np.array([True, False, True, False]),
                    site_id=np.zeros(5, dtype=int))


def test_disjointness_catches_overlap_and_passes_on_disjoint():
    a = make_cohort(**_ok_kwargs())
    a = Cohort(x=a.x, y=a.y, site_id=a.site_id, site_labels=("s0", "s1", "s2"))
    b = Cohort(x=a.x, y=a.y, site_id=a.site_id, site_labels=("s2", "s3", "s4"))
    with pytest.raises(CohortError, match="s2"):
        assert_site_disjoint(a=a, b=b)
    c = Cohort(x=a.x, y=a.y, site_id=a.site_id, site_labels=("t0", "t1", "t2"))
    assert_site_disjoint(a=a, c=c)               # disjoint -> no raise


def test_site_sizes_always_equals_bincount():
    coh = make_cohort(**_ok_kwargs(n=9, n_sites=3))
    assert np.array_equal(
        coh.site_sizes,
        np.bincount(coh.site_id, minlength=coh.n_sites))
    # holds too for a directly-built cohort with an empty trailing site
    coh2 = Cohort(x=coh.x, y=coh.y, site_id=coh.site_id,
                  site_labels=("a", "b", "c", "d"))
    assert coh2.site_sizes.tolist() == [3, 3, 3, 0]
    assert np.array_equal(
        coh2.site_sizes, np.bincount(coh2.site_id, minlength=coh2.n_sites))


def test_both_classes_required():
    kw = _ok_kwargs()
    kw["y"] = np.ones(6, dtype=bool)             # one class only
    with pytest.raises(CohortError, match="both classes"):
        make_cohort(**kw)


def test_target_pool_exempt_from_both_classes():
    """An all-negative TARGET pool is a legitimate deployment scenario at ~9.5%
    prevalence (small single-site batches): require_both_classes=False must
    admit it, while the strict default (fitting cohorts) still rejects."""
    kw = _ok_kwargs()
    kw["y"] = np.zeros(6, dtype=bool)            # all-negative pool
    with pytest.raises(CohortError, match="both classes"):
        make_cohort(**kw)                        # strict default unchanged
    coh = make_cohort(**kw, require_both_classes=False)
    assert coh.n == 6 and not coh.y.any()

    # and the generator passes the flag through for single-site target draws
    from certgate.data import SimConfig, draw_cohort
    rng = np.random.default_rng(0)
    for _ in range(50):                          # small pools: all-negative likely
        t = draw_cohort(SimConfig(), 1, rng, site_label_prefix="tp",
                        require_both_classes=False)
        assert t.n >= 1                          # never raises, whatever the draw


# ---- audit V4/V10: site-identity canonicalization and loud dirt rejection --

def test_dirty_site_ids_whitespace_merges_to_one_site():
    """'H1' vs 'H1 ' is one hospital with a dirty column, not two independent
    clusters -- the cluster count feeds MIN_CAL_CLUSTERS and the betting
    test's effective n (audit V4). Surrounding whitespace is unambiguous dirt:
    canonicalization strips it, so the two spellings MERGE into one site."""
    dense, labels = densify_sites(np.array(["H1", "H1 ", "H2"], dtype=object))
    assert labels == ("H1", "H2")
    assert dense.tolist() == [0, 0, 1]


def test_dirty_site_ids_case_collision_raises():
    with pytest.raises(CohortError, match="cosmetic"):
        densify_sites(np.array(["h1", "H1", "H2"], dtype=object))


def test_dirty_site_ids_string_numeric_spelling_raises():
    """String '1' vs '1.0' (two CSV exports of one float column) must not
    become two clusters."""
    with pytest.raises(CohortError, match="cosmetic"):
        densify_sites(np.array(["1", "1.0", "2"], dtype=object))


def test_numeric_int_float_ids_merge_to_one_site():
    """Actual numerics 1 and 1.0 are unambiguously the same id (the pandas
    float-dtype column case): merged, not split, not raised."""
    dense, labels = densify_sites(np.array([1, 1.0, 2, 2.0], dtype=object))
    assert labels == ("1", "2")
    assert dense.tolist() == [0, 0, 1, 1]


def test_missing_site_ids_rejected():
    """None / NaN / empty site ids must never become a bona fide pseudo-site
    (audit V10) -- mirroring coerce_labels' treatment of the label column."""
    with pytest.raises(CohortError, match="None"):
        densify_sites(np.array(["A", None], dtype=object))
    with pytest.raises(CohortError, match="NaN"):
        densify_sites(np.array(["A", float("nan")], dtype=object))
    with pytest.raises(CohortError, match="empty"):
        densify_sites(np.array(["A", "   "], dtype=object))


def test_clean_ids_with_stripped_canonical_labels():
    dense, labels = densify_sites(np.array([" s-01 ", "s-02"], dtype=object))
    assert labels == ("s-01", "s-02")           # canonical form is stripped
    assert dense.tolist() == [0, 1]


# ---- audit V5: a repeated site_label declares one physical site ------------

def test_duplicate_site_labels_rejected_by_make_cohort():
    kw = _ok_kwargs()
    with pytest.raises(CohortError, match="repeated site_labels"):
        make_cohort(**kw, site_labels=("H-A", "H-A", "H-B"))


def test_duplicate_site_labels_rejected_by_cohort_directly():
    kw = _ok_kwargs()
    coh = make_cohort(**kw)
    with pytest.raises(CohortError, match="unique"):
        Cohort(x=coh.x, y=coh.y, site_id=coh.site_id,
               site_labels=("H-A", "H-A", "H-B"))


# ---- audit V17: shape discipline at the boundary ---------------------------

def test_column_shaped_y_rejected():
    """(n,1) bool y broadcasts predict(x) != y into an (n,n) matrix deep in
    the pipeline -- must be a typed CohortError at the boundary."""
    kw = _ok_kwargs()
    kw["y"] = kw["y"].reshape(-1, 1)
    with pytest.raises(CohortError, match="1-D"):
        make_cohort(**kw)


def test_column_shaped_site_id_rejected():
    kw = _ok_kwargs()
    kw["site_id"] = kw["site_id"].reshape(-1, 1)
    with pytest.raises(CohortError, match="1-D"):
        make_cohort(**kw)


# ---- audit V15: the contract holds on DIRECT Cohort construction ----------

def test_cohort_post_init_enforces_contract():
    kw = _ok_kwargs()
    coh = make_cohort(**kw)
    # float y
    with pytest.raises(CohortError, match="bool"):
        Cohort(x=coh.x, y=coh.y.astype(np.float64), site_id=coh.site_id,
               site_labels=coh.site_labels)
    # non-finite x
    bad_x = coh.x.copy()
    bad_x[0, 0] = np.nan
    with pytest.raises(CohortError, match="non-finite"):
        Cohort(x=bad_x, y=coh.y, site_id=coh.site_id,
               site_labels=coh.site_labels)
    # site_id outside the label range
    bad_sid = coh.site_id.copy()
    bad_sid[0] = 99
    with pytest.raises(CohortError, match="site_id"):
        Cohort(x=coh.x, y=coh.y, site_id=bad_sid,
               site_labels=coh.site_labels)
    # a trailing EMPTY site remains a legitimate direct construction (the
    # record-carrying cluster gate's fixture pattern -- audit V12)
    ok = Cohort(x=coh.x, y=coh.y, site_id=coh.site_id,
                site_labels=coh.site_labels + ("empty-extra",))
    assert ok.site_sizes.tolist()[-1] == 0


# ---- verification F1/F3/N4: Unicode + precision hardening ------------------

def test_invisible_and_nfd_spellings_merge_to_one_site():
    """verification F1: NFD-vs-NFC spellings and invisible format characters
    (ZWSP/BOM/soft hyphen) are one hospital -- canonicalization must fold
    them, not silently split the site."""
    import unicodedata
    nfc = unicodedata.normalize("NFC", "H\u00f4pital-01")
    nfd = unicodedata.normalize("NFD", "H\u00f4pital-01")
    assert nfc != nfd                                # genuinely distinct bytes
    dense, labels = densify_sites(np.array([nfc, nfd, "B"], dtype=object))
    assert len(labels) == 2
    assert dense[0] == dense[1] != dense[2]          # NFC/NFD merged; B apart
    for ch in ("\u200b", "\ufeff", "\u00ad", "\u200d", "\u2060"):
        dense, labels = densify_sites(
            np.array(["A", "A" + ch, "B"], dtype=object))
        assert len(labels) == 2, f"invisible char {ch!r} split the site"
        assert dense.tolist() == [0, 0, 1]


def test_huge_integer_string_ids_stay_distinct():
    """verification N4: 18+-digit surrogate keys (Epic CSN scale) differing in
    the last digit are DISTINCT sites; float64 round-tripping falsely collided
    them. Exact integer arithmetic must keep them apart."""
    a, b = "725100000000000123", "725100000000000124"
    dense, labels = densify_sites(np.array([a, b], dtype=object))
    assert len(labels) == 2
    assert dense.tolist() == [0, 1]


def test_float_ids_beyond_2_53_rejected():
    """verification F3: a float64 site id at or beyond 2**53 has lost integer
    resolution -- emitting a lossy label could silently merge distinct
    hospitals, so it must be a loud typed rejection."""
    with pytest.raises(CohortError, match="2\*\*53"):
        densify_sites(np.array([float(2**53), float(2**53 + 2)], dtype=object))


# ---- verification F2: cross-cohort identity uses the same normal form ------

def test_disjointness_catches_case_variant_overlap():
    """verification F2: 'h1' vs 'H1' raises INSIDE a cohort (collision check);
    it must equally raise BETWEEN cohorts -- raw string comparison let a
    case-variant respelling of S_cal pass as S_aux, voiding the walk order's
    S_cal-independence."""
    kw = _ok_kwargs()
    base = make_cohort(**kw)
    a = Cohort(x=base.x, y=base.y, site_id=base.site_id,
               site_labels=("s-0008", "s-0010", "s-0012"))
    b = Cohort(x=base.x, y=base.y, site_id=base.site_id,
               site_labels=("S-0008", "S-0010", "S-0012"))
    with pytest.raises(CohortError, match="share sites"):
        assert_site_disjoint(a=a, b=b)
    c = Cohort(x=base.x, y=base.y, site_id=base.site_id,
               site_labels=("t-1", "t-2", "t-3"))
    assert_site_disjoint(a=a, c=c)               # genuinely disjoint: no raise
