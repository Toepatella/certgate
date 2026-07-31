"""SPEC section "validate.py": Cohort container + loud, typed input contract.

Encodes the data discipline of METHODS section 2 (the site is the honest unit
of independence). Every rejection is a loud, typed ``CohortError`` carrying a
named reason -- the code never guesses at a caller's intent (audit F05/F35/F37).
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
    """First-axis length of an array-like; 0 for a scalar (drives the alignment check)."""
    arr = np.asarray(a)
    return int(arr.shape[0]) if arr.ndim >= 1 else 0


@dataclass(frozen=True)
class Cohort:
    """Immutable multi-site cohort (SPEC validate.py).

    Holds only ``x, y, site_id, site_labels`` -- no oracle latent/site fields.
    ``site_sizes`` is DERIVED from ``site_id`` on every access and is never an
    independent input (audit F38).

    ``__post_init__`` (audit V15) enforces the documented contract on DIRECT
    construction too, not only through ``make_cohort`` -- the container is a
    public export and a contract that is optional through the public API is not
    a contract. NOTE: unlike ``make_cohort``'s input rule, ``__post_init__``
    does NOT require every dense index to carry records: a Cohort with trailing
    empty sites is a legitimate state (it is how the record-carrying cluster
    gate is exercised -- audit V12).
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
        """Per-site record counts -- ALWAYS ``np.bincount(site_id, minlength=n_sites)`` (audit F38)."""
        return np.bincount(self.site_id, minlength=self.n_sites)


def coerce_labels(raw, positive_label, allow_absent_positive: bool = False) -> np.ndarray:
    """Explicit two-value map raw -> bool (SPEC validate.py; audit F05/F35/F37).

    Maps ``positive_label`` to True and the single other observed value to
    False. Raises ``CohortError`` on NaN/missing values, and on any value
    outside ``{positive_label, the one other observed value}``. Never guesses.

    ``allow_absent_positive`` is the sanctioned opt-in (wired from
    ``from_raw(require_both_classes=False)``, TARGET pools only): when the
    positive label is ABSENT *and* exactly one other value is observed, return
    all-False instead of raising -- a legitimately all-negative deployment pool
    at ~9.5% prevalence. The strict default stays strict (typo protection); a
    NaN/None value, or more than one distinct observed value, still raises even
    when opted in.
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
        # Positive label absent. Strict default rejects (a typo in positive_label
        # must never silently pass as all-negative). The opt-in admits a genuinely
        # single-class target pool as all-False -- but ONLY if exactly one value is
        # observed; >1 distinct is still ambiguous and raises (audit F05/F35/F37).
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
    """Canonical string form of one raw site id (SPEC validate.py; audit
    V4/V10, Unicode-hardened per verification F1, precision-guarded per F3).

    Rejects missing or ambiguous identity loudly -- ``None``, float NaN, empty
    or whitespace-only strings, and floats at or beyond 2**53 (integer
    resolution lost: a lossy label must never be emitted silently) must never
    become a bona fide pseudo-cluster (the site is the unit of statistical
    independence). Strings are NFKC-normalized, format-category (Cf)
    characters (ZWSP/BOM/soft-hyphen/... -- the invisible-suffix channel that
    silently split one hospital into two clusters) are deleted, then
    surrounding whitespace is stripped; integral numerics (``1`` and ``1.0``,
    the pandas float-dtype column case) map to the same integer string.
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
    """Aggressive normal form used ONLY for near-duplicate collision checks
    and cross-cohort identity comparison (audit V4; verification F2): casefold
    plus numeric-lexeme collapse ('1' vs '1.0' as strings). Integer lexemes
    collapse with EXACT integer arithmetic -- float64 round-tripping falsely
    collided distinct 18+-digit surrogate keys (verification N4). Never used
    as a label -- a collision here is a loud rejection, not a merge; the code
    does not guess which merge the caller intended.
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
    """Public composition of canonicalization + normalization (verification
    F2): the single normal form under which site identity is compared ACROSS
    cohorts (``assert_site_disjoint``, the run_certgate target gates), so dirt
    that is loud inside one cohort cannot slip silently between cohorts.
    """
    return _normalized_site_id(_canonical_site_id(s))


def densify_sites(raw_site_ids) -> tuple[np.ndarray, tuple[str, ...]]:
    """Map arbitrary site identifiers to dense ``0..K-1`` (SPEC validate.py;
    audit F39, hardened by audit V4/V10).

    Canonical order is ``np.unique`` over the canonicalized form of each id
    (see ``_canonical_site_id``). Returns ``(dense int64 ids, labels)`` with
    labels index-aligned to the dense ids.

    Collision check (audit V4): if two DISTINCT canonical labels collide under
    the aggressive normal form (``'H1'`` vs ``'h1 '``; string ``'1'`` vs
    ``'1.0'``), the site column is dirty and a ``CohortError`` names the
    colliding ids. Loud, because the cluster count feeds ``MIN_CAL_CLUSTERS``
    and the betting test's effective n: cosmetic noise that splits one hospital
    into two "independent" clusters buys certification strength the honest
    clustering refuses.
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

    Checks fire in order: length alignment; ``x`` 2-D float64-convertible & all
    finite; ``y`` strictly bool dtype; ``site_id`` integer, ``>=0``, dense (every
    index ``0..max`` present); ``expect_features`` match; both classes present.
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

    # fitting cohorts need both classes (head fit / BBSE site stats break otherwise);
    # target pools may be legitimately all-negative and pass require_both_classes=False
    if require_both_classes and not (bool(y.any()) and bool((~y).any())):
        raise CohortError("make_cohort: both classes must be present (found only one)")

    return Cohort(x=x, y=y, site_id=site_id, site_labels=site_labels)


def from_raw(x, y_raw, positive_label, site_ids_raw, *,
             require_both_classes: bool = True) -> Cohort:
    """Coerce raw labels + densify raw site ids, then ``make_cohort`` (SPEC validate.py).

    ``require_both_classes`` passes through to ``make_cohort`` AND opts
    ``coerce_labels`` into ``allow_absent_positive`` (``= not
    require_both_classes``): the sole sanctioned path for an all-negative TARGET
    pool to flow in from raw inputs. Fitting cohorts keep the strict default --
    single-class data breaks the head fit and BBSE site stats -- while a target
    pool may legitimately be all-negative and must flow through, not crash.
    """
    y = coerce_labels(y_raw, positive_label,
                      allow_absent_positive=not require_both_classes)
    dense, labels = densify_sites(site_ids_raw)
    return make_cohort(x, y, dense, site_labels=labels,
                       require_both_classes=require_both_classes)


def assert_site_disjoint(**named) -> None:
    """Assert pairwise-disjoint ``site_labels`` across named cohorts (SPEC validate.py; audit F03).

    Comparison is under the SAME canonical+normalized form ``densify_sites``
    uses within a cohort (verification F2): raw string equality let a
    case-variant or trailing-space respelling of S_cal pass as S_aux, voiding
    the walk order's S_cal-independence. Raises ``CohortError`` naming the two
    cohorts and the RAW overlapping labels. This is the assertion v1 promised
    at pipeline entry and never had.
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
