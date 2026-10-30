"""Settle the seven registered eICU predictions against the released artifacts.

The protocol froze seven numbered predictions before any eICU byte was read,
and the preflight wrote them to disk (EICU_preflight.json, key "predictions")
before the first certificate existed. The runner never scored them: the
manuscript's settlement was written by hand, and the panel found it reads
prediction P7 as confirmed when its site clause failed (207 hospitals carried
an outcome, not the 208 registered). This file scores every prediction
clause by clause from the released files, so the settlement can be diffed
against the text instead of trusted.

Everything is read from experiments/out/: the predictions from the preflight,
the observations from EICU_pooled.csv, EICU_per_site.csv,
EICU_diagnostics.json and EICU_attrition.csv. The restricted extract is never
touched, nothing under a frozen output directory is opened for writing, and
EICU-SUMMARY.md is never a target -- its section list is an append-only pin,
so the settlement lives in its own file.

How a verdict is reached. Every quantitative phrase in a prediction is a
clause with a registered range and an observed value. A prediction whose
protocol entry states its own falsification rule (P3: "falsified if BBSE
certifies a tau the baseline walk does not") is confirmed unless that rule
fires, and its other clauses are reported beside it. Otherwise: confirmed when
every clause holds; falsified when the clause on the registered settling
quantity fails; partly when that clause holds but another registered count
does not. Quantities that exist once per re-split are scored on the majority
of the twenty, with the published split (replicate 0) shown separately; a
prediction that registers an aggregate over the re-splits (P6's mean
coverage) is scored on that aggregate, taken at each re-split's operative
rung (its strictest certified alpha). P3's falsification rule is checked on
all 25 pools of every re-split at both rungs. The rule is printed in the
output so a reader can disagree with it in the open.

Run: python -m experiments.settle_predictions --out DIR
     (the released out-settled/ is refused, so a bare run writes nothing)

Writes EICU-PREDICTIONS-SETTLED.md and .json into DIR; the released copy is
experiments/out-settled/, frozen as released.
The JSON carries a _run block (UTC, git sha, sha256 of every input read).

Refs: EICU-PROTOCOL 9 (the predictions), 14.1 (operator checklist);
fix-pass plan WP2; panel action items 11 and 23.
"""

import argparse
import collections
import os
import sys

import numpy as np

from experiments.derive_fixpass_numbers import (EXP_DIR, assert_not_frozen,
                                                is_apache_absence,
                                                operative_rankings,
                                                run_block, rel_path,
                                                _read_csv, _read_json)
from experiments.run_eicu import _write_json

OUT_DIR = os.path.join(EXP_DIR, "out-settled")
INPUTS = dict(
    preflight="out/EICU_preflight.json",
    pooled="out/EICU_pooled.csv",
    per_site="out/EICU_per_site.csv",
    diagnostics="out/EICU_diagnostics.json",
    attrition="out/EICU_attrition.csv",
)
ALPHA_OPERATIVE = "0.1"
N_REPLICATES = 20
N_TARGET_HOSPITALS = 24                 # per re-split; the pooled arm is the 25th pool
VERDICTS = ("confirmed", "partly", "falsified")

POST_HOC = ("[MEASURE] POST-HOC (2026-09-04): clause-level settlement of the "
            "seven registered predictions, derived from the released "
            "artifacts after the fact; certifies nothing and changes no "
            "certified quantity. The registered wording is quoted from "
            "EICU_preflight.json verbatim.")

RULE = ("A prediction whose protocol entry states its own falsification rule "
        "is confirmed unless that rule fires; its other clauses are reported "
        "beside it. Otherwise: confirmed when every clause holds; falsified "
        "when the clause on the registered settling quantity fails; partly "
        "when that clause holds but another registered count does not. "
        "Per-re-split quantities are scored on the majority of the twenty; "
        "the published split (replicate 0) is shown separately.")


def _clause(text, registered, observed, met, **extra):
    return dict(clause=text, registered=registered, observed=observed,
                met=bool(met), **extra)


def _majority(k, n=N_REPLICATES):
    return k > n / 2


def _operative_rows(pooled):
    """{replicate: its certified pooled row at the operative rung}: the
    strictest certified alpha (report.py), the selection
    run_eicu._failure_criteria makes for F-B's mean_operative_coverage."""
    ops = {}
    for r in pooled:
        if r["certified"] != "True":
            continue
        rep = int(r["replicate"])
        if rep not in ops or float(r["alpha"]) < float(ops[rep]["alpha"]):
            ops[rep] = r
    return ops


def _reasons_bbse(cell):
    """The bbse-mode reasons in a pipe-joined 'mode:reason' cell."""
    return [part[len("bbse:"):] for part in (cell or "").split("|")
            if part.startswith("bbse:")]


_MODES = ("baseline", "bbse")


def _reason_key(r):
    """The reason column: 'reason' on EICU_per_site.csv, 'decline_reason' on
    EICU_pooled.csv."""
    return "reason" if "reason" in r else "decline_reason"


def _mode_outcomes(cell):
    """A pipe-joined 'mode:outcome' cell -> {mode: outcome}; gate tokens
    such as 'pool-too-small' carry no colon and are skipped."""
    return dict(part.split(":", 1) for part in (cell or "").split("|")
                if ":" in part)


def _covering_modes(r):
    """The modes backing the deployed tau on one pool row; empty if declined.

    EICU_pooled.csv carries them in 'modes'. EICU_per_site.csv has no such
    column, but on a certified row its reason cell lists exactly the modes
    that did NOT back the deployed tau (run_eicu._eval_rung,
    skip="covering"), so the covering set is the complement."""
    if r["certified"] != "True":
        return set()
    if r.get("modes"):
        return set(filter(None, r["modes"].split("|")))
    return set(_MODES) - set(_mode_outcomes(r[_reason_key(r)]))


def _bbse_certified(r):
    """Whether BBSE certified on this pool row: it backs the deployed tau, or
    it certified a threshold that does not cover it."""
    return r["certified"] == "True" and (
        "bbse" in _covering_modes(r)
        or _mode_outcomes(r[_reason_key(r)]).get("bbse")
        == "certified-not-covering")


def _bbse_rule_fires(r):
    """P3's falsification rule on one pool row: BBSE certified a tau the
    baseline walk did not (audit 2026-10 EICU-12).

    The deployed tau is the larger of the modes' taus (report._combine_alpha).
    The rule fires when BBSE backs the deployed tau and baseline does not, or
    when BBSE is certified-not-covering: baseline deployed, so BBSE's own tau
    lies below every tau baseline certified. With both modes covering, the
    released fields cannot show whether BBSE also certified a lower tau; that
    case never arises in the released data, where BBSE certified nothing."""
    return _bbse_certified(r) and _covering_modes(r) != set(_MODES)


# ---------------------------------------------------------------- P1 .. P7

def settle_p1(pooled):
    op = [r for r in pooled if r["alpha"] == ALPHA_OPERATIVE]
    strict = [r for r in pooled if r["alpha"] == "0.05"]
    k10 = sum(r["certified"] == "True" for r in op)
    k05_refused = sum(r["certified"] != "True" for r in strict)
    both = sum(1 for a, b in zip(sorted(op, key=lambda r: int(r["replicate"])),
                                 sorted(strict, key=lambda r: int(r["replicate"])))
               if a["certified"] == "True" and b["certified"] != "True")
    clauses = [
        _clause("alpha = 0.10 certifies on the pooled arm", ">= 15 of 20",
                f"{k10} of {len(op)}", k10 >= 15),
        _clause("alpha = 0.05 does not certify on the pooled arm",
                ">= 15 of 20", f"{k05_refused} of {len(strict)}",
                k05_refused >= 15),
        _clause("both hold in the same re-split", ">= 15 of 20",
                f"{both} of {len(op)}", both >= 15),
    ]
    return clauses, "confirmed" if all(c["met"] for c in clauses) \
        else "falsified", None


def settle_p2(pooled):
    op = [r for r in pooled if r["alpha"] == ALPHA_OPERATIVE]
    # A re-split with no deployed tau leaves the cell blank (so does a tau no
    # target hospital answers at): it meets neither clause, and the majority
    # stays over all twenty (audit 2026-10 EICU-12). P2 stays on the
    # alpha = 0.10 rows: at 0.05 the per-site bar is 0.05, a different
    # quantity from the registered alpha = 0.10 synthetic comparators.
    by_rep = {int(r["replicate"]): float(r["per_site_exceed_frac"])
              for r in op if r["per_site_exceed_frac"] not in ("", None)}
    vals = [by_rep[k] for k in sorted(by_rep)]
    k_dir = sum(v > 0.02 for v in vals)
    k_int = sum(0.05 <= v <= 0.30 for v in vals)
    mean = f"{np.mean(vals):.4f}" if vals else "none"
    span = f"[{min(vals):.4f}, {max(vals):.4f}]" if vals else "none"
    pub = f"{by_rep[0]:.4f}" if 0 in by_rep else "none"
    clauses = [
        _clause("per-site dispersion diagnostic at the deployed tau, pooled "
                "arm, exceeds 0.02", "> 0.02 (direction)",
                f"{k_dir} of {N_REPLICATES} re-splits; mean {mean}; "
                f"published split {pub}", _majority(k_dir)),
        _clause("... and lands inside the registered interval",
                "[0.05, 0.30] (settling quantity)",
                f"{k_int} of {N_REPLICATES} re-splits; range {span}",
                _majority(k_int)),
    ]
    verdict = "confirmed" if all(c["met"] for c in clauses) else (
        "falsified" if not clauses[1]["met"] else "partly")
    # Erratum 2026-10-29 (EICU-PROTOCOL.md, dated erratum to P2; audit
    # 2026-10 EICU-3): the 0.02 below, like the registration's, is E1's
    # single-fresh-site hard-violation rate at s_u = 0.5
    # (hard_violation_rate_diag); on per_site_exceed_frac, the statistic
    # scored here, that arm gave 0.055 (0.1634 at s_u = 2.0), above the eICU
    # mean of 0.0271. "The registered floor" reads true only as the
    # interval's 0.05 (the mean clears the 0.02 direction floor). The string
    # stays as released (it is emitted into the frozen out-settled/); no
    # verdict uses it. The script no longer reproduces out-settled/ byte for
    # byte: the P4 clause label names the registered aps_/apv_ set (audit
    # 2026-10 EICU-12), and out-settled/ is not re-emitted.
    note = ("real hospitals were LESS dispersed at the deployed tau than "
            "the registered floor; the synthetic s_u = 0.5 arm gave 0.02")
    return clauses, verdict, dict(
        per_replicate=[(round(by_rep[i], 4) if i in by_rep else None)
                       for i in range(N_REPLICATES)], note=note)


def settle_p3(pooled, per_site):
    op_pool = {r["replicate"]: r for r in pooled
               if r["alpha"] == ALPHA_OPERATIVE}
    per_rep = []
    modal_hits = 0
    for rep in range(N_REPLICATES):
        rows = [r for r in per_site if r["replicate"] == str(rep)
                and r["alpha"] == ALPHA_OPERATIVE]
        pooled_row = op_pool[str(rep)]
        reasons = collections.Counter()
        n_pools = len(rows) + 1
        n_bbse_declined = 0
        for r in rows + [pooled_row]:
            if _bbse_certified(r):
                continue          # a BBSE certificate, not a decline
            key = _reason_key(r)
            if r[key] == "pool-too-small":
                n_bbse_declined += 1          # gated before either mode ran
                continue
            rs = _reasons_bbse(r[key])
            if rs:
                n_bbse_declined += 1
                reasons.update(rs)
        share = n_bbse_declined / n_pools
        modal = reasons.most_common(1)[0][0] if reasons else None
        modal_ok = modal in ("bbse-misspecified", "bbse-ill-conditioned")
        modal_hits += modal_ok
        per_rep.append(dict(replicate=rep, n_pools=n_pools,
                            bbse_declined_share=round(share, 4),
                            reasons=dict(reasons), modal_reason=modal))
    # The falsification rule names no rung and covers all 25 pools: a pool
    # counts once if, at either rung, BBSE certified a tau the baseline walk
    # did not (audit 2026-10 EICU-12; the per-site table has no modes
    # column, and the old check read it as never-BBSE).
    bbse_only = len({(r["replicate"], r.get("site", "pooled"))
                     for r in pooled + per_site if _bbse_rule_fires(r)})
    k_share =sum(d["bbse_declined_share"] >= 0.90 for d in per_rep)
    clauses = [
        _clause("BBSE declines on the pools of each re-split",
                ">= 90% of the 25 pools per re-split",
                f"{k_share} of {N_REPLICATES} re-splits at >= 0.90 "
                f"(min share {min(d['bbse_declined_share'] for d in per_rep)})",
                _majority(k_share)),
        _clause("the modal BBSE decline reason", "bbse-misspecified or "
                "bbse-ill-conditioned", f"modal reason met in {modal_hits} of "
                f"{N_REPLICATES} re-splits; failsafe is modal in "
                f"{N_REPLICATES - modal_hits} (characterisation clause)",
                _majority(modal_hits)),
        _clause("falsification rule: BBSE certifies a tau the baseline walk "
                "does not", "0 pools", f"{bbse_only} pools over "
                f"{N_REPLICATES} re-splits", bbse_only == 0),
    ]
    verdict = "falsified" if bbse_only > 0 or not clauses[0]["met"] \
        else "confirmed"
    note = ("P3 carries its own falsification rule in the protocol, which "
            "did not fire; the modal-reason phrase is a characterisation of "
            "the mechanism and is reported as it came out (bbse-misspecified "
            f"modal in {modal_hits} of {N_REPLICATES} re-splits; failsafe, "
            "meaning the mode fit but certified no threshold at both "
            f"endpoints, modal in {N_REPLICATES - modal_hits}). Under a "
            "stricter every-clause reading this would be 'partly'.")
    return clauses, verdict, dict(per_replicate=per_rep, note=note)


def settle_p4(diagnostics):
    per = []
    # one ranking per re-split, at its operative rung; the registered set is
    # the presence flags and the aps_/apv_ __missing siblings only (audit
    # 2026-10 EICU-12)
    for rep, blk in operative_rankings(diagnostics).items():
        top3 = blk["ranking"][:3]
        hits = [dict(feature=e["feature"], gap=e["gap"]) for e in top3
                if is_apache_absence(e["feature"])]
        per.append(dict(replicate=rep,
                        top3=[dict(feature=e["feature"], gap=e["gap"])
                              for e in top3],
                        unsigned_hit=bool(hits),
                        signed_hit=any(h["gap"] < 0 for h in hits),
                        hits=hits))
    per.sort(key=lambda d: d["replicate"])
    k_unsigned = sum(d["unsigned_hit"] for d in per)
    k_signed = sum(d["signed_hit"] for d in per)
    leak = diagnostics["leak_probe"]
    alarms = sum(1 for l in leak if l["auc_alarm"] or l["ablation_alarm"])
    om = diagnostics["outcome_missingness"]
    gate_fired = any(v["gate_applies"] and v["prevalence_ratio"] > v["cap"]
                     for v in om.values())
    flagged = diagnostics["outcome_screen"]["n_flagged"]
    clauses = [
        _clause("an APACHE-absence feature (aps_present, apv_present or an "
                "aps_*__missing / apv_*__missing sibling) sits in the top 3 "
                "of the abstention gap ranking, pooled arm (registered "
                "unsigned rule)",
                "top 3 (every re-split)",
                f"{k_unsigned} of {N_REPLICATES} re-splits",
                _majority(k_unsigned)),
        _clause("... with the registered leak sign (more attribution on "
                "declined stays, gap < 0) -- the signed reading",
                "gap < 0", f"{k_signed} of {N_REPLICATES} re-splits; the "
                f"{k_unsigned} unsigned hits all carry positive gaps",
                _majority(k_signed)),
        _clause("amendment A1 precondition: every F-D leg clear and the "
                "prevalence-ratio gate silent, so a hit would read as "
                "confirmation and not as the leak signature",
                "0 alarms, gate not fired",
                f"{alarms} leak alarms, {flagged} flagged screens, gate "
                f"fired={gate_fired}", alarms == 0 and not gate_fired),
    ]
    verdict = "confirmed" if clauses[0]["met"] and clauses[2]["met"] \
        else "falsified"
    hits_text = "; ".join(
        f"re-split {d['replicate']}: " + ", ".join(
            f"{h['feature']} {h['gap']:+.3f}" for h in d["hits"])
        for d in per if d["unsigned_hit"])
    note = (f"the unsigned rule holds on {k_unsigned} of {N_REPLICATES} "
            f"re-splits ({hits_text}); both hits pull harder on ANSWERED "
            "stays, the opposite direction from the registered leak "
            "signature, so under a signed reading P4 holds on "
            f"{k_signed} of {N_REPLICATES}")
    return clauses, verdict, dict(per_replicate=per, note=note)


def settle_p5(per_site):
    counts = []
    for rep in range(N_REPLICATES):
        rows = [r for r in per_site if r["replicate"] == str(rep)
                and r["alpha"] == ALPHA_OPERATIVE]
        counts.append(sum(r["reason"] == "pool-too-small" for r in rows))
    k = sum(1 <= c <= 6 for c in counts)
    clauses = [
        _clause("the per-hospital arm returns pool-too-small for some of "
                "the 24 target hospitals", ">= 1 and <= 6 of 24, per re-split",
                f"in range on {k} of {N_REPLICATES} re-splits; counts "
                f"{sorted(collections.Counter(counts).items())} "
                f"(published split {counts[0]}; total "
                f"{sum(counts)} of {N_REPLICATES * N_TARGET_HOSPITALS})",
                _majority(k)),
    ]
    verdict = "confirmed" if clauses[0]["met"] else "falsified"
    note = ("the floor bit on fewer hospitals than registered: 3 pools of "
            "480 over the 20 re-splits, never more than one per re-split")
    return clauses, verdict, dict(per_replicate=counts, note=note)


def settle_p6(pooled):
    # P6 registers a MEAN over the re-splits (F-B's mean_operative_coverage),
    # so it is scored on that mean, each re-split read at its operative rung;
    # the per-re-split count is shown beside it (audit 2026-10 EICU-12)
    ops = _operative_rows(pooled)
    cov = [float(ops[k]["coverage"]) for k in sorted(ops)]
    k = sum(0.60 <= v <= 0.95 for v in cov)
    mean = float(np.mean(cov)) if cov else None
    observed = "no re-split certified"
    if cov:
        observed = (f"{k} of {len(cov)} re-splits inside; mean {mean:.4f}, "
                    f"range [{min(cov):.4f}, {max(cov):.4f}]")
    clauses = [
        _clause("mean coverage at the operative rung, pooled arm",
                "[0.60, 0.95]", observed,
                mean is not None and 0.60 <= mean <= 0.95),
    ]
    verdict = "confirmed" if clauses[0]["met"] else "falsified"
    return clauses, verdict, dict(per_replicate=[round(v, 4) for v in cov])


def settle_p7(attrition):
    att = {r["step"]: r for r in attrition}
    prim, arl = att["primary-cohort"], att["apache-result-linked"]
    n_stays, n_sites = int(prim["n_stays"]), int(prim["n_sites"])
    n_arl = int(arl["n_sites"])
    raw_sites = int(att["raw-unit-stays"]["n_sites"])
    clauses = [
        _clause("primary-cohort size (settling quantity)",
                "[130 000, 175 000] stays", f"{n_stays:,}",
                130_000 <= n_stays <= 175_000),
        _clause("primary-cohort hospital count", "208 sites",
                f"{n_sites} ({raw_sites} in the raw unit-stay table; one "
                "hospital carries no stay with a known outcome)",
                n_sites == 208),
        _clause("apache-result-linked hospital count", "<= 195 sites "
                "(>= 13 hospitals deleted)", f"{n_arl} ({n_sites - n_arl} "
                "deleted from the primary cohort)",
                n_arl <= 195),
    ]
    if all(c["met"] for c in clauses):
        verdict = "confirmed"
    elif clauses[0]["met"]:
        verdict = "partly"
    else:
        verdict = "falsified"
    note = ("the size and APACHE-linkage clauses hold; the site clause "
            "failed by one hospital (207, not 208), which the manuscript's "
            "hand-written settlement had scored as confirmed")
    return clauses, verdict, None


# ------------------------------------------------------------------ driver

def settle(paths=None):
    paths = paths or {k: os.path.join(EXP_DIR, v) for k, v in INPUTS.items()}
    missing = [rel_path(p) for p in paths.values() if not os.path.exists(p)]
    if missing:
        raise SystemExit(f"settle_predictions: missing released inputs "
                         f"{missing} (reason=missing-input)")
    preflight = _read_json(paths["preflight"])
    pooled = _read_csv(paths["pooled"])
    per_site = _read_csv(paths["per_site"])
    diagnostics = _read_json(paths["diagnostics"])
    attrition = _read_csv(paths["attrition"])
    registered = {p["id"]: p for p in preflight["predictions"]}
    if sorted(registered) != [f"P{i}" for i in range(1, 8)]:
        raise SystemExit(f"settle_predictions: expected P1..P7 in the "
                         f"preflight, found {sorted(registered)} "
                         f"(reason=predictions-drifted)")

    settled = {
        "P1": settle_p1(pooled),
        "P2": settle_p2(pooled),
        "P3": settle_p3(pooled, per_site),
        "P4": settle_p4(diagnostics),
        "P5": settle_p5(per_site),
        "P6": settle_p6(pooled),
        "P7": settle_p7(attrition),
    }
    predictions = []
    for pid in sorted(settled):
        clauses, verdict, extra = settled[pid]
        if verdict not in VERDICTS:
            raise AssertionError(f"settle_predictions: bad verdict {verdict}")
        entry = dict(id=pid, registered=registered[pid]["prediction"],
                     settled_by=registered[pid]["settled_by"],
                     verdict=verdict, clauses=clauses)
        if extra:
            entry.update(extra)
        predictions.append(entry)
    tally = {v: sum(1 for p in predictions if p["verdict"] == v)
             for v in VERDICTS}
    doc = {
        "post_hoc": POST_HOC,
        "rule": RULE,
        "tally": tally,
        "tally_text": (f"{tally['confirmed']} confirmed / {tally['partly']} "
                       f"partly / {tally['falsified']} falsified"),
        "headline": (f"{tally['confirmed']} confirmed / {tally['partly']} "
                     f"partly / {tally['falsified']} falsified; partly = "
                     + ", ".join(p["id"] for p in predictions
                                 if p["verdict"] == "partly")
                     + "; falsified = "
                     + ", ".join(p["id"] for p in predictions
                                 if p["verdict"] == "falsified")),
        "manuscript_before_fix": ("four confirmed (P1, P3, P6, P7), three "
                                  "falsified (P2, P4, P5); P7's site clause "
                                  "was not scored"),
        "predictions": predictions,
    }
    return {"_run": run_block(list(paths.values())), **doc}


def render_md(doc):
    lines = ["# eICU-CRD v2.0 -- the seven registered predictions, settled",
             "",
             doc["post_hoc"], "",
             f"**Tally: {doc['tally_text']}.** Before this file the "
             f"manuscript read: {doc['manuscript_before_fix']}.", "",
             f"**Rule.** {doc['rule']}", "",
             "| id | verdict | registered (verbatim) | settled by |",
             "|---|---|---|---|"]
    for p in doc["predictions"]:
        reg = p["registered"].replace("|", "/")
        lines.append(f"| {p['id']} | **{p['verdict']}** | {reg} | "
                     f"{p['settled_by'].replace('|', '/')} |")
    lines.append("")
    for p in doc["predictions"]:
        lines += [f"## {p['id']} -- {p['verdict']}", "",
                  "| clause | registered | observed | met |",
                  "|---|---|---|---|"]
        for c in p["clauses"]:
            lines.append(f"| {c['clause']} | {c['registered']} | "
                         f"{c['observed']} | {'yes' if c['met'] else 'NO'} |")
        if p.get("note"):
            lines += ["", f"Note: {p['note']}"]
        lines.append("")
    r = doc["_run"]
    lines += ["## Provenance", "",
              f"- utc: {r['utc']}", f"- git sha: {r['git_sha']}",
              "- inputs (sha256):"]
    lines += [f"    - `{k}` {v}" for k, v in r["inputs"].items()]
    lines.append("")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="settle the seven registered eICU predictions")
    ap.add_argument("--out", default=OUT_DIR,
                    help="output directory (never a frozen one; the "
                         "default, the released out-settled/, is refused)")
    args = ap.parse_args(argv)
    md_path = os.path.join(args.out, "EICU-PREDICTIONS-SETTLED.md")
    json_path = os.path.join(args.out, "EICU-PREDICTIONS-SETTLED.json")
    for p in (md_path, json_path):
        assert_not_frozen(p)
    doc = settle()
    os.makedirs(args.out, exist_ok=True)
    _write_json(json_path, doc, "settle_predictions",
                per_item_keys=("predictions",))
    with open(md_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(render_md(doc))
    print(render_md(doc))
    print(f"[certgate] wrote {md_path} and {json_path}", file=sys.stderr)
    return doc


if __name__ == "__main__":
    main()
