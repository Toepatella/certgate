"""Corrected eICU composition and exact S_aux atom margin, replayed per re-split.

Status: POST-HOC (2026-10-29). Nothing this file computes is a certified
quantity. No certificate, threshold, guarantee string or registered prediction
descends from it, and every released artifact it reads stays byte-frozen.

Two released eICU numbers were computed by formulas the 2026-10 mathematical
audit corrected, and neither can be corrected from the released artifacts
alone, because the inputs they need were never written out. This file
recomputes both from the restricted extract by replaying the released
primary arm.

1. The BBSE-implied answered positive fraction (audit BBSE-1, contract C1).
   The released composition re-weighted the head's posterior odds by
   rho_point = odds(pi_t)/odds(pi_s), where pi_s is the S_aux prevalence. The
   head is a logistic fit on S_train, so its odds carry the S_train prior and
   the correct multiplier is odds(pi_t)/odds(pi_train) =
   rho_point * odds(clip pi_s)/odds(pi_train). Here pi_train = train.y.mean()
   and pi_source = the fit's diagnostics "pi_s", which is what the fixed
   explain.composition computes. pi_train for the published split is in no
   released artifact. Each replicate's corrected value is reported beside the
   released one, and the released one is re-derived here and must equal
   EICU_diagnostics.json exactly.
2. The exact S_aux atom-unit certification margin (audit CORE-3).
   The released diagnostic.feasibility margin (pipeline._feasibility) is a
   record-pooled proxy: max_tau cov(tau)(alpha - risk(tau)) * mean_c(g_c/M).
   The atom-unit margin that walk_order ranks by is
   max_tau (alpha - mean_c Z_c(tau)), with Z_c the influence_atoms of S_aux.
   For alpha in ALPHA_LADDER each replicate reports the exact margin, the
   released proxy, the information floor margin_floor(n_carrying, DELTA,
   alpha) at the record-carrying calibration count, and both margin/floor
   ratios.

The replay is run_eicu.run_certification's pooled arm, call for call, on ONE
build from run_eicu._build_and_gate: etl.site_split(site_raw, replicate=r),
etl.impute on S_train, run_eicu._build_cohorts, fit_head(train) and
run_certgate(train, aux, cal, target.x, target_site_id=..., oracle_target_y=
target.y). No draw is made here. The streams are the replayed experiment's
own: the split from SeedSequence([SEED, EICU_SPLIT_NAMESPACE, r]) inside
etl.site_split, the BBSE bootstrap from pipeline._bbse_seed_rng (sha256 of
the target bytes), and the walks from certify.certification_rng. The per-
hospital arm, the leak probe, the panel and the figures consume no stream the
pooled arm reads, so they are left out.

Before anything is written the replay must reproduce the release exactly:

  * extract identity: run_eicu._data_sha(--data) must equal the data_sha in
    the released EICU_provenance.json (reason=extract-mismatch);
  * replicate 0, against EICU_certificate.json, by exact float equality: the
    operative alpha, tau*, tau_idx and deploy mode; diagnostic coverage,
    n_target, n_cal and n_cal_carrying; the BBSE rho_point and pi_s; the
    feasibility margin, floor and ratio for every alpha; the predicted, BBSE
    (released formula) and oracle composition fractions
    (reason=self-check-failed, raised as soon as replicate 0 is replayed);
  * every replicate, against EICU_diagnostics.json and EICU_pooled.csv: the
    BBSE rho_point and q_target, the composition_three_way row (alpha, tau,
    and all three fractions), and the pooled row's certified, tau, tau_idx,
    coverage, n_answered and n_cal_carrying cells (reason=replay-mismatch);
  * the report's own corrected composition must equal a direct
    explain.composition call with the two priors, and the report's
    feasibility must equal pipeline._feasibility recomputed here
    (reason=internal-mismatch).

Every write goes through run_eicu.assert_aggregate_only (the JSON via
run_eicu._write_json, the CSVs via run_eicu._write_table, the README
explicitly). No record-level array leaves memory. The script refuses the
frozen output directories.

Run (DUA holder, on the restricted extract):

    python -m experiments.eicu_composition_margin --data <DATA_DIR> --replicates 20

Optional: --out DIR (default experiments/out-eicu-composition/), --reference
DIR (the released run to reproduce; default experiments/out/), --quiet.

Writes EICU_composition_margin.json (with a _run block: UTC, git sha, sha256
of every released file read; plus the extract's data_sha and the sha256 of
each table file), EICU_composition_corrected.csv (one row per replicate),
EICU_margin_exact.csv (one row per replicate and alpha) and README.md.

Refs: audits 2026-10 BBSE-1 (composition-prior#L1#0, #L2#0) and CORE-3
(floor#L1#1); SPEC "explain.py", "pipeline.py"; METHODS 4.
"""

import argparse
import ast
import os
import re
import sys
import time

import numpy as np

from certgate.certify import influence_atoms, margin_floor, walk_order
from certgate.constants import (ALPHA_LADDER, DELTA, M_INFLUENCE, PI_CLIP,
                                SEED, TAU_GRID)
from certgate.explain import composition
from certgate.model import fit_head
from certgate.pipeline import _feasibility, run_certgate
from certgate.validate import CohortError
from experiments import eicu_etl as etl
from experiments import run_eicu as re_
from experiments.derive_fixpass_numbers import (EXP_DIR, assert_not_frozen,
                                                run_block, sha256_file,
                                                _read_csv, _read_json)

OUT_DIR = os.path.join(EXP_DIR, "out-eicu-composition")
REFERENCE_DIR = os.path.join(EXP_DIR, "out")
ARM = "primary"
REFERENCE_FILES = dict(certificate="EICU_certificate.json",
                       diagnostics="EICU_diagnostics.json",
                       pooled="EICU_pooled.csv",
                       provenance="EICU_provenance.json")
JSON_NAME = "EICU_composition_margin.json"
COMPOSITION_CSV = "EICU_composition_corrected.csv"
MARGIN_CSV = "EICU_margin_exact.csv"
README_NAME = "README.md"
# derive_fixpass_numbers.FROZEN_DIRS names the release directories and these
# released post-hoc sidecars too; the list is kept so this sidecar refuses
# them on its own.
RELEASED_SIDECAR_DIRS = ("out-rev2", "out-timing", "out-settled",
                         "out-e9a-rescore", "out-e9b-positives",
                         "out-bbse-probe", "out-derived")
POOLED_CHECK_COLUMNS = ("certified", "tau", "tau_idx", "coverage",
                        "n_answered")

POST_HOC = ("[MEASURE] POST-HOC (2026-10-29): replay of the released eICU "
            "primary arm to recompute (1) the BBSE-implied answered "
            "positive fraction with the head's S_train prior (audit BBSE-1, "
            "contract C1) and (2) the exact S_aux atom-unit certification "
            "margin beside the released record-pooled feasibility proxy "
            "(audit CORE-3). Nothing here is a certified quantity; no "
            "certificate, threshold, guarantee or registered prediction "
            "descends from it, and the released artifacts are unchanged.")

ESTIMANDS = dict(
    bbse_released=("released formula: mean over the answered set of "
                   "p_t = o_t/(1+o_t), o_t = rho_point * odds_head(x); "
                   "divides out the S_aux prior pi_s"),
    bbse_corrected=("fixed explain.composition (contract C1): o_t = "
                    "rho_point * odds(clip(pi_s, PI_CLIP, 1-PI_CLIP)) / "
                    "odds(pi_train) * odds_head(x), pi_train = train.y.mean() "
                    "= the S_train record prevalence the head's odds carry"),
    margin_atom=("exact S_aux atom-unit margin max_tau (alpha - mean_c "
                 "Z_c(tau)), Z_c = influence_atoms(score_aux, err_aux, ...) "
                 "over all aux.n_sites columns; argmax = walk_order(atoms)[0]"),
    margin_atom_answered=("the same maximum restricted to thresholds with "
                          "S_aux coverage > 0, the domain the proxy uses; "
                          "where nothing answers every atom is alpha and the "
                          "margin is exactly 0"),
    margin_proxy=("released diagnostic.feasibility margin = "
                  "pipeline._feasibility: max_tau cov(tau) * (alpha - "
                  "risk(tau)) * mean_c min(n_c, M)/M, cov and risk pooled "
                  "over S_aux records"),
    floor=("margin_floor(n_cal_carrying, DELTA, alpha) = "
           "ln(1/DELTA)(1-alpha)/n, the information floor in atom units at "
           "the record-carrying calibration count; a first-order heuristic, "
           "not an impossibility bound"),
)


# ------------------------------------------------------------- write guard --

def assert_writable(path):
    """Refuse every frozen directory: the release, the released sidecars and
    the other post-hoc sidecars of the 2026-10 audit."""
    assert_not_frozen(path, own="out-eicu-composition")
    target = os.path.normcase(os.path.abspath(path))
    for name in RELEASED_SIDECAR_DIRS:
        frozen = os.path.normcase(os.path.join(EXP_DIR, name))
        if target == frozen or target.startswith(frozen + os.sep):
            raise SystemExit(
                f"refusing to write {path}: experiments/{name}/ is a released, "
                f"frozen directory; this sidecar writes to its own "
                f"(reason=frozen-output-dir)")


# ----------------------------------------------------------------- formulas --

def _odds(p):
    return p / (1.0 - p)


def released_bbse_fraction(head, target_x, answered_mask, rho_point):
    """The pre-fix bbse_true_class, line for line (explain.py at c27e798).

    Re-weights the head's odds by rho_point alone, which leaves
    odds(pi_train)/odds(pi_s) in every record. Returns (positive_fraction,
    expected_n_positive); NaN when nothing is answered.
    """
    answered_mask = np.asarray(answered_mask, dtype=bool)
    if not answered_mask.any():
        return float("nan"), float("nan")
    p_s = np.asarray(head.predict_proba(target_x), dtype=np.float64)
    odds_s = p_s / np.clip(1.0 - p_s, 1e-12, None)
    odds_t = float(rho_point) * odds_s
    p_t = odds_t / (1.0 + odds_t)
    return (float(p_t[answered_mask].mean()),
            float(p_t[answered_mask].sum()))


def corrected_bbse_block(head, target_x, answered_mask, rho_point, pi_source,
                         pi_train):
    """explain.composition's bbse_true_class with both priors (contract C1)."""
    return composition(head, target_x, answered_mask, rho_point,
                       pi_source=pi_source, pi_train=pi_train)[
                           "bbse_true_class"]


def atom_margin(score_aux, err_aux, aux, alpha):
    """Exact S_aux atom-unit margin, the quantity walk_order ranks by.

    margin(tau) = alpha - mean_c Z_c(tau) over every aux.n_sites column, so
    its maximum sits at walk_order(atoms)[0]. Also returns the maximum over
    thresholds with S_aux coverage > 0 (the proxy's domain) and the S_aux
    record coverage at each argmax.
    """
    atoms = influence_atoms(score_aux, err_aux, aux.site_id, aux.n_sites,
                            TAU_GRID, alpha, M_INFLUENCE)
    margin = alpha - atoms.mean(axis=1)
    first = int(walk_order(atoms)[0])
    if margin[first] != margin.max():                 # pragma: no cover
        raise SystemExit(
            f"eicu_composition_margin: walk_order's first threshold "
            f"{first} is not the margin argmax (reason=internal-mismatch)")
    cov = np.array([float((score_aux >= t).mean()) for t in TAU_GRID])
    live = np.flatnonzero(cov > 0.0)
    out = dict(margin_atom=float(margin[first]), tau_idx_atom=first,
               tau_atom=float(TAU_GRID[first]),
               aux_coverage_at_atom=float(cov[first]),
               margin_atom_answered=None, tau_idx_atom_answered=None)
    if live.size:
        j = int(live[np.argmax(margin[live])])
        out.update(margin_atom_answered=float(margin[j]),
                   tau_idx_atom_answered=j)
    return out


def _ratio(m, floor):
    return (float(m / floor) if (m is not None and floor is not None
                                 and floor > 0) else None)


# ------------------------------------------------------------------- replay --

def replay_replicate(r, x_raw, y_raw, site_raw):
    """run_certification's pooled arm for replicate r, call for call.

    Returns the report and the objects the sidecar's two computations need;
    nothing record-level is returned beyond what stays in memory here.
    """
    idx, sets = etl.site_split(site_raw, replicate=r)
    for a, b in (("train", "aux"), ("train", "cal"), ("aux", "cal"),
                 ("train", "target"), ("aux", "target"), ("cal", "target")):
        if set(sets[a]) & set(sets[b]):
            raise CohortError(
                f"eicu_composition_margin: site_split(replicate={r}) returned "
                f"splits {a!r} and {b!r} sharing sites")
    x, _ = etl.impute(x_raw, idx["train"], verbose=False)
    cohorts = re_._build_cohorts(x, y_raw, site_raw, idx, ARM, r)
    train, aux, cal = cohorts["train"], cohorts["aux"], cohorts["cal"]
    target = cohorts["target"]
    head = fit_head(train)
    t_sites = [site_raw[i] for i in np.asarray(idx["target"],
                                                  dtype=int).tolist()]
    rep = run_certgate(train, aux, cal, target.x,
                       target_label=etl.EICU_POOLED_TARGET_LABEL,
                       target_site_id=t_sites, oracle_target_y=target.y)
    return dict(rep=rep, head=head, train=train, aux=aux, cal=cal,
                target=target)


def analyse_replicate(r, ctx):
    """Aggregate-only record of one replicate: margins, composition, checks."""
    rep, head = ctx["rep"], ctx["head"]
    train, aux, cal, target = (ctx["train"], ctx["aux"], ctx["cal"],
                               ctx["target"])
    diag = rep.get("diagnostic") or {}
    op = rep.get("operative")
    n_carrying = int((cal.site_sizes > 0).sum())
    pi_train = float(np.mean(train.y))
    internal = []

    # ---- pooled rows exactly as run_eicu writes them ----------------------
    evals = {alpha: re_._eval_rung(head, rep, alpha, target.x, target.y)
             for alpha in ALPHA_LADDER}

    # ---- (2) exact atom margin vs released proxy vs floor -----------------
    score_aux = head.score(aux.x)
    err_aux = head.predict(aux.x) != aux.y
    released_feas = diag.get("feasibility") or {}
    margins = {}
    for alpha in ALPHA_LADDER:
        key = str(float(alpha))
        atom = atom_margin(score_aux, err_aux, aux, alpha)
        proxy = _feasibility(head, aux, alpha, n_carrying)
        if released_feas and released_feas.get(key) != proxy:
            internal.append(f"replicate {r} alpha {key}: report feasibility "
                            f"{released_feas.get(key)} != recomputed {proxy}")
        floor = (float(margin_floor(n_carrying, DELTA, alpha))
                 if n_carrying > 0 else None)
        m_atom, m_proxy = atom["margin_atom"], proxy["margin"]
        margins[key] = dict(
            alpha=float(alpha), n_cal_carrying=n_carrying, floor=floor,
            **atom,
            margin_proxy=m_proxy, ratio_proxy=proxy["ratio"],
            ratio_atom=_ratio(m_atom, floor),
            ratio_atom_answered=_ratio(atom["margin_atom_answered"], floor),
            proxy_minus_atom=(None if m_proxy is None else m_proxy - m_atom),
            proxy_relative_error=(None if (m_proxy is None or m_atom == 0.0)
                                  else (m_proxy - m_atom) / abs(m_atom)),
            atom_clears_floor=(None if floor is None else bool(m_atom >= floor)),
            proxy_clears_floor=(None if (floor is None or m_proxy is None)
                                else bool(m_proxy >= floor)))

    # ---- (1) BBSE-implied composition, released formula vs corrected ------
    bb = diag.get("bbse") or {}
    rho, pi_s = bb.get("rho_point"), bb.get("pi_s")
    comp = diag.get("composition") or {}
    comp_row = None
    if op is not None:
        mask = np.asarray(rep["answered_mask"], dtype=bool)
        n_ans = int(mask.sum())
        pred = (comp.get("predicted_class") or {})
        orac = (comp.get("oracle_true_class") or {})
        comp_row = dict(
            replicate=r, operative_alpha=float(op["alpha"]),
            tau=float(op["tau"]), tau_idx=int(op["tau_idx"]),
            n_answered=n_ans, pi_train=pi_train, bbse_fitted=rho is not None,
            rho_point=rho, pi_source=None, pi_t_implied=None,
            odds_multiplier=None,
            predicted_positive_fraction=pred.get("positive_fraction"),
            oracle_positive_fraction=orac.get("positive_fraction"),
            oracle_n_positive=orac.get("n_positive"),
            bbse_released=None, expected_n_positive_released=None,
            bbse_corrected=None, expected_n_positive_corrected=None,
            corrected_minus_released=None, released_minus_oracle=None,
            corrected_minus_oracle=None)
        if rho is not None:
            rel_frac, rel_n = released_bbse_fraction(head, target.x, mask, rho)
            cor = corrected_bbse_block(head, target.x, mask, rho, pi_s,
                                       pi_train)
            rep_cor = comp.get("bbse_true_class") or {}
            if (rep_cor.get("positive_fraction") != cor["positive_fraction"]
                    or rep_cor.get("odds_multiplier")
                    != cor["odds_multiplier"]
                    or rep_cor.get("pi_train") != pi_train):
                internal.append(
                    f"replicate {r}: report bbse_true_class "
                    f"{rep_cor.get('positive_fraction')} / multiplier "
                    f"{rep_cor.get('odds_multiplier')} / pi_train "
                    f"{rep_cor.get('pi_train')} != direct composition "
                    f"{cor['positive_fraction']} / {cor['odds_multiplier']} "
                    f"/ {pi_train}")
            q, c0, c1 = bb.get("q_target"), bb.get("c0"), bb.get("c1")
            pi_t = (None if None in (q, c0, c1) or c1 == c0 else
                    float(np.clip((q - c0) / (c1 - c0), PI_CLIP,
                                  1.0 - PI_CLIP)))
            oracle = comp_row["oracle_positive_fraction"]
            comp_row.update(
                pi_source=cor["pi_source"], pi_t_implied=pi_t,
                odds_multiplier=cor["odds_multiplier"],
                bbse_released=rel_frac, expected_n_positive_released=rel_n,
                bbse_corrected=cor["positive_fraction"],
                expected_n_positive_corrected=cor["expected_n_positive"],
                corrected_minus_released=cor["positive_fraction"] - rel_frac,
                released_minus_oracle=(None if oracle is None
                                       else rel_frac - oracle),
                corrected_minus_oracle=(None if oracle is None else
                                        cor["positive_fraction"] - oracle))

    return dict(
        replicate=r, reason=rep.get("reason"),
        n_sites=dict(train=int(train.n_sites), aux=int(aux.n_sites),
                     cal=int(cal.n_sites), target=int(target.n_sites)),
        n_cal_carrying=n_carrying, n_target=int(target.n), pi_train=pi_train,
        operative=(None if op is None else
                   dict(alpha=float(op["alpha"]), tau=float(op["tau"]),
                        tau_idx=int(op["tau_idx"]),
                        deploy_mode=op["deploy_mode"])),
        coverage=diag.get("coverage"),
        bbse=dict(fitted=rho is not None, rho_point=rho, pi_s=pi_s,
                  q_target=bb.get("q_target"), c0=bb.get("c0"),
                  c1=bb.get("c1")),
        composition=comp_row, margins=margins,
        _evals=evals, _report=rep, _internal=internal)


# ------------------------------------------------------------- self-checks --

def _same(a, b):
    """Exact equality with None standing for null / non-finite."""
    def norm(v):
        if isinstance(v, np.generic):
            v = v.item()
        if isinstance(v, float) and not np.isfinite(v):
            return None
        return v
    a, b = norm(a), norm(b)
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return float(a) == float(b)
    return a == b


def _provenance_data_sha(prov):
    meta = prov.get("meta")
    if isinstance(meta, dict):
        return meta.get("data_sha")
    if isinstance(meta, str):
        try:
            parsed = ast.literal_eval(meta)
            if isinstance(parsed, dict):
                return parsed.get("data_sha")
        except (ValueError, SyntaxError):
            pass
        m = re.search(r"'data_sha':\s*'([0-9a-f]{64})'", meta)
        return m.group(1) if m else None
    return None


def check_replicate0(rec, cert):
    """Replicate 0 against EICU_certificate.json; returns {field: pair}."""
    rep = rec["_report"]
    cd = cert.get("diagnostic") or {}
    rd = rep.get("diagnostic") or {}
    cop, rop = cert.get("operative"), rep.get("operative")
    pairs = {}
    for k in ("alpha", "tau", "tau_idx", "deploy_mode"):
        pairs[f"operative.{k}"] = ((cop or {}).get(k) if cop else None,
                                   (rop or {}).get(k) if rop else None)
    for k in ("coverage", "n_target", "n_cal", "n_cal_carrying"):
        pairs[f"diagnostic.{k}"] = (cd.get(k), rd.get(k))
    cb, rb = cd.get("bbse") or {}, rd.get("bbse") or {}
    for k in ("rho_point", "pi_s"):
        pairs[f"bbse.{k}"] = (cb.get(k), rb.get(k))
    cf, rf = cd.get("feasibility") or {}, rd.get("feasibility") or {}
    for alpha in ALPHA_LADDER:
        key = str(float(alpha))
        for k in ("margin", "floor", "ratio"):
            pairs[f"feasibility.{key}.{k}"] = ((cf.get(key) or {}).get(k),
                                               (rf.get(key) or {}).get(k))
    cc, comp = cd.get("composition") or {}, rec["composition"] or {}
    pairs["composition.predicted_class"] = (
        (cc.get("predicted_class") or {}).get("positive_fraction"),
        comp.get("predicted_positive_fraction"))
    pairs["composition.bbse_true_class(released formula)"] = (
        (cc.get("bbse_true_class") or {}).get("positive_fraction"),
        comp.get("bbse_released"))
    pairs["composition.oracle_true_class"] = (
        (cc.get("oracle_true_class") or {}).get("positive_fraction"),
        comp.get("oracle_positive_fraction"))
    return pairs


def check_against_release(rec, diag_rel, pooled_rel):
    """One replicate against EICU_diagnostics.json and EICU_pooled.csv."""
    r = rec["replicate"]
    bad = []
    bbse_rel = [b for b in diag_rel.get("bbse") or []
                if b.get("replicate") == r]
    if len(bbse_rel) != 1:
        bad.append(f"replicate {r}: {len(bbse_rel)} released bbse rows")
    else:
        for k in ("rho_point", "q_target"):
            if not _same(bbse_rel[0].get(k), rec["bbse"][k]):
                bad.append(f"replicate {r} bbse.{k}: released "
                           f"{bbse_rel[0].get(k)!r} vs replayed "
                           f"{rec['bbse'][k]!r}")
    comp_rel = [c for c in diag_rel.get("composition_three_way") or []
                if c.get("replicate") == r]
    comp = rec["composition"]
    if comp is None:
        if comp_rel:
            bad.append(f"replicate {r}: released composition row but no "
                       f"operative rung in the replay")
    elif len(comp_rel) != 1:
        bad.append(f"replicate {r}: {len(comp_rel)} released composition "
                   f"rows, replay has an operative rung")
    else:
        c = comp_rel[0]
        for rk, mk in (("alpha", "operative_alpha"),
                       ("predicted_positive_fraction",
                        "predicted_positive_fraction"),
                       ("bbse_implied_positive_fraction", "bbse_released"),
                       ("oracle_positive_fraction",
                        "oracle_positive_fraction")):
            if not _same(c.get(rk), comp[mk]):
                bad.append(f"replicate {r} composition.{rk}: released "
                           f"{c.get(rk)!r} vs replayed {comp[mk]!r}")
        if not _same(c.get("tau"), round(comp["tau"], 6)):
            bad.append(f"replicate {r} composition.tau: released "
                       f"{c.get('tau')!r} vs replayed {comp['tau']!r}")
    for alpha in ALPHA_LADDER:
        rows = [p for p in pooled_rel if p.get("replicate") == str(r)
                and p.get("arm") == ARM and float(p.get("alpha")) == alpha]
        if len(rows) != 1:
            bad.append(f"replicate {r} alpha {alpha}: {len(rows)} released "
                       f"pooled rows")
            continue
        ev = rec["_evals"][alpha]
        cells = {k: ev[k] for k in POOLED_CHECK_COLUMNS}
        cells["n_cal_carrying"] = rec["n_cal_carrying"]
        for k, v in cells.items():
            if str(re_._csv_cell(v)) != rows[0].get(k):
                bad.append(f"replicate {r} alpha {alpha} pooled.{k}: "
                           f"released {rows[0].get(k)!r} vs replayed "
                           f"{re_._csv_cell(v)!r}")
    return bad


# ----------------------------------------------------------------- summary --

def summarise(records):
    comps = [x["composition"] for x in records
             if x["composition"] and x["composition"]["bbse_released"]
             is not None]
    s = re_._summary_stats
    comp_summary = dict(
        n_replicates_with_bbse_composition=len(comps),
        bbse_released=s([c["bbse_released"] for c in comps]),
        bbse_corrected=s([c["bbse_corrected"] for c in comps]),
        oracle=s([c["oracle_positive_fraction"] for c in comps]),
        odds_multiplier=s([c["odds_multiplier"] for c in comps]),
        pi_train=s([c["pi_train"] for c in comps]),
        pi_source=s([c["pi_source"] for c in comps]),
        abs_error_released=s([abs(c["released_minus_oracle"]) for c in comps
                              if c["released_minus_oracle"] is not None]),
        abs_error_corrected=s([abs(c["corrected_minus_oracle"])
                               for c in comps
                               if c["corrected_minus_oracle"] is not None]),
        n_corrected_closer_to_oracle=sum(
            1 for c in comps if c["corrected_minus_oracle"] is not None
            and abs(c["corrected_minus_oracle"])
            < abs(c["released_minus_oracle"])))
    margin_summary = {}
    for alpha in ALPHA_LADDER:
        key = str(float(alpha))
        ms = [x["margins"][key] for x in records]
        margin_summary[key] = dict(
            margin_atom=s([m["margin_atom"] for m in ms]),
            margin_proxy=s([m["margin_proxy"] for m in ms]),
            floor=s([m["floor"] for m in ms]),
            ratio_atom=s([m["ratio_atom"] for m in ms]),
            ratio_proxy=s([m["ratio_proxy"] for m in ms]),
            proxy_relative_error=s([m["proxy_relative_error"] for m in ms]),
            n_atom_clears_floor=sum(1 for m in ms if m["atom_clears_floor"]),
            n_proxy_clears_floor=sum(1 for m in ms
                                     if m["proxy_clears_floor"]),
            n_floor_verdict_agrees=sum(
                1 for m in ms if m["atom_clears_floor"]
                == m["proxy_clears_floor"]),
            n_replicates=len(ms))
    return dict(composition=comp_summary, margins=margin_summary)


def _headline(rec0):
    parts = []
    c = rec0["composition"]
    if c and c["bbse_released"] is not None:
        parts.append(f"replicate 0 BBSE-implied answered positive fraction "
                     f"{c['bbse_released']:.4f} released -> "
                     f"{c['bbse_corrected']:.4f} corrected (oracle "
                     f"{c['oracle_positive_fraction']:.4f}; pi_train "
                     f"{c['pi_train']:.4f}, pi_s {c['pi_source']:.4f})")
    else:
        parts.append("replicate 0 has no BBSE-implied composition (no "
                     "operative rung or the BBSE fit declined)")
    for key, m in rec0["margins"].items():
        proxy = ("n/a" if m["margin_proxy"] is None
                 else f"{m['margin_proxy']:.4f}")
        ratio_p = ("n/a" if m["ratio_proxy"] is None
                   else f"{m['ratio_proxy']:.2f}")
        ratio_a = ("n/a" if m["ratio_atom"] is None
                   else f"{m['ratio_atom']:.2f}")
        floor = "n/a" if m["floor"] is None else f"{m['floor']:.4f}"
        parts.append(f"alpha={key}: exact atom margin "
                     f"{m['margin_atom']:.4f} (x{ratio_a} floor {floor}) vs "
                     f"proxy {proxy} (x{ratio_p})")
    return "; ".join(parts)


def _public(rec):
    return {k: v for k, v in rec.items() if not k.startswith("_")}


COMPOSITION_FIELDS = ["replicate", "operative_alpha", "tau", "tau_idx",
                      "n_answered", "bbse_fitted", "pi_train", "pi_source",
                      "pi_t_implied", "rho_point", "odds_multiplier",
                      "predicted_positive_fraction", "bbse_released",
                      "bbse_corrected", "oracle_positive_fraction",
                      "oracle_n_positive", "expected_n_positive_released",
                      "expected_n_positive_corrected",
                      "corrected_minus_released", "released_minus_oracle",
                      "corrected_minus_oracle"]
MARGIN_FIELDS = ["replicate", "alpha", "n_cal_carrying", "floor",
                 "margin_atom", "tau_idx_atom", "tau_atom",
                 "aux_coverage_at_atom", "margin_atom_answered",
                 "tau_idx_atom_answered", "margin_proxy", "ratio_atom",
                 "ratio_atom_answered", "ratio_proxy", "proxy_minus_atom",
                 "proxy_relative_error", "atom_clears_floor",
                 "proxy_clears_floor"]


def _r6(v):
    return round(v, 6) if isinstance(v, float) and np.isfinite(v) else v


def _readme(out_dir, doc):
    name = os.path.basename(os.path.normpath(out_dir))
    lines = [
        f"# {name}/ -- POST-HOC corrected eICU composition and exact S_aux "
        f"margin",
        "",
        "**Status: POST-HOC (2026-10-29).** Nothing in this directory is a "
        "certified quantity. No certificate, threshold, guarantee string or "
        "registered prediction descends from it, and the released eICU "
        "artifacts (`experiments/out/`) are unchanged.",
        "",
        "Produced by `experiments/eicu_composition_margin.py` on the "
        "restricted eICU-CRD v2.0 extract (DUA holder only):",
        "",
        f"    python -m experiments.eicu_composition_margin --data <DATA_DIR> "
        f"--replicates {doc['config']['replicates']}",
        "",
        "It replays the released primary arm, re-split by re-split, exactly "
        "as `experiments/run_eicu.py` builds it (one `_build_and_gate` "
        "build; `site_split`, `impute`, `_build_cohorts`, `fit_head`, "
        "`run_certgate` on the 24-hospital pooled pool), and refuses to "
        "write unless the replay reproduces the release: the extract's "
        "`data_sha`, replicate 0's tau*, tau_idx, coverage, n_cal, BBSE "
        "rho_point and pi_s, feasibility and composition against "
        "`EICU_certificate.json`, and every replicate's BBSE, composition "
        "and pooled cells against `EICU_diagnostics.json` and "
        "`EICU_pooled.csv`, all by exact equality.",
        "",
        "What is computed:",
        "",
        "- **Corrected BBSE-implied answered positive fraction** (audit "
        "BBSE-1, contract C1). The released value re-weighted the head's "
        "odds by `rho_point = odds(pi_t)/odds(pi_s)` alone, dividing out "
        "the S_aux prior `pi_s`; the head's odds carry the S_train prior, "
        "so the corrected multiplier is `rho_point * odds(clip pi_s) / "
        "odds(pi_train)` with `pi_train = train.y.mean()`. Both are "
        "reported per replicate (`EICU_composition_corrected.csv`), beside "
        "the oracle fraction.",
        "- **Exact S_aux atom-unit margin** (audit CORE-3): "
        "`max_tau (alpha - mean_c Z_c(tau))`, the quantity `walk_order` "
        "ranks by, beside the released record-pooled feasibility proxy "
        "(`pipeline._feasibility`) and the information floor "
        "`margin_floor(n_cal_carrying, DELTA, alpha)`, with both "
        "margin/floor ratios, for alpha = 0.05 and 0.10 "
        "(`EICU_margin_exact.csv`). The floor is a first-order heuristic, "
        "not an impossibility bound.",
        "",
        "Files: `EICU_composition_margin.json` (per-replicate records, "
        "summaries across re-splits, the self-check, `_run` with UTC, git "
        "sha and the sha256 of every released file read, and the extract's "
        "`data_sha` and per-table sha256), `EICU_composition_corrected.csv`, "
        "`EICU_margin_exact.csv`. Aggregate quantities only: every write "
        "passed `run_eicu.assert_aggregate_only`.",
        "",
        "The re-splits are re-splits of one hospital population on one "
        "extract, so the spread across them is split-to-split variation, "
        "not sampling uncertainty.",
        "",
        f"Headline: {doc['headline']}",
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------- run --

def _load_reference(ref_dir):
    paths = {k: os.path.join(ref_dir, v) for k, v in REFERENCE_FILES.items()}
    missing = [p for p in paths.values() if not os.path.isfile(p)]
    if missing:
        raise SystemExit(
            f"eicu_composition_margin: released reference files missing: "
            f"{missing} (reason=missing-reference)")
    ref = dict(certificate=_read_json(paths["certificate"]),
               diagnostics=_read_json(paths["diagnostics"]),
               pooled=_read_csv(paths["pooled"]),
               provenance=_read_json(paths["provenance"]))
    return ref, paths


def _table_hashes(data_dir):
    """sha256 of each table the ETL reads (etl.EICU_TABLES), by file name.

    A digest of a whole gzip file carries no record; the extract's own
    data_sha (run_eicu._data_sha) travels beside it.
    """
    out = {}
    for table in etl.EICU_TABLES:
        path = etl._resolve_table_path(data_dir, table)
        out[os.path.basename(path)] = sha256_file(path)
    return out


def run(data_dir, replicates=etl.EICU_SPLIT_REPLICATES,
        reference_dir=REFERENCE_DIR, verbose=True):
    """Replay, self-check and compute. Writes nothing; returns (doc, rows)."""
    t0 = time.perf_counter()
    replicates = int(replicates)
    ref, ref_paths = _load_reference(reference_dir)
    rel_reps = ref["diagnostics"].get("replicates")
    if ref["diagnostics"].get("arm") != ARM:
        raise SystemExit(
            f"eicu_composition_margin: reference arm "
            f"{ref['diagnostics'].get('arm')!r} is not {ARM!r} "
            f"(reason=reference-arm)")
    if not 1 <= replicates <= int(rel_reps or 0):
        raise SystemExit(
            f"eicu_composition_margin: --replicates must be in 1..{rel_reps} "
            f"(the released run's count), got {replicates} "
            f"(reason=bad-replicates)")
    released_sha = _provenance_data_sha(ref["provenance"])
    data_sha = re_._data_sha(data_dir)
    if data_sha is None or data_sha != released_sha:
        raise SystemExit(
            f"eicu_composition_margin: extract identity {data_sha} does not "
            f"match the released run's data_sha {released_sha}; nothing "
            f"replayed or written (reason=extract-mismatch)")

    warnings = []
    built = re_._build_and_gate(data_dir, ARM, replicates, warnings, verbose)
    x_raw, y_raw, site_raw = built[0], built[5], built[6]

    records, mismatches, internal, check0 = [], [], [], None
    for r in range(replicates):
        rec = analyse_replicate(r, replay_replicate(r, x_raw, y_raw,
                                                    site_raw))
        if r == 0:
            pairs = check_replicate0(rec, ref["certificate"])
            failed = {k: v for k, v in pairs.items() if not _same(*v)}
            if failed:
                raise SystemExit(
                    f"eicu_composition_margin: replicate 0 does not reproduce "
                    f"the released EICU_certificate.json: "
                    f"{ {k: list(v) for k, v in failed.items()} }; nothing "
                    f"written (reason=self-check-failed)")
            check0 = {k: dict(released=v[0], replayed=v[1], equal=True)
                      for k, v in pairs.items()}
        mismatches.extend(check_against_release(rec, ref["diagnostics"],
                                                ref["pooled"]))
        internal.extend(rec["_internal"])
        records.append(rec)
        re_._say(verbose, f"composition/margin replay: replicate {r} done "
                          f"({time.perf_counter() - t0:.0f} s)")
    if internal:
        raise SystemExit(
            f"eicu_composition_margin: {len(internal)} internal "
            f"inconsistencies: {internal[:3]}; nothing written "
            f"(reason=internal-mismatch)")
    if mismatches:
        raise SystemExit(
            f"eicu_composition_margin: {len(mismatches)} released cells did "
            f"not replay exactly: {mismatches[:5]}; nothing written "
            f"(reason=replay-mismatch)")

    doc = dict(
        post_hoc=POST_HOC, estimands=ESTIMANDS,
        config=dict(arm=ARM, replicates=replicates,
                    alphas=[float(a) for a in ALPHA_LADDER],
                    delta=DELTA, m_influence=M_INFLUENCE, pi_clip=PI_CLIP,
                    seed=SEED, n_tau=int(len(TAU_GRID)),
                    target_label=etl.EICU_POOLED_TARGET_LABEL),
        extract=dict(data_sha=data_sha, tables_sha256=_table_hashes(data_dir)),
        self_check=dict(
            extract_data_sha_matches_release=True,
            replicate0_vs_certificate=check0,
            replicates_vs_diagnostics_and_pooled=dict(
                replicates_checked=replicates, mismatches=0),
            internal=dict(report_composition_equals_direct_call=True,
                          report_feasibility_equals_recomputed=True)),
        headline=_headline(records[0]),
        summary=summarise(records),
        replicates=[_public(x) for x in records],
        warnings=warnings,
        wall_clock_s=round(time.perf_counter() - t0, 1))
    comp_rows = [{k: _r6(x["composition"][k]) for k in COMPOSITION_FIELDS}
                 for x in records if x["composition"] is not None]
    margin_rows = [dict(replicate=x["replicate"],
                        **{k: _r6(v) for k, v in m.items()
                           if k in MARGIN_FIELDS})
                   for x in records for m in x["margins"].values()]
    return doc, comp_rows, margin_rows, list(ref_paths.values())


def _pregate(payload, comp_rows, margin_rows, readme):
    """Every gate the writers apply, run before any file is opened.

    run_eicu's writers gate as they go, so a record-level value found in the
    JSON after the CSVs were written would leave a partial directory. The
    same checks run here first (the JSON envelope and each per-replicate
    item exactly as _write_json gates them), so a refusal writes nothing.
    """
    for name, rows in ((COMPOSITION_CSV, comp_rows), (MARGIN_CSV,
                                                      margin_rows)):
        for i, row in enumerate(rows):
            re_.assert_aggregate_only(row, f"{name}[{i}]")
    ready = re_._json_ready(payload)
    items = ready.get("replicates") or []
    re_.assert_aggregate_only(
        {k: (f"<{len(v)} items>" if k == "replicates" else v)
         for k, v in ready.items()}, JSON_NAME)
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise etl.EicuError(
                f"eicu_composition_margin: {JSON_NAME}.replicates[{i}] is not "
                f"a dict (reason=record-level-output)")
        re_.assert_aggregate_only(item, f"{JSON_NAME}.replicates[{i}]")
    re_.assert_aggregate_only({"readme": readme}, README_NAME)


def write_outputs(out_dir, doc, comp_rows, margin_rows, input_paths):
    """Gate everything, then write the JSON, the two CSVs and the README."""
    paths = {k: os.path.join(out_dir, v) for k, v in
             dict(json=JSON_NAME, comp=COMPOSITION_CSV, margin=MARGIN_CSV,
                  readme=README_NAME).items()}
    for p in paths.values():
        assert_writable(p)
    payload = {"_run": run_block(input_paths), **doc}
    readme = _readme(out_dir, doc)
    _pregate(payload, comp_rows, margin_rows, readme)
    os.makedirs(out_dir, exist_ok=True)
    re_._write_table(paths["comp"], comp_rows, COMPOSITION_FIELDS,
                     COMPOSITION_CSV)
    re_._write_table(paths["margin"], margin_rows, MARGIN_FIELDS, MARGIN_CSV)
    re_._write_json(paths["json"], payload, JSON_NAME,
                    per_item_keys=("replicates",))
    with open(paths["readme"], "w", encoding="utf-8", newline="\n") as fh:
        fh.write(readme)
    return paths


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="POST-HOC: corrected eICU BBSE composition and exact "
                    "S_aux atom margin, replayed over the released re-splits")
    ap.add_argument("--data", required=True,
                    help="directory holding the gzipped eICU CSV tables "
                         "(restricted; never committed or redistributed)")
    ap.add_argument("--out", default=OUT_DIR,
                    help="output directory (aggregate artifacts only); "
                         "frozen directories are refused")
    ap.add_argument("--replicates", type=int,
                    default=etl.EICU_SPLIT_REPLICATES,
                    help=f"re-splits to replay, 0..N-1; the released primary "
                         f"arm has {etl.EICU_SPLIT_REPLICATES}")
    ap.add_argument("--reference", default=REFERENCE_DIR,
                    help="the released run to reproduce (default "
                         "experiments/out/)")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    for name in (JSON_NAME, COMPOSITION_CSV, MARGIN_CSV, README_NAME):
        assert_writable(os.path.join(args.out, name))
    doc, comp_rows, margin_rows, inputs = run(
        args.data, args.replicates, args.reference, verbose=not args.quiet)
    paths = write_outputs(args.out, doc, comp_rows, margin_rows, inputs)
    print(f"[certgate] {doc['headline']}")
    print(f"[certgate] wrote {sorted(paths.values())} "
          f"({doc['wall_clock_s']} s)", file=sys.stderr)
    return doc


if __name__ == "__main__":
    main()
