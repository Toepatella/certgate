"""SPEC section "report.py": tiered report, guarantee text, provenance.

Every number carries a tier tag -- ``certified`` / ``estimated`` /
``diagnostic`` -- so the guarantee is never confused with an estimate
(METHODS sections 3, 6, 7). The decline partition splits the target pool
exactly once and asserts its parts sum to ``n_target``. Guarantee text is a
verbatim obligation (audit F01/F02, corrected by audit V1/V3/V13/V27): the
POPULATION-AVERAGE estimand with the mandatory between-site-dispersion clause,
the explicit "not a realized-error-count bound" clause, the baseline-only
shared ``1-delta`` event, the operative-rung selection clause, the
tagged-assumption wording, the concept/combined-shift out-of-scope disclosure,
and -- for BBSE rows -- the four-parameter box with its bootstrap caveat.
``tests/test_report.py`` freezes the exact emitted string.
"""

import datetime
import hashlib
import importlib.metadata
import platform

import numpy as np

from certgate.constants import (SEED, ALPHA_LADDER, BBSE_DELTA_CONF, DELTA,
                                M_INFLUENCE, TAU_GRID)
from certgate.certify import margin_floor
from certgate.explain import composition, cohort_abstention_profile

_PACKAGES = ("numpy", "scipy", "scikit-learn")
_ASSUMPTION = {"baseline": "exchangeability", "bbse": "label shift"}


def provenance(seed=SEED, **arrays_and_meta) -> dict:
    """Reproducibility block for one run (SPEC report.py; audit F49).

    Records package versions (``numpy``, ``scipy``, ``scikit-learn`` via
    ``importlib.metadata``), the Python version, the protocol ``SEED``, a
    sha256 content hash of every ndarray keyword, any scalar metadata, and a
    UTC timestamp. The timestamp is intentionally the only non-deterministic
    field, so callers comparing runs for determinism must exclude it.
    """
    versions = {}
    for pkg in _PACKAGES:
        try:
            versions[pkg] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:      # pragma: no cover
            versions[pkg] = "unknown"
    input_hashes, meta = {}, {}
    for name, obj in arrays_and_meta.items():
        if isinstance(obj, np.ndarray):
            # the digest binds dtype and shape as well as content (audit V11):
            # a reshaped or transposed matrix must not be provenance-identical
            # to the original.
            arr = np.ascontiguousarray(obj)
            h = hashlib.sha256()
            h.update(arr.dtype.str.encode())
            h.update(repr(arr.shape).encode())
            h.update(arr.tobytes())
            input_hashes[name] = h.hexdigest()
        else:
            meta[name] = obj
    return {
        "python": platform.python_version(),
        "packages": versions,
        "seed": int(seed),
        "input_hashes": input_hashes,
        "meta": meta,
        "timestamp_utc": datetime.datetime.now(
            datetime.timezone.utc).isoformat(),
    }


def _statement(alpha: float, modes) -> str:
    """Verbatim guarantee text for a certified row (SPEC report.py; audit
    F01/F02, corrected by audit V1/V3/V13/V27 -- the exact string is frozen by
    ``tests/test_report.py``; any silent weakening of a clause fails there).
    """
    assumption = " or ".join(_ASSUMPTION[m] for m in modes)
    # V1 + verification G-1/G-3: the certified estimand and the probability
    # attribution are MODE-DEPENDENT. Baseline certifies the unweighted risk
    # over the calibration site population (probability over the calibration
    # draw); BBSE certifies the rho-REWEIGHTED risk -- the population risk at
    # the target class prevalence -- and its probability is over the joint
    # draw (calibration sites, S_aux split, target pool). Naming the
    # calibration-population unweighted risk on a BBSE row emitted a
    # demonstrably false certificate under a downward prevalence shift (G-1).
    if "bbse" in modes and "baseline" in modes:
        head_clause = (
            f"With confidence >= {1.0 - DELTA:.2f}, the M={M_INFLUENCE} "
            f"influence-weighted answered-set risk is <= {alpha} under the "
            f"tagged assumption ({assumption}): under exchangeability this is "
            f"the risk averaged over the population of sites from which the "
            f"calibration sites were drawn (probability over the calibration "
            f"draw); under label shift it is that population risk reweighted "
            f"to the target class prevalence identified by the BBSE "
            f"correction (probability over the joint draw of the calibration "
            f"sites, the auxiliary split and the target pool).")
    elif "bbse" in modes:
        head_clause = (
            f"Under the tagged assumption ({assumption}), with probability "
            f">= {1.0 - DELTA:.2f} over the joint draw of the calibration "
            f"sites, the auxiliary split and the target pool, the "
            f"M={M_INFLUENCE} influence-weighted answered-set risk, averaged "
            f"over the site population and reweighted to the target class "
            f"prevalence identified by the BBSE correction, is <= {alpha}.")
    else:
        head_clause = (
            f"Under the tagged assumption ({assumption}), with probability "
            f">= {1.0 - DELTA:.2f} over the draw of calibration sites, the "
            f"M={M_INFLUENCE} influence-weighted answered-set risk, averaged "
            f"over the population of sites from which the calibration sites "
            f"were drawn, is <= {alpha}.")
    parts = [
        head_clause,
        # V1: mandatory dispersion clause, same force as the binomial clause.
        "This bounds a site-population average, NOT any individual site's "
        "answered error rate: under between-site heterogeneity individual "
        "sites can exceed alpha while the average stays within budget, at a "
        "rate this certificate does not measure or bound.",
        "It is NOT a bound on this batch's realized error count, which exceeds "
        "alpha at binomial-dispersion rates even under a valid certificate.",
    ]
    if "bbse" not in modes:
        # V3, narrowed per verification G-7: what is shared is the certified
        # THRESHOLDS (coverage/diagnostics remain target-dependent). True only
        # because the baseline permutation stream is target-label-free; BBSE
        # fits depend on the target pool through the q_t interval, so no
        # shared event exists there and the clause is omitted whenever BBSE
        # covers the row.
        parts.append(
            "In the exchangeable mode the certified thresholds are a function "
            f"of the calibration draw alone -- one 1-{DELTA:.2f} event shared "
            f"by every target pool the certificate is applied to.")
    parts.append(
        # V27: the operative rung is a data-driven selection over the ladder.
        f"The operative rung is the strictest certified alpha, a data-driven "
        f"selection over the {{{ALPHA_LADDER[0]}, {ALPHA_LADDER[1]}}} ladder; "
        f"the selected claim holds jointly at probability "
        f">= {1.0 - len(ALPHA_LADDER) * DELTA:.2f}.")
    parts.append(
        "Concept shift and combined shift are OUT OF SCOPE and undetectable "
        "from unlabeled data -- the certificate is void there.")
    if "bbse" in modes:
        # V2/V13: four estimated parameters; the old "single non-finite-sample
        # step" claim was false while q_t went unbudgeted.
        parts.append(
            "The [rho_lo, rho_hi] box covers FOUR estimated parameters "
            f"(c0, c1, pi_source, q_target) at Bonferroni "
            f"delta_conf={BBSE_DELTA_CONF}, spent over the auxiliary (S_aux) "
            "site split and the target pool, not the calibration draw named "
            "above. The (c0, c1, pi_source) intervals are percentile cluster "
            "bootstraps -- asymptotic, with realized joint coverage at small "
            "cluster counts measurably below nominal (see METHODS); the "
            "q_target interval is finite-sample Clopper-Pearson for "
            "single-site pools and a cluster bootstrap for multi-site pools.")
    return " ".join(parts)


def _bootstrap_estimate(head, cal, tau, weights=None, n_boot=500, seed=SEED,
                        max_attempts=None):
    """Estimated-tier answered-set risk at ``tau`` (SPEC report.py; v1 report.py:14-35).

    Point estimate plus a cluster bootstrap over S_cal sites, weighted under
    the deploy mode when weights are supplied. This is an ESTIMATE of the
    (re-weighted) target risk, never the certified guarantee -- so it is
    labelled with the weighting it used.

    Resampling discipline (audit V21, mirroring shift.py's audit-F40/B-8
    rule): resamples with zero answered mass are topped up rather than
    silently dropped -- quantiling over a reduced count keeps only the
    high-mass resamples and biases the interval. If ``n_boot`` valid resamples
    cannot be collected within ``2 * n_boot`` attempts, the CI is NaN, never a
    quantile over fewer draws. An empty answered set yields a NaN point, never
    0.0.
    """
    rng = np.random.default_rng(seed)
    score = head.score(cal.x)
    err = head.predict(cal.x) != cal.y
    ans = score >= tau
    w = np.ones(cal.n, dtype=np.float64) if weights is None else np.asarray(
        weights, dtype=np.float64)
    n_sites = cal.n_sites
    num = np.bincount(cal.site_id, weights=w * ans * err, minlength=n_sites)
    den = np.bincount(cal.site_id, weights=w * ans, minlength=n_sites)
    total_den = den.sum()
    point = float(num.sum() / total_den) if total_den > 0 else float("nan")
    draws = []
    n_attempts = 0
    if max_attempts is None:
        max_attempts = 2 * n_boot
    while len(draws) < n_boot and n_attempts < max_attempts:
        idx = rng.integers(0, n_sites, n_sites)
        n_attempts += 1
        d = den[idx].sum()
        if d > 0:
            draws.append(num[idx].sum() / d)
    if len(draws) >= n_boot:
        lo, hi = (float(v) for v in np.quantile(draws, [0.025, 0.975]))
    else:                                # top-up failed: NaN, never a reduced
        lo = hi = float("nan")           # -count quantile (audit V21)
    return dict(tier="estimated", point=point, ci95=(lo, hi),
                n_boot=len(draws), n_attempts=n_attempts)


def _rm_vs_unweighted(head, cal, tau, weights=None) -> dict:
    """Influence-weighted risk R_M vs the plain record-mean risk (audit F26).

    Reveals when the M-cap is masking a heavy-tail: a large positive gap means
    the influence weighting is catching bad news that an unweighted read hides.
    """
    score = head.score(cal.x)
    err = (head.predict(cal.x) != cal.y).astype(np.float64)
    ans = (score >= tau).astype(np.float64)
    sizes = cal.site_sizes.astype(np.float64)
    per_site_infl = np.where(sizes > 0,
                             np.minimum(sizes, M_INFLUENCE)
                             / np.maximum(sizes, 1.0), 0.0)
    infl = per_site_infl[cal.site_id]
    w = np.ones(cal.n, dtype=np.float64) if weights is None else np.asarray(
        weights, dtype=np.float64)
    num = float(np.sum(infl * ans * err * w))
    den = float(np.sum(infl * ans * w))
    r_m = num / den if den > 0 else float("nan")
    ans_bool = score >= tau
    unweighted = float(err[ans_bool].mean()) if ans_bool.any() else float("nan")
    return dict(r_m=r_m, unweighted_risk=unweighted, gap=r_m - unweighted)


def _capped_influence_share(cal) -> float:
    """Fraction of records whose realized contribution is capped by M (audit F26)."""
    sizes = cal.site_sizes.astype(np.float64)
    excess = np.maximum(sizes - M_INFLUENCE, 0.0).sum()
    total = sizes.sum()
    return float(excess / total) if total > 0 else 0.0


def _combine_alpha(mode_results_alpha: dict) -> dict:
    """OR-combine baseline and BBSE for one alpha (SPEC pipeline step 6; v1 M1).

    Deploy the most conservative certified threshold (max tau across modes),
    then list only the modes that certified that exact threshold index -- the
    OR-guarantee "if either tagged assumption holds" rests on the modes that
    actually back the deployed tau.

    Certified rows additionally carry ``mode_outcomes`` (fixture audit
    2026-07-25): {mode: "covering" | "certified-not-covering" | <decline
    reason>}, so a certified row still records why the non-deploying mode did
    not contribute -- on real data, BBSE silently not contributing is the
    interesting signal, and it was previously unrecoverable from the report.
    """
    cert = {m: r for m, r in mode_results_alpha.items()
            if r.get("tau_idx") is not None}
    if not cert:
        return dict(status="declined",
                    reasons={m: r.get("reason")
                             for m, r in mode_results_alpha.items()})
    deploy = max(cert, key=lambda m: cert[m]["tau"])
    didx = cert[deploy]["tau_idx"]
    covered = sorted(m for m, r in cert.items() if didx in r["certified"])
    outcomes = {}
    for m, r in mode_results_alpha.items():
        if r.get("tau_idx") is None:
            outcomes[m] = r.get("reason") or "declined"
        elif didx in r["certified"]:
            outcomes[m] = "covering"
        else:
            outcomes[m] = "certified-not-covering"
    return dict(status="certified", tau=float(TAU_GRID[didx]), tau_idx=int(didx),
                deploy_mode=deploy, modes=covered, mode_outcomes=outcomes)


def build_report(*, target_label, head, cal, target_x, mode_results,
                 feasibility, bbse_fit, provenance_block,
                 oracle_y=None, gate_reason=None,
                 target_site_id_supplied=False) -> dict:
    """Assemble the full tiered report for one target pool (SPEC report.py).

    ``mode_results`` maps ``alpha -> {"baseline": r, "bbse": r}`` where each
    ``r`` has ``certified`` (list of tau indices), ``tau_idx``, ``tau`` and
    ``reason``. ``gate_reason`` (``"insufficient-clusters"`` | ``"pool-too-small"``)
    short-circuits to an all-declined report whose partition puts every target
    record in the gate bucket.
    """
    target_x = np.asarray(target_x, dtype=np.float64)
    n_target = int(target_x.shape[0])
    n_cal = int(cal.n_sites)
    n_carrying = int((cal.site_sizes > 0).sum())

    # ---- gated exits (record-carrying cluster gate / target-pool floor) ----
    if gate_reason is not None:
        partition = _partition(n_target, 0, 0, gate_reason)
        # same diagnostic key set as a full report (audit V25): a consumer
        # indexing a gated report must get None, not KeyError. Only
        # capped_influence_share is computable without a head -- so compute it.
        diagnostic = dict(tier="diagnostic", n_target=n_target, coverage=0.0,
                          n_cal=n_cal, n_cal_carrying=n_carrying,
                          feasibility=feasibility, gate_reason=gate_reason,
                          capped_influence_share=_capped_influence_share(cal),
                          rm_vs_unweighted=None, composition=None,
                          abstention_profile=None, bbse=None,
                          target_site_id_supplied=bool(target_site_id_supplied))
        return dict(target_label=str(target_label), reason=gate_reason,
                    certified=[], operative=None, estimated=None,
                    diagnostic=diagnostic, decline_partition=partition,
                    answered_mask=np.zeros(n_target, dtype=bool),
                    provenance=provenance_block)

    score_t = head.score(target_x)

    # ---- certified tier: one row per alpha, OR-combined across modes ----
    certified_tier, operative = [], None
    # iterate only the rungs actually certified this run (caller may pass a
    # subset of the ladder), preserving ladder order (strictest first)
    for alpha in (a for a in ALPHA_LADDER if a in mode_results):
        combined = _combine_alpha(mode_results[alpha])
        row = dict(alpha=float(alpha), tier="certified", **combined)
        if combined["status"] == "certified":
            row["coverage"] = float((score_t >= combined["tau"]).mean())
            row["statement"] = _statement(alpha, combined["modes"])
            if operative is None:            # strictest (first) certified alpha
                operative = dict(alpha=float(alpha), tau=combined["tau"],
                                 tau_idx=combined["tau_idx"],
                                 deploy_mode=combined["deploy_mode"],
                                 modes=combined["modes"])
        certified_tier.append(row)

    # ---- answered mask + decline partition at the operative rung ----
    if operative is not None:
        answered = score_t >= operative["tau"]
        partition = _partition(n_target, int(answered.sum()),
                               int((~answered).sum()), None)
    else:
        answered = np.zeros(n_target, dtype=bool)
        partition = _partition(n_target, 0, 0, "failsafe")

    # ---- estimated tier (deploy-mode-weighted cluster bootstrap on S_cal) ----
    estimated = None
    if operative is not None:
        weights = None
        if operative["deploy_mode"] == "bbse" and not bbse_fit.declined:
            weights = np.where(cal.y, bbse_fit.rho_point, 1.0)
        estimated = _bootstrap_estimate(head, cal, operative["tau"],
                                        weights=weights)
        estimated["weighting"] = operative["deploy_mode"]

    # ---- diagnostic tier ----
    if operative is not None:
        w_dep = None
        if operative["deploy_mode"] == "bbse" and not bbse_fit.declined:
            w_dep = np.where(cal.y, bbse_fit.rho_point, 1.0)
        rm_gap = _rm_vs_unweighted(head, cal, operative["tau"], weights=w_dep)
    else:
        rm_gap = None
    # the BBSE-implied composition view is an ESTIMATED quantity, not part of
    # the certificate: supply rho_point whenever the fit did not decline,
    # regardless of which mode won deployment (verification N5 -- gating it on
    # deploy_mode silently degraded the documented three-way composition to
    # two-way everywhere BBSE fits but loses the OR-combination).
    rho_pt = bbse_fit.rho_point if not bbse_fit.declined else None

    comp = composition(head, target_x, answered, rho_point=rho_pt,
                       oracle_y=oracle_y)
    abst = cohort_abstention_profile(head, target_x, answered)

    diagnostic = dict(
        tier="diagnostic",
        n_target=n_target,
        coverage=float(answered.mean()) if n_target else 0.0,
        n_cal=n_cal,
        n_cal_carrying=n_carrying,
        feasibility=feasibility,                       # floor@n_carrying, per rung
        capped_influence_share=_capped_influence_share(cal),
        rm_vs_unweighted=rm_gap,
        composition=comp,
        abstention_profile=abst,
        bbse=bbse_fit.diagnostics,
        # a report whose record-level target identity was never checked must
        # be distinguishable from one whose was (verification F4)
        target_site_id_supplied=bool(target_site_id_supplied),
    )

    return dict(target_label=str(target_label), reason=None,
                certified=certified_tier, operative=operative,
                estimated=estimated, diagnostic=diagnostic,
                decline_partition=partition, answered_mask=answered,
                provenance=provenance_block)


def _partition(n_target, answered, below_tau, structural_reason) -> dict:
    """Exact decline partition (SPEC report.py). Keys always present; exactly
    one structural bucket is populated. Asserts the parts sum to ``n_target``."""
    part = {"answered": 0, "below_tau": 0, "failsafe": 0,
            "pool-too-small": 0, "insufficient-clusters": 0}
    if structural_reason is not None:
        part[structural_reason] = int(n_target)
    else:
        part["answered"] = int(answered)
        part["below_tau"] = int(below_tau)
    assert sum(part.values()) == int(n_target), \
        "decline partition must sum to n_target"
    return part


def render_text(report: dict) -> str:
    """Human-readable one-block summary of a report object (SPEC report.py)."""
    lines = [f"=== target {report['target_label']} ==="]
    if report.get("reason"):
        lines.append(f"  [gate] {report['reason']} "
                     f"(n_cal_carrying="
                     f"{report['diagnostic'].get('n_cal_carrying')})")
    for row in report["certified"]:
        if row["status"] == "certified":
            lines.append(
                f"  [certified] alpha={row['alpha']:.2f}: tau={row['tau']:.3f} "
                f"via {row['deploy_mode']} (modes {','.join(row['modes'])}, "
                f"coverage {row['coverage']:.2f})")
        else:
            rs = ",".join(f"{m}:{r}" for m, r in row["reasons"].items())
            lines.append(f"  [declined ] alpha={row['alpha']:.2f}: {rs}")
    if report.get("estimated"):
        e = report["estimated"]
        lines.append(
            f"  [estimated] answered-set risk ({e['weighting']}-weighted) "
            f"{e['point']:.4f} (95% cluster-bootstrap "
            f"{e['ci95'][0]:.4f}-{e['ci95'][1]:.4f}, n_boot={e['n_boot']})")
    d = report["diagnostic"]
    lines.append(f"  [diagnostic] coverage {d['coverage']:.2f}, "
                 f"n_cal_carrying {d['n_cal_carrying']}")
    db = report["decline_partition"]
    # "[partition]" not "[declines]": the dict includes the ANSWERED count, and
    # on a certified report the old label read as N declines (fixture audit
    # 2026-07-25)
    lines.append("  [partition] " + ", ".join(f"{k} {v}" for k, v in db.items()))
    return "\n".join(lines)
