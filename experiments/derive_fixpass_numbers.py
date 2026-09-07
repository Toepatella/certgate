"""Read-only derivation of every number the 2026-09 fix pass pastes into the paper.

The adversarial panel's action list asks for a few dozen quantities that were
never printed but are all recoverable from released artifacts: the head's own
discrimination over the twenty re-splits, the three-way composition on the
published split, the two hospitals behind the seven hard violations, the
eight subgroup cells over budget, the coefficient-free driver contrast, the
exact intervals on small counts, the replication count of every synthetic
arm. This file derives them all in one place, from the released files alone,
so the manuscript and its artifacts can be checked against each other by
diffing one JSON.

Nothing under experiments/out*/ is opened for writing and no pipeline is
re-run. The restricted extract is never touched: every input is an aggregate
artifact already in the repository.

Six values are pinned. They are the ones the manuscript quotes most and the
ones a referee reaches for first; if the derivation stops reproducing any of
them the script refuses to emit anything, in the manner of
experiments/panel_confusion_tables.py. That makes this the repository's first
text-to-artifact guard.

The four post-hoc sidecars of the same fix pass (E9-A rescoring, E9-B
positives arm, BBSE coverage probe, settled predictions) are folded in when
their outputs exist, so the coherence sweep reads one file. Lane C's
re-emitted eICU run (experiments/out-rev2/) is likewise read when present.

Run: python -m experiments.derive_fixpass_numbers [--out PATH]

Writes experiments/out-derived/fixpass_numbers.json and prints it. The JSON
carries a _run block (UTC, git sha, sha256 of every input read).

Refs: fix-pass plan WP2; panel action items 4-14, 19, 23, 27.
"""

import argparse
import csv
import datetime
import hashlib
import json
import os
import subprocess
import sys

import numpy as np
from scipy.stats import spearmanr

from certgate.certify import margin_floor
from certgate.constants import ALPHA_LADDER, DELTA
from experiments.run_synthetic import (SHIFT_BASE, _existing_summary_blocks,
                                       _rate_ci95)
from experiments.run_eicu import _write_json
from experiments.panel_confusion_tables import derive as _confusion_tables

EXP_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(EXP_DIR)
OUT_DIR = os.path.join(EXP_DIR, "out-derived")
OUT_PATH = os.path.join(OUT_DIR, "fixpass_numbers.json")

# The frozen output directories. Every sidecar in this fix pass refuses to
# write into them; the three byte-identity gates are what certify them.
FROZEN_DIRS = ("out", "out-panel", "out-sens", "out-subgroups",
               "out-faithfulness")

INPUTS = dict(
    panel="out/EICU_reliability_panel.json",
    pooled="out/EICU_pooled.csv",
    certificate="out/EICU_certificate.json",
    per_site="out/EICU_per_site.csv",
    diagnostics="out/EICU_diagnostics.json",
    preflight="out/EICU_preflight.json",
    attrition="out/EICU_attrition.csv",
    subgroups="out-subgroups/EICU_subgroups.csv",
    faithfulness="out-faithfulness/EICU_faithfulness.csv",
    sens_pooled="out-sens/EICU_pooled.csv",
    sens_attrition="out-sens/EICU_attrition.csv",
    e1="out/E1_validity.csv",
    e9a="out/E9_bbse_frontier.csv",
    e9b="out/E9_fnr.csv",
    summary="out/summary.md",
)
SIDECARS = dict(
    e9a_rescore="out-e9a-rescore/E9a_rescore.json",
    e9b_positives="out-e9b-positives/E9b_fnr_positives.json",
    bbse_probe="out-bbse-probe/BBSE_probe.json",
    settled="out-settled/EICU-PREDICTIONS-SETTLED.json",
    rev2_pooled="out-rev2/EICU_pooled.csv",
    rev2_faithfulness="out-rev2/EICU_faithfulness.csv",
    rev2_diagnostics="out-rev2/EICU_diagnostics.json",
)

# The six pinned values (path -> expected, decimals compared). If any stops
# reproducing, nothing is written. Paths are '/'-joined because one key
# ("alpha0.10") carries a dot of its own.
PINS = {
    "composition_20_resplits/answered/observed_positive_fraction/mean":
        (0.0524, 4),
    "head_auc_s_cal/mean": (0.8618, 4),
    "published_split/n_predicted_positive_answered": (63, 0),
    "fairness/cells_over_alpha/n": (8, 0),
    "fairness/cells_status_ok": (570, 0),
    # The panel's action list quoted this as 0.63; the derivation gives
    # 0.6364 (|coef| against |gap| over the ten Table S10 features), so the
    # pin holds the derived value at 3 dp and the manuscript quotes 0.64.
    "faithfulness_rep0/spearman_abs_coef_vs_abs_gap": (0.636, 3),
    "e1/baseline_deploying_draws_alpha0.10": (194, 0),
}

APACHE_ABSENCE_TOKENS = ("aps_present", "apv_present", "__missing")
OVER_CAP_CANDIDATES = ("apv_ejectfx__missing", "apv_electivesurgery__missing")


# ------------------------------------------------------------- shared helpers

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_sha():
    """HEAD sha, or 'unknown' outside a git checkout."""
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_DIR,
                              capture_output=True, text=True, check=True,
                              timeout=30).stdout.strip()
    except Exception:                       # not a checkout, git absent
        return "unknown"


def rel_path(path):
    return os.path.relpath(path, REPO_DIR).replace(os.sep, "/")


def run_block(input_paths):
    """The provenance stamp every fix-pass sidecar carries as its _run key."""
    return dict(
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat(
            timespec="seconds"),
        git_sha=git_sha(),
        inputs={rel_path(p): sha256_file(p) for p in input_paths})


def assert_not_frozen(path):
    """Refuse any write that would land in a frozen output directory."""
    target = os.path.normcase(os.path.abspath(path))
    for name in FROZEN_DIRS:
        frozen = os.path.normcase(os.path.join(EXP_DIR, name))
        if target == frozen or target.startswith(frozen + os.sep):
            raise SystemExit(
                f"refusing to write {path}: experiments/{name}/ is frozen "
                f"(byte-identical by gate); sidecars write to their own "
                f"directory (reason=frozen-output-dir)")
    if os.path.basename(path) == "EICU-SUMMARY.md":
        raise SystemExit(
            f"refusing to write {path}: EICU-SUMMARY.md is append-only pinned "
            f"and never a sidecar target (reason=frozen-summary)")


def _read_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _f(cell):
    """CSV cell -> float, with blanks read as None (suppressed), never 0."""
    return None if cell in ("", None) else float(cell)


def _stats(vals, dp=4):
    vals = [float(v) for v in vals if v is not None]
    if not vals:
        return None
    return dict(n=len(vals), mean=round(float(np.mean(vals)), dp),
                sd=(round(float(np.std(vals, ddof=1)), dp)
                    if len(vals) > 1 else None),
                min=round(float(np.min(vals)), dp),
                max=round(float(np.max(vals)), dp))


def _ci(k, n):
    return dict(k=int(k), n=int(n),
                rate=(round(k / n, 4) if n else None),
                ci95=_rate_ci95(k, n))


# ------------------------------------------------------------ eICU sections

def composition_section(panel):
    """Twenty-re-split composition means from the post-hoc panel."""
    out = {}
    for scope in ("answered", "declined", "all"):
        obs = [p["composition"][scope]["observed_positive_fraction"]
               for p in panel["panels"]]
        pred = [p["composition"][scope]["predicted_positive_fraction"]
                for p in panel["panels"]]
        out[scope] = dict(observed_positive_fraction=_stats(obs),
                          predicted_positive_fraction=_stats(pred))
    out["note"] = ("means over the 20 re-splits of the panel's composition "
                   "block; the published split (replicate 0) is one of them")
    return out


def head_auc_section(pooled):
    """The head's out-of-sample AUC on S_cal, one value per re-split."""
    rows = [r for r in pooled if r["alpha"] == "0.1"]
    aucs = {int(r["replicate"]): float(r["head_auc_oos"]) for r in rows}
    best = max(aucs, key=aucs.get)
    return dict(set="S_cal (the 74 calibration hospitals; run_eicu leak "
                    "probe, head_auc_oos)",
                **_stats(list(aucs.values())),
                argmax_replicate=best, max_value=round(aucs[best], 6),
                ablation_drop=_stats([float(r["ablation_drop"]) for r in rows]),
                note=("the manuscript's 'peaks at 0.867' is this maximum, "
                      "replicate 4, on S_cal; pool and answered-set AUC "
                      "come from the out-rev2 re-emission when present"))


def calibration_section(panel):
    out = {}
    for scope in ("answered", "declined"):
        out[scope] = dict(
            slope=_stats([p["calibration"][scope]["slope"]
                          for p in panel["panels"]]),
            intercept=_stats([p["calibration"][scope]["intercept"]
                              for p in panel["panels"]]),
            ece=_stats([p["ece"][scope].get("ece")
                        for p in panel["panels"]]))
    out["skill_margin_answered"] = _stats(
        [p["skill"]["answered"]["skill_margin"] for p in panel["panels"]])
    out["note"] = ("post-hoc panel, descriptive; skill_margin_answered is "
                   "constant-rule error minus head error on the answered set, "
                   "i.e. the head's margin over the constant rule")
    return out


def three_way_section(cert, diagnostics):
    """The published-split composition read three ways, plus what BBSE's
    point estimate implies about the target prevalence."""
    comp = cert["diagnostic"]["composition"]
    bb = cert["diagnostic"]["bbse"]
    q, c0, c1, pi_s = bb["q_target"], bb["c0"], bb["c1"], bb["pi_s"]
    pi_t_implied = (q - c0) / (c1 - c0)
    oracle = comp["oracle_true_class"]["positive_fraction"]
    # pool prevalence on the published split: the panel's 'all' scope
    pool_prev = diagnostics["composition_three_way"][0].get(
        "oracle_positive_fraction")
    rows = diagnostics["composition_three_way"]
    return dict(
        published_split=dict(
            predicted_class=round(comp["predicted_class"]["positive_fraction"], 4),
            bbse_implied=round(comp["bbse_true_class"]["positive_fraction"], 4),
            oracle=round(oracle, 4),
            rho_point=round(bb["rho_point"], 4),
            rho_box=[round(bb["rho_lo"], 4), round(bb["rho_hi"], 4)],
            n_predicted_positive=comp["predicted_class"]["n_positive"],
            expected_n_positive_bbse=round(
                comp["bbse_true_class"]["expected_n_positive"], 1),
            n_positive_oracle=comp["oracle_true_class"]["n_positive"]),
        bbse_transfer=dict(
            q_observed=round(q, 4), c0=round(c0, 4), c1=round(c1, 4),
            pi_s=round(pi_s, 4),
            implied_target_prevalence=round(pi_t_implied, 4),
            understatement_of_answered_positive_load=round(
                1.0 - comp["bbse_true_class"]["positive_fraction"] / oracle, 3),
            note=("expected_q_at_observed_prevalence uses the pool's oracle "
                  "prevalence from the 20-re-split block; a q below it means "
                  "the auxiliary-split confusion rates do not transfer to the "
                  "held-out hospitals")),
        per_replicate=_stats([r["bbse_implied_positive_fraction"]
                              for r in rows]),
        per_replicate_oracle=_stats([r["oracle_positive_fraction"]
                                     for r in rows]),
        _pool_prevalence_rep0_oracle_answered=pool_prev)


def _finish_three_way(section, panel):
    """Add the pool-prevalence arithmetic once the panel is at hand."""
    p0 = panel["panels"][0]
    pool_prev = p0["composition"]["all"]["observed_positive_fraction"]
    bt = section["bbse_transfer"]
    c0, c1, pi_s = bt["c0"], bt["c1"], bt["pi_s"]
    bt["pool_prevalence_observed"] = round(pool_prev, 4)
    bt["expected_q_at_observed_prevalence"] = round(
        c0 * (1.0 - pool_prev) + c1 * pool_prev, 4)
    odds = lambda p: p / (1.0 - p)
    bt["true_odds_ratio_vs_pi_s"] = round(odds(pool_prev) / odds(pi_s), 3)
    section.pop("_pool_prevalence_rep0_oracle_answered", None)
    return section


def dispersion_section(per_site):
    rows = [r for r in per_site if r["alpha"] == "0.1"]
    certified = [r for r in rows if r["certified"] == "True"]
    hard = [r for r in certified if r["hard"] == "True"]
    by_site = {}
    for r in certified:
        by_site.setdefault(r["site"], []).append(r)
    hosp = {}
    for site in sorted({r["site"] for r in hard}):
        app = by_site[site]
        hosp[site] = dict(
            appearances=len(app),
            n_hard=sum(1 for r in app if r["hard"] == "True"),
            n_target=int(app[0]["n_target"]),
            beds=app[0]["numbedscategory"], teaching=app[0]["teachingstatus"],
            region=app[0]["region"],
            coverage_range=[min(float(r["coverage"]) for r in app),
                            max(float(r["coverage"]) for r in app)],
            answered_err_range=[
                min(float(r["answered_err_rate"]) for r in app),
                max(float(r["answered_err_rate"]) for r in app)])
    errs = [float(r["answered_err_rate"]) for r in certified
            if r["answered_err_rate"] not in ("", None)]
    reasons = {}
    for r in rows:
        if r["certified"] != "True":
            reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1
    return dict(pools=len(rows), certified=len(certified),
                refused=reasons,
                hard=_ci(len(hard), len(certified)),
                hospitals_with_hard_violations=hosp,
                answered_err=dict(median=round(float(np.median(errs)), 4),
                                  p10=round(float(np.percentile(errs, 10)), 4),
                                  p90=round(float(np.percentile(errs, 90)), 4),
                                  max=round(float(np.max(errs)), 4)))


def published_split_section(panel, cert, pooled):
    p0 = panel["panels"][0]
    ans, dec, allp = (p0["composition"][s] for s in ("answered", "declined",
                                                     "all"))
    tables = _confusion_tables(panel)
    a0 = next(r for r in tables["per_replicate"]["answered"]
              if r["replicate"] == 0)
    deaths = allp["n_observed_positive"]
    row0 = next(r for r in pooled if r["replicate"] == "0"
                and r["alpha"] == "0.1")
    answered_err = float(row0["answered_err_rate"])
    answered_mortality = ans["observed_positive_fraction"]
    return dict(
        n_target=allp["n"], n_answered=ans["n"], n_declined=dec["n"],
        n_predicted_positive_answered=ans["n_predicted_positive"],
        positive_call_rate_answered=round(
            ans["n_predicted_positive"] / ans["n"], 4),
        deaths_total=deaths,
        deaths_declined=dec["n_observed_positive"],
        deaths_answered=ans["n_observed_positive"],
        deaths_answered_caught_tp=a0["tp"],
        deaths_answered_missed_fn=a0["fn"],
        death_shares=dict(
            deferred=round(dec["n_observed_positive"] / deaths, 3),
            answered_missed=round(a0["fn"] / deaths, 3),
            answered_caught=round(a0["tp"] / deaths, 3)),
        answered_error=answered_err,
        answered_mortality=round(answered_mortality, 4),
        answered_error_over_mortality=round(
            answered_err / answered_mortality, 3),
        fn_share_of_answered_deaths=round(
            a0["fn"] / ans["n_observed_positive"], 3),
        constant_rule_margin_rep0=round(answered_mortality - answered_err, 4),
        note=("published split = replicate 0; the constant survive-everyone "
              "rule errs at the answered mortality, so the head's margin "
              "over it is answered_mortality - answered_error"))


def over_cap_section(preflight, diagnostics):
    osm = preflight["outcome_stratified_missingness"]
    over = {k: v for k, v in osm.items()
            if v.get("gate_applies") and v.get("prevalence_ratio") is not None
            and v["prevalence_ratio"] > v.get("cap", 2.0)}
    top10 = [e["feature"] for e in
             diagnostics["abstention_gap_ranking"]["replicate0_alpha0.1"]
             ["ranking"]]
    items = {}
    for k, v in sorted(over.items(), key=lambda kv: -kv[1]["prevalence_ratio"]):
        items[k] = dict(prevalence_ratio=v["prevalence_ratio"],
                        n_missing=v["n_missing"], n_present=v["n_present"],
                        prevalence_missing=v["prevalence_missing"],
                        prevalence_present=v["prevalence_present"],
                        in_figure3_top_ten=k in top10)
    return dict(cap=2.0, n_over_cap=len(items), indicators=items,
                whole_row_flags={k: osm[k]["prevalence_ratio"]
                                 for k in ("aps_present", "apv_present")
                                 if k in osm})


def p4_signed_section(diagnostics):
    """The registered P4 rule (unsigned top-3) and its signed reading."""
    per = []
    for key, blk in diagnostics["abstention_gap_ranking"].items():
        rep = int(key.split("_")[0].replace("replicate", ""))
        top3 = blk["ranking"][:3]
        hits = [dict(feature=e["feature"], rank=i + 1, gap=e["gap"])
                for i, e in enumerate(top3)
                if any(t in e["feature"] for t in APACHE_ABSENCE_TOKENS)]
        per.append(dict(replicate=rep,
                        top3=[(e["feature"], e["gap"]) for e in top3],
                        unsigned_hit=bool(hits),
                        signed_hit=any(h["gap"] < 0 for h in hits),
                        hits=hits))
    per.sort(key=lambda d: d["replicate"])
    exceptions = [d for d in per if d["unsigned_hit"]]
    return dict(
        rule=("an APACHE-absence feature (aps_present, apv_present or an "
              "*__missing sibling) in the top 3 of the |gap| ranking"),
        unsigned_satisfied=sum(d["unsigned_hit"] for d in per),
        signed_satisfied=sum(d["signed_hit"] for d in per),
        n_replicates=len(per),
        exceptions=[dict(replicate=d["replicate"], hits=d["hits"])
                    for d in exceptions],
        note=("a negative gap means the feature carries more attribution on "
              "declined stays (the registered leak direction); every "
              "exception's gap is positive, so under a signed reading P4 "
              "is satisfied on none"),
        top_driver_all_replicates=sorted(
            {d["top3"][0][0] for d in per}))


def fairness_section(subgroups, alpha=0.10):
    cells = subgroups
    ok = [c for c in cells if c["status"] == "ok"]
    resolvable_err = [c for c in ok if _f(c["answered_err_rate"]) is not None]
    over = [c for c in resolvable_err
            if _f(c["answered_err_rate"]) > alpha]
    by_level = {}
    for c in cells:
        by_level.setdefault((c["dim"], c["level"]), []).append(c)
    table = []
    for (dim, level), grp in by_level.items():
        res = [c for c in grp if c["status"] == "ok"
               and _f(c["answered_err_rate"]) is not None]
        covs = [_f(c["coverage"]) for c in grp if _f(c["coverage"]) is not None]
        errs = [_f(c["answered_err_rate"]) for c in res]
        table.append(dict(
            dim=dim, level=level, n_cells=len(grp),
            mean_n=round(float(np.mean([float(c["n"]) for c in grp])), 1),
            coverage_mean=(round(float(np.mean(covs)), 4) if covs else None),
            coverage_min=(round(float(np.min(covs)), 4) if covs else None),
            answered_err_mean=(round(float(np.mean(errs)), 4) if errs else None),
            answered_err_max=(round(float(np.max(errs)), 4) if errs else None),
            cells_over_alpha=sum(1 for e in errs if e > alpha),
            cells_resolvable=len(res),
            answered_err_suppressed=sum(
                1 for c in grp if _f(c["answered_err_rate"]) is None),
            declined_err_suppressed=sum(
                1 for c in grp if _f(c["declined_err_rate"]) is None)))
    # age gradient and the severity-proportionality reading
    age = {}
    for row in table:
        if row["dim"] != "age_band":
            continue
        grp = by_level[(row["dim"], row["level"])]
        shares, dec_mort = [], []
        for c in grp:
            dp, ap = _f(c["declined_pos_rate"]), _f(c["answered_pos_rate"])
            n, na = float(c["n"]), float(c["n_answered"])
            if dp is None or ap is None:
                continue
            dd, ad = dp * (n - na), ap * na
            shares.append(dd / (dd + ad))
            dec_mort.append(dp)
        age[row["level"]] = dict(
            coverage_mean=row["coverage_mean"],
            deferral_mean=(round(1.0 - row["coverage_mean"], 4)
                           if row["coverage_mean"] is not None else None),
            answered_err_mean=row["answered_err_mean"],
            deferred_death_share=(round(float(np.mean(shares)), 3)
                                  if shares else None),
            deferred_death_share_cells=len(shares),
            declined_mortality=(round(float(np.mean(dec_mort)), 3)
                                if dec_mort else None))
    bands = sorted(age)
    lo, hi = age[bands[0]], age[bands[-1]]
    gradients = dict(
        bands=[bands[0], bands[-1]],
        answered_err_ratio=round(hi["answered_err_mean"]
                                 / lo["answered_err_mean"], 2),
        deferral_ratio=round(hi["deferral_mean"] / lo["deferral_mean"], 2))
    over_rows = [dict(replicate=int(c["replicate"]), dim=c["dim"],
                      level=c["level"], answered_err_rate=_f(c["answered_err_rate"]),
                      n_answered=int(float(c["n_answered"])))
                 for c in over]
    over_rows.sort(key=lambda d: (d["dim"], d["level"], d["replicate"]))
    by_lvl_over = {}
    for d in over_rows:
        by_lvl_over[f"{d['dim']}={d['level']}"] = \
            by_lvl_over.get(f"{d['dim']}={d['level']}", 0) + 1
    return dict(
        n_cells=len(cells), cells_status_ok=len(ok),
        cells_suppressed=len(cells) - len(ok),
        cells_resolvable_answered_err=len(resolvable_err),
        cells_over_alpha=dict(n=len(over), by_level=by_lvl_over,
                              max=max(d["answered_err_rate"] for d in over_rows)
                              if over_rows else None,
                              rows=over_rows),
        row_means_all_below_alpha=all(
            (r["answered_err_mean"] or 0.0) <= alpha for r in table),
        row_mean_max=max(r["answered_err_mean"] for r in table
                         if r["answered_err_mean"] is not None),
        table_s8_rows=table,
        age=age, age_gradients=gradients,
        dims=sorted({c["dim"] for c in cells}))


def faithfulness_section(faith, replicate="0"):
    rows = [r for r in faith if r["replicate"] == replicate]
    feats = []
    for r in rows:
        coef, gap = float(r["coef"]), float(r["gap_int"])
        feats.append(dict(feature=r["feature"], coef=coef, gap_int=gap,
                          rank_int=int(r["rank_int"]),
                          delta_mean_abs_z=round(gap / abs(coef), 4),
                          abs_coef=abs(coef)))
    feats.sort(key=lambda d: d["rank_int"])
    rho = spearmanr([d["abs_coef"] for d in feats],
                    [abs(d["gap_int"]) for d in feats]).statistic
    by_dz = sorted(feats, key=lambda d: d["delta_mean_abs_z"])
    coef_rank = sorted(feats, key=lambda d: -d["abs_coef"])
    return dict(
        replicate=int(replicate), n_features=len(feats),
        factorisation="gap_j = |w_j| * (mean|z_j| answered - mean|z_j| declined)",
        spearman_abs_coef_vs_abs_gap=round(float(rho), 4),
        features=[{k: v for k, v in d.items() if k != "abs_coef"}
                  for d in feats],
        delta_mean_abs_z_ranking=[(d["feature"], d["delta_mean_abs_z"])
                                  for d in by_dz],
        abs_coef_ranking_within_ten=[(d["feature"], round(d["abs_coef"], 4))
                                     for d in coef_rank],
        top_driver_rank_by_abs_coef_within_ten=1 + [
            d["feature"] for d in coef_rank].index(feats[0]["feature"]),
        next_largest_abs_coef_ratio=round(
            coef_rank[0]["abs_coef"] / coef_rank[1]["abs_coef"], 2))


def sens_section(sens_pooled, sens_attrition):
    rows = [r for r in sens_pooled if r["alpha"] == "0.1"]
    certs = [r for r in rows if r["certified"] == "True"]
    arm = rows[0]["arm"]
    att = {r["step"]: r for r in sens_attrition if r["arm"] == arm}
    last = att.get("apache-complete-arm") or list(att.values())[-1]
    return dict(
        arm=arm, n_replicates=len(rows),
        n_sites=int(last["n_sites"]), n_stays=int(last["n_stays"]),
        prevalence=float(last["prevalence"]),
        certified=_ci(len(certs), len(rows)),
        certified_alpha0_05=_ci(sum(1 for r in sens_pooled
                                    if r["alpha"] == "0.05"
                                    and r["certified"] == "True"),
                                len(rows)),
        mean_coverage=(round(float(np.mean([float(r["coverage"])
                                            for r in certs])), 4)
                       if certs else None),
        mean_tau=(round(float(np.mean([float(r["tau"]) for r in certs])), 4)
                  if certs else None),
        rm_fresh=_stats([float(r["rm_fresh"]) for r in certs]),
        rm_exceed=sum(1 for r in certs if r["rm_exceed"] == "True"),
        n_cal_carrying=int(rows[0]["n_cal_carrying"]),
        head_auc_s_cal=_stats([float(r["head_auc_oos"]) for r in rows]),
        decline_reasons={r["decline_reason"]: 1 for r in rows
                         if r["certified"] != "True"})


def primary_pooled_section(pooled, attrition):
    rows = {a: [r for r in pooled if r["alpha"] == a] for a in ("0.05", "0.1")}
    certs = [r for r in rows["0.1"] if r["certified"] == "True"]
    att = {r["step"]: r for r in attrition}
    return dict(
        certified_alpha0_10=_ci(len(certs), len(rows["0.1"])),
        certified_alpha0_05=_ci(sum(1 for r in rows["0.05"]
                                    if r["certified"] == "True"),
                                len(rows["0.05"])),
        rm_exceed=_ci(sum(1 for r in certs if r["rm_exceed"] == "True"),
                      len(certs)),
        mean_coverage=round(float(np.mean([float(r["coverage"])
                                           for r in certs])), 4),
        mean_tau=round(float(np.mean([float(r["tau"]) for r in certs])), 4),
        rm_fresh=_stats([float(r["rm_fresh"]) for r in certs]),
        answered_err=_stats([float(r["answered_err_rate"]) for r in certs]),
        per_site_exceed_frac_mean=round(float(np.mean(
            [float(r["per_site_exceed_frac"]) for r in certs])), 4),
        n_target=_stats([float(r["n_target"]) for r in certs], 0),
        n_cal_carrying=int(certs[0]["n_cal_carrying"]),
        cohort=dict(n_stays=int(att["primary-cohort"]["n_stays"]),
                    n_sites=int(att["primary-cohort"]["n_sites"]),
                    prevalence=float(att["primary-cohort"]["prevalence"]),
                    n_sites_apache_result_linked=int(
                        att["apache-result-linked"]["n_sites"])))


# ------------------------------------------------------- synthetic sections

def e1_section(e1):
    sub = [r for r in e1 if r["s_u"] == "0.5" and r["alpha"] == "0.1"]
    base = [r for r in sub if r["certified"] == "True"
            and r["deploy_mode"] == "baseline"]
    return {"baseline_deploying_draws_alpha0.10": len(base),
            "draws": len(sub),
            "note": ("the influence-cap sweep replays these draws; six "
                     "validity-grid draws deployed a BBSE threshold and are "
                     "excluded from Table S4")}


def e9a_section(e9a):
    odds = lambda p: p / (1.0 - p)
    out = dict(population_odds_ratio=round(odds(SHIFT_BASE) / odds(0.095), 3),
               cells={}, exceeding_rows=[])
    keys = sorted({(int(r["n_source_sites"]), r["target_mode"], r["alpha"])
                   for r in e9a}, key=lambda k: (k[0], k[1], k[2]))
    for n, mode, alpha in keys:
        sub = [r for r in e9a if int(r["n_source_sites"]) == n
               and r["target_mode"] == mode and r["alpha"] == alpha]
        certs = [r for r in sub if r["certified"] == "True"]
        exc = [r for r in certs if r["rm_exceed"] == "True"]
        centres_c = [(float(r["rho_lo"]) + float(r["rho_hi"])) / 2
                     for r in certs]
        centres_all = [(float(r["rho_lo"]) + float(r["rho_hi"])) / 2
                       for r in sub if r["rho_lo"] not in ("", None)]
        out["cells"][f"{n}|{mode}|{alpha}"] = dict(
            R=len(sub), certified=_ci(len(certs), len(sub)),
            rm_exceed=_ci(len(exc), len(certs)),
            box_centre_certified=_stats(centres_c),
            box_centre_all_fitted=_stats(centres_all),
            mean_tau=(round(float(np.mean([float(r["tau"]) for r in certs])), 4)
                      if certs else None))
        for r in exc:
            out["exceeding_rows"].append(dict(
                n_source_sites=n, target_mode=mode, draw=int(r["draw"]),
                alpha=float(alpha), tau=float(r["tau"]),
                rm_fresh=float(r["rm_fresh"]),
                rho_lo=round(float(r["rho_lo"]), 4),
                rho_hi=round(float(r["rho_hi"]), 4)))
    return out


def e9b_section(e9b):
    out = dict(cells={}, truth_by_sites={})
    sites = sorted({int(r["n_sites"]) for r in e9b})
    budgets = sorted({float(r["fnr_budget"]) for r in e9b})
    for n in sites:
        truth = [float(r["true_fnr_at_lowest_tau"]) for r in e9b
                 if int(r["n_sites"]) == n
                 and float(r["fnr_budget"]) == budgets[0]]
        out["truth_by_sites"][str(n)] = _stats(truth)
        for b in budgets:
            sub = [r for r in e9b if int(r["n_sites"]) == n
                   and float(r["fnr_budget"]) == b]
            certs = [r for r in sub if r["certified"] == "True"]
            out["cells"][f"{n}|{b}"] = dict(
                R=len(sub), certified=_ci(len(certs), len(sub)),
                fnr_exceed=_ci(sum(1 for r in certs
                                   if r["fnr_exceed"] == "True"), len(certs)),
                mean_fnr_fresh=(round(float(np.mean(
                    [float(r["fnr_fresh"]) for r in certs])), 4)
                    if certs else None))
    return out


def r_counts_section(summary_path):
    blocks = _existing_summary_blocks(summary_path)
    parsed = {}
    for name, block in blocks.items():
        body = block.split("\n", 1)[1].rsplit("\n", 1)[0]
        parsed[name] = json.loads(body)
    e = parsed
    return dict(
        E1=dict(R=e["E1"]["R"], eval_sites=e["E1"]["eval_sites"]),
        E2=dict(R_anchor=e["E2"]["R"], R_sweep=e["E2"]["R_sweep"]),
        E3=dict(R=e["E3"]["R"]), E4=dict(R=e["E4"]["R"]),
        E5=dict(case_study_draws=1,
                R_replication=e["E5"]["replication"]["R"]),
        E6=dict(draws=1), E7=dict(R=e["E7"]["R"]),
        E8=dict(R=e["E8"]["R"], noise_R=e["E8"]["noise_R"],
                n_boot=e["E8"]["n_boot"]),
        E9=dict(R_bbse_frontier=e["E9"]["R"], fnr_R=e["E9"]["fnr_R"]),
        sentence=("R = 200 calibration draws unless stated: the label-shift "
                  "power frontier uses 50 per point, the label-shift "
                  "magnitude sweep 100, the aleatoric frontier 300; the "
                  "explanation case study and the coverage-and-composition "
                  "arm are single draws"))


def exact_cis_section(fair, disp, primary, e9a):
    return {
        "eicu_rm_exceed_0_of_20": primary["rm_exceed"]["ci95"],
        "eicu_alpha0_10_certified_20_of_20": primary["certified_alpha0_10"]["ci95"],
        "eicu_hard_7_of_477": disp["hard"]["ci95"],
        "eicu_pool_too_small_3_of_480": _rate_ci95(3, 480),
        "fairness_cells_8_of_570": _rate_ci95(fair["cells_over_alpha"]["n"],
                                              fair["cells_status_ok"]),
        "e9a_single_site_1200_exceed_alpha0_10":
            e9a["cells"]["1200|single-site-cp|0.1"]["rm_exceed"],
        "e9a_single_site_1200_exceed_alpha0_05":
            e9a["cells"]["1200|single-site-cp|0.05"]["rm_exceed"],
        "note": "exact Clopper-Pearson 95% intervals, run_synthetic._rate_ci95",
    }


def floor_section(cert):
    n = cert["diagnostic"]["n_cal_carrying"]
    feas = cert["diagnostic"]["feasibility"]
    return dict(
        n_cal_carrying=n,
        floor={str(a): round(float(margin_floor(n, DELTA, a)), 4)
               for a in ALPHA_LADDER},
        margin_on_s_aux={k: round(v["margin"], 4) for k, v in feas.items()},
        ratio={k: round(v["ratio"], 3) for k, v in feas.items()},
        estimated_answered_risk_s_cal=round(cert["estimated"]["point"], 4),
        note=("ln(1/delta)(1-alpha)/n at the record-carrying calibration "
              "count; a margin in atom units, a feasibility diagnostic, "
              "never a gate"))


# --------------------------------------------------------------- sidecars

def _sidecar_headline(name, path):
    """Fold in a sidecar's headline block when its output exists."""
    if not os.path.exists(path):
        return dict(status="absent", path=rel_path(path))
    if path.endswith(".json"):
        doc = _read_json(path)
        return dict(status="present", path=rel_path(path),
                    headline=doc.get("headline", "<no headline key>"),
                    run=doc.get("_run", {}).get("utc"))
    return dict(status="present", path=rel_path(path))


def _rev2_sections(paths):
    """Lane C's re-emitted run: only the new columns, only when present."""
    out = {}
    p = paths["rev2_pooled"]
    if os.path.exists(p):
        rows = [r for r in _read_csv(p) if r["alpha"] == "0.1"]
        new_cols = ("head_auc_pool", "head_brier_pool", "head_auc_answered",
                    "head_brier_answered", "apache_iva_auc_pool",
                    "apache_iva_brier_pool", "n_apache_available_pool")
        found = {c: _stats([_f(r[c]) for r in rows]) for c in new_cols
                 if rows and c in rows[0]}
        out["pooled_new_columns"] = found or "no new columns found"
    p = paths["rev2_faithfulness"]
    if os.path.exists(p):
        rows = _read_csv(p)
        reps = sorted({r["replicate"] for r in rows}, key=int)
        per = {}
        for rep in reps:
            sec = faithfulness_section(rows, rep)
            per[rep] = dict(spearman=sec["spearman_abs_coef_vs_abs_gap"],
                            top_driver=sec["features"][0]["feature"],
                            top_driver_delta_mean_abs_z=sec["features"][0]
                            ["delta_mean_abs_z"])
        out["faithfulness_by_replicate"] = per
        out["faithfulness_spearman"] = _stats(
            [v["spearman"] for v in per.values()])
    return out or dict(status="absent")


# ------------------------------------------------------------------- driver

def derive():
    paths = {k: os.path.join(EXP_DIR, v) for k, v in INPUTS.items()}
    side = {k: os.path.join(EXP_DIR, v) for k, v in SIDECARS.items()}
    missing = [rel_path(p) for p in paths.values() if not os.path.exists(p)]
    if missing:
        raise SystemExit(f"derive_fixpass_numbers: missing released inputs "
                         f"{missing} (reason=missing-input)")

    panel = _read_json(paths["panel"])
    pooled = _read_csv(paths["pooled"])
    cert = _read_json(paths["certificate"])
    per_site = _read_csv(paths["per_site"])
    diagnostics = _read_json(paths["diagnostics"])
    preflight = _read_json(paths["preflight"])
    attrition = _read_csv(paths["attrition"])
    subgroups = _read_csv(paths["subgroups"])
    faith = _read_csv(paths["faithfulness"])
    sens_pooled = _read_csv(paths["sens_pooled"])
    sens_att = _read_csv(paths["sens_attrition"])
    e1 = _read_csv(paths["e1"])
    e9a = _read_csv(paths["e9a"])
    e9b = _read_csv(paths["e9b"])

    fair = fairness_section(subgroups)
    disp = dispersion_section(per_site)
    primary = primary_pooled_section(pooled, attrition)
    e9a_sec = e9a_section(e9a)
    three = _finish_three_way(three_way_section(cert, diagnostics), panel)
    doc = {
        "post_hoc": ("[MEASURE] POST-HOC (2026-09-04): read-only derivation "
                     "from released artifacts for the fix pass; certifies "
                     "nothing, settles no registered prediction, and no "
                     "certified quantity descends from it."),
        "composition_20_resplits": composition_section(panel),
        "head_auc_s_cal": head_auc_section(pooled),
        "calibration_20_resplits": calibration_section(panel),
        "three_way_composition": three,
        "primary_pooled": primary,
        "per_hospital_dispersion": disp,
        "published_split": published_split_section(panel, cert, pooled),
        "over_cap_indicators": over_cap_section(preflight, diagnostics),
        "p4_signed": p4_signed_section(diagnostics),
        "fairness": fair,
        "faithfulness_rep0": faithfulness_section(faith, "0"),
        "sensitivity_arm": sens_section(sens_pooled, sens_att),
        "information_floor": floor_section(cert),
        "e1": e1_section(e1),
        "e9a_frozen": e9a_sec,
        "e9b_frozen": e9b_section(e9b),
        "r_counts": r_counts_section(paths["summary"]),
        "exact_cis": exact_cis_section(fair, disp, primary, e9a_sec),
        "sidecars": {k: _sidecar_headline(k, side[k]) for k in
                     ("e9a_rescore", "e9b_positives", "bbse_probe", "settled")},
        "rev2": _rev2_sections(side),
    }

    # The pins: refuse to emit if any stops reproducing.
    def _lookup(path):
        node = doc
        for part in path.split("/"):
            node = node[part]
        return node
    pins = {}
    for name, (expected, dp) in PINS.items():
        got = _lookup(name)
        ok = (round(float(got), dp) == round(float(expected), dp)) if dp \
            else int(got) == int(expected)
        pins[name] = dict(expected=expected, derived=got, status=ok)
        if not ok:
            raise SystemExit(
                f"derive_fixpass_numbers: pin {name} = {got}, expected "
                f"{expected} -- the manuscript and the artifacts have "
                f"drifted; nothing written (reason=pin-failed)")
    doc["pins"] = pins
    read = list(paths.values()) + [side[k] for k in side
                                   if os.path.exists(side[k])]
    return {"_run": run_block(read), **doc}


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="derive the fix-pass numbers from released artifacts")
    ap.add_argument("--out", default=OUT_PATH)
    args = ap.parse_args(argv)
    assert_not_frozen(args.out)
    doc = derive()
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    _write_json(args.out, doc, "derive_fixpass_numbers")
    print(json.dumps(doc, indent=2))
    print(f"[certgate] wrote {args.out}", file=sys.stderr)
    return doc


if __name__ == "__main__":
    main()
