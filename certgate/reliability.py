"""Post-hoc selective reliability panel (SPEC section "reliability.py").

ADDED 2026-08-01, AFTER the eICU-CRD v2.0 extract was read. This module is a
DESCRIPTIVE DIAGNOSTIC in the ``harness.py`` register: it measures, it never
certifies. It is NOT part of the pre-extract protocol freeze (commit
9f25b491b2554d0a4bd7aaaf44081c185d01715f), nothing in ``pipeline.py`` or
``report.py`` imports it, and it settles none of ``EICU-PROTOCOL.md``'s frozen
predictions P1-P7 or failure criteria F-A-F-E. Every number it produces from
the real extract carries ``POST_HOC_LABEL`` (A6 discipline).

PORTED, byte-exactly, from the verified reference implementation in
``selective-reliability-panel/srp`` (581 tests green, deterministic): identical
input arrays must give an identical panel dict, including every bootstrap
endpoint. Three consequences are binding and are why the values below are what
they are rather than what a fresh derivation would have chosen:

  - the digest prefix stays the byte literal ``b"srp/1"`` and
    ``SCHEMA_VERSION`` stays ``"srp/1"``. Renaming either moves EVERY interval
    in the panel: the prefix is the first thing hashed into ``input_digest``
    and the digest seeds every stream.
  - the root seed stays ``PANEL_SEED = 20260731`` -- srp's own, NOT
    ``constants.SEED = 20260721``. It is RENAMED, never RE-POINTED:
    re-pointing it at ``constants.SEED`` would silently discard the external
    verification that is the whole reason to port rather than re-derive.
    Determinism is unaffected (identical inputs still give byte-identical
    output; no wall clock enters any artifact) and no certified quantity
    descends from it -- the panel is downstream of the certificate and feeds
    nothing back.
  - NO key of the emitted dict is renamed. ``tests/test_reliability_panel.py``
    pins the sha256 of the emitted dict on a frozen fixture against a literal
    produced by the sandbox implementation; a rename breaks that pin, which is
    a design change, not a nuisance.

THE conflation trap, stated once. ``Head.predict_proba(x)`` returns
``p1 = P(y=1|x)``; ``Head.score(x) = max(p1, 1-p1)`` in [0.5, 1] is the
SELECTIVE-GATING confidence. The panel bins and regresses ``p1``; the answered
mask is ``score >= tau_star``. Feeding ``score`` as ``p`` passes validation
silently -- it is finite and in [0, 1] -- and yields a fully populated but
meaningless panel. The guard is therefore structural at the boundary:
``panel_from_head`` is the ONLY entry point the drivers use and it computes
both quantities itself. A driver never constructs ``p``.

Third-party imports: numpy ONLY, at module top level (audit F16). NO
``from certgate ...`` import of any kind -- the module is a DAG leaf and never
sees a ``Head``, a ``Cohort``, or the certified path (``head`` is reached only
by duck typing inside ``panel_from_head``).
"""

import hashlib
import math
from dataclasses import dataclass

import numpy as np


class PanelError(ValueError):
    """The single exception type; every rejection is typed and reason-named,
    in the ``certgate/validate.py`` register."""


# --- frozen panel constants (pinned literally by tests/test_constants.py) ----
# NOT in constants.py, deliberately: that block is the A-PRIORI pre-extract
# surface of the certified protocol and these values were frozen AFTER the
# extract had been seen -- putting them there would place post-hoc values under
# a pre-registration claim they do not carry. ``harness.SIZE_BINS`` is the
# standing precedent for a module-local frozen tuple inside the core package.

SCHEMA_VERSION = "srp/1"        # emitted verbatim AND hashed as the digest
                                # prefix -- renaming it moves every interval
PANEL_SEED = 20260731           # srp's own root seed; the first entropy word of
                                # every SeedSequence in derive_rng. RENAMED
                                # from srp's `SEED`, never re-pointed at
                                # constants.SEED = 20260721
DEFAULT_BIN_EDGES = (0.0, 0.02, 0.05, 0.10, 0.20, 0.35, 0.55, 1.01)
                                # 7 bins. 1.01 is a SENTINEL, never a bound: it
                                # is what lets p == 1.0 land in the last bin
                                # under the strict `<` test. bin_bounds clamps
                                # the EMITTED hi with min(hi, 1.0) so the last
                                # bin READS [0.55, 1.0]. Replacing 1.01 with
                                # 1.0 silently drops every p == 1.0 record and
                                # breaks "per-bin counts sum to n". IDENTICAL
                                # to the explain dashboard's edges because
                                # examples/explain_dashboard.py IMPORTS this
                                # tuple rather than restating it, and
                                # test_dashboard_bin_edges_match pins that the
                                # two actually BIN alike (same boundaries, same
                                # membership, same binned quantity) rather than
                                # merely sharing a constant
DECISION_THRESHOLD = 0.5        # yhat = (p >= this). Equals Head.predict's
                                # rule, which is what makes
                                # skill.<scope>.model_error_rate the certgate
                                # answered error rate on that scope.
                                # UNRELATED to the caller's gate tau
LOGIT_EPS = 1e-6                # |logit| <= 13.815510557964274, so p == 0.0
                                # and p == 1.0 stay usable regression inputs
IRLS_MAX_ITER = 100             # iteration cap; reaching it reports
                                # 'not-converged', never a stopped number
IRLS_TOL = 1e-8                 # converged when max(abs(FULL Newton step))
                                # falls below this
IRLS_MAX_ABS_COEF = 30.0        # reporting range on the coefficients. |beta|
                                # past this is 'coef-out-of-range' (the MLE
                                # exists but lies outside the range);
                                # 'separable' (the MLE does not exist) is a
                                # DIFFERENT status decided BEFORE iterating,
                                # and collapsing the two implies the opposite
                                # operational action
IRLS_MIN_WEIGHT = 1e-10         # floor on the working weight mu*(1-mu); keeps
                                # the normal matrix invertible WITHOUT a ridge
IRLS_MIN_RECORDS = 20           # below this the two-parameter fit is not worth
                                # reporting: 'too-few-records'
N_BOOT = 2000                   # required VALID resample draws per statistic;
                                # same order as BBSE_BOOT, for the same reason
BOOT_MAX_ATTEMPTS = 4000        # == 2 * N_BOOT. NEVER read at runtime: the
                                # enforced budget is the RELATION 2 * n_boot
                                # resolved inside site_bootstrap_ci, so a
                                # lowered n_boot gets a proportionally lowered
                                # budget and settings.boot_max_attempts
                                # truthfully echoes 2*n_boot, not this constant
CI_LEVEL = 0.95                 # two-sided percentile interval level
MIN_SITES_FOR_CI = 10           # cluster floor, checked against
                                # n_sites_carrying BEFORE any resampling work
                                # (n_attempts == 0). Same measured lesson as
                                # constants.BBSE_MIN_TARGET_SITES = 10: a
                                # percentile bootstrap over fewer carrying
                                # sites cannot approach nominal coverage
ROUND_DP = 6                    # decimal places, applied ONCE at emit time.
                                # `settings` is EXEMPT and has to be: LOGIT_EPS
                                # and IRLS_TOL both collapse to 0.0 at 6 dp
FIG_DPI = 110                   # matches every existing experiment figure
CI_STATUSES = ("ok", "empty-bin", "too-few-sites", "degenerate-resamples",
               "undefined-point", "truncated-resamples")
                                # the EXHAUSTIVE interval-status vocabulary;
                                # 'truncated-resamples' = a resample refit was
                                # rejected for its VALUE, so a quantile would
                                # delete the tail rather than thin it
FIT_STATUSES = ("ok", "too-few-records", "single-class", "degenerate-design",
                "separable", "coef-out-of-range", "not-converged", "singular")
                                # the EXHAUSTIVE calibration-fit vocabulary

# --- A6-register labels ------------------------------------------------------
# The label is a hand-appended string in the same '[MEASURE]' register the ETL
# uses for amendment A6: a panel artifact in a separate JSON file inherits
# nothing, so the real-extract driver carries it in FIVE places (the run
# warnings, the top of EICU_reliability_panel.json, the EICU-RELIABILITY
# summary block, the face of EICU_reliability_panel.png, and a leading
# post_hoc column on every EICU_reliability.csv row -- the artifact most
# easily detached from its directory).

POST_HOC_LABEL = (
    "[MEASURE] POST-HOC (2026-08-01): the selective reliability panel is a "
    "DESCRIPTIVE diagnostic added AFTER the eICU-CRD v2.0 extract was read. It "
    "is NOT part of the pre-extract protocol freeze (commit "
    "9f25b491b2554d0a4bd7aaaf44081c185d01715f), it alters no certified "
    "quantity, and it settles none of the frozen predictions P1-P7 or failure "
    "criteria F-A-F-E. Its bins, seed and bootstrap counts were fixed before "
    "it was run on this extract but AFTER the extract had been seen, so they "
    "carry NO pre-registration claim. Every figure and number derived from "
    "this panel must carry this label.")

# The synthetic side has no data-seen problem -- only an added-after-publication
# one -- so E6 gets a shorter sibling.
E6_POST_HOC_NOTE = (
    "[MEASURE] POST-HOC (2026-08-01): added after the E1-E7 grid was "
    "published. Descriptive only -- it alters no certified quantity and no "
    "number in E1-E7 moves because of it (the panel self-seeds from a digest "
    "of its own inputs and consumes no _rng(6) draw).")

# The mandatory disclosures, emitted verbatim as ``notes``. Each names a way the
# panel can be misread; dropping one is a contract change, not an editorial
# decision. Note 2 is the estimand-honesty clause in certgate's own register:
# every interval here is MARGINAL and there is no simultaneity claim.
NOTES = (
    "Estimand: every reported quantity is a record-weighted ratio of sums over the fixed "
    "site population; a large site contributes proportionally more than a small one.",
    "Every interval is a MARGINAL two-sided percentile interval from an independent "
    "one-stage site resample. There is no joint-coverage claim: do not difference two "
    "interval endpoints -- differences that matter are computed as their own statistic "
    "inside a shared resample (skill.contrast, brier.reference.brier_difference).",
    "The expected calibration error is a plug-in estimate on fixed a-priori bins. It is "
    "positively biased and the bias grows as per-bin counts shrink; a percentile interval "
    "does not correct bias, so the interval covers the biased plug-in estimand, not true "
    "calibration error.",
    "The answered and declined subsets are selected by the caller's gate, so each is an "
    "average over a site population whose composition differs from the full record set. "
    "Compare skill.answered against skill.all before reading a low answered error rate as "
    "scorer accuracy.",
    "The reference-scorer Brier is computed on the answered records that carry a finite "
    "reference probability. Compare it ONLY against brier_primary_matched, which uses the "
    "identical denominator, never against brier.primary_answered.",
    "A null statistic means undefined or suppressed, never zero. A null interval carries "
    "its reason in the adjacent ci_status field.",
)

CI_CONVENTION = (
    "two-sided percentile: np.quantile(draws, [0.025, 0.975], method='linear')"
)
WEIGHTING = "record-weighted ratio-of-sums over resampled sites (no influence cap)"

_MAX_HALVINGS = 30      # the IRLS line search's own cap; 2**-30 of a step is noise


# ===========================================================================
# boundary -- the ONLY place this module raises (certgate/validate.py idiom)
# ===========================================================================
#
# Message shape everywhere:  "<function>: <what is wrong> -- <why it matters>",
# with the offending value interpolated using !r and an ASCII "--". The message
# names the FIX ("densify the site index"), never a guess at what was meant.
#
# Check order is CONTRACT, not convenience:
#   1. array-length alignment across every supplied array;
#   2. p: 1-D, float64-convertible, all finite, all within [0, 1] (NO tolerance);
#   3. answered: STRICTLY bool dtype, 1-D;
#   4. y: STRICTLY bool dtype, 1-D;
#   5. site_id: integer dtype, all >= 0, DENSE (bincount gap check);
#   6. n >= 1;
#   7. decision_threshold: finite, in the OPEN interval (0, 1);
#   8. bin_edges: len >= 2, strictly increasing, edges[0] <= 0.0, edges[-1] > 1.0;
#   9. p_ref (when supplied): 1-D, no +/-Inf, every finite entry in [0, 1].
#      NaN is accepted here and NOWHERE else -- it is the ONE missing marker.
#
# Alignment is first so that two simultaneous defects report the STRUCTURAL one:
# a length mismatch makes every value check meaningless.
#
# NOTHING is coerced. An int8 0/1 vector is not a mask, an (n, 1) column is not a
# vector (it would broadcast a later comparison into an (n, n) matrix), and a
# sparse site index is not remapped -- a silent remap changes WHICH RECORDS MOVE
# TOGETHER under the cluster bootstrap, and every interval in the panel would
# quietly describe a different clustering.


@dataclass(frozen=True, eq=False)
class PanelInputs:
    """One validated, immutable bundle. Everything downstream reads this only.

    Attributes
    ----------
    p
        ``(n,)`` float64, finite, within [0, 1]. The predicted probability of the
        POSITIVE class -- ``Head.predict_proba``, NEVER the max-class confidence
        transform ``Head.score``.
    answered
        ``(n,)`` strict ``bool``. The caller's gate decision per record.
    site_id
        ``(n,)`` integer, dense ``0 .. n_sites-1``. The dtype is preserved exactly
        as supplied, because the content digest is taken over raw bytes.
    y
        ``(n,)`` strict ``bool``. The true label per record.
    p_ref
        ``(n,)`` float64 or ``None``. ``NaN`` marks a record with no reference.
    decision_threshold
        Float in the OPEN interval (0, 1).
    bin_edges
        Strictly increasing tuple of floats, first <= 0.0, last > 1.0.
    """

    p: np.ndarray
    answered: np.ndarray
    site_id: np.ndarray
    y: np.ndarray
    p_ref: object
    decision_threshold: float
    bin_edges: tuple

    @property
    def n(self) -> int:
        """Number of records."""
        return int(self.p.shape[0])

    @property
    def n_sites(self) -> int:
        """Size of the FIXED site population. Denseness is already enforced."""
        return int(self.site_id.max()) + 1

    @property
    def n_bins(self) -> int:
        """Number of reliability bins."""
        return len(self.bin_edges) - 1


def _fail(message: str) -> None:
    raise PanelError(f"validate_inputs: {message}")


def _as_array(name: str, value):
    """``np.asarray`` with a typed failure for anything not array-shaped."""
    try:
        arr = np.asarray(value)
    except (TypeError, ValueError) as exc:      # pragma: no cover - numpy is permissive
        _fail(
            f"{name} could not be read as an array ({exc}) -- pass a one-dimensional "
            f"numpy array of length n, one entry per record"
        )
    if arr.ndim == 0:
        _fail(
            f"{name} is a scalar with shape {arr.shape!r} -- every input must be a "
            f"one-dimensional array of length n, one entry per record"
        )
    return arr


def _require_1d(name: str, arr: np.ndarray) -> None:
    if arr.ndim != 1:
        _fail(
            f"{name} has shape {arr.shape!r}, which is not one-dimensional -- an (n, 1) "
            f"column would broadcast a later comparison into an (n, n) matrix, so pass a "
            f"flat (n,) array (use .ravel() deliberately if that is what you meant)"
        )


def _require_bool(name: str, arr: np.ndarray) -> None:
    if arr.dtype != np.bool_:
        _fail(
            f"{name} has dtype {arr.dtype!r}, not bool -- a 0/1 integer or float vector "
            f"is rejected rather than coerced, so cast it yourself with "
            f".astype(bool) and be sure the mapping is the one you intend"
        )


def validate_inputs(p, answered, site_id, y, p_ref=None, *,
                    decision_threshold: float = DECISION_THRESHOLD,
                    bin_edges=DEFAULT_BIN_EDGES) -> PanelInputs:
    """Run every contract check in the documented order; return a frozen bundle.

    Raises
    ------
    PanelError
        On the FIRST failure, naming the check, the offending value and why the
        check exists.
    """
    # --- 1. array-length alignment -----------------------------------------
    supplied = {
        "p": _as_array("p", p),
        "answered": _as_array("answered", answered),
        "site_id": _as_array("site_id", site_id),
        "y": _as_array("y", y),
    }
    if p_ref is not None:
        supplied["p_ref"] = _as_array("p_ref", p_ref)

    lengths = {name: int(arr.shape[0]) for name, arr in supplied.items()}
    if len(set(lengths.values())) > 1:
        _fail(
            f"array lengths do not align: {lengths!r} -- row i of every supplied array "
            f"must describe the same record, so they all share one length n"
        )

    # --- 2. p ---------------------------------------------------------------
    p_arr = supplied["p"]
    _require_1d("p", p_arr)
    try:
        p_f = np.asarray(p_arr, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        _fail(
            f"p has dtype {p_arr.dtype!r} and is not convertible to float64 ({exc}) -- "
            f"p is the predicted probability of the positive class and must be numeric"
        )
    bad = ~np.isfinite(p_f)
    if bool(bad.any()):
        first = int(np.flatnonzero(bad)[0])
        _fail(
            f"p[{first}] is {float(p_f[first])!r}, which is not finite -- NaN is the "
            f"sanctioned missing marker for p_ref only; every predicted probability must "
            f"be a real number in [0.0, 1.0]"
        )
    out_of_range = (p_f < 0.0) | (p_f > 1.0)
    if bool(out_of_range.any()):
        first = int(np.flatnonzero(out_of_range)[0])
        _fail(
            f"p[{first}] is {float(p_f[first])!r}, outside [0.0, 1.0] with no tolerance "
            f"-- p must be a probability, not a log-odds, a percentage or a max-class "
            f"confidence value"
        )

    # --- 3. answered --------------------------------------------------------
    answered_arr = supplied["answered"]
    _require_bool("answered", answered_arr)
    _require_1d("answered", answered_arr)

    # --- 4. y ---------------------------------------------------------------
    y_arr = supplied["y"]
    _require_bool("y", y_arr)
    _require_1d("y", y_arr)

    # --- 5. site_id ---------------------------------------------------------
    site_arr = supplied["site_id"]
    _require_1d("site_id", site_arr)
    if not np.issubdtype(site_arr.dtype, np.integer):
        _fail(
            f"site_id has dtype {site_arr.dtype!r}, not an integer type -- the site index "
            f"is the resampling unit and a float index cannot address a site block; cast "
            f"it to an integer dtype yourself"
        )
    if site_arr.size:
        smallest = int(site_arr.min())
        if smallest < 0:
            first = int(np.flatnonzero(site_arr < 0)[0])
            _fail(
                f"site_id[{first}] is {smallest!r}, which is negative -- site indices run "
                f"0 .. n_sites-1 and the population size is read off the maximum"
            )
        top = int(site_arr.max())
        present = np.bincount(np.asarray(site_arr, dtype=np.int64), minlength=top + 1)
        gaps = np.flatnonzero(present == 0)
        if gaps.size:
            _fail(
                f"site_id is not dense: index {int(gaps[0])!r} carries no record while "
                f"{top!r} is present -- densify the site index to 0 .. n_sites-1 before "
                f"the call; the panel refuses to remap it silently because a remap changes "
                f"which records move together under the cluster bootstrap"
            )

    # --- 6. n >= 1 ----------------------------------------------------------
    if lengths["p"] < 1:
        _fail(
            "the input carries no records (n = 0) -- there is nothing to bin, fit or "
            "resample, so an empty panel would be a row of nulls pretending to be a result"
        )

    # --- 7. decision_threshold ----------------------------------------------
    try:
        threshold = float(decision_threshold)
    except (TypeError, ValueError):
        _fail(
            f"decision_threshold is {decision_threshold!r}, which is not a float -- it is "
            f"the cut that turns p into a predicted class, yhat = (p >= threshold)"
        )
    if not math.isfinite(threshold) or not (0.0 < threshold < 1.0):
        _fail(
            f"decision_threshold is {threshold!r}, outside the open interval (0.0, 1.0) -- "
            f"at 0.0 every record is predicted positive and at 1.0 almost none is, so "
            f"neither endpoint is a usable class cut"
        )

    # --- 8. bin_edges -------------------------------------------------------
    try:
        edges = tuple(float(e) for e in bin_edges)
    except (TypeError, ValueError):
        _fail(
            f"bin_edges is {bin_edges!r}, which is not a sequence of floats -- pass the "
            f"a-priori bin boundaries as a tuple of numbers"
        )
    if len(edges) < 2:
        _fail(
            f"bin_edges is {edges!r}, which defines no bin -- at least two edges are "
            f"needed to bound a single bin"
        )
    if any(not math.isfinite(e) for e in edges):
        _fail(
            f"bin_edges is {edges!r} and holds a non-finite edge -- every boundary must be "
            f"a real number so that bin membership is decidable"
        )
    if any(upper <= lower for lower, upper in zip(edges, edges[1:])):
        _fail(
            f"bin_edges is {edges!r} and is not strictly increasing -- a repeated or "
            f"decreasing edge makes bin membership ambiguous"
        )
    if edges[0] > 0.0:
        _fail(
            f"bin_edges starts at {edges[0]!r}, above 0.0 -- the first edge must be at or "
            f"below 0.0 or records at p == 0.0 fall outside every bin"
        )
    if edges[-1] <= 1.0:
        _fail(
            f"bin_edges ends at {edges[-1]!r}, which is not above 1.0 -- the last edge is a "
            f"SENTINEL: membership is upper-open, so an edge of exactly 1.0 silently drops "
            f"every record at p == 1.0"
        )

    # --- 9. p_ref -----------------------------------------------------------
    ref_f = None
    if p_ref is not None:
        ref_arr = supplied["p_ref"]
        _require_1d("p_ref", ref_arr)
        try:
            ref_f = np.asarray(ref_arr, dtype=np.float64)
        except (TypeError, ValueError) as exc:
            _fail(
                f"p_ref has dtype {ref_arr.dtype!r} and is not convertible to float64 "
                f"({exc}) -- the reference scorer reports a probability per record"
            )
        infinite = np.isinf(ref_f)
        if bool(infinite.any()):
            first = int(np.flatnonzero(infinite)[0])
            _fail(
                f"p_ref[{first}] is {float(ref_f[first])!r} -- NaN is the ONE sanctioned "
                f"missing marker in this module; an infinity is a defect, not a gap"
            )
        finite = np.isfinite(ref_f)
        outside = finite & ((ref_f < 0.0) | (ref_f > 1.0))
        if bool(outside.any()):
            first = int(np.flatnonzero(outside)[0])
            _fail(
                f"p_ref[{first}] is {float(ref_f[first])!r}, outside [0.0, 1.0] -- every "
                f"finite reference value must be a probability of the positive class"
            )
        ref_f = np.ascontiguousarray(ref_f)

    return PanelInputs(
        p=np.ascontiguousarray(p_f),
        answered=answered_arr,
        site_id=site_arr,
        y=y_arr,
        p_ref=ref_f,
        decision_threshold=threshold,
        bin_edges=edges,
    )


# ===========================================================================
# determinism -- the ONLY place a numpy Generator is constructed
# ===========================================================================


def _feed(hasher, array) -> None:
    """Absorb one array as (dtype string, shape repr, contiguous bytes).

    A contiguous copy is taken first, so a strided VIEW of the same values hashes
    the same as the values themselves -- the digest is about content, not layout.
    The dtype string IS content: an int32 and an int64 site index carry the same
    values but different bytes, and they are different inputs.
    """
    contiguous = np.ascontiguousarray(array)
    hasher.update(contiguous.dtype.str.encode("ascii"))
    hasher.update(repr(contiguous.shape).encode("ascii"))
    hasher.update(contiguous.tobytes())


def input_digest(inputs: PanelInputs) -> str:
    """64-character lowercase sha256 hex over the validated inputs' CONTENT.

    Free-text labels are DELIBERATELY excluded, the same rule
    ``certify.certification_rng`` follows (audit V3): a cosmetic rename must
    never be able to move a reported number. The digest seeds every stream, so
    the prefix ``b"srp/1"`` is load-bearing -- see the module docstring.
    """
    hasher = hashlib.sha256()
    hasher.update(b"srp/1")

    _feed(hasher, inputs.p)
    _feed(hasher, np.ascontiguousarray(inputs.answered).view(np.uint8))
    _feed(hasher, inputs.site_id)
    _feed(hasher, inputs.y)
    if inputs.p_ref is None:
        # An ABSENT reference scorer and an ALL-MISSING one are different inputs.
        hasher.update(b"|noref")
    else:
        _feed(hasher, inputs.p_ref)

    hasher.update(repr(float(inputs.decision_threshold)).encode("ascii"))
    hasher.update(repr(tuple(float(e) for e in inputs.bin_edges)).encode("ascii"))
    return hasher.hexdigest()


def derive_rng(digest: str, stat_key: str) -> np.random.Generator:
    """An independent, reproducible generator for ONE statistic.

    ``stat_key`` is a fixed ``'<scope>/<statistic>'`` string. The WHOLE key is
    hashed, never a prefix, so ``bin1`` and ``bin11`` cannot collide.

    A full panel opens AT MOST ``2 * n_bins + 13`` streams -- 27 at the default
    7-bin edges: ``2 * n_bins`` reliability bins, 2 ece, 2 calibration, 2 brier,
    3 skill scopes, 1 skill contrast and 3 composition scopes. That is a
    CEILING, not a count. An empty bin and an undefined-point block are decided
    BEFORE any generator is constructed and open none, so the realised number is
    data-dependent and is often lower (a gate that answers only low-probability
    records leaves most declined bins empty).
    """
    material = hashlib.sha256(
        digest.encode("ascii") + b"|" + stat_key.encode("utf-8")
    ).digest()
    sequence = np.random.SeedSequence([
        PANEL_SEED,
        int.from_bytes(material[0:4], "big"),
        int.from_bytes(material[4:8], "big"),
        int.from_bytes(material[8:12], "big"),
        int.from_bytes(material[12:16], "big"),
    ])
    return np.random.default_rng(sequence)


# ===========================================================================
# binning + CSR site grouping (pure index arithmetic)
# ===========================================================================
#
# Membership is LOWER-CLOSED / UPPER-OPEN: bin b holds edges[b] <= p < edges[b+1].
# Bins are cut on p and on nothing else -- NEVER on a confidence transform such
# as max(p, 1-p), which lives in [0.5, 1.0], is a different quantity on a
# different domain, and silently relabels every bin.
# Edges are frozen a priori and are NEVER recomputed inside a resample: quantile
# edges per draw would make the bins a random object and the interval would no
# longer refer to a fixed estimand.


def assign_bins(p, bin_edges) -> np.ndarray:
    """Bin index per record, or ``-1`` outside ``[edges[0], edges[-1])``.

    Validation guarantees ``p`` lies in [0, 1] and the edge contract guarantees
    the span covers it, so on validated input the ``-1`` flag never fires; it
    exists so this function is total and testable in isolation.
    """
    edges = np.asarray(tuple(float(e) for e in bin_edges), dtype=np.float64)
    values = np.ascontiguousarray(p, dtype=np.float64)

    # side='right' puts an exact interior edge in the bin ABOVE it: lower-closed.
    index = np.searchsorted(edges, values, side="right").astype(np.int64) - 1
    outside = (values < edges[0]) | (values >= edges[-1])
    index[outside] = -1
    return index


def bin_bounds(bin_edges) -> list:
    """The ``(lo, hi)`` pairs AS EMITTED, one per bin.

    ``hi`` is ``min(edges[b+1], 1.0)``, so the 1.01 sentinel top edge is clamped
    for display while the membership test above still accepts ``p == 1.0``.
    """
    edges = tuple(float(e) for e in bin_edges)
    return [(edges[b], min(edges[b + 1], 1.0)) for b in range(len(edges) - 1)]


def group_by_site(site_id, n_sites: int) -> tuple:
    """CSR-style grouping of record indices by site.

    Returns
    -------
    order
        ``(n,)`` int64 record indices sorted by site with a STABLE sort, so
        records keep their input order within a site and the grouping is
        platform independent (byte-identical output depends on it).
    starts
        ``(n_sites + 1,)`` int64 offsets. Site ``s`` owns
        ``order[starts[s]:starts[s+1]]``; a site carrying no record is an EMPTY
        SPAN, never a missing one.
    """
    sid = np.ascontiguousarray(site_id, dtype=np.int64)
    order = np.argsort(sid, kind="stable").astype(np.int64, copy=False)
    counts = np.bincount(sid, minlength=int(n_sites)).astype(np.int64)
    starts = np.zeros(int(n_sites) + 1, dtype=np.int64)
    np.cumsum(counts, out=starts[1:])
    return order, starts


def gather_sites(order, starts, idx) -> np.ndarray:
    """Record indices for the drawn sites, in draw order, WHOLE BLOCKS at a time.

    A site drawn twice contributes its block twice. The result may be empty
    (every drawn site carried no record, or no site was drawn at all).
    """
    drawn = np.ascontiguousarray(idx, dtype=np.int64)
    if drawn.size == 0:
        return np.empty(0, dtype=np.int64)

    block_start = starts[drawn]
    lengths = starts[drawn + 1] - block_start
    total = int(lengths.sum())
    if total == 0:
        return np.empty(0, dtype=np.int64)

    ends = np.cumsum(lengths)
    offsets = np.repeat(ends - lengths, lengths)
    within = np.arange(total, dtype=np.int64) - offsets
    return order[np.repeat(block_start, lengths) + within]


# ===========================================================================
# the ONE resampling primitive
# ===========================================================================
#
# * The unit is the SITE, always, ONE STAGE. A draw is
#   ``idx = rng.integers(0, n_sites, n_sites)``: n_sites indices drawn WITH
#   replacement from the FULL site population. Whole record blocks move together
#   and a site drawn twice contributes its records twice to BOTH numerator and
#   denominator. Two-stage resampling (sites, then records within drawn sites) is
#   FORBIDDEN -- it injects within-site sampling variance the site-superpopulation
#   estimand does not contain, and it would reintroduce inside this diagnostic
#   layer exactly the record-as-unit failure E7 exists to demonstrate.
# * The site POPULATION is fixed. Sites carrying no record in the current scope
#   or bin remain in the draw; ``n_sites_carrying`` is a REPORTED count only.
#   Passing carrying as ``n_sites`` would redefine the population per bin and the
#   bins would stop being averages over the same thing.
# * Cluster floor: below ``min_sites`` carrying sites the interval is suppressed
#   BEFORE any resampling work (n_attempts == 0).
# * Top-up or decline (audit F40/B-8, V21): an invalid draw is discarded and
#   redrawn against the attempt budget; a reduced draw count is NEVER quantiled.
# * Percentile convention: ONE ``np.quantile(draws, [a, 1-a], axis=0,
#   method='linear')`` call over the whole (n_boot, n_names) matrix. No BCa, no
#   studentisation, no bias correction.
#
# Every interval this module emits is MARGINAL. Two endpoints from different
# blocks -- or two names inside one block -- carry NO simultaneous-coverage
# claim and must never be differenced; differences that matter are their own
# statistic inside a shared resample.


def null_ci(status: str, n_sites_carrying: int = 0) -> dict:
    """The canonical suppressed-interval record.

    Keeps every emitted block the same shape whether or not an interval exists,
    so a reader never has to distinguish "absent" from "undefined" by probing for
    a ``KeyError``.
    """
    return {
        "ci": None,
        "ci_status": str(status),
        "n_boot_valid": 0,
        "n_attempts": 0,
        "n_sites_carrying": int(n_sites_carrying),
    }


def _usable(values, n_names: int) -> bool:
    """A draw is usable only if it returned one FINITE float per name."""
    if values is None:
        return False
    if len(values) != n_names:
        return False
    for value in values:
        if not np.isfinite(value):
            return False
    return True


def site_bootstrap_ci(statistic, names: tuple, n_sites: int, n_sites_carrying: int,
                      *, rng: np.random.Generator, n_boot: int = N_BOOT,
                      max_attempts=None, ci_level: float = CI_LEVEL,
                      min_sites: int = MIN_SITES_FOR_CI) -> dict:
    """One-stage SITE bootstrap around a caller-supplied statistic.

    Parameters
    ----------
    statistic
        ``Callable[[np.ndarray], tuple[float, ...] | None]``. It receives the
        drawn site indices and returns one float per entry of ``names``, or
        ``None`` to declare the draw INVALID (its own validity predicate).
        Each statistic's predicate is stated at its definition and differs by
        estimand -- choosing the wrong one biases the interval.
    names
        Output names, in order. Every name is quantiled from the SAME valid
        draws, so exact relations between names survive; the intervals are still
        MARGINAL and carry no joint claim.
    max_attempts
        ``None`` (what every panel statistic uses) resolves to the RELATION
        ``2 * n_boot``, so a caller that lowers ``n_boot`` gets a proportionally
        lowered budget. ``BOOT_MAX_ATTEMPTS`` is never read here.

    Returns
    -------
    dict
        ``{'ci': {name: {'lo': float, 'hi': float}} | None, 'ci_status': str,
        'n_boot_valid': int, 'n_attempts': int, 'n_sites_carrying': int}``.
    """
    n_sites = int(n_sites)
    carrying = int(n_sites_carrying)
    required = int(n_boot)
    budget = 2 * required if max_attempts is None else int(max_attempts)
    n_names = len(names)

    if carrying < int(min_sites):
        return null_ci("too-few-sites", carrying)

    draws = np.empty((required, n_names), dtype=np.float64)
    collected = 0
    attempts = 0

    while collected < required and attempts < budget:
        idx = rng.integers(0, n_sites, n_sites)
        attempts += 1
        values = statistic(idx)
        if not _usable(values, n_names):
            continue        # invalid draw: discarded and redrawn, charged to budget
        draws[collected, :] = values
        collected += 1

    if collected < required:
        # NEVER quantile a reduced draw count: keeping only the well-populated
        # resamples biases the interval in favour of the easy draws, which is
        # precisely the failure this panel exists to expose.
        return {
            "ci": None,
            "ci_status": "degenerate-resamples",
            "n_boot_valid": collected,
            "n_attempts": attempts,
            "n_sites_carrying": carrying,
        }

    alpha = (1.0 - float(ci_level)) / 2.0
    bounds = np.quantile(draws, [alpha, 1.0 - alpha], axis=0, method="linear")
    return {
        "ci": {
            name: {"lo": float(bounds[0, position]), "hi": float(bounds[1, position])}
            for position, name in enumerate(names)
        },
        "ci_status": "ok",
        "n_boot_valid": collected,
        "n_attempts": attempts,
        "n_sites_carrying": carrying,
    }


# ===========================================================================
# items 1 and 3 -- reliability curve and expected calibration error
# ===========================================================================


def _require_every_record_binned(function_name, bins, p, bin_edges):
    """Reject the ``-1`` ``assign_bins`` returns outside the edge span.

    Both consumers take ``bin_edges`` as a parameter and are exported for direct
    use, so a caller can pass edges that do not bracket its ``p`` even though
    ``selective_reliability_panel``'s validation makes this unreachable through
    the entry point. An unbinned record must NOT be silently dropped (the two
    functions would then disagree about the denominator) and must NOT fold into a
    neighbouring (site, bin) slot (the flattened index arithmetic in
    ``expected_calibration_error`` would corrupt the per-site sums the bootstrap
    indexes). It is a boundary error, and it is loud.
    """
    if bool((bins < 0).any()):
        i = int(np.flatnonzero(bins < 0)[0])
        raise PanelError(
            f"{function_name}: p[{i}] is {float(p[i])!r}, outside the span of "
            f"bin_edges {tuple(float(e) for e in bin_edges)!r} -- every record "
            "must fall in a bin or the per-bin counts no longer sum to the "
            "subset size"
        )


def _site_index(site_id):
    """Site ids as contiguous int64 -- bincount and the CSR grouping need it."""
    return np.ascontiguousarray(site_id, dtype=np.int64)


def _n_carrying(site_id, n_sites) -> int:
    """Distinct sites contributing at least one record to the given selection.

    THE one from-scratch derivation, and the quantity the ``min_sites`` cluster
    floor is checked against. A block that has ALREADY built its per-site count
    vector for its own statistic reads ``np.count_nonzero`` off that local
    instead of calling this; what must never regrow is a second definition of
    the derivation itself, which could then drift from this one and suppress
    intervals in some blocks and not others.
    """
    site_id = np.asarray(site_id, dtype=np.int64)
    if site_id.size == 0:
        return 0
    return int(np.count_nonzero(np.bincount(site_id, minlength=int(n_sites))))


def _flatten_ci(block, name):
    """Collapse a one-name bootstrap result to the emitted {'lo','hi'} shape."""
    ci = block["ci"]
    if ci is None:
        return None
    pair = ci[name]
    return {"lo": float(pair["lo"]), "hi": float(pair["hi"])}


def reliability_curve(p, y, site_id, n_sites, *, digest, scope,
                      bin_edges=DEFAULT_BIN_EDGES, n_boot=N_BOOT,
                      ci_level=CI_LEVEL, min_sites=MIN_SITES_FOR_CI) -> list:
    """Per-bin reliability records for one scope.

    Estimand (bin b, scope S)
        ``E[y | record falls in bin b, record in scope S]``, estimated as the
        RECORD-WEIGHTED ratio of sums over the fixed site population:
        (sum over sites of positives in bin b) / (sum over sites of records in
        bin b). A large site contributes proportionally more than a small one;
        this is NOT a per-site average.

    ``p``, ``y`` and ``site_id`` are ALREADY restricted to the scope by the
    caller; ``n_sites`` is the FULL site count so the population resampled is
    identical across scopes and across bins.

    Returns exactly ``len(bin_edges) - 1`` records in ascending bin order. Empty
    bins are emitted with ``n = 0`` and null statistics -- never dropped, because
    a missing bin and a bin the scope never reaches are different facts.

    Each per-bin interval is MARGINAL: the seven bins carry no simultaneous
    coverage claim and their endpoints must not be differenced.
    """
    p = np.ascontiguousarray(p, dtype=np.float64)
    yf = np.ascontiguousarray(y).astype(np.float64)
    sid = _site_index(site_id)

    bins = assign_bins(p, bin_edges)
    _require_every_record_binned("reliability_curve", bins, p, bin_edges)
    bounds = bin_bounds(bin_edges)

    records = []
    for b, (lo_edge, hi_edge) in enumerate(bounds):
        mask = bins == b
        n_b = int(np.count_nonzero(mask))

        # Per-site record and positive counts INSIDE this bin, length n_sites, so
        # a site with no record here contributes a hard zero to both the
        # numerator and the denominator of every resample.
        denom = np.bincount(sid[mask], minlength=n_sites).astype(np.float64)
        numer = np.bincount(sid[mask], weights=yf[mask], minlength=n_sites)
        carrying = int(np.count_nonzero(denom))

        if n_b == 0:
            boot = null_ci("empty-bin", 0)
            mean_predicted = None
            observed = None
            ci = None
        else:
            mean_predicted = float(p[mask].mean())
            observed = float(numer.sum() / denom.sum())

            def _observed_rate(idx, _numer=numer, _denom=denom):
                d = _denom[idx].sum()
                if d <= 0.0:        # validity predicate: resampled denominator > 0
                    return None
                return (float(_numer[idx].sum() / d),)

            boot = site_bootstrap_ci(
                _observed_rate, ("observed",), n_sites, carrying,
                rng=derive_rng(digest, f"{scope}/reliability/bin{b}"),
                n_boot=n_boot, ci_level=ci_level, min_sites=min_sites)
            ci = _flatten_ci(boot, "observed")

        records.append({
            "index": b,
            "lo": float(lo_edge),
            "hi": float(hi_edge),
            "n": n_b,
            "n_sites_carrying": int(boot["n_sites_carrying"]),
            "mean_predicted": mean_predicted,
            "observed": observed,
            "ci": ci,
            "ci_status": boot["ci_status"],
            "n_boot_valid": int(boot["n_boot_valid"]),
            "n_attempts": int(boot["n_attempts"]),
        })

    return records


def expected_calibration_error(p, y, site_id, n_sites, *, digest, scope,
                               bin_edges=DEFAULT_BIN_EDGES, n_boot=N_BOOT,
                               ci_level=CI_LEVEL,
                               min_sites=MIN_SITES_FOR_CI) -> dict:
    """Count-weighted mean absolute calibration gap for one scope.

    Estimand (scope S)
        ``sum over NON-EMPTY bins of (n_b / n_total) * |mean_predicted_b -
        observed_b|`` with ``n_total`` the number of records in the scope, so the
        weights sum to 1 exactly. Empty bins are EXCLUDED, not folded in as a
        zero gap.

    This is a PLUG-IN estimate: it is positively biased (finite per-bin counts
    inflate the mean absolute gap) and the bias grows as per-bin counts shrink. A
    percentile interval does not correct bias, so the emitted MARGINAL interval
    covers the biased plug-in estimand, NOT true calibration error. That
    disclosure is ``notes[2]`` and must travel with the number.

    Validity predicate for a resample: it carries at least one record.
    """
    p = np.ascontiguousarray(p, dtype=np.float64)
    yf = np.ascontiguousarray(y).astype(np.float64)
    sid = _site_index(site_id)

    n_total = int(p.shape[0])
    n_bins = len(bin_edges) - 1
    bins = assign_bins(p, bin_edges)
    _require_every_record_binned("expected_calibration_error", bins, p, bin_edges)
    carrying = _n_carrying(sid, n_sites)

    # (n_sites, n_bins) sufficient statistics: record count, sum of predicted
    # probability, sum of label. Everything either statistic needs is a linear
    # sum over sites, so a resample is a fancy-indexed row sum -- NO rebinning.
    flat = sid * n_bins + bins
    size = n_sites * n_bins
    cnt = np.bincount(flat, minlength=size).astype(np.float64).reshape(n_sites, n_bins)
    sum_p = np.bincount(flat, weights=p, minlength=size).reshape(n_sites, n_bins)
    sum_y = np.bincount(flat, weights=yf, minlength=size).reshape(n_sites, n_bins)

    def _ece_from_sums(c, sp, sy):
        total = c.sum()
        if total <= 0.0:
            return None
        nonempty = c > 0.0
        if not np.any(nonempty):
            return None
        cn = c[nonempty]
        gap = np.abs(sp[nonempty] / cn - sy[nonempty] / cn)
        return float(((cn / total) * gap).sum())

    point = _ece_from_sums(cnt.sum(axis=0), sum_p.sum(axis=0), sum_y.sum(axis=0))
    n_nonempty = int(np.count_nonzero(cnt.sum(axis=0) > 0.0))

    if point is None:
        boot = null_ci("undefined-point", carrying)
        ci = None
    else:

        def _ece(idx):
            value = _ece_from_sums(
                cnt[idx].sum(axis=0), sum_p[idx].sum(axis=0), sum_y[idx].sum(axis=0))
            return None if value is None else (value,)

        boot = site_bootstrap_ci(
            _ece, ("ece",), n_sites, carrying,
            rng=derive_rng(digest, f"{scope}/ece"),
            n_boot=n_boot, ci_level=ci_level, min_sites=min_sites)
        ci = _flatten_ci(boot, "ece")

    return {
        "ece": point,
        "n": n_total,
        "n_bins_nonempty": n_nonempty,
        "n_sites_carrying": int(boot["n_sites_carrying"]),
        "ci": ci,
        "ci_status": boot["ci_status"],
        "n_boot_valid": int(boot["n_boot_valid"]),
        "n_attempts": int(boot["n_attempts"]),
    }


# ===========================================================================
# item 2 -- weak calibration (IRLS logistic of y on the clipped logit of p)
# ===========================================================================
#
# Estimand: the maximum-likelihood one-covariate logistic regression
#     P(y = 1 | p) = sigmoid(intercept + slope * logit(p))
# on the records of one scope, logit clipped at LOGIT_EPS so p == 0 / 1 stay
# usable. slope == 1 and intercept == 0 is the classical WEAK-calibration
# summary: implied by calibration, not implying it, which is why the reliability
# curve and the ECE are reported alongside rather than replaced by it.
#
# NO ridge, NO shrinkage, NO fallback slope anywhere: a regularised fit would
# quietly change the estimand and report a plausible number where the data
# support none.


def clipped_logit(p, eps=LOGIT_EPS) -> np.ndarray:
    """``log(pc / (1 - pc))`` with ``pc = clip(p, eps, 1 - eps)``.

    Clipping is what makes ``p == 0.0`` and ``p == 1.0`` usable regression inputs
    at all. At eps = 1e-6 the transform saturates at +/-13.815510557964274, so a
    handful of saturated records cannot drag the fit to infinity on their own.
    """
    pc = np.clip(np.ascontiguousarray(p, dtype=np.float64), eps, 1.0 - eps)
    return np.log(pc / (1.0 - pc))


def _sigmoid(t):
    """Overflow-free logistic; ``exp()`` only ever sees non-positive input.

    The naive ``1/(1+exp(-t))`` raises an overflow warning for t << 0, and the
    suite runs warnings-as-errors, so a fit on well-separated scores would ABORT
    instead of reporting 'separable'.
    """
    out = np.empty_like(t)
    pos = t >= 0.0
    neg = ~pos
    out[pos] = 1.0 / (1.0 + np.exp(-t[pos]))
    e = np.exp(t[neg])
    out[neg] = e / (1.0 + e)
    return out


def _is_separated(z, yf) -> bool:
    """True when the two classes do not overlap along the single covariate.

    Albert-Anderson: for a logistic model the MLE EXISTS iff the classes overlap.
    With one covariate that reduces to an interval test. Checked BEFORE iterating
    because the mandated weight floor keeps the normal matrix invertible, so
    Newton does not blow the coefficients past ``max_abs_coef`` on separated
    data -- it crawls and would hit the cap and report 'not-converged', naming
    the wrong defect (the fit did not run out of iterations; the estimate does
    not exist). This pre-loop test is the ONLY source of the 'separable' status.
    """
    pos = yf > 0.0
    z_pos = z[pos]
    z_neg = z[~pos]
    return bool(np.max(z_neg) <= np.min(z_pos) or np.max(z_pos) <= np.min(z_neg))


def _deviance(yf, t) -> float:
    """Binomial deviance at linear predictor ``t``, overflow-free via logaddexp."""
    return -2.0 * (float(yf @ t) - float(np.logaddexp(0.0, t).sum()))


def _fit_result(slope, intercept, status, iterations, n, n_positive) -> dict:
    return {
        "slope": slope,
        "intercept": intercept,
        "status": status,
        "iterations": int(iterations),
        "n": int(n),
        "n_positive": int(n_positive),
    }


def fit_calibration_line(p, y, *, eps=LOGIT_EPS, max_iter=IRLS_MAX_ITER,
                         tol=IRLS_TOL, max_abs_coef=IRLS_MAX_ABS_COEF,
                         min_weight=IRLS_MIN_WEIGHT,
                         min_records=IRLS_MIN_RECORDS) -> dict:
    """Point fit only -- no resampling, no IO, NEVER raises.

    Returns ``{'slope', 'intercept', 'status', 'iterations', 'n', 'n_positive'}``
    with ``slope`` and ``intercept`` ``None`` unless ``status == 'ok'``. An
    unconverged number is never emitted and no inf or NaN ever leaves here.

    Degenerate branches, all returning ``None`` with a status:

        too-few-records    n < min_records
        single-class       0 or n positives -- the slope is unidentified
        degenerate-design  the clipped logit has zero variance
        separable          the classes do not overlap (Albert-Anderson, decided
                           BEFORE iterating); the MLE does NOT exist
        coef-out-of-range  some |coefficient| exceeded max_abs_coef while
                           iterating. DISTINCT IN KIND from 'separable': the
                           classes overlap and the MLE exists and is finite, it
                           simply lies outside the reporting range. Collapsing
                           the two claims the wrong thing and leads to the
                           opposite operational action
        not-converged      the iteration cap was reached with the step >= tol
        singular           the normal matrix was not solvable, or the step was
                           non-finite, or no scale of a descent direction helped
    """
    p = np.ascontiguousarray(p, dtype=np.float64)
    yf = np.ascontiguousarray(y).astype(np.float64)
    n = int(p.shape[0])
    n_positive = int(np.count_nonzero(yf))

    if n < min_records:
        return _fit_result(None, None, "too-few-records", 0, n, n_positive)
    if n_positive == 0 or n_positive == n:
        return _fit_result(None, None, "single-class", 0, n, n_positive)

    z = clipped_logit(p, eps=eps)
    if float(np.max(z) - np.min(z)) == 0.0:
        # Every record shares one predicted probability: the slope is not
        # identified and the normal matrix is exactly singular.
        return _fit_result(None, None, "degenerate-design", 0, n, n_positive)

    if _is_separated(z, yf):
        return _fit_result(None, None, "separable", 0, n, n_positive)

    X = np.column_stack([np.ones(n, dtype=np.float64), z])
    beta = np.zeros(2, dtype=np.float64)
    linear = X @ beta
    deviance = _deviance(yf, linear)
    iterations = 0

    for _ in range(max_iter):
        mu = _sigmoid(linear)
        w = np.clip(mu * (1.0 - mu), min_weight, None)
        try:
            step = np.linalg.solve(X.T @ (w[:, None] * X), X.T @ (yf - mu))
        except np.linalg.LinAlgError:
            return _fit_result(None, None, "singular", iterations, n, n_positive)
        if not np.all(np.isfinite(step)):
            # An ill-conditioned solve can return inf without raising.
            return _fit_result(None, None, "singular", iterations, n, n_positive)

        # Step-halving on the deviance: accept the largest of step, step/2,
        # step/4, ... that does not increase it. The Hessian is positive definite
        # under the weight floor, so the Newton direction is a descent direction
        # and a small enough scale always qualifies; the 1e-12 slack absorbs
        # float noise at the optimum. A full step that already decreases the
        # deviance -- the ordinary case -- is accepted unchanged, so a
        # well-behaved fit follows the plain-Newton trajectory exactly. This is
        # what lets a finite-but-large MLE be converged TO instead of overshot
        # into the coefficient bound.
        scale = 1.0
        for _halving in range(_MAX_HALVINGS):
            candidate_linear = X @ (beta + scale * step)
            candidate_deviance = _deviance(yf, candidate_linear)
            if math.isfinite(candidate_deviance) and (
                    candidate_deviance <= deviance + 1e-12):
                break
            scale *= 0.5
        else:
            # No scale of a descent direction improves the fit: numerically
            # pathological, and a number from here would not be an estimate.
            return _fit_result(None, None, "singular", iterations, n, n_positive)

        beta = beta + scale * step
        linear = candidate_linear
        deviance = candidate_deviance
        iterations += 1

        # TERMINATION ORDER IS LOAD-BEARING. The range check runs BEFORE the
        # convergence check in the same iteration: swapping the two lines lets a
        # |beta| just over the bound report 'ok'.
        if np.any(np.abs(beta) > max_abs_coef):
            # The iterate left the reporting range. With step-halving in force
            # this is not a transient overshoot: the MLE itself sits beyond the
            # bound. The estimate exists; the coefficient is refused.
            return _fit_result(None, None, "coef-out-of-range", iterations, n,
                               n_positive)
        if float(np.max(np.abs(step))) < tol:
            # Convergence is judged on the FULL Newton step: at the optimum it is
            # tiny regardless of any halving, and a halved step must never
            # satisfy a tolerance the full step would have failed.
            return _fit_result(float(beta[1]), float(beta[0]), "ok", iterations,
                               n, n_positive)

    return _fit_result(None, None, "not-converged", iterations, n, n_positive)


def calibration_pair(p, y, site_id, n_sites, *, digest, scope, n_boot=N_BOOT,
                     ci_level=CI_LEVEL, min_sites=MIN_SITES_FOR_CI) -> dict:
    """Point fit plus cluster-robust MARGINAL intervals on both coefficients.

    ``p``, ``y`` and ``site_id`` are ALREADY restricted to the scope; ``n_sites``
    is the FULL site population, so sites carrying no record in this scope remain
    in the draw and contribute an empty block.

    This is the ONLY statistic whose resample MATERIALISES the drawn record
    blocks (``gather_sites``) and refits from scratch; every other statistic
    indexes precomputed per-site sums.

    Suppression:
      * point status != 'ok' -> ``null_ci('undefined-point')``, no resampling at
        all: there is no point estimate for an interval to be around.
      * a refit returning 'coef-out-of-range' is a VALUE-dependent rejection
        (RP-4). The driver tops it up and a closure counter records it; the block
        is then OVERWRITTEN with ``ci=None, ci_status='truncated-resamples'``,
        carrying ``n_boot_valid`` / ``n_attempts`` / ``n_sites_carrying`` through
        UNCHANGED so the attempt counts stay honest. A quantile over the retained
        draws would DELETE the tail of the resampling distribution, not thin it.

    Both coefficients come from the SAME valid draws, so the pair is at least
    mutually consistent -- but each is still a MARGINAL percentile interval and
    the two endpoints must not be differenced or read as a joint region.
    """
    p = np.ascontiguousarray(p, dtype=np.float64)
    yb = np.ascontiguousarray(y)
    sid = np.ascontiguousarray(site_id, dtype=np.int64)

    point = fit_calibration_line(p, yb)
    carrying = _n_carrying(sid, n_sites)

    if point["status"] != "ok":
        boot = null_ci("undefined-point", carrying)
        ci = None
    else:
        order, starts = group_by_site(sid, n_sites)
        truncated = {"count": 0}

        def _refit(idx):
            rec = gather_sites(order, starts, idx)
            if rec.size == 0:
                return None
            fit = fit_calibration_line(p[rec], yb[rec])
            if fit["status"] == "coef-out-of-range":
                # Rejected for the statistic's VALUE, not for being undefined.
                # Counted so the whole interval can be refused below -- letting
                # the driver top this up would delete the tail of the resampling
                # distribution and quantile only the middle.
                truncated["count"] += 1
                return None
            if fit["status"] != "ok":
                # Structurally invalid draw (no usable MLE inside it), not a
                # zero: topped up by the bootstrap driver.
                return None
            return (fit["slope"], fit["intercept"])

        boot = site_bootstrap_ci(
            _refit, ("slope", "intercept"), n_sites, carrying,
            rng=derive_rng(digest, f"{scope}/calibration"),
            n_boot=n_boot, ci_level=ci_level, min_sites=min_sites)
        if truncated["count"] > 0:
            boot = {
                "ci": None,
                "ci_status": "truncated-resamples",
                "n_boot_valid": int(boot["n_boot_valid"]),
                "n_attempts": int(boot["n_attempts"]),
                "n_sites_carrying": int(boot["n_sites_carrying"]),
            }
        ci = (None if boot["ci"] is None else {
            name: {"lo": float(boot["ci"][name]["lo"]),
                   "hi": float(boot["ci"][name]["hi"])}
            for name in ("slope", "intercept")})

    return {
        "slope": point["slope"],
        "intercept": point["intercept"],
        "status": point["status"],
        "iterations": point["iterations"],
        "n": point["n"],
        "n_positive": point["n_positive"],
        "n_sites_carrying": int(boot["n_sites_carrying"]),
        "ci": ci,
        "ci_status": boot["ci_status"],
        "n_boot_valid": int(boot["n_boot_valid"]),
        "n_attempts": int(boot["n_attempts"]),
    }


# ===========================================================================
# item 4 -- Brier, answered subset only
# ===========================================================================


def _site_sums(values, site_id, n_sites) -> np.ndarray:
    return np.bincount(np.asarray(site_id, dtype=np.int64),
                       weights=np.asarray(values, dtype=np.float64),
                       minlength=int(n_sites))


def brier_block(p, y, site_id, n_sites, p_ref, *, digest, n_boot=N_BOOT,
                ci_level=CI_LEVEL, min_sites=MIN_SITES_FOR_CI) -> dict:
    """Squared-error block for the answered subset.

    Estimands
        ``primary_answered.value`` = ``mean((p - y)**2)`` over ALL answered
        records, as a record-weighted ratio of sums over the fixed site
        population.

        ``reference.*`` (only with a reference scorer) is DENOMINATOR-MATCHED.
        The availability mask is ``isfinite(p_ref)`` on the answered records and
        yields three numbers on that ONE mask: ``brier_reference`` (the reference
        scorer), ``brier_primary_matched`` (the PRIMARY scorer on the IDENTICAL
        subset), and ``brier_difference`` = reference - matched.

    ``brier_primary_matched`` is the ONLY fair comparison for the reference
    score. The unmatched ``primary_answered.value`` keeps the WIDER answered
    denominator and must NEVER be differenced against the reference;
    ``available_share`` exposes the size of that gap so the prohibition is
    checkable rather than merely stated (``notes[4]``).

    ``brier_difference`` is a SINGLE statistic per resample -- the third element
    of a 3-tuple from ONE stream -- never a subtraction of two independently
    bootstrapped endpoints, which is strictly wider and has no coverage claim.

    ``p``, ``y``, ``site_id`` and ``p_ref`` are ALREADY restricted to the
    answered subset; ``n_sites`` is the FULL site count. Validity predicate for
    both streams: the resample carries at least one record in the relevant mask.
    """
    n_sites = int(n_sites)
    p_arr = np.ascontiguousarray(p, dtype=np.float64)
    y_arr = np.ascontiguousarray(y).astype(np.float64)
    sid = np.ascontiguousarray(site_id, dtype=np.int64)

    n = int(p_arr.shape[0])
    squared = (p_arr - y_arr) ** 2

    counts = np.bincount(sid, minlength=n_sites).astype(np.float64)
    sums = _site_sums(squared, sid, n_sites)
    carrying = int(np.count_nonzero(counts))

    # ---- primary, over every answered record ------------------------------
    if n == 0:
        primary_boot = null_ci("undefined-point", carrying)
        primary_value = None
        primary_ci = None
    else:
        primary_value = float(sums.sum() / counts.sum())

        def _primary(idx, _sums=sums, _counts=counts):
            denominator = _counts[idx].sum()
            if denominator <= 0.0:
                return None
            return (float(_sums[idx].sum() / denominator),)

        primary_boot = site_bootstrap_ci(
            _primary, ("brier_primary",), n_sites, carrying,
            rng=derive_rng(digest, "answered/brier_primary"),
            n_boot=n_boot, ci_level=ci_level, min_sites=min_sites)
        primary_ci = _flatten_ci(primary_boot, "brier_primary")

    primary = {
        "value": primary_value,
        "n": n,
        "n_sites_carrying": int(primary_boot["n_sites_carrying"]),
        "ci": primary_ci,
        "ci_status": primary_boot["ci_status"],
        "n_boot_valid": int(primary_boot["n_boot_valid"]),
        "n_attempts": int(primary_boot["n_attempts"]),
    }

    if p_ref is None:
        # An explicit null VALUE, not a missing key.
        return {"primary_answered": primary, "reference": None}

    # ---- reference, on the availability mask -------------------------------
    ref_arr = np.ascontiguousarray(p_ref, dtype=np.float64)
    available = np.isfinite(ref_arr)
    n_available = int(np.count_nonzero(available))
    available_share = None if n == 0 else float(n_available) / float(n)

    mask = available.astype(np.float64)
    counts_ref = _site_sums(mask, sid, n_sites)
    # n_sites_carrying for THIS section is taken on the AVAILABILITY mask, so the
    # reference can be floor-suppressed while the primary is not.
    carrying_ref = int(np.count_nonzero(counts_ref))

    if n_available == 0:
        reference = {
            "n_available": 0,
            "available_share": available_share,
            "n_sites_carrying": carrying_ref,
            "brier_reference": None,
            "brier_primary_matched": None,
            "brier_difference": None,
            **{key: value
               for key, value in null_ci("undefined-point", carrying_ref).items()
               if key != "n_sites_carrying"},
        }
        return {"primary_answered": primary, "reference": reference}

    # Squared errors accumulated per site with the missing entries zeroed out;
    # the denominator is the availability count, so both scores share one mask.
    ref_squared = np.where(available,
                           (np.nan_to_num(ref_arr, nan=0.0) - y_arr) ** 2, 0.0)
    matched_squared = np.where(available, squared, 0.0)
    sums_ref = _site_sums(ref_squared, sid, n_sites)
    sums_matched = _site_sums(matched_squared, sid, n_sites)

    denominator = counts_ref.sum()
    value_ref = float(sums_ref.sum() / denominator)
    value_matched = float(sums_matched.sum() / denominator)

    def _reference(idx, _r=sums_ref, _m=sums_matched, _c=counts_ref):
        total = _c[idx].sum()
        if total <= 0.0:
            return None
        reference_score = float(_r[idx].sum() / total)
        matched_score = float(_m[idx].sum() / total)
        return (reference_score, matched_score, reference_score - matched_score)

    boot = site_bootstrap_ci(
        _reference,
        ("brier_reference", "brier_primary_matched", "brier_difference"),
        n_sites, carrying_ref,
        rng=derive_rng(digest, "answered/brier_reference"),
        n_boot=n_boot, ci_level=ci_level, min_sites=min_sites)

    reference = {
        "n_available": n_available,
        "available_share": available_share,
        "n_sites_carrying": int(boot["n_sites_carrying"]),
        "brier_reference": value_ref,
        "brier_primary_matched": value_matched,
        "brier_difference": value_ref - value_matched,
        "ci": boot["ci"],
        "ci_status": boot["ci_status"],
        "n_boot_valid": int(boot["n_boot_valid"]),
        "n_attempts": int(boot["n_attempts"]),
    }
    return {"primary_answered": primary, "reference": reference}


# ===========================================================================
# items 5 and 6 -- the cherry-picking decomposition and the composition block
# ===========================================================================
#
# Item 5 answers the only question this panel exists to answer: is the low error
# rate on the answered subset evidence that the scorer is ACCURATE ON WHAT IT
# ANSWERS, or evidence that the gate simply REMOVED THE HARD RECORDS? At
# single-digit prevalence an alpha near the prevalence is close to what a
# constant always-negative rule achieves (METHODS "Loss"), so meeting the budget
# is not by itself evidence the gate is doing anything.


def _site_counts(site_id, n_sites) -> np.ndarray:
    """Records per site, length ``n_sites``, float64 so ratios never int-divide."""
    return np.bincount(np.asarray(site_id, dtype=np.int64),
                       minlength=n_sites).astype(np.float64)


def _margin_from_totals(total, positives, errors) -> tuple:
    """``(model_error_rate, constant_predictor_error_rate, skill_margin)``.

    ``total`` must already be known positive; the caller owns the validity
    predicate so an invalid resample is discarded rather than divided by zero.
    """
    model_error_rate = errors / total
    positive_rate = positives / total
    constant_error_rate = min(positive_rate, 1.0 - positive_rate)
    return (model_error_rate, constant_error_rate,
            constant_error_rate - model_error_rate)


def skill_decomposition(p, y, site_id, n_sites, *, digest, scope,
                        decision_threshold=DECISION_THRESHOLD, n_boot=N_BOOT,
                        ci_level=CI_LEVEL, min_sites=MIN_SITES_FOR_CI) -> dict:
    """Realized error, constant-predictor error and their margin, for one scope.

    Arithmetic, per scope S::

        yhat                          = (p >= decision_threshold)
        model_error_rate              = mean(yhat != y)
        positive_rate                 = mean(y)
        constant_predictor_class      = bool(positive_rate > 0.5)  # STRICT: a
                                        # 0.5 tie predicts NEGATIVE
        constant_predictor_error_rate = min(positive_rate, 1 - positive_rate)
        skill_margin                  = constant_predictor_error_rate
                                        - model_error_rate

    ``skill_margin`` is BASELINE MINUS MODEL, so positive means the scorer beats
    the trivial in-scope rule. A margin at or below zero on the answered subset
    while the raw answered error rate looks small is exactly the cherry-picking
    signature this panel exists to expose.

    Because ``DECISION_THRESHOLD = 0.5`` coincides with ``Head.predict``'s rule,
    ``model_error_rate`` IS certgate's answered error rate on that scope -- a
    free cross-consistency check, not a second estimand.

    The baseline is RECOMPUTED inside every resample and its class may FLIP
    between draws; that variation belongs to the statistic, and freezing the
    class from the point estimate would remove real variation from the interval.

    One shared stream (``'<scope>/skill'``) returns the triple, so the three
    MARGINAL intervals refer to the same draws. Validity predicate: the resample
    carries at least one record.
    """
    p = np.asarray(p)
    y = np.asarray(y)
    site_id = np.asarray(site_id, dtype=np.int64)
    n_sites = int(n_sites)

    n = int(p.shape[0])
    y_float = y.astype(np.float64)
    yhat = p >= decision_threshold
    n_positive = int(y_float.sum())

    counts = _site_counts(site_id, n_sites)
    positives = _site_sums(y_float, site_id, n_sites)
    errors = _site_sums((yhat != y).astype(np.float64), site_id, n_sites)
    n_sites_carrying = int(np.count_nonzero(counts))

    if n == 0:
        boot = null_ci("undefined-point", n_sites_carrying)
        point = (None, None, None)
        positive_rate = None
        constant_predictor_class = None
    else:
        total = float(counts.sum())
        model_error_rate, constant_error_rate, margin = _margin_from_totals(
            total, float(positives.sum()), float(errors.sum()))
        positive_rate = float(positives.sum()) / total
        constant_predictor_class = bool(positive_rate > 0.5)
        point = (float(model_error_rate), float(constant_error_rate), float(margin))

        def statistic(idx):
            total_b = float(counts[idx].sum())
            if total_b <= 0.0:
                return None
            triple = _margin_from_totals(
                total_b, float(positives[idx].sum()), float(errors[idx].sum()))
            return (float(triple[0]), float(triple[1]), float(triple[2]))

        boot = site_bootstrap_ci(
            statistic,
            ("model_error_rate", "constant_predictor_error_rate", "skill_margin"),
            n_sites, n_sites_carrying,
            rng=derive_rng(digest, f"{scope}/skill"),
            n_boot=n_boot, ci_level=ci_level, min_sites=min_sites)

    return {
        "n": n,
        "n_sites_carrying": int(boot["n_sites_carrying"]),
        "n_positive": n_positive,
        "positive_rate": positive_rate,
        "model_error_rate": point[0],
        "constant_predictor_class": constant_predictor_class,
        "constant_predictor_error_rate": point[1],
        "skill_margin": point[2],
        "ci": boot["ci"],
        "ci_status": boot["ci_status"],
        "n_boot_valid": int(boot["n_boot_valid"]),
        "n_attempts": int(boot["n_attempts"]),
    }


def skill_contrast(p, y, answered, site_id, n_sites, *, digest,
                   decision_threshold=DECISION_THRESHOLD, n_boot=N_BOOT,
                   ci_level=CI_LEVEL, min_sites=MIN_SITES_FOR_CI) -> dict:
    """THE HEADLINE STATISTIC: how much of the answered margin is the gate's doing.

    FULL arrays in, NOT scope-restricted. Computes, inside ONE shared resample
    (``'contrast/skill'``), the pair::

        answered_minus_all      = skill_margin(answered) - skill_margin(all)
        answered_minus_declined = skill_margin(answered) - skill_margin(declined)

    Each is a SINGLE statistic per draw, never a subtraction of two independently
    bootstrapped endpoints. A strongly negative ``answered_minus_all`` says the
    answered subset is where the scorer has the LEAST skill relative to a
    constant predictor -- the low answered error rate came from the gate's
    selection, not from the scorer.

    The point estimate is ``_margins(np.arange(n_sites))`` -- each site once.
    Validity predicate: the resample carries at least one answered record AND (if
    anything is declined) at least one declined record. With no declined records
    at all, ``answered_minus_declined`` is a null POINT (not zero) and only the
    first name is resampled. The cluster floor uses ``min(carrying_a,
    carrying_d)``, or ``carrying_a`` alone when nothing is declined.

    THE ONLY block that does not emit ``n_sites_carrying``.
    """
    p = np.asarray(p)
    y = np.asarray(y)
    answered = np.asarray(answered)
    site_id = np.asarray(site_id, dtype=np.int64)
    n_sites = int(n_sites)

    y_float = y.astype(np.float64)
    yhat = p >= decision_threshold
    err = (yhat != y).astype(np.float64)

    ans = answered.astype(np.float64)
    dec = (~answered).astype(np.float64)

    counts_a = _site_sums(ans, site_id, n_sites)
    positives_a = _site_sums(y_float * ans, site_id, n_sites)
    errors_a = _site_sums(err * ans, site_id, n_sites)

    counts_d = _site_sums(dec, site_id, n_sites)
    positives_d = _site_sums(y_float * dec, site_id, n_sites)
    errors_d = _site_sums(err * dec, site_id, n_sites)

    n_answered = int(counts_a.sum())
    n_declined = int(counts_d.sum())
    has_declined = n_declined > 0

    carrying_a = int(np.count_nonzero(counts_a))
    carrying_d = int(np.count_nonzero(counts_d))
    n_sites_carrying = carrying_a if not has_declined else min(carrying_a, carrying_d)

    if n_answered == 0:
        boot = null_ci("undefined-point", n_sites_carrying)
        return {
            "answered_minus_all": None,
            "answered_minus_declined": None,
            "ci": boot["ci"],
            "ci_status": boot["ci_status"],
            "n_boot_valid": int(boot["n_boot_valid"]),
            "n_attempts": int(boot["n_attempts"]),
        }

    def _margins(idx):
        """(answered, declined-or-None, all) skill margins for a set of sites."""
        total_a = float(counts_a[idx].sum())
        total_d = float(counts_d[idx].sum())
        if total_a <= 0.0:
            return None
        if has_declined and total_d <= 0.0:
            return None
        margin_a = _margin_from_totals(
            total_a, float(positives_a[idx].sum()), float(errors_a[idx].sum()))[2]
        margin_all = _margin_from_totals(
            total_a + total_d,
            float(positives_a[idx].sum()) + float(positives_d[idx].sum()),
            float(errors_a[idx].sum()) + float(errors_d[idx].sum()))[2]
        if not has_declined:
            return margin_a, None, margin_all
        margin_d = _margin_from_totals(
            total_d, float(positives_d[idx].sum()), float(errors_d[idx].sum()))[2]
        return margin_a, margin_d, margin_all

    full = np.arange(n_sites, dtype=np.int64)
    margin_a, margin_d, margin_all = _margins(full)
    answered_minus_all = float(margin_a - margin_all)
    answered_minus_declined = None if margin_d is None else float(margin_a - margin_d)

    if has_declined:
        names = ("answered_minus_all", "answered_minus_declined")

        def statistic(idx):
            got = _margins(idx)
            if got is None:
                return None
            m_a, m_d, m_all = got
            return (float(m_a - m_all), float(m_a - m_d))

    else:
        names = ("answered_minus_all",)

        def statistic(idx):
            got = _margins(idx)
            if got is None:
                return None
            m_a, _m_d, m_all = got
            return (float(m_a - m_all),)

    boot = site_bootstrap_ci(
        statistic, names, n_sites, n_sites_carrying,
        rng=derive_rng(digest, "contrast/skill"),
        n_boot=n_boot, ci_level=ci_level, min_sites=min_sites)

    return {
        "answered_minus_all": answered_minus_all,
        "answered_minus_declined": answered_minus_declined,
        "ci": boot["ci"],
        "ci_status": boot["ci_status"],
        "n_boot_valid": int(boot["n_boot_valid"]),
        "n_attempts": int(boot["n_attempts"]),
    }


def composition_block(p, y, site_id, n_sites, *, digest, scope,
                      decision_threshold=DECISION_THRESHOLD, n_boot=N_BOOT,
                      ci_level=CI_LEVEL, min_sites=MIN_SITES_FOR_CI) -> dict:
    """Predicted-positive and observed-positive fractions for one scope.

        predicted_positive_fraction = mean(p >= decision_threshold)
        observed_positive_fraction  = mean(y)

    Both come from ONE stream (``'<scope>/composition'``), so the two MARGINAL
    intervals refer to the same draws. Validity predicate: the resample carries
    at least one record.

    This is the CI-bearing, three-SCOPE sibling of ``explain.composition``'s
    answered-only point estimate. ``explain.composition`` is UNCHANGED
    (``report.py`` depends on it) and the two must agree on the answered
    predicted-positive fraction -- pinned by test.

    Read the three scopes together: a gate that answers where the positive rate
    is low has shifted the composition of the answered subset away from the full
    record set, and that shift -- not scorer accuracy -- can be the whole reason
    the answered error rate looks small.
    """
    p = np.asarray(p)
    y = np.asarray(y)
    site_id = np.asarray(site_id, dtype=np.int64)
    n_sites = int(n_sites)

    n = int(p.shape[0])
    yhat_float = (p >= decision_threshold).astype(np.float64)
    y_float = y.astype(np.float64)

    counts = _site_counts(site_id, n_sites)
    predicted = _site_sums(yhat_float, site_id, n_sites)
    observed = _site_sums(y_float, site_id, n_sites)
    n_sites_carrying = int(np.count_nonzero(counts))

    n_predicted_positive = int(yhat_float.sum())
    n_observed_positive = int(y_float.sum())

    if n == 0:
        boot = null_ci("undefined-point", n_sites_carrying)
        predicted_fraction = None
        observed_fraction = None
    else:
        total = float(counts.sum())
        predicted_fraction = float(predicted.sum()) / total
        observed_fraction = float(observed.sum()) / total

        def statistic(idx):
            total_b = float(counts[idx].sum())
            if total_b <= 0.0:
                return None
            return (float(predicted[idx].sum()) / total_b,
                    float(observed[idx].sum()) / total_b)

        boot = site_bootstrap_ci(
            statistic,
            ("predicted_positive_fraction", "observed_positive_fraction"),
            n_sites, n_sites_carrying,
            rng=derive_rng(digest, f"{scope}/composition"),
            n_boot=n_boot, ci_level=ci_level, min_sites=min_sites)

    return {
        "n": n,
        "n_sites_carrying": int(boot["n_sites_carrying"]),
        "n_predicted_positive": n_predicted_positive,
        "predicted_positive_fraction": predicted_fraction,
        "n_observed_positive": n_observed_positive,
        "observed_positive_fraction": observed_fraction,
        "ci": boot["ci"],
        "ci_status": boot["ci_status"],
        "n_boot_valid": int(boot["n_boot_valid"]),
        "n_attempts": int(boot["n_attempts"]),
    }


# ===========================================================================
# the orchestrator -- the ONLY assembler of the emitted dict
# ===========================================================================


def _emit(node, round_dp: int):
    """One recursive pass: plain Python types, rounded floats, non-finite -> None.

    BRANCH ORDER IS LOAD-BEARING: ``bool`` is tested BEFORE ``int`` because
    Python's bool is an int subclass -- reversing the two lines turns
    ``constant_predictor_class`` and ``reference_supplied`` into 0/1.
    """
    if node is None or isinstance(node, str):
        return node
    if isinstance(node, (bool, np.bool_)):
        return bool(node)
    if isinstance(node, dict):
        return {str(key): _emit(value, round_dp) for key, value in node.items()}
    if isinstance(node, (list, tuple)):
        return [_emit(value, round_dp) for value in node]
    if isinstance(node, (int, np.integer)):
        return int(node)
    if isinstance(node, (float, np.floating)):
        value = float(node)
        return round(value, round_dp) if math.isfinite(value) else None
    return node


def selective_reliability_panel(p, answered, site_id, y, p_ref=None, *,
                                decision_threshold: float = DECISION_THRESHOLD,
                                bin_edges=DEFAULT_BIN_EDGES,
                                n_boot: int = N_BOOT, ci_level: float = CI_LEVEL,
                                min_sites: int = MIN_SITES_FOR_CI,
                                round_dp: int = ROUND_DP, timestamp=None) -> dict:
    """Build the complete selective reliability panel. Descriptive; certifies nothing.

    Arrays in, plain JSON-serializable dict out; nothing is read from or written
    to disk. ``timestamp=None`` emits ``generated_utc: None`` so the default
    output is byte-identical for identical inputs and NO WALL CLOCK enters any
    emitted artifact.

    TWELVE top-level keys, ALWAYS all present: ``schema_version``,
    ``generated_utc``, ``input_digest``, ``settings``, ``counts``,
    ``reliability``, ``calibration``, ``ece``, ``brier``, ``skill``,
    ``composition``, ``notes``. Optional content degrades to an explicit null
    VALUE, never by key omission -- a reader must never have to tell "absent"
    from "undefined" by probing for a ``KeyError``.

    SCOPES DIFFER BY ITEM, deliberately: reliability / calibration / ece are
    answered+declined only; skill / composition carry all three plus
    ``skill.contrast``; brier is answered-only.

    Rounding happens EXACTLY ONCE, here, at emit time; ``settings`` is EXEMPT and
    has to be (``logit_eps`` and ``irls.tol`` both collapse to 0.0 at 6 dp). NaN
    can never reach the emitted dict, so ``json.dumps(panel, allow_nan=False)``
    succeeds on every legal input -- including all-answered, none-answered,
    single-class and two-site pools.

    Every interval in the result is MARGINAL. There is no simultaneity claim
    anywhere in the panel (``notes[1]``).
    """
    inputs = validate_inputs(p, answered, site_id, y, p_ref,
                             decision_threshold=decision_threshold,
                             bin_edges=bin_edges)
    digest = input_digest(inputs)

    n_sites = inputs.n_sites
    edges = inputs.bin_edges
    threshold = inputs.decision_threshold

    p_all = np.ascontiguousarray(inputs.p, dtype=np.float64)
    y_all = np.ascontiguousarray(inputs.y).astype(bool)
    s_all = np.ascontiguousarray(inputs.site_id, dtype=np.int64)
    answered_mask = np.ascontiguousarray(inputs.answered).astype(bool)
    declined_mask = ~answered_mask

    scope_arrays = {
        "answered": (p_all[answered_mask], y_all[answered_mask], s_all[answered_mask]),
        "declined": (p_all[declined_mask], y_all[declined_mask], s_all[declined_mask]),
        "all": (p_all, y_all, s_all),
    }

    shared = {"n_boot": n_boot, "ci_level": ci_level, "min_sites": min_sites}

    # ---- items 1 and 3 -----------------------------------------------------
    reliability = {}
    ece = {}
    for scope in ("answered", "declined"):
        sp, sy, ss = scope_arrays[scope]
        reliability[scope] = reliability_curve(
            sp, sy, ss, n_sites, digest=digest, scope=scope, bin_edges=edges, **shared)
        ece[scope] = expected_calibration_error(
            sp, sy, ss, n_sites, digest=digest, scope=scope, bin_edges=edges, **shared)

    # ---- item 2 ------------------------------------------------------------
    calibration = {}
    for scope in ("answered", "declined"):
        sp, sy, ss = scope_arrays[scope]
        calibration[scope] = calibration_pair(
            sp, sy, ss, n_sites, digest=digest, scope=scope, **shared)

    # ---- item 4 ------------------------------------------------------------
    ap, ay, asite = scope_arrays["answered"]
    answered_ref = None if inputs.p_ref is None else inputs.p_ref[answered_mask]
    brier = brier_block(ap, ay, asite, n_sites, answered_ref, digest=digest, **shared)

    # ---- item 5 ------------------------------------------------------------
    skill = {}
    for scope in ("answered", "declined", "all"):
        sp, sy, ss = scope_arrays[scope]
        skill[scope] = skill_decomposition(
            sp, sy, ss, n_sites, digest=digest, scope=scope,
            decision_threshold=threshold, **shared)
    skill["contrast"] = skill_contrast(
        p_all, y_all, answered_mask, s_all, n_sites, digest=digest,
        decision_threshold=threshold, **shared)

    # ---- item 6 ------------------------------------------------------------
    composition = {}
    for scope in ("answered", "declined", "all"):
        sp, sy, ss = scope_arrays[scope]
        composition[scope] = composition_block(
            sp, sy, ss, n_sites, digest=digest, scope=scope,
            decision_threshold=threshold, **shared)

    # ---- counts ------------------------------------------------------------
    n_records = inputs.n
    n_answered = int(np.count_nonzero(answered_mask))
    n_declined = n_records - n_answered
    counts = {
        "n_records": n_records,
        "n_sites": n_sites,
        "n_answered": n_answered,
        "n_declined": n_declined,
        "coverage": float(n_answered) / float(n_records),
        "n_sites_answered": _n_carrying(scope_arrays["answered"][2], n_sites),
        "n_sites_declined": _n_carrying(scope_arrays["declined"][2], n_sites),
        "n_positive_all": int(np.count_nonzero(y_all)),
        "reference_supplied": inputs.p_ref is not None,
    }

    # Assembled AFTER the emit pass and deliberately EXEMPT from rounding.
    settings = {
        "seed": PANEL_SEED,
        "decision_threshold": float(threshold),
        "bin_edges": [float(e) for e in edges],
        "n_bins": len(edges) - 1,
        "n_boot": int(n_boot),
        # The budget actually enforced by every statistic in this panel: the
        # RELATION 2 * n_boot, which equals the frozen BOOT_MAX_ATTEMPTS only at
        # the production N_BOOT. Echoing the constant here at a non-default
        # n_boot would be a false statement in the provenance record.
        "boot_max_attempts": 2 * int(n_boot),
        "ci_level": float(ci_level),
        "ci_convention": CI_CONVENTION,
        "bootstrap_unit": "site",
        "min_sites_for_ci": int(min_sites),
        "weighting": WEIGHTING,
        "logit_eps": LOGIT_EPS,
        "irls": {
            "max_iter": IRLS_MAX_ITER,
            "tol": IRLS_TOL,
            "max_abs_coef": IRLS_MAX_ABS_COEF,
            "min_weight": IRLS_MIN_WEIGHT,
            "min_records": IRLS_MIN_RECORDS,
        },
        "round_dp": int(round_dp),
    }

    stamp = None if timestamp is None else str(timestamp)

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_utc": stamp,
        "input_digest": digest,
        "settings": settings,
        "counts": _emit(counts, round_dp),
        "reliability": _emit(reliability, round_dp),
        "calibration": _emit(calibration, round_dp),
        "ece": _emit(ece, round_dp),
        "brier": _emit(brier, round_dp),
        "skill": _emit(skill, round_dp),
        "composition": _emit(composition, round_dp),
        "notes": list(NOTES),
    }


# ===========================================================================
# certgate adapters (added by the port; not in srp)
# ===========================================================================


def panel_from_head(head, x, y, site_id, tau_star, *, answered_mask=None,
                    p_ref=None, **panel_kwargs) -> dict:
    """THE ONLY entry point the drivers use -- and the structural close of the
    ``predict_proba`` / ``score`` conflation trap.

    ::

        p        = head.predict_proba(x)          <- the BINNED quantity, P(y=1|x)
        answered = head.score(x) >= tau_star      <- the GATE, max(p1, 1-p1)

    The caller NEVER constructs ``p``. Feeding ``score`` as ``p`` passes
    ``validate_inputs`` silently -- it is finite and in [0, 1] -- and produces a
    fully populated but meaningless panel (the four bins below 0.5 are empty and
    the calibration slope is inverted). There is no automatic guard inside the
    statistics, so the guard is structural here.

    ``head`` is reached only by DUCK TYPING: this module has no certgate import
    and never sees a ``Head`` type.

    Parameters
    ----------
    x
        ``(n, d)`` float64 RAW features (the head standardizes internally).
    tau_star
        The RAW operative tau, or ``None`` for the legal no-rung-certified case.
    answered_mask
        The mask actually DEPLOYED, e.g. ``report["answered_mask"]``. When it is
        supplied AND ``tau_star`` is not ``None`` the two are cross-checked with
        ``np.array_equal``; a mismatch raises ``PanelError`` with
        ``reason=deployed-mask-mismatch``. That is what catches a mask re-derived
        from a tau ROUNDED to 6 dp: it disagrees with the deployed one at the
        boundary. With ``tau_star=None`` the supplied mask is used as given, the
        answered scope is empty, and every answered statistic emits ``None`` with
        ``ci_status = 'undefined-point'``.
    """
    x = np.asarray(x, dtype=np.float64)
    p = np.asarray(head.predict_proba(x), dtype=np.float64)

    gate = None
    if tau_star is not None:
        gate = np.asarray(np.asarray(head.score(x), dtype=np.float64)
                          >= float(tau_star)).astype(bool)

    if answered_mask is None:
        if gate is None:
            raise PanelError(
                "panel_from_head: tau_star is None and no answered_mask was supplied "
                "-- with no rung certified the caller must pass the deployed (all-False) "
                "mask explicitly; the panel will not invent a gate "
                "(reason=no-gate-supplied)")
        answered = gate
    else:
        answered = np.asarray(answered_mask)
        if answered.dtype != np.bool_:
            raise PanelError(
                f"panel_from_head: answered_mask has dtype {answered.dtype!r}, not bool "
                f"-- the deployed mask is a boolean per record and is never coerced "
                f"(reason=answered-mask-not-bool)")
        if gate is not None and not np.array_equal(answered, gate):
            n_bad = int(np.count_nonzero(answered != gate))
            raise PanelError(
                f"panel_from_head: supplied answered_mask disagrees with "
                f"head.score(x) >= tau_star at {n_bad} records -- a mask re-derived from "
                f"a ROUNDED tau disagrees with the deployed one at the boundary; pass "
                f"the RAW operative tau (reason=deployed-mask-mismatch)")

    return selective_reliability_panel(
        p, answered, site_id, y, p_ref, **panel_kwargs)


# The CSV field list for panel_reliability_rows, in emitted order.
PANEL_RELIABILITY_FIELDS = ("scope", "index", "lo", "hi", "n", "n_sites_carrying",
                            "mean_predicted", "observed", "ci_lo", "ci_hi",
                            "ci_status", "n_boot_valid", "n_attempts")


def panel_reliability_rows(panel: dict) -> list:
    """Flatten ``reliability.{answered, declined}`` to CSV rows.

    ``ci`` becomes ``ci_lo`` / ``ci_hi``; a ``None`` stays ``None`` and the
    drivers' ``_write_csv`` / ``_write_table`` projection turns it into a BLANK
    CELL. Exactly ``2 * n_bins`` rows.
    """
    rows = []
    for scope in ("answered", "declined"):
        for record in panel["reliability"][scope]:
            ci = record.get("ci")
            rows.append({
                "scope": scope,
                "index": record["index"],
                "lo": record["lo"],
                "hi": record["hi"],
                "n": record["n"],
                "n_sites_carrying": record["n_sites_carrying"],
                "mean_predicted": record["mean_predicted"],
                "observed": record["observed"],
                "ci_lo": None if ci is None else ci["lo"],
                "ci_hi": None if ci is None else ci["hi"],
                "ci_status": record["ci_status"],
                "n_boot_valid": record["n_boot_valid"],
                "n_attempts": record["n_attempts"],
            })
    return rows


# The two scopes the reliability curve is drawn for, in emitted order. `all` is
# deliberately absent: reliability/ece/calibration are answered+declined only.
PANEL_CURVE_SCOPES = ("answered", "declined")


def panel_ci_halfwidths(point, ci, ci_status="ok") -> tuple:
    """``(lo, hi)`` error-bar half-widths around ``point``, CLAMPED at ``0.0``.

    THE reason this is a named function and not two inline subtractions: a
    percentile interval is NOT required to straddle its own point estimate.
    ``site_bootstrap_ci`` quantiles the resampling distribution and makes no
    such guarantee, and for a paired ratio-of-sums over a few dozen sites
    (``brier.reference.brier_difference`` most of all) the point estimate can
    fall outside its own interval. matplotlib RAISES
    ``ValueError: 'yerr' must not contain negative values`` rather than
    warning, so an unclamped half-width lets a DESCRIPTIVE figure abort a
    certified run after every certification arm has already been paid for --
    the exact failure mode RP-8's guard around the panel computation exists to
    prevent, one layer further out.

    ``(0.0, 0.0)`` -- an interval-free marker, never a fabricated zero-width
    interval -- whenever ``ci`` is absent or ``ci_status`` is not ``'ok'``.
    """
    if ci is None or ci_status != "ok" or point is None:
        return (0.0, 0.0)
    return (max(float(point) - float(ci["lo"]), 0.0),
            max(float(ci["hi"]) - float(point), 0.0))


def panel_reliability_series(panel: dict, scope: str) -> tuple:
    """The plottable ``(xs, ys, lo, hi)`` series for one scope's curve.

    ONE definition of the drawing contract, shared by every figure built from a
    panel (``run_synthetic._e6_reliability_figure``,
    ``run_eicu._reliability_figure``) so that a fix to one can no longer leave
    the other behind:

      * an EMPTY bin is ABSENT from the series, never plotted as a zero -- a bin
        the scope never reached and a bin whose observed rate is 0 are different
        facts;
      * an interval is drawn only when its ``ci_status`` is ``'ok'``;
      * the half-widths go through ``panel_ci_halfwidths``, so they can never be
        negative.

    Returns four equal-length lists, all empty when the scope reaches no bin
    (the legal all-answered / all-declined shapes).
    """
    xs, ys, lo, hi = [], [], [], []
    for rec in panel["reliability"][scope]:
        if rec["mean_predicted"] is None or rec["observed"] is None:
            continue                       # empty bin: absent, never a zero
        xs.append(rec["mean_predicted"])
        ys.append(rec["observed"])
        d_lo, d_hi = panel_ci_halfwidths(rec["observed"], rec.get("ci"),
                                         rec["ci_status"])
        lo.append(d_lo)
        hi.append(d_hi)
    return xs, ys, lo, hi


def panel_headline(panel: dict) -> dict:
    """The scalars a summary block carries.

    Values are ALREADY rounded to ``ROUND_DP`` by the emit pass -- callers must
    NOT round again (the round-once invariant; a second pass makes the last
    decimal irreproducible).
    """
    reference = panel["brier"]["reference"]
    return {
        "ece_answered": panel["ece"]["answered"]["ece"],
        "ece_declined": panel["ece"]["declined"]["ece"],
        "calibration_slope_answered": panel["calibration"]["answered"]["slope"],
        "calibration_status_answered": panel["calibration"]["answered"]["status"],
        "brier_answered": panel["brier"]["primary_answered"]["value"],
        "brier_difference_vs_reference": (
            None if reference is None else reference["brier_difference"]),
        "skill_margin_answered": panel["skill"]["answered"]["skill_margin"],
        "skill_margin_answered_minus_all": (
            panel["skill"]["contrast"]["answered_minus_all"]),
        "coverage": panel["counts"]["coverage"],
    }
