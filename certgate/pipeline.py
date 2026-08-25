"""run_certgate orchestration (SPEC "pipeline.py"; METHODS 1-7).

One entry point wires together the data-discipline assertions, the frozen head,
the S_aux ordering and feasibility diagnostics, the per-alpha baseline and BBSE
certification walks, the OR-combination, and the tiered report.

S_cal reaches the certified path only through the certification walks. The
estimated and diagnostic tiers read it downstream without feedback (METHODS 2).

The order of the loud gates matches the SPEC exactly:
  1.  site-disjointness of (train, aux, cal)                       (audit F03)
  2.  finite target features                                       (audit F36)
  2b. feature-column alignment: target_x 2-D & width == train.d    (real-data)
  3.  record-carrying calibration-cluster floor                    (audit B-5)
  4.  registered target-pool floor                                 (audit B-6)
Nothing is fitted until all of them pass.
"""

import hashlib

import numpy as np

from certgate.constants import (SEED, ALPHA_LADDER, DELTA, M_INFLUENCE,
                                TAU_GRID, MIN_CAL_CLUSTERS, MIN_ANSWERABLE,
                                MODE_BASELINE, MODE_BBSE)
from certgate.validate import (Cohort, CohortError, assert_site_disjoint,
                               densify_sites, normalized_label)
from certgate.model import fit_head
from certgate.certify import (influence_atoms, walk_order, margin_floor,
                              fixed_sequence_walk, certification_rng)
from certgate.shift import (BBSEFit, bbse_diagnostics, fit_bbse,
                            certify_bbse)
from certgate.report import build_report, provenance


def _feasibility(head, aux, alpha, n_carrying) -> dict:
    """Feasibility diagnostic for one alpha. Never a gate.

      - margin: the best record-weighted certification margin achievable on
        S_aux, cov*(alpha-risk)*E[g/M]
      - floor: the information floor at the true record-carrying calibration
        count
      - ratio: their quotient

    Refs: SPEC pipeline step 5; METHODS 4; audit F51.
    """
    score = head.score(aux.x)
    err = head.predict(aux.x) != aux.y
    sizes = aux.site_sizes.astype(np.float64)
    e_g_over_m = float(np.mean(np.minimum(sizes, M_INFLUENCE) / M_INFLUENCE))
    # best stays None (JSON null) until some threshold attains coverage. A -inf
    # sentinel is not strict-JSON serialisable and reads as a very bad but real
    # margin (audit V16).
    best = None
    for tau in TAU_GRID:
        ans = score >= tau
        cov = float(ans.mean())
        if cov == 0.0:
            continue
        risk = float(err[ans].mean())
        cand = cov * (alpha - risk) * e_g_over_m
        best = cand if best is None else max(best, cand)
    floor = float(margin_floor(n_carrying, DELTA, alpha)) if n_carrying > 0 \
        else None
    ratio = (float(best / floor) if (best is not None and floor is not None
                                     and floor > 0) else None)
    return dict(margin=(None if best is None else float(best)),
                floor=floor, ratio=ratio)


def _baseline_walk(head, cal, order, alpha) -> dict:
    """Baseline (exchangeable) certification walk for one alpha at full DELTA.

    The permutation stream is target-label-free (audit V3). Baseline atoms are
    target-independent, so one calibration draw yields one certificate shared
    by every target pool it is applied to. That is what makes the
    shared-1-delta-event clause in the guarantee text true.
    """
    score = head.score(cal.x)
    err = head.predict(cal.x) != cal.y
    atoms = influence_atoms(score, err, cal.site_id, cal.n_sites, TAU_GRID,
                            alpha, M_INFLUENCE)
    rng = certification_rng(alpha, MODE_BASELINE)
    certified, deployed = fixed_sequence_walk(atoms, order, alpha, DELTA,
                                              TAU_GRID, rng=rng)
    return dict(certified=certified,
                tau_idx=deployed,
                tau=(None if deployed is None else float(TAU_GRID[deployed])),
                reason=(None if deployed is not None else "failsafe"))


def _bbse_seed_rng(target_x, dense_target_sites=None):
    """Deterministic Generator for the BBSE cluster bootstrap.

    Seeded from a sha256 of the target data -- dtype, shape and bytes of
    target_x, plus the dense target site partition when supplied. Distinct
    pools get distinct draws; byte-identical pools get byte-identical fits.

    Never the free-text target label. Label-seeding moved the deployed
    threshold and the answered set under a cosmetic respelling of the same
    bytes.

    Refs: SPEC determinism; verification G-2.
    """
    h = hashlib.sha256()
    arr = np.ascontiguousarray(target_x)
    h.update(arr.dtype.str.encode())
    h.update(repr(arr.shape).encode())
    h.update(arr.tobytes())
    if dense_target_sites is not None:
        sid = np.ascontiguousarray(dense_target_sites)
        h.update(sid.dtype.str.encode())
        h.update(repr(sid.shape).encode())
        h.update(sid.tobytes())
    d = h.digest()
    return np.random.default_rng(np.random.SeedSequence(
        [SEED, MODE_BBSE, int.from_bytes(d[:4], "big"),
         int.from_bytes(d[4:8], "big")]))


def run_certgate(train, aux, cal, target_x, *, target_label="target",
                 target_site_id=None, alphas=ALPHA_LADDER,
                 oracle_target_y=None, modes=("baseline", "bbse")) -> dict:
    """Certify a target pool end to end and return the tiered report (SPEC).

      - modes: the assumption modes to run, OR-combined per alpha
      - target_site_id: per-record raw site labels for a multi-site pool,
        feeding the BBSE q_t interval and the disjointness assertion. None
        declares a single-site pool
      - oracle_target_y: harness only, feeds the diagnostic composition

    A gated exit -- insufficient-clusters or pool-too-small -- still returns a
    full report carrying the reason and an all-declined partition.
    """
    modes = tuple(modes)
    alphas = tuple(alphas)
    bad = [a for a in alphas if a not in ALPHA_LADDER]
    if bad or not alphas:
        raise ValueError(
            f"run_certgate: alphas must be a non-empty subset of the frozen "
            f"ladder {ALPHA_LADDER}, got {alphas} (reason=alpha-not-in-ladder)")
    # 0. loud boundary validation (audits V18, V19, V23).
    bad_modes = [m for m in modes if m not in ("baseline", "bbse")]
    if bad_modes or not modes:
        raise ValueError(
            f"run_certgate: modes must be a non-empty subset of "
            f"('baseline', 'bbse'), got {modes} (reason=unknown-mode) -- a "
            f"misspelled mode must never yield an all-declined report "
            f"indistinguishable from a statistical decline")
    for name, coh in (("train", train), ("aux", aux), ("cal", cal)):
        if not (bool(coh.y.any()) and bool((~coh.y).any())):
            raise CohortError(
                f"run_certgate: fitting cohort {name!r} contains a single "
                f"class -- the require_both_classes=False relaxation is "
                f"sanctioned for TARGET pools only (reason=single-class-"
                f"fitting-cohort)")
    # target_x must be a feature matrix, not a Cohort -- the natural mistake,
    # since the other three arguments are Cohorts. Raise a typed error naming
    # target.x, not a raw numpy TypeError (fixture audit 2026-07-25).
    if isinstance(target_x, Cohort):
        raise ValueError(
            "run_certgate: target_x must be the raw feature matrix, not a "
            "Cohort -- pass target.x (and its per-record raw site labels as "
            "target_site_id) (reason=target-is-cohort)")
    try:
        target_x = np.asarray(target_x, dtype=np.float64)
    except (TypeError, ValueError) as e:
        raise ValueError(
            "run_certgate: target_x is not convertible to a float64 feature "
            "matrix (reason=target-not-numeric)") from e
    n_target_rows = int(target_x.shape[0]) if target_x.ndim >= 1 else 0
    if oracle_target_y is not None:
        oy = np.asarray(oracle_target_y)
        if oy.ndim != 1 or oy.dtype.kind != "b" or oy.shape[0] != n_target_rows:
            raise ValueError(
                f"run_certgate: oracle_target_y must be a 1-D bool array of "
                f"length {n_target_rows}, got ndim={oy.ndim} "
                f"dtype={oy.dtype} len={oy.shape[0] if oy.ndim else 0} "
                f"(reason=bad-oracle-labels) -- silent coercion fabricated "
                f"compositions (audit V19)")
        oracle_target_y = oy

    # 1. data discipline: S_train / S_aux / S_cal must be site-disjoint.
    assert_site_disjoint(train=train, aux=aux, cal=cal)

    # 1b. target disjointness. Two rules make it hold:
    #     - comparisons run under the same canonical, normalized form
    #       densify_sites uses; raw equality let 's-0000 ' and case variants
    #       slip through
    #     - target_site_id is length-checked here at the boundary, not only
    #       inside fit_bbse on the BBSE path
    #     A target whose own records sit in S_cal gets a threshold selected
    #     partly on itself. That is the leak F03 exists to prevent, on the one
    #     split F03 did not cover.
    #     Ref: audit V9; verification F2, F4, N3.
    norm_cohort_labels = {normalized_label(s): s
                          for s in (set(train.site_labels)
                                    | set(aux.site_labels)
                                    | set(cal.site_labels))}
    if normalized_label(target_label) in norm_cohort_labels:
        raise CohortError(
            f"run_certgate: target_label {str(target_label)!r} names a "
            f"train/aux/cal site "
            f"({norm_cohort_labels[normalized_label(target_label)]!r} under "
            f"the canonical normal form) -- the target pool must be "
            f"site-disjoint from every fitting and calibration split "
            f"(audit V9)")
    dense_target_sites = None
    target_site_labels = None
    if target_site_id is not None:
        sid_arr = np.asarray(target_site_id)
        if sid_arr.ndim != 1 or sid_arr.shape[0] != n_target_rows:
            raise CohortError(
                f"run_certgate: target_site_id must be 1-D with one entry per "
                f"target record ({n_target_rows}), got ndim="
                f"{sid_arr.ndim} len={sid_arr.shape[0] if sid_arr.ndim else 0} "
                f"(reason=bad-target-site-id) -- a partial column must never "
                f"satisfy the disjointness gate (verification F4/N3)")
        dense_target_sites, target_site_labels = densify_sites(target_site_id)
        overlap = {normalized_label(s) for s in target_site_labels} \
            & set(norm_cohort_labels)
        if overlap:
            raw = sorted(norm_cohort_labels[k] for k in overlap)
            raise CohortError(
                f"run_certgate: target sites {raw!r} appear in train/aux/cal "
                f"(compared under the canonical normal form) -- the target "
                f"pool must be site-disjoint from every fitting and "
                f"calibration split (audit V9)")

    # 2. finite target features (loud; audit F36).
    if not np.isfinite(target_x).all():
        raise ValueError(
            "run_certgate: target_x contains non-finite values "
            "(reason=nonfinite-features)")

    # 2b. feature-column alignment (real-data column discipline). The head is
    #     fit on train and then scores aux, cal and target_x. A width mismatch
    #     would otherwise surface deep inside head.score as an opaque numpy
    #     broadcast error, so gate it loudly here against train.d.
    d_train = train.d
    if target_x.ndim != 2 or target_x.shape[1] != d_train:
        raise ValueError(
            f"run_certgate: target_x must be 2-D with {d_train} feature columns "
            f"(train.d), got shape {tuple(target_x.shape)} "
            "(reason=feature-width-mismatch)")
    if aux.d != d_train or cal.d != d_train:
        raise ValueError(
            f"run_certgate: aux and cal feature width must match train.d={d_train}, "
            f"got aux.d={aux.d}, cal.d={cal.d} "
            "(reason=feature-width-mismatch)")

    # provenance binds every array the certificate depends on: x, y and the
    # site partition of all three cohorts, plus the target. Flipping one
    # calibration label must change the recorded hashes (audit V11).
    prov_arrays = dict(
        train_x=np.asarray(train.x), train_y=np.asarray(train.y),
        train_site_id=np.asarray(train.site_id),
        aux_x=np.asarray(aux.x), aux_y=np.asarray(aux.y),
        aux_site_id=np.asarray(aux.site_id),
        cal_x=np.asarray(cal.x), cal_y=np.asarray(cal.y),
        cal_site_id=np.asarray(cal.site_id),
        target_x=target_x)
    if dense_target_sites is not None:
        prov_arrays["target_site_id"] = dense_target_sites
        # two different labelings share the same dense array, so bind the
        # canonical labels too (verification F4)
        prov_arrays["target_site_labels"] = np.frombuffer(
            "\x00".join(target_site_labels).encode(), dtype=np.uint8)
    # the run configuration binds too, so two runs with different certified
    # tiers never share a byte-identical record (verification N8)
    prov = provenance(target_label=str(target_label),
                      modes=list(modes), alphas=[float(a) for a in alphas],
                      **prov_arrays)

    n_carrying = int((cal.site_sizes > 0).sum())
    # the not-run placeholder carries the same diagnostics key set as a real
    # fit, all None, so diagnostic['bbse'] indexes uniformly whatever modes
    # ran. Gated exits are the one exception: they emit diagnostic['bbse'] =
    # None wholesale, per audit V25's None-for-uncomputable rule.
    # Ref: fixture audit 2026-07-25.
    empty_bbse = BBSEFit(True, "not-run", float("nan"), float("nan"),
                         float("nan"), bbse_diagnostics(), {})

    # 3. record-carrying calibration-cluster floor: count only sites that
    #    actually carry records (audit B-5).
    if n_carrying < MIN_CAL_CLUSTERS:
        return build_report(target_label=target_label, head=None, cal=cal,
                            target_x=target_x, mode_results={},
                            feasibility={}, bbse_fit=empty_bbse,
                            provenance_block=prov,
                            oracle_y=oracle_target_y,
                            gate_reason="insufficient-clusters",
                            target_site_id_supplied=dense_target_sites is not None)

    # 4. registered target-pool floor (audit B-6).
    if n_target_rows < MIN_ANSWERABLE:
        return build_report(target_label=target_label, head=None, cal=cal,
                            target_x=target_x, mode_results={},
                            feasibility={}, bbse_fit=empty_bbse,
                            provenance_block=prov,
                            oracle_y=oracle_target_y,
                            gate_reason="pool-too-small",
                            target_site_id_supplied=dense_target_sites is not None)

    # 5. fit head; S_aux ordering + feasibility per alpha; fit BBSE once.
    head = fit_head(train)
    score_aux = head.score(aux.x)
    err_aux = head.predict(aux.x) != aux.y
    walk_orders, feasibility = {}, {}
    for alpha in alphas:
        atoms_aux = influence_atoms(score_aux, err_aux, aux.site_id,
                                    aux.n_sites, TAU_GRID, alpha, M_INFLUENCE)
        walk_orders[alpha] = walk_order(atoms_aux)
        # str(alpha) keys, "0.05" and "0.1", so a saved report JSON-round-trips
        # without json.dump silently stringifying float keys (fixture audit
        # 2026-07-25)
        feasibility[str(alpha)] = _feasibility(head, aux, alpha, n_carrying)

    run_bbse = "bbse" in modes
    if run_bbse:
        bbse_fit = fit_bbse(head, aux, target_x,
                            _bbse_seed_rng(target_x, dense_target_sites),
                            target_site_id=dense_target_sites)
    else:
        bbse_fit = empty_bbse

    # 6. per alpha: baseline walk + BBSE dual-endpoint walk.
    mode_results = {}
    for alpha in alphas:
        per = {}
        if "baseline" in modes:
            per["baseline"] = _baseline_walk(head, cal, walk_orders[alpha],
                                             alpha)
        if run_bbse:
            r = certify_bbse(head, bbse_fit, cal, alpha)
            per["bbse"] = dict(certified=r["certified"], tau_idx=r["tau_idx"],
                               tau=r["tau"], reason=r["reason"])
        mode_results[alpha] = per

    # 7. tiered report (operative rung + partition + explain artifacts inside).
    return build_report(target_label=target_label, head=head, cal=cal,
                        target_x=target_x, mode_results=mode_results,
                        feasibility=feasibility, bbse_fit=bbse_fit,
                        provenance_block=prov, oracle_y=oracle_target_y,
                        gate_reason=None,
                        target_site_id_supplied=dense_target_sites is not None)
