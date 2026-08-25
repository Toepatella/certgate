"""Cohort container plus the loud, typed input contract.

Encodes the data discipline of METHODS 2: the site is the honest unit of
independence. Every rejection is a typed CohortError carrying a named reason,
because the code never guesses at a caller's intent.

Refs: SPEC "validate.py"; METHODS 2; audits F05, F35, F37.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

import numpy as np

_INT_LEXEME = re.compile(r"^[+-]?\d+$")


class CohortError(ValueError):
    """Every Cohort-contract rejection is loud, typed, and message-named (SPEC validate.py)."""


def _nrows(a) -> int:
    """First-axis length of an array-like, or 0 for a scalar."""
    arr = np.asarray(a)
    return int(arr.shape[0]) if arr.ndim >= 1 else 0


@dataclass(frozen=True)
class Cohort:
    """Immutable multi-site cohort.

    Holds only x, y, site_id, site_labels -- no oracle latent or site fields.
    site_sizes is derived from site_id on every access, never an independent
    input.

    __post_init__ enforces the contract on direct construction too, not only
    through make_cohort. The container is a public export, and a contract that
    is optional through the public API is not a contract.

    One difference from make_cohort's input rule: __post_init__ does not
    require every dense index to carry records. A Cohort with trailing empty
    sites is a legitimate state, and is how the record-carrying cluster gate
    gets exercised.

    Refs: SPEC "validate.py"; audits F38, V15, V12.
    """

    x: np.ndarray                  # (n, d) float64, all finite
    y: np.ndarray                  # (n,) bool STRICTLY
    site_id: np.ndarray            # (n,) int64, dense 0..n_sites-1, every index present
    site_labels: tuple[str, ...]   # original identifiers, index-aligned to dense ids, unique

    def __post_init__(self):
        x, y, site_id = self.x, self.y, self.site_id
        if not (isinstance(x, np.ndarray) and x.ndim == 2):
            raise CohortError("Cohort: x must be a 2-D ndarray (n, d)")
        if x.dtype != np.float64:
            raise CohortError("Cohort: x must be float64")
        if not np.isfinite(x).all():
            raise CohortError("Cohort: x contains non-finite values (NaN/inf)")
        if not (isinstance(y, np.ndarray) and y.ndim == 1
                and y.dtype.kind == "b"):
            raise CohortError("Cohort: y must be a 1-D bool ndarray")
        if not (isinstance(site_id, np.ndarray) and site_id.ndim == 1
                and site_id.dtype.kind in ("i", "u")):
            raise CohortError("Cohort: site_id must be a 1-D integer ndarray")
        if not (x.shape[0] == y.shape[0] == site_id.shape[0]):
            raise CohortError("Cohort: length mismatch between x, y, site_id")
        labels = self.site_labels
        if not (isinstance(labels, tuple)
                and all(isinstance(s, str) for s in labels)):
            raise CohortError("Cohort: site_labels must be a tuple of str")
        if len(set(labels)) != len(labels):
            raise CohortError(
                "Cohort: site_labels must be unique -- a repeated label "
                "declares one physical site spanning two independent clusters "
                "(audit V5)")
        if site_id.size:
            if int(site_id.min()) < 0 or int(site_id.max()) >= len(labels):
                raise CohortError(
                    "Cohort: site_id must lie in [0, len(site_labels))")

    @property
    def n(self) -> int:
        return int(self.x.shape[0])

    @property
    def d(self) -> int:
        return int(self.x.shape[1])

    @property
    def n_sites(self) -> int:
        return len(self.site_labels)

    @property
    def site_sizes(self) -> np.ndarray:
        """Per-site record counts, always np.bincount(site_id, minlength=n_sites) (audit F38)."""
        return np.bincount(self.site_id, minlength=self.n_sites)


def coerce_labels(raw, positive_label, allow_absent_positive: bool = False) -> np.ndarray:
    """Explicit two-value map from raw labels to bool.

    Maps positive_label to True and the single other observed value to False.
    Raises CohortError on NaN or missing values, and on any value outside those
    two. It never guesses.

    allow_absent_positive is the sanctioned opt-in, wired from
    from_raw(require_both_classes=False) and meant for target pools only. When
    the positive label is absent and exactly one other value is observed, it
    returns all-False instead of raising -- a legitimately all-negative
    deployment pool at ~9.5% prevalence.

    The strict default stays strict, which is the typo protection. Even under
    the opt-in, a NaN or None value still raises, and so does more than one
    distinct observed value.

    Refs: SPEC "validate.py"; audits F05, F35, F37.
    """
    arr = np.asarray(raw)
    if arr.ndim != 1:
        raise CohortError("coerce_labels: labels must be 1-D")
    flat = arr.ravel()
    kind = arr.dtype.kind
    if kind in ("f", "c"):
        if not np.isfinite(arr).all():
            raise CohortError("coerce_labels: non-finite (NaN/inf) label value present; labels must be complete")
    elif kind == "O":
        for v in flat.tolist():
            if v is None:
                raise CohortError("coerce_labels: missing (None) label value present")
            if isinstance(v, float) and np.isnan(v):
                raise CohortError("coerce_labels: NaN label value present")
    pos_mask = np.asarray(arr == positive_label, dtype=bool)
    if not pos_mask.any():
        # Positive label absent. The strict default rejects: a typo in
        # positive_label must never silently pass as all-negative. The opt-in
        # admits a genuinely single-class pool as all-False, but only if
        # exactly one value is observed -- more than one is still ambiguous.
        # Ref: audits F05, F35, F37.
        if not allow_absent_positive:
            raise CohortError(f"coerce_labels: positive_label {positive_label!r} not present among labels")
        observed = set(flat.tolist())
        if len(observed) > 1:
            raise CohortError(
                f"coerce_labels: positive_label {positive_label!r} absent and "
                f"{len(observed)} distinct label values present; the all-negative "
                f"opt-in admits only a single observed value, got "
                f"{sorted(map(repr, observed))!r}")
        return pos_mask                                   # all-False, single observed value
    other_set = set(flat[~pos_mask].tolist())
    if len(other_set) > 1:
        raise CohortError(
            f"coerce_labels: more than two distinct label values -- "
            f"positive {positive_label!r} plus {sorted(map(repr, other_set))!r}")
    return pos_mask


def _canonical_site_id(s) -> str:
    """Canonical string form of one raw site id.

    Missing or ambiguous identity is rejected loudly. None, float NaN, empty or
    whitespace-only strings, and floats at or beyond 2**53 must never become a
    pseudo-cluster, because the site is the unit of statistical independence.
    Past 2**53 integer resolution is lost, and a lossy label must never be
    emitted silently.

    Strings are cleaned in three steps:

      - NFKC normalization;
      - deletion of format-category (Cf) characters -- ZWSP, BOM, soft hyphen
        and friends, the invisible-suffix channel that silently split one
        hospital into two clusters;
      - stripping of surrounding whitespace.

    Integral numerics map to the same integer string, so 1 and 1.0 agree. That
    is the pandas float-dtype column case.

    Refs: SPEC "validate.py"; audits V4, V10; verifications F1, F3.
    """
    if s is None:
        raise CohortError(
            "densify_sites: missing (None) site id -- site identity is the "
            "unit of statistical independence and must be complete")
    if isinstance(s, (float, np.floating)):
        if np.isnan(s):
            raise CohortError(
                "densify_sites: NaN site id -- site identity must be complete")
        f = float(s)
        if not np.isfinite(f):
            raise CohortError(
                "densify_sites: non-finite site id -- site identity must be "
                "complete")
        if abs(f) >= 2.0 ** 53:
            raise CohortError(
                f"densify_sites: float site id {f!r} at or beyond 2**53 -- "
                f"integer resolution is lost at this magnitude and distinct "
                f"sites could silently merge; supply the id as int or string "
                f"(verification F3)")
        return str(int(f)) if f.is_integer() else repr(f)
    if isinstance(s, (int, np.integer)) and not isinstance(s, bool):
        return str(int(s))
    text = unicodedata.normalize("NFKC", str(s))
    text = "".join(c for c in text if unicodedata.category(c) != "Cf")
    text = text.strip()
    if not text:
        raise CohortError(
            "densify_sites: empty/whitespace-only site id -- site identity "
            "must be complete")
    return text


def _normalized_site_id(canonical: str) -> str:
    """Aggressive normal form, for collision checks only.

    Two uses: near-duplicate collision checks, and cross-cohort identity
    comparison. The form is casefold plus numeric-lexeme collapse, so the
    strings '1' and '1.0' agree. Integer lexemes collapse with exact integer
    arithmetic, since float64 round-tripping falsely collided distinct
    18+-digit surrogate keys.

    This is never used as a label. A collision here is a loud rejection, not a
    merge -- the code does not guess which merge the caller intended.

    Refs: audit V4; verifications F2, N4.
    """
    t = canonical.casefold()
    if _INT_LEXEME.match(t):
        return str(int(t))                       # arbitrary precision, exact
    try:
        f = float(t)
    except ValueError:
        return t
    if np.isfinite(f) and abs(f) < 2.0 ** 53:
        return str(int(f)) if f.is_integer() else repr(f)
    return t


def normalized_label(s) -> str:
    """Public composition of canonicalization and normalization.

    This is the single normal form under which site identity is compared across
    cohorts, by assert_site_disjoint and the run_certgate target gates. Dirt
    that is loud inside one cohort therefore cannot slip silently between them.

    Refs: verification F2.
    """
    return _normalized_site_id(_canonical_site_id(s))


def densify_sites(raw_site_ids) -> tuple[np.ndarray, tuple[str, ...]]:
    """Map arbitrary site identifiers to dense ids 0..K-1.

    Canonical order is np.unique over the canonicalized form of each id, per
    _canonical_site_id. Returns (dense int64 ids, labels), with labels
    index-aligned to the dense ids.

    Collision check: if two distinct canonical labels collide under the
    aggressive normal form -- 'H1' against 'h1 ', or the strings '1' and '1.0'
    -- the site column is dirty and a CohortError names the colliding ids.

    That rejection is loud on purpose. The cluster count feeds MIN_CAL_CLUSTERS
    and the betting test's effective n, so cosmetic noise that splits one
    hospital into two "independent" clusters buys certification strength the
    honest clustering refuses.

    Refs: SPEC "validate.py"; audits F39, V4, V10.
    """
    labels_str = np.array([_canonical_site_id(s) for s in raw_site_ids],
                          dtype=object)
    uniq = np.unique(labels_str)                # sorted unique canonical forms
    by_norm: dict[str, list[str]] = {}
    for lab in uniq.tolist():
        by_norm.setdefault(_normalized_site_id(lab), []).append(lab)
    collisions = {k: v for k, v in by_norm.items() if len(v) > 1}
    if collisions:
        detail = "; ".join(f"{sorted(v)!r}" for v in collisions.values())
        raise CohortError(
            f"densify_sites: distinct site ids that differ only cosmetically "
            f"(case/whitespace/numeric spelling): {detail} -- the site column "
            f"is dirty; clean it rather than letting one hospital split into "
            f"multiple 'independent' clusters (audit V4)")
    label_to_idx = {lab: i for i, lab in enumerate(uniq.tolist())}
    dense = np.array([label_to_idx[s] for s in labels_str.tolist()], dtype=np.int64)
    return dense, tuple(str(u) for u in uniq.tolist())


def make_cohort(x, y, site_id, site_labels=None, expect_features=None,
                require_both_classes=True) -> Cohort:
    """Build a Cohort behind a loud input contract (SPEC validate.py).

    Checks fire in this order:

      - x, y and site_id have matching lengths;
      - x is 2-D, float64-convertible, and all finite;
      - y is strictly bool dtype;
      - site_id is integer, >= 0, and dense (every index 0..max present);
      - x has expect_features columns;
      - both classes are present.
    """
    if not (_nrows(x) == _nrows(y) == _nrows(site_id)):
        raise CohortError("make_cohort: length mismatch between x, y, site_id")

    try:
        x = np.asarray(x, dtype=np.float64)
    except (ValueError, TypeError) as e:
        raise CohortError("make_cohort: x must be float64-convertible") from e
    if x.ndim != 2:
        raise CohortError("make_cohort: x must be 2-D (n, d)")
    if not np.isfinite(x).all():
        raise CohortError("make_cohort: x contains non-finite values (NaN/inf)")

    y = np.asarray(y)
    if y.ndim != 1:
        raise CohortError(
            "make_cohort: y must be 1-D; an (n,1) column broadcasts predict!=y "
            "into an (n,n) matrix downstream (audit V17)")
    if y.dtype.kind != "b":
        raise CohortError("make_cohort: y must be bool dtype; use coerce_labels to map raw labels")

    site_id = np.asarray(site_id)
    if site_id.ndim != 1:
        raise CohortError("make_cohort: site_id must be 1-D (audit V17)")
    if site_id.dtype.kind not in ("i", "u"):
        raise CohortError("make_cohort: site_id must be integer dtype; use densify_sites")
    site_id = site_id.astype(np.int64)
    if site_id.size == 0 or site_id.min() < 0:
        raise CohortError("make_cohort: site_id must be non-empty and >= 0")
    max_id = int(site_id.max())
    present = np.bincount(site_id, minlength=max_id + 1)
    if (present == 0).any():
        raise CohortError("make_cohort: site_id not dense; missing index in 0..max; use densify_sites")
    n_sites = max_id + 1

    if site_labels is None:
        site_labels = tuple(str(i) for i in range(n_sites))
    else:
        site_labels = tuple(str(s) for s in site_labels)
        if len(site_labels) != n_sites:
            raise CohortError(
                f"make_cohort: site_labels length {len(site_labels)} != number of dense sites {n_sites}")
        if len(set(site_labels)) != n_sites:
            dupes = sorted({s for s in site_labels if site_labels.count(s) > 1})
            raise CohortError(
                f"make_cohort: repeated site_labels {dupes!r} -- a repeated "
                f"label declares one physical site, which cannot span two "
                f"independent clusters (audit V5)")

    if expect_features is not None and x.shape[1] != expect_features:
        raise CohortError(f"make_cohort: expected {expect_features} features, got {x.shape[1]}")

    # Fitting cohorts need both classes -- the head fit and BBSE site stats
    # break otherwise. Target pools may be legitimately all-negative and pass
    # require_both_classes=False.
    if require_both_classes and not (bool(y.any()) and bool((~y).any())):
        raise CohortError("make_cohort: both classes must be present (found only one)")

    return Cohort(x=x, y=y, site_id=site_id, site_labels=site_labels)


def from_raw(x, y_raw, positive_label, site_ids_raw, *,
             require_both_classes: bool = True) -> Cohort:
    """Coerce raw labels, densify raw site ids, then build the Cohort.

    require_both_classes passes through to make_cohort, and also sets
    coerce_labels' allow_absent_positive to its negation. That is the one
    sanctioned path for an all-negative target pool to arrive from raw inputs.

    Fitting cohorts keep the strict default, since single-class data breaks the
    head fit and BBSE site stats. A target pool may legitimately be
    all-negative and must flow through rather than crash.

    Refs: SPEC "validate.py".
    """
    y = coerce_labels(y_raw, positive_label,
                      allow_absent_positive=not require_both_classes)
    dense, labels = densify_sites(site_ids_raw)
    return make_cohort(x, y, dense, site_labels=labels,
                       require_both_classes=require_both_classes)


def assert_site_disjoint(**named) -> None:
    """Assert pairwise-disjoint site_labels across the named cohorts.

    Comparison uses the same canonical-plus-normalized form densify_sites uses
    within a cohort. Raw string equality was not enough: a case-variant or
    trailing-space respelling of S_cal passed as S_aux, voiding the walk
    order's S_cal-independence.

    Raises CohortError naming the two cohorts and the raw overlapping labels.
    This is the assertion v1 promised at pipeline entry and never had.

    Refs: SPEC "validate.py"; audit F03; verification F2.
    """
    items = list(named.items())
    norm = [(name, {normalized_label(s): s for s in c.site_labels})
            for name, c in items]
    for i in range(len(norm)):
        name_a, map_a = norm[i]
        for j in range(i + 1, len(norm)):
            name_b, map_b = norm[j]
            overlap = set(map_a) & set(map_b)
            if overlap:
                pairs = sorted((map_a[k], map_b[k]) for k in overlap)
                raise CohortError(
                    f"assert_site_disjoint: cohorts {name_a!r} and {name_b!r} "
                    f"share sites (raw label pairs, compared under the "
                    f"canonical normal form) {pairs!r}")
