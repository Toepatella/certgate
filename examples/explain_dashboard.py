"""Self-contained interactive HTML dashboard for the explanation layer.

Renders, for a scored cohort at one operating threshold, what a reader sees
per case — and lets them interrogate it live. Two audiences, one toggle, two
genuinely different UIs:

PLAIN LANGUAGE (default) — an airy clinician view with no jargon: verdicts in
everyday words, percentages instead of logits, a "how to read this page"
walkthrough, live what-if controls, one-click smallest-change flips, and a
printable case summary.

ADVANCED — an analyst workbench: a tabbed detail panel (Decision / Waterfall /
Response / Numbers / Hospitals / Calibration), a live status bar carrying the
raw quantities, a waterfall of the logit build-up, exact per-feature response
curves with the counterfactual crossings marked, a full-precision numbers
table, per-hospital coverage and answered-error (the site is the unit the
guarantee is stated over), a retrospective reliability curve, CSV/JSON export,
a click-to-filter cohort histogram, the full-cohort abstention profile, and
keyboard shortcuts with a help overlay. Both modes get dark mode and print
styling.

REAL-FEATURE STRUCTURE (2026-07-31, after the first eICU run). A real matrix is
not 161 free-moving numbers: 64 of them are ONE-HOT levels of 6 categoricals
and 47 are MISSINGNESS flags paired to a parent value. A slider on either is
not just useless, it builds an input vector no patient could have — two
genders at once, or a "measured" value whose own flag says it was never
recorded. So the page now:

  * renders each one-hot group as a single DROPDOWN, setting the chosen level
    to 1 and its siblings to 0, so every what-if is a legal vector;
  * pairs each parent with its flag: a not-recorded parent is shown greyed
    with a "not recorded" chip (its number is the imputation placeholder, not
    a measurement), and toggling the flag says so;
  * tags each counterfactual by what KIND of change it asks for — physiology,
    category, or a pure recording artifact, which is not a clinical change at
    all;
  * formats deltas to significant figures, because on a near-threshold real
    case every row rounded to "+0.000" at three decimals.

The output is ONE .html file with no external assets or network access. The
embedded data is record-level BY DESIGN (the page recomputes the head's own
arithmetic offline), which is harmless for the synthetic demo and is a DUA
matter for anything built from a restricted extract: those builds are
gitignored (`explain_dashboard_eicu*.html`) and stay on the analyst's machine.
Per-case OUTCOMES are additionally opt-in (`include_outcomes=True`) and always
labelled retrospective. Nothing here touches the certified path and this
script never writes into ``experiments/out``.

Honesty constraints carried into the page itself (SPEC explain.py):
  * counterfactuals, what-ifs and curves are SCORE-SPACE questions to the gate
    ("what would the gate need"), never causal or clinical advice;
  * the minimal flip clears the bar by the documented 1e-9 logit headroom, so
    it is the WEAKEST answerable answer;
  * the certificate is a site-population-average guarantee — no single record
    carries a certified property, and an UNCERTIFIED build says so loudly;
  * the threshold explorer is fenced as intuition-only;
  * the abstention panel states the replicated E5 null (abstention is
    cancellation; no stable single-feature driver);
  * every display cap is disclosed on the page — never a silent truncation.

Run:  python -m examples.explain_dashboard   (writes examples/explain_dashboard.html)
"""
from __future__ import annotations

import json
import os

import numpy as np

from certgate.explain import cohort_abstention_profile, counterfactual_to_answer
from certgate.constants import SEED
from certgate.data import SimConfig, draw_cohort, split_sites
from certgate.model import fit_head

_MAX_ANSWERED_SHOWN = 60
_MAX_DECLINED_SHOWN = 500
_MISSING_SUFFIXES = ("__missing", " (not recorded)")


def _pretty(name):
    """Display name: drop the block prefix, say 'not recorded' in words."""
    out = name
    for pre in ("aps_", "apv_"):
        if out.startswith(pre):
            out = out[len(pre):]
    if out.endswith("__missing"):
        out = out[: -len("__missing")] + " (not recorded)"
    return out


def _stem(name):
    for suf in _MISSING_SUFFIXES:
        if name.lower().endswith(suf):
            return name[: -len(suf)].strip()
    return None


def _classify(names):
    """Group features and recover one-hot groups + parent/flag pairs."""
    groups, onehot = [], {}
    demo = {"age", "age_masked", "gender", "ethnicity", "admissionheight",
            "admissionweight", "pre_icu_hours"}
    for j, nm in enumerate(names):
        if "=" in nm:
            key, level = nm.split("=", 1)
            onehot.setdefault(key.strip(), []).append([j, level.strip()])
            groups.append("categoricals")
        elif _stem(nm) is not None:
            groups.append("recording flags")
        elif nm.lower() in demo or nm.lower().lstrip("aps_apv_") in demo:
            groups.append("demographics")
        elif nm.startswith("apv_"):
            groups.append("chronic / treatment")
        else:
            groups.append("physiology")
    by_stem = {}
    for j, nm in enumerate(names):
        s = _stem(nm)
        if s is not None:
            by_stem[s.lower()] = j
    flag_of = {}                       # parent index -> flag index
    for j, nm in enumerate(names):
        f = by_stem.get(nm.strip().lower())
        if f is not None and f != j:
            flag_of[j] = f
    return groups, onehot, flag_of


def _case_payload(head, x_row, idx, tau_star, names, site=None, outcome=None):
    cf = counterfactual_to_answer(head, x_row, tau_star)
    out = {
        "idx": int(idx),
        "declined": bool(cf["declined"]),
        "margin_to_answer": round(cf["margin_to_answer"], 6),
        "x": [float(v) for v in np.asarray(x_row, dtype=np.float64)],
        "counterfactuals": [],
        "delta_x_min": None,
        "l2_distance_z": (round(cf["l2_distance_z"], 6)
                          if np.isfinite(cf["l2_distance_z"]) else None),
        "confidence_at_flip": (round(cf["confidence_at_flip"], 6)
                               if cf["confidence_at_flip"] is not None else None),
    }
    if site is not None:
        out["site"] = str(site)
    if outcome is not None:
        out["outcome"] = bool(outcome)
    if cf["declined"] and cf["flip_verified"]:
        out["delta_x_min"] = [float(v) for v in cf["delta_x_min_l2"]]
        for j in cf["single_feature_ranking"][:6]:
            j = int(j)
            out["counterfactuals"].append({
                "j": j,
                "delta_x": float(cf["single_feature_delta_x"][j]),
                "delta_z": float(cf["single_feature_delta_z"][j]),
                "answers_as": "predicted-positive" if cf["answered_class_on_flip"]
                              else "predicted-negative",
            })
    return out


def build_dashboard(head, x, tau_star, out_path, feature_names=None,
                    oracle_y=None, cohort_label="synthetic demonstration cohort",
                    certificate=None, site_ids=None, include_outcomes=False):
    """Write a self-contained interactive explanation dashboard for ``x``.

    ``feature_names`` are RAW model names (``aps_ph``, ``gender=Male``,
    ``aps_ph__missing``); display names and the one-hot / missingness
    structure are derived from them. ``certificate`` renders the deployment's
    certificate banner — pass ``None`` and the page shows an explicit
    UNCERTIFIED DEMONSTRATION banner instead. ``site_ids`` adds the hospital
    each case came from (the unit the guarantee is stated over) and enables
    the per-hospital panel. ``oracle_y`` enables the AGGREGATE retrospective
    panels (composition, reliability); per-case outcome reveal additionally
    requires ``include_outcomes=True`` and is always labelled retrospective.

    Display caps are disclosed on the page, never silent. Returns ``out_path``.
    """
    x = np.asarray(x, dtype=np.float64)
    n, d = x.shape
    if feature_names is None:
        feature_names = [f"feature {j}" for j in range(d)]
    feature_names = list(feature_names)
    display = [_pretty(nm) for nm in feature_names]
    groups, onehot, flag_of = _classify(feature_names)
    binary = [bool(np.all(np.isin(np.unique(x[:, j]), (0.0, 1.0))))
              for j in range(d)]

    scores = head.score(x)
    answered = scores >= tau_star
    p1 = np.asarray(head.predict_proba(x), dtype=np.float64)
    oracle = None if oracle_y is None else np.asarray(oracle_y, dtype=bool)
    sites = None if site_ids is None else [str(s) for s in site_ids]

    declined_idx = np.flatnonzero(~answered)
    answered_idx = np.flatnonzero(answered)

    def _spread(pool, cap):
        """Cap the browsable set, round-robin ACROSS HOSPITALS.

        Taking the first N clusters by row order, which on a site-sorted
        extract means a handful of hospitals -- and the site is the unit the
        guarantee is stated over, so a browser that shows 4 of 24 hospitals
        misrepresents the deployment. Deterministic: hospitals in sorted
        order, cases within a hospital in index order.
        """
        if sites is None or len(pool) <= cap:
            return pool[:cap]
        by = {}
        for i in pool:
            by.setdefault(sites[i], []).append(i)
        out, keys = [], sorted(by)
        while len(out) < cap and any(by[k] for k in keys):
            for k in keys:
                if by[k] and len(out) < cap:
                    out.append(by[k].pop(0))
        return np.array(sorted(out), dtype=int)

    shown_dec = _spread(declined_idx, _MAX_DECLINED_SHOWN)
    shown_ans = _spread(answered_idx, _MAX_ANSWERED_SHOWN)
    cases = [
        _case_payload(head, x[i], i, tau_star, feature_names,
                      site=None if sites is None else sites[i],
                      outcome=None if (oracle is None or not include_outcomes)
                              else bool(oracle[i]))
        for i in np.concatenate([shown_dec, shown_ans])
    ]

    prof = cohort_abstention_profile(head, x, answered)

    def _clean(arr):
        return [None if not np.isfinite(v) else round(float(v), 6) for v in arr]

    # ---- aggregate panels (safe regardless of include_outcomes) -----------
    per_site = None
    if sites is not None:
        agg = {}
        for i, s in enumerate(sites):
            e = agg.setdefault(s, {"site": s, "n": 0, "n_answered": 0,
                                   "n_err": 0, "n_pos": 0})
            e["n"] += 1
            if answered[i]:
                e["n_answered"] += 1
                if oracle is not None:
                    pred = p1[i] >= 0.5
                    if bool(pred) != bool(oracle[i]):
                        e["n_err"] += 1
                    if oracle[i]:
                        e["n_pos"] += 1
        per_site = []
        for e in agg.values():
            row = {"site": e["site"], "n": e["n"], "n_answered": e["n_answered"],
                   "coverage": round(e["n_answered"] / e["n"], 4) if e["n"] else None}
            if oracle is not None and e["n_answered"]:
                row["answered_err"] = round(e["n_err"] / e["n_answered"], 4)
                row["answered_pos_frac"] = round(e["n_pos"] / e["n_answered"], 4)
            per_site.append(row)
        per_site.sort(key=lambda r: -r["n"])

    reliability = None
    if oracle is not None:
        edges = [0.0, 0.02, 0.05, 0.10, 0.20, 0.35, 0.55, 1.01]
        reliability = []
        for lo, hi in zip(edges[:-1], edges[1:]):
            m = answered & (p1 >= lo) & (p1 < hi)
            k = int(m.sum())
            reliability.append({
                "lo": lo, "hi": min(hi, 1.0), "n": k,
                "mean_predicted": round(float(p1[m].mean()), 4) if k else None,
                "observed": round(float(oracle[m].mean()), 4) if k else None})

    composition = {
        "predicted_positive_fraction":
            round(float((p1[answered] >= 0.5).mean()), 4) if answered.any() else None,
        "oracle_positive_fraction_answered":
            (round(float(oracle[answered].mean()), 4)
             if oracle is not None and answered.any() else None),
        "oracle_positive_fraction_declined":
            (round(float(oracle[~answered].mean()), 4)
             if oracle is not None and (~answered).any() else None),
        "oracle_positive_fraction_cohort":
            round(float(oracle.mean()), 4) if oracle is not None else None,
    }

    payload = {
        "tau_star": float(tau_star),
        "cohort_label": cohort_label,
        "certificate": certificate,
        "n_total": int(n),
        "n_answered": int(answered.sum()),
        "n_declined": int((~answered).sum()),
        "coverage": round(float(answered.mean()), 4),
        "feature_names": display,
        "raw_names": feature_names,
        "groups": groups,
        "onehot": onehot,
        "flag_of": {str(k): v for k, v in flag_of.items()},
        "binary": binary,
        "head": {"coef": [float(v) for v in head.coef],
                 "mu": [float(v) for v in head.mu],
                 "sd": [float(v) for v in head.sd],
                 "intercept": float(head.intercept)},
        "all_scores": [round(float(s), 4) for s in scores],
        "composition": composition,
        "per_site": per_site,
        "reliability": reliability,
        "include_outcomes": bool(include_outcomes and oracle is not None),
        "has_oracle": oracle is not None,
        "shown": {"declined": int(len(shown_dec)), "answered": int(len(shown_ans)),
                  "declined_total": int(len(declined_idx)),
                  "answered_total": int(len(answered_idx))},
        "abstention_profile": {
            "mean_abs_phi_answered": _clean(prof["mean_abs_phi_answered"]),
            "mean_abs_phi_declined": _clean(prof["mean_abs_phi_declined"]),
            "n_answered": int(prof["n_answered"]),
            "n_declined": int(prof["n_declined"]),
        },
        "cases": cases,
    }
    html = _HTML_TEMPLATE.replace("__PAYLOAD__",
                                  json.dumps(payload, sort_keys=True))
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html)
    return out_path


_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CertGate Explain</title>
<style>
  :root { --ink:#1a2233; --mut:#5b6572; --line:#d8dee7; --bg:#f4f6fa;
          --card:#ffffff; --pos:#2563eb; --neg:#b45309; --dec:#b91c1c;
          --ans:#15803d; --chip:#e8edf5; --hl:#eef4ff; --histbar:#c7d4e8;
          --histdec:#f3b8b8; --fence:#fffbf5; --amber:#fef3c7; --ambert:#92400e;
          --shadow:0 1px 3px rgba(16,24,40,.07); }
  body.dark { --ink:#e6ebf3; --mut:#98a2b3; --line:#2a3446; --bg:#0f1520;
          --card:#171e2b; --pos:#5b8def; --neg:#d98f3d; --dec:#e05d5d;
          --ans:#3fae6a; --chip:#232c3d; --hl:#1d2a44; --histbar:#33415c;
          --histdec:#5c3434; --fence:#1c1a14; --amber:#3a300f; --ambert:#f4d47c;
          --shadow:0 1px 3px rgba(0,0,0,.4); }
  * { box-sizing:border-box; }
  body { margin:0; font:15px/1.55 system-ui,Segoe UI,Roboto,sans-serif;
         color:var(--ink); background:var(--bg); }
  body.adv { font-size:13.5px; }
  header { padding:16px 22px 4px; max-width:1240px; margin:0 auto; }
  h1 { font-size:19px; margin:0 0 2px; }
  body.adv h1 { font-size:17px; }
  h2 { font-size:14px; margin:0 0 8px; }
  .sub { color:var(--mut); font-size:13px; }
  main { max-width:1240px; margin:0 auto; padding:10px 22px 30px; }
  .card { background:var(--card); border:1px solid var(--line);
          border-radius:12px; padding:15px 17px; margin:12px 0;
          box-shadow:var(--shadow); }
  body.adv .card { border-radius:8px; padding:12px 14px; }
  .caveat { border-left:4px solid var(--dec); font-size:13px; }
  .caveat b { color:var(--dec); }
  .strip { display:flex; gap:18px; flex-wrap:wrap; font-size:13px; }
  .strip div b { display:block; font-size:17px; }
  .cols { display:flex; gap:12px; align-items:flex-start; flex-wrap:wrap; }
  .side { flex:0 0 286px; max-width:100%; }
  .detail { flex:1 1 520px; min-width:320px; }
  .chip { display:inline-block; padding:3px 10px; border-radius:999px;
          background:var(--chip); cursor:pointer; font-size:12.5px;
          border:1px solid transparent; user-select:none; }
  .chip.on { background:var(--hl); border-color:var(--pos); color:var(--pos);
             font-weight:600; }
  .tag { display:inline-block; padding:1px 7px; border-radius:999px;
         font-size:11px; background:var(--chip); color:var(--mut); }
  .tag.rec { background:var(--amber); color:var(--ambert); }
  .tag.cat { background:var(--hl); color:var(--pos); }
  input[type=text], select { font:inherit; padding:5px 8px; color:var(--ink);
          background:var(--card); border:1px solid var(--line);
          border-radius:8px; width:100%; }
  .cl { margin-top:8px; max-height:420px; overflow-y:auto;
        border:1px solid var(--line); border-radius:8px; }
  .cl div { padding:5px 9px; cursor:pointer; font-size:12.5px;
            border-bottom:1px solid var(--line); }
  .cl div:last-child { border-bottom:none; }
  .cl div:hover { background:var(--hl); }
  .cl div.sel { background:var(--hl); font-weight:600; }
  .cl .m { color:var(--mut); }
  .verdict { display:inline-block; padding:2px 10px; border-radius:999px;
             color:#fff; font-weight:600; font-size:13px; }
  .verdict.declined { background:var(--dec); }
  .verdict.answered { background:var(--ans); }
  .badge { display:inline-block; padding:1px 8px; border-radius:999px;
           background:var(--amber); color:var(--ambert); font-size:11.5px;
           font-weight:600; margin-left:8px; }
  button { font:inherit; font-size:12.5px; padding:6px 10px; margin:2px 4px 2px 0;
           border:1px solid var(--line); border-radius:8px; background:var(--card);
           color:var(--ink); cursor:pointer; }
  button:hover { background:var(--hl); }
  button.primary { border-color:var(--pos); color:var(--pos); font-weight:600; }
  button.attn { border-color:var(--dec); color:var(--dec); font-weight:600; }
  .gauge { position:relative; height:26px; background:linear-gradient(90deg,
           #fee2e2,#fef9c3 55%,#dcfce7); border-radius:6px;
           border:1px solid var(--line); margin:8px 0 2px; }
  body.dark .gauge { background:linear-gradient(90deg,#3d1d1d,#3a300f 55%,#15321f); }
  .gauge .tau { position:absolute; top:-4px; bottom:-4px; width:2px; background:var(--ink); }
  .gauge .tau::after { content:attr(data-l); position:absolute; top:-16px;
                left:-14px; font-size:11px; color:var(--ink); }
  .gauge .needle { position:absolute; top:2px; bottom:2px; width:8px;
                   border-radius:4px; background:var(--pos); transition:left .15s; }
  .gaxis { display:flex; justify-content:space-between; font-size:11px; color:var(--mut); }
  .srow { display:grid; grid-template-columns:150px 1fr 82px 18px; gap:8px;
          align-items:center; margin:2px 0; }
  .srow label { font-size:12px; color:var(--mut); text-align:right;
                white-space:nowrap; overflow:hidden; cursor:pointer; }
  .srow label:hover { color:var(--pos); }
  .srow label.notrec { opacity:.55; font-style:italic; }
  .srow input[type=range] { width:100%; accent-color:var(--pos); }
  .srow .v { font-size:12px; font-variant-numeric:tabular-nums; }
  .srow .v.imp { color:var(--ambert); }
  .rst { color:var(--dec); cursor:pointer; font-size:14px; line-height:1;
         user-select:none; visibility:hidden; }
  .rst.on { visibility:visible; }
  table { border-collapse:collapse; width:100%; font-size:13px; }
  th,td { text-align:left; padding:4px 8px; border-bottom:1px solid var(--line); }
  th { color:var(--mut); font-weight:600; }
  .barrow { display:flex; align-items:center; gap:8px; margin:2px 0; }
  .barlab { width:150px; font-size:12px; color:var(--mut); text-align:right;
            overflow:hidden; white-space:nowrap; }
  .barbox { flex:1; display:flex; height:13px; position:relative; }
  .barbox .mid { position:absolute; left:50%; top:-2px; bottom:-2px; width:1px;
                 background:var(--line); }
  .bar { height:13px; border-radius:3px; transition:width .15s; }
  .bar.pos { background:var(--pos); margin-left:50%; }
  .bar.neg { background:var(--neg); }
  .barval { width:66px; font-size:11.5px; color:var(--mut);
            font-variant-numeric:tabular-nums; }
  .hist { display:flex; align-items:flex-end; height:90px; gap:1px;
          position:relative; margin-top:6px; }
  .hist .hb { flex:1; background:var(--histbar); border-radius:2px 2px 0 0; min-height:1px; }
  .hist .hb.dec { background:var(--histdec); }
  body.adv .hist .hb { cursor:pointer; }
  body.adv .hist .hb:hover { outline:1.5px solid var(--pos); }
  .hist .hb.hsel { outline:2px solid var(--pos); }
  .hist .tau { position:absolute; top:-4px; bottom:-14px; width:2px; background:var(--ink); }
  .num { font-variant-numeric:tabular-nums; }
  .note { color:var(--mut); font-size:12px; }
  .fence { border:1.5px dashed var(--neg); border-radius:10px; padding:12px 16px;
           margin:12px 0; background:var(--fence); }
  .fence b.t { color:var(--neg); }
  .certb { border-radius:10px; padding:10px 16px; margin:12px 0 0; font-size:13px;
           border:1.5px solid; }
  .certb.uncert { border-color:var(--dec); color:var(--dec); background:var(--fence);
                  font-weight:600; }
  .certb.cert { border-color:var(--ans); background:var(--fence); }
  .certb.cert b { color:var(--ans); }
  .certb .cl2 { font-weight:400; color:var(--mut); font-size:12px; display:block;
                margin-top:2px; }
  .tabs { display:flex; gap:4px; border-bottom:1px solid var(--line);
          margin:10px 0; flex-wrap:wrap; }
  .tabbtn { padding:5px 12px; font-size:12.5px; cursor:pointer;
            border:1px solid transparent; border-bottom:none;
            border-radius:8px 8px 0 0; color:var(--mut); user-select:none; }
  .tabbtn.on { background:var(--hl); border-color:var(--line); color:var(--pos);
               font-weight:600; }
  .tabpane { display:none; }
  .tabpane.on { display:block; }
  body.simple #tab-decision { display:block !important; }
  .statusbar { display:flex; gap:16px; flex-wrap:wrap; margin-top:12px;
               padding:7px 10px; border:1px solid var(--line); border-radius:8px;
               background:var(--bg); font-size:11.5px; color:var(--mut);
               font-variant-numeric:tabular-nums; }
  .statusbar b { color:var(--ink); font-weight:600; }
  svg text { fill:var(--mut); font:10.5px system-ui; }
  svg .axis { stroke:var(--line); stroke-width:1; }
  svg .curve { stroke:var(--pos); stroke-width:2; fill:none; }
  svg .tauline { stroke:var(--ink); stroke-width:1; stroke-dasharray:4 3; }
  svg .cross { fill:var(--dec); }
  svg .nowpt { fill:var(--pos); }
  .helpov { position:fixed; inset:0; background:rgba(10,14,20,.55); display:none; z-index:50; }
  .helpov.on { display:flex; align-items:center; justify-content:center; }
  .helpov .card { max-width:460px; }
  .profrow { display:flex; align-items:center; gap:8px; margin:2px 0; }
  .profrow .plab { width:150px; font-size:12px; color:var(--mut); text-align:right;
                   overflow:hidden; white-space:nowrap; }
  .profrow .pbox { flex:1; height:12px; display:flex; gap:2px; }
  .profrow .pa { background:var(--ans); height:12px; border-radius:2px; }
  .profrow .pd { background:var(--dec); height:12px; border-radius:2px; }
  .profrow .pval { width:150px; font-size:11px; color:var(--mut);
                   font-variant-numeric:tabular-nums; }
  .grphead { margin:10px 0 2px; font-size:12px; font-weight:600; color:var(--pos);
             cursor:pointer; user-select:none; }
  .outc { display:inline-block; padding:1px 7px; border-radius:999px; font-size:11px;
          font-weight:600; }
  .outc.d { background:#fee2e2; color:#991b1b; }
  .outc.s { background:#dcfce7; color:#166534; }
  body.dark .outc.d { background:#4a1d1d; color:#fca5a5; }
  body.dark .outc.s { background:#14351f; color:#86efac; }
  @media print {
    .side,.fence,.modebar,.hist,.gaxis,footer,.tabs,.statusbar,#cohortstrip,
    .helpov,button,.sub,#profpanel { display:none !important; }
    .card { box-shadow:none; border-color:#bbb; page-break-inside:avoid; }
    body { background:#fff; }
  }
</style>
</head>
<body class="simple">
<header>
  <div class="modebar" style="float:right;display:flex;gap:6px;flex-wrap:wrap">
    <span class="chip on" id="modeSimple" title="everyday language, no jargon">Plain language</span>
    <span class="chip" id="modeAdv" title="analyst workbench">Advanced</span>
    <span class="chip" id="outcT" title="reveal what actually happened (retrospective)">Outcomes</span>
    <span class="chip" id="darkT" title="dark mode">&#9789;</span>
    <span class="chip" id="printT" title="print the selected case">Print</span>
  </div>
  <h1>CertGate Explain</h1>
  <div class="sub">
    <span class="simponly">A safety gate sits in front of this computer model:
      it answers only when confident enough, and hands everything else to a
      person. Pick a case to see why it decided the way it did &mdash; and try
      changing the inputs yourself.</span>
    <span class="advonly" id="subtitleAdv"></span>
  </div>
</header>
<main>
  <div id="certbanner"></div>
  <div class="card caveat">
    <span class="simponly">
      <b>Read this first.</b> This page describes the <b>computer program</b>,
      never the patient. "What would need to change for the computer to answer"
      is a fact about how the program decides &mdash; <b>not</b> medical advice,
      <b>not</b> a treatment suggestion, and not something anyone could do to a
      patient. A case flipped by the smallest change is answered with the
      <b>lowest confidence the program is allowed</b>. The safety promise is
      about <b>average</b> mistakes across many hospitals, not any one case
      here. Data shown: <span id="cohortlabelS"></span>.
    </span>
    <span class="advonly">
      <b>Read this first.</b> Every interactive control asks a <b>score-space</b>
      question of the gate: <i>what would the model's inputs need to be</i> for
      this case to clear the answering bar. Not causal claims, not treatment
      suggestions, not clinically achievable actions. The minimal flip clears
      the bar by the documented 1e-9 logit headroom &mdash; the <b>weakest
      answerable</b> answer. The certificate is a
      <b>site-population-average</b> guarantee over answered cases: no
      individual record carries a certified property. Cohort:
      <span id="cohortlabel"></span>.
    </span>
  </div>

  <details class="simponly card" style="margin-top:0">
    <summary>How to read this page (30 seconds)</summary>
    <ol class="note">
      <li><b>Pick a case</b> on the left. Green = the program answered; red =
        it wasn't sure enough and handed the case to a person.</li>
      <li><b>The meter</b> shows how sure it was. It must clear the dark line.</li>
      <li><b>The bars</b> show what pushed confidence up or down. When pushes
        and pulls cancel out, it hands the case over.</li>
      <li><b>Try the controls</b> &mdash; change a value and watch it re-decide.
        The red button puts everything back.</li>
      <li>Values marked <i>not recorded</i> were never measured for this
        patient; the number beside them is a stand-in the model fills in.</li>
    </ol>
  </details>

  <div class="card">
    <div class="strip" id="cohortstrip"></div>
    <div class="hist" id="hist"></div>
    <div class="gaxis">
      <span><span class="simponly">totally unsure (50/50)</span><span class="advonly">score 0.50</span></span>
      <span><span class="simponly">completely certain</span><span class="advonly">1.00</span></span></div>
    <div class="note">
      <span class="simponly">Every case, grouped by how sure the program was.
        Red bars: not sure enough, handed to a person.</span>
      <span class="advonly">Confidence-score distribution over all
        <span id="ntot"></span> cases; red bins sit below &#964;* =
        <span id="taulab"></span>. Click a bin to filter the case list.</span></div>
    <div class="advonly" id="profpanel" style="margin-top:12px"></div>
  </div>

  <div class="cols">
    <div class="side card">
      <h2>Cases</h2>
      <span class="chip" data-f="all">all</span>
      <span class="chip on" data-f="declined"><span class="simponly">handed over</span><span class="advonly">declined</span></span>
      <span class="chip" data-f="answered">answered</span>
      <span class="chip" id="binclear" style="display:none">score filter &#10005;</span>
      <div style="margin:8px 0 4px"><input type="text" id="search" placeholder="search case number&#8230;" aria-label="search cases"></div>
      <div id="sitewrap" style="margin-bottom:4px"></div>
      <select id="sortSel" aria-label="sort cases">
        <option value="margin_asc">most borderline first</option>
        <option value="margin_desc">least borderline first</option>
        <option value="idx">by case number</option>
      </select>
      <div style="margin-top:6px">
        <button id="jmpContested">most contested</button>
        <button id="jmpRandom">random</button>
      </div>
      <div class="cl" id="caselist"></div>
      <div class="note" id="capnote" style="margin-top:6px"></div>
    </div>
    <div class="detail card" id="detail"></div>
  </div>

  <div class="fence" id="explorer">
    <b class="t"><span class="simponly">What if the bar were set differently? &mdash; just for understanding.</span><span class="advonly">Threshold explorer &mdash; intuition only.</span></b>
    <span class="note"><span class="simponly">In real use the bar is set by the
      safety certificate, never by hand. Sliding it changes nothing above and
      promises nothing.</span><span class="advonly">Deployed thresholds are
      selected by the certificate; moving this confers no guarantee and does
      not change the verdicts above.</span></span><br>
    <div class="srow" style="grid-template-columns:150px 1fr 260px">
      <label><span class="simponly">try a bar</span><span class="advonly">explore &#964;</span></label>
      <input type="range" id="tauX" min="0.55" max="0.99" step="0.01" aria-label="explore threshold">
      <span class="v" id="tauXv"></span>
    </div>
  </div>
</main>
<div class="helpov" id="helpov"><div class="card">
  <h2>Keyboard shortcuts</h2>
  <table>
    <tr><td><kbd>&#8592;</kbd>/<kbd>&#8594;</kbd></td><td>previous / next case</td></tr>
    <tr><td><kbd>1</kbd>&#8211;<kbd>6</kbd></td><td>Decision / Waterfall / Response / Numbers / Hospitals / Calibration</td></tr>
    <tr><td><kbd>f</kbd></td><td>apply smallest flip</td></tr>
    <tr><td><kbd>r</kbd></td><td>reset to recorded inputs</td></tr>
    <tr><td><kbd>o</kbd></td><td>toggle retrospective outcomes</td></tr>
    <tr><td><kbd>?</kbd></td><td>this panel</td></tr>
  </table>
  <button id="helpclose">Close</button>
</div></div>
<footer>
  <span class="simponly">This page works entirely on your computer &mdash;
    nothing is sent anywhere. It re-runs the program's own arithmetic, so what
    you see is the real decision rule. Switch to <b>Advanced</b> for full
    technical detail.</span>
  <span class="advonly">CertGate Explain. Generated by
    <code>examples/explain_dashboard.py</code>; recomputes the head's float64
    arithmetic locally, so sliders, flips, curves and waterfalls re-run the
    deployed rule <code>score &gt;= &#964;</code>. Attributions are exact
    interventional Shapley values; counterfactuals from
    <code>counterfactual_to_answer</code>; abstention profile from
    <code>cohort_abstention_profile</code> (SPEC "explain.py"). Self-contained,
    no network. Builds from a restricted extract embed record-level data and
    are gitignored.</span>
</footer>
<script>
"use strict";
const DATA = __PAYLOAD__;
const H = DATA.head, TAU = DATA.tau_star, NAMES = DATA.feature_names;
const RAW = DATA.raw_names, D = NAMES.length;
const L_STAR = Math.log(TAU/(1-TAU));
const FLAG_OF = DATA.flag_of || {};          // parent -> flag
const PARENT_OF = {};
Object.keys(FLAG_OF).forEach(p => { PARENT_OF[FLAG_OF[p]] = +p; });
const ONEHOT = DATA.onehot || {};
const MEMBER_GROUP = {};                     // feature index -> onehot key
Object.keys(ONEHOT).forEach(k => ONEHOT[k].forEach(([j]) => MEMBER_GROUP[j] = k));

const sigfmt = (v, n) => {
  n = n || 3;
  if (v === 0) return "0";
  const a = Math.abs(v);
  if (a >= 1e4 || a < 1e-3) return v.toExponential(2);
  const dec = Math.max(0, n - 1 - Math.floor(Math.log10(a)));
  return v.toFixed(Math.min(dec, 6));
};
const signed = v => (v >= 0 ? "+" : "") + sigfmt(v);
const fmt = (v, n=4) => (v === null || v === undefined) ? "—" : (+v).toFixed(n);

const sigmoid = z => z >= 0 ? 1/(1+Math.exp(-z)) : (e => e/(1+e))(Math.exp(z));
const logitOf = x => { let s = H.intercept;
  for (let j = 0; j < D; j++) s += H.coef[j]*(x[j]-H.mu[j])/H.sd[j]; return s; };
const scoreOf = x => { const p = sigmoid(logitOf(x)); return Math.max(p, 1-p); };
const riskOf = x => sigmoid(logitOf(x));
const phiOf = x => H.coef.map((c,j) => c*(x[j]-H.mu[j])/H.sd[j]);

const dual = (s,a) => "<span class='simponly'>"+s+"</span><span class='advonly'>"+a+"</span>";
function kindOf(j) {
  if (MEMBER_GROUP[j] !== undefined) return "category";
  if (PARENT_OF[j] !== undefined) return "recording";
  return "clinical";
}
function kindTag(j) {
  const k = kindOf(j);
  if (k === "recording") return "<span class='tag rec'>" +
    dual("about record-keeping, not the patient", "recording artifact") + "</span>";
  if (k === "category") return "<span class='tag cat'>" + dual("category", "one-hot level") + "</span>";
  return "";
}

function setMode(m) {
  document.body.classList.remove("simple","adv");
  document.body.classList.add(m);
  document.getElementById("modeSimple").classList.toggle("on", m === "simple");
  document.getElementById("modeAdv").classList.toggle("on", m === "adv");
  if (m === "adv") redrawAdvanced();
}
document.getElementById("modeSimple").onclick = () => setMode("simple");
document.getElementById("modeAdv").onclick = () => setMode("adv");
document.getElementById("darkT").onclick = e => {
  document.body.classList.toggle("dark"); e.target.classList.toggle("on"); };
document.getElementById("printT").onclick = () => window.print();
let showOutcomes = false;
const outcChip = document.getElementById("outcT");
if (!DATA.include_outcomes) { outcChip.style.opacity = .4;
  outcChip.title = "per-case outcomes were not included in this build"; }
outcChip.onclick = () => {
  if (!DATA.include_outcomes) return;
  showOutcomes = !showOutcomes;
  outcChip.classList.toggle("on", showOutcomes);
  rebuildList(order[cur]); };

// ---- certification banner ----
(function(){
  const el = document.getElementById("certbanner"), C = DATA.certificate;
  if (!C) {
    el.innerHTML = "<div class='certb uncert' role='status'>" + dual(
      "&#9888; DEMONSTRATION ONLY — this deployment carries NO safety certificate. The threshold here exists to show the displays; none of its answers carry any guarantee.",
      "&#9888; UNCERTIFIED DEMONSTRATION — no certificate attaches to this operating threshold. Explanations are shown WITHOUT the guarantee that is the system's point; do not quote numbers from this page as certified.") + "</div>";
  } else {
    const f = Object.keys(C).sort().map(k => k + " = " + C[k]);
    el.innerHTML = "<div class='certb cert'><b>&#10003; Certified deployment</b> — " +
      f.join(" · ") + "<span class='cl2'>The certificate bounds a " +
      "site-population-average error rate among answered cases; it is not a " +
      "per-record or per-site property, and it certifies no single answer on " +
      "this page.</span></div>";
  }
})();

document.getElementById("subtitleAdv").textContent =
  "τ* = " + TAU + " (L* = " + L_STAR.toFixed(6) + ") · " + DATA.cohort_label +
  " · " + D + " features (" + Object.keys(ONEHOT).length + " one-hot groups, " +
  Object.keys(PARENT_OF).length + " recording flags)";
document.getElementById("cohortlabel").textContent = DATA.cohort_label;
document.getElementById("cohortlabelS").textContent = DATA.cohort_label;
document.getElementById("taulab").textContent = TAU;
document.getElementById("ntot").textContent = DATA.n_total.toLocaleString();
const strip = document.getElementById("cohortstrip");
const stat = (s,a,val,pct) => {
  const el = document.createElement("div");
  const shown = (typeof val === "number" && val % 1)
    ? dual(pct ? (val*100).toFixed(1)+"%" : fmt(val), fmt(val))
    : (val === null ? "—" : (+val).toLocaleString());
  el.innerHTML = "<b class='num'>"+shown+"</b>"+dual(s,a); strip.appendChild(el); };
stat("cases reviewed","cases scored",DATA.n_total);
stat("answered","answered",DATA.n_answered);
stat("handed to a person","declined",DATA.n_declined);
stat("share answered","coverage",DATA.coverage,true);
const CP = DATA.composition;
stat("of answered: flagged higher-risk","answered predicted-positive",CP.predicted_positive_fraction,true);
if (CP.oracle_positive_fraction_answered !== null) {
  stat("of answered: truly higher-risk (known only retrospectively)",
       "answered oracle-positive (retrospective)",CP.oracle_positive_fraction_answered,true);
  stat("of handed-over: truly higher-risk","declined oracle-positive (retrospective)",
       CP.oracle_positive_fraction_declined,true);
}

// ---- histogram ----
const NB = 50, bins = new Array(NB).fill(0);
DATA.all_scores.forEach(s => bins[Math.min(NB-1, Math.floor((s-0.5)/0.5*NB))]++);
let binSel = null;
const hist = document.getElementById("hist"), bmax = Math.max(...bins);
bins.forEach((n,b) => {
  const lo = 0.5+b*0.5/NB, hi = lo+0.5/NB;
  const el = document.createElement("div");
  el.className = "hb" + (hi <= TAU ? " dec" : "");
  el.style.height = (n/bmax*100).toFixed(1)+"%";
  el.title = n+" cases in ["+lo.toFixed(3)+", "+hi.toFixed(3)+")";
  el.onclick = () => {
    if (!document.body.classList.contains("adv")) return;
    const same = binSel && binSel[0] === lo;
    [...hist.children].forEach(c => c.classList && c.classList.remove("hsel"));
    binSel = same ? null : [lo,hi];
    if (!same) el.classList.add("hsel");
    document.getElementById("binclear").style.display = binSel ? "inline-block" : "none";
    rebuildList(); };
  hist.appendChild(el); });
const tl = document.createElement("div"); tl.className = "tau";
tl.style.left = ((TAU-0.5)/0.5*100).toFixed(2)+"%"; hist.appendChild(tl);
document.getElementById("binclear").onclick = () => {
  binSel = null; [...hist.children].forEach(c => c.classList && c.classList.remove("hsel"));
  document.getElementById("binclear").style.display = "none"; rebuildList(); };

// ---- abstention profile ----
(function(){
  const P = DATA.abstention_profile;
  if (!P || P.mean_abs_phi_declined.some(v => v === null)) return;
  const idx = NAMES.map((_,j) => j)
    .sort((a,b) => (P.mean_abs_phi_declined[b]-P.mean_abs_phi_answered[b])
                 - (P.mean_abs_phi_declined[a]-P.mean_abs_phi_answered[a]))
    .slice(0, 14);
  const mx = Math.max(...P.mean_abs_phi_answered, ...P.mean_abs_phi_declined, 1e-9);
  let h = "<h2>Cohort abstention profile <span class='note'>mean |&#966;| per feature, " +
    "answered ("+P.n_answered.toLocaleString()+") vs declined ("+P.n_declined.toLocaleString()+
    "), full cohort · top 14 by gap</span></h2>";
  idx.forEach(j => {
    const a = P.mean_abs_phi_answered[j], d = P.mean_abs_phi_declined[j];
    h += "<div class='profrow'><div class='plab' title='"+NAMES[j]+"'>"+NAMES[j]+"</div>"+
      "<div class='pbox'><div class='pa' style='width:"+(a/mx*50).toFixed(1)+"%'></div>"+
      "<div class='pd' style='width:"+(d/mx*50).toFixed(1)+"%'></div></div>"+
      "<div class='pval'>ans "+a.toFixed(3)+" · dec "+d.toFixed(3)+"</div></div>"; });
  h += "<p class='note'>Interpretation caution (replicated E5 null, R=200): no single " +
    "feature is a stable abstention driver — a decline is a CANCELLATION of signed " +
    "contributions, a configuration property no per-feature magnitude can localize. " +
    "Read gaps descriptively, never causally.</p>";
  document.getElementById("profpanel").innerHTML = h;
})();

// ---- case browser ----
let filter = "declined", query = "", sortBy = "margin_asc", siteSel = "";
let order = [], cur = 0, xCur = null, selFeat = 0;
let featShowAll = false, featQuery = "", visIdx = [];
const wlog = [];
const caseList = document.getElementById("caselist");

(function(){
  const sites = [...new Set(DATA.cases.map(c => c.site).filter(Boolean))].sort();
  if (!sites.length) return;
  const w = document.getElementById("sitewrap");
  w.innerHTML = "<select id='siteSel' aria-label='filter by hospital'><option value=''>all hospitals ("+sites.length+")</option>" +
    sites.map(s => "<option value='"+s+"'>"+s+"</option>").join("") + "</select>";
  document.getElementById("siteSel").onchange = e => { siteSel = e.target.value; rebuildList(); };
})();

function logEvt(msg) {
  wlog.unshift("case "+DATA.cases[order[cur]].idx+" · "+msg);
  if (wlog.length > 60) wlog.length = 60;
  const lb = document.getElementById("logbox");
  if (lb) lb.innerHTML = wlog.map(e => "<div>"+e+"</div>").join(""); }
function computeVisIdx() {
  const all = NAMES.map((_,j) => j).filter(j => MEMBER_GROUP[j] === undefined);
  if (featQuery) { const q = featQuery.toLowerCase();
    return all.filter(j => NAMES[j].toLowerCase().includes(q)); }
  if (all.length <= 20 || featShowAll) return all;
  const c = DATA.cases[order[cur]], phi = phiOf(xCur);
  const keep = new Set(all.slice().sort((a,b) => Math.abs(phi[b])-Math.abs(phi[a])).slice(0,12));
  all.forEach(j => { if (xCur[j] !== c.x[j]) keep.add(j); });
  return all.filter(j => keep.has(j)); }

function rebuildList(keepCase) {
  const kept = keepCase === undefined ? null : DATA.cases[keepCase].idx;
  order = DATA.cases.map((c,i) => i).filter(i => {
    const c = DATA.cases[i];
    if (filter === "declined" && !c.declined) return false;
    if (filter === "answered" && c.declined) return false;
    if (query && !String(c.idx).includes(query)) return false;
    if (siteSel && c.site !== siteSel) return false;
    if (binSel) { const s = scoreOf(c.x); if (s < binSel[0] || s >= binSel[1]) return false; }
    return true; });
  order.sort((a,b) => {
    const A = DATA.cases[a], B = DATA.cases[b];
    if (sortBy === "idx") return A.idx - B.idx;
    const dd = Math.abs(A.margin_to_answer) - Math.abs(B.margin_to_answer);
    return sortBy === "margin_asc" ? dd : -dd; });
  cur = Math.max(0, order.findIndex(i => DATA.cases[i].idx === kept));
  caseList.innerHTML = "";
  order.forEach((i,k) => {
    const c = DATA.cases[i], row = document.createElement("div");
    let extra = c.site ? " · "+c.site : "";
    if (showOutcomes && c.outcome !== undefined)
      extra += " <span class='outc "+(c.outcome?"d":"s")+"'>"+
        (c.outcome ? "died" : "survived")+"</span>";
    row.innerHTML = "case "+c.idx+" <span class='m'>"+
      (c.declined ? dual(Math.abs(c.margin_to_answer) < 0.1
          ? "handed over · a whisker away" : "handed to a person",
          "declined · margin "+sigfmt(c.margin_to_answer))
        : "answered")+extra+"</span>";
    if (k === cur) row.className = "sel";
    row.onclick = () => { cur = k; selectCase(); };
    caseList.appendChild(row); });
  const S = DATA.shown;
  document.getElementById("capnote").innerHTML =
    "Showing " + order.length + " of " + (S.declined_total+S.answered_total).toLocaleString() +
    " cases. This build embeds " + S.declined.toLocaleString() + " of " +
    S.declined_total.toLocaleString() + " declined and " + S.answered.toLocaleString() +
    " of " + S.answered_total.toLocaleString() + " answered — cohort-level panels " +
    "above use ALL cases.";
  if (order.length) selectCase();
  else document.getElementById("detail").innerHTML = "<p class='note'>No cases match.</p>"; }

function selectCase() {
  [...caseList.children].forEach((el,k) => el.className = k === cur ? "sel" : "");
  const el = caseList.children[cur];
  if (el) el.scrollIntoView({block:"nearest"});
  xCur = DATA.cases[order[cur]].x.slice();
  renderDetail(); }

// ---- visualizations ----
function bars(phi, lead, idxs) {
  const use = idxs || phi.map((_,j) => j);
  const mx = Math.max(...use.map(j => Math.abs(phi[j]*lead)), 1e-9);
  return use.map(j => {
    const v = phi[j]*lead, w = Math.abs(v)/mx*50;
    const bar = v >= 0 ? "<div class='bar pos' style='width:"+w+"%'></div>"
      : "<div class='bar neg' style='width:"+w+"%;margin-left:"+(50-w)+"%'></div>";
    return "<div class='barrow'><div class='barlab' title='"+NAMES[j]+"'>"+NAMES[j]+
      "</div><div class='barbox'><div class='mid'></div>"+bar+"</div>"+
      "<div class='barval num'>"+sigfmt(v)+"</div></div>"; }).join(""); }

function waterfallSVG() {
  const phi = phiOf(xCur);
  let ord = phi.map((v,j) => j).sort((a,b) => Math.abs(phi[b])-Math.abs(phi[a]));
  let rest = []; if (ord.length > 14) { rest = ord.slice(14); ord = ord.slice(0,14); }
  const steps = [["intercept", H.intercept]];
  ord.forEach(j => steps.push([NAMES[j], phi[j]]));
  if (rest.length) steps.push(["other ("+rest.length+")", rest.reduce((s,j)=>s+phi[j],0)]);
  let cum = 0;
  const pts = steps.map(([lab,v]) => { const f = cum; cum += v; return [lab,f,cum]; });
  const lo = Math.min(-L_STAR, ...pts.map(p=>Math.min(p[1],p[2])))-0.3;
  const hi = Math.max(L_STAR, ...pts.map(p=>Math.max(p[1],p[2])))+0.3;
  const W = 660, Hh = 40+24*pts.length, X = v => 170+(v-lo)/(hi-lo)*(W-190);
  let s = "<svg viewBox='0 0 "+W+" "+Hh+"' style='max-width:100%'>";
  [[L_STAR,"+L*"],[-L_STAR,"−L*"],[0,"0"]].forEach(([v,lab]) => {
    s += "<line class='tauline' x1='"+X(v)+"' y1='14' x2='"+X(v)+"' y2='"+(Hh-16)+
      "'/><text x='"+(X(v)-8)+"' y='11'>"+lab+"</text>"; });
  pts.forEach(([lab,a,b],i) => {
    const y = 22+24*i, x0 = X(Math.min(a,b)), w = Math.max(Math.abs(X(b)-X(a)),1.5);
    s += "<text x='164' y='"+(y+10)+"' text-anchor='end'>"+lab+"</text>"+
      "<rect x='"+x0+"' y='"+y+"' width='"+w+"' height='13' rx='2' fill='"+
      (i===0?"var(--mut)":((b-a)>=0?"var(--pos)":"var(--neg)"))+"'/>"+
      "<text x='"+(X(Math.max(a,b))+4)+"' y='"+(y+10)+"'>"+
      (i===0?sigfmt(a):signed(b-a))+"</text>"; });
  const fx = X(pts[pts.length-1][2]);
  s += "<line x1='"+fx+"' y1='14' x2='"+fx+"' y2='"+(Hh-16)+
    "' stroke='var(--pos)' stroke-width='2'/><text x='"+(fx+4)+"' y='"+(Hh-4)+
    "'>logit "+sigfmt(pts[pts.length-1][2],5)+"</text>";
  return s+"</svg>"; }

function responseHTML(j) {
  const g = MEMBER_GROUP[j];
  if (g !== undefined) {                       // categorical: level table
    let h = "<p class='note'>Exact effect of switching <b>"+g+"</b> to each of "+
      "its levels, all other inputs held at their current what-if values.</p>"+
      "<table><tr><th>level</th><th>risk</th><th>confidence</th><th>gate</th></tr>";
    ONEHOT[g].forEach(([jj,level]) => {
      const t = xCur.slice();
      ONEHOT[g].forEach(([kk]) => t[kk] = 0.0); t[jj] = 1.0;
      const sc = scoreOf(t), on = xCur[jj] >= 0.5;
      h += "<tr"+(on?" style='font-weight:600'":"")+"><td>"+level+(on?" ← current":"")+
        "</td><td class='num'>"+(riskOf(t)*100).toFixed(1)+"%</td><td class='num'>"+
        sc.toFixed(4)+"</td><td>"+(sc>=TAU?"answers":"declines")+"</td></tr>"; });
    return h+"</table>"; }
  if (DATA.binary[j]) {
    let h = "<p class='note'>Exact effect of each state of <b>"+NAMES[j]+"</b>.</p>"+
      "<table><tr><th>state</th><th>risk</th><th>confidence</th><th>gate</th></tr>";
    [0,1].forEach(v => { const t = xCur.slice(); t[j] = v; const sc = scoreOf(t);
      h += "<tr"+(xCur[j]===v?" style='font-weight:600'":"")+"><td>"+(v?"yes":"no")+
        (xCur[j]===v?" ← current":"")+"</td><td class='num'>"+(riskOf(t)*100).toFixed(1)+
        "%</td><td class='num'>"+sc.toFixed(4)+"</td><td>"+(sc>=TAU?"answers":"declines")+
        "</td></tr>"; });
    return h+"</table>"; }
  const lo = H.mu[j]-4*H.sd[j], hi = H.mu[j]+4*H.sd[j];
  const W = 660, Hh = 190, PX = 46, PY = 16;
  const X = t => PX+(t-lo)/(hi-lo)*(W-PX-10), Y = s => Hh-24-(s-0.5)/0.5*(Hh-24-PY);
  const xa = xCur.slice(); let path = "";
  for (let k = 0; k <= 160; k++) { const t = lo+(hi-lo)*k/160; xa[j] = t;
    path += (k?"L":"M")+X(t).toFixed(1)+" "+Y(scoreOf(xa)).toFixed(1); }
  let s = "<p class='note'>Exact score response to <b>"+NAMES[j]+"</b>; red dots are "+
    "the bar crossings (the gate answers exactly there).</p>"+
    "<svg viewBox='0 0 "+W+" "+Hh+"' style='max-width:100%'>";
  s += "<line class='axis' x1='"+PX+"' y1='"+(Hh-24)+"' x2='"+(W-8)+"' y2='"+(Hh-24)+"'/>"+
    "<line class='axis' x1='"+PX+"' y1='"+PY+"' x2='"+PX+"' y2='"+(Hh-24)+"'/>"+
    "<line class='tauline' x1='"+PX+"' y1='"+Y(TAU)+"' x2='"+(W-8)+"' y2='"+Y(TAU)+
    "'/><text x='"+(PX+2)+"' y='"+(Y(TAU)-3)+"'>bar τ* = "+TAU+"</text>";
  ["0.5","0.75","1.0"].forEach(v => { s += "<text x='"+(PX-6)+"' y='"+(Y(+v)+4)+
    "' text-anchor='end'>"+v+"</text>"; });
  s += "<path class='curve' d='"+path+"'/>";
  const base = logitOf(xCur)-H.coef[j]*(xCur[j]-H.mu[j])/H.sd[j];
  if (H.coef[j] !== 0) [L_STAR,-L_STAR].forEach(tg => {
    const t = H.mu[j]+H.sd[j]*(tg-base)/H.coef[j];
    if (t >= lo && t <= hi) s += "<circle class='cross' cx='"+X(t)+"' cy='"+Y(TAU)+
      "' r='4'><title>answers if "+NAMES[j]+" = "+sigfmt(t,4)+"</title></circle>"; });
  s += "<circle class='nowpt' cx='"+X(xCur[j])+"' cy='"+Y(scoreOf(xCur))+
    "' r='4.5'><title>current</title></circle></svg>";
  return s; }

function numbersHTML() {
  const c = DATA.cases[order[cur]], phi = phiOf(xCur);
  let h = "<table><tr><th>j</th><th>feature</th><th>kind</th><th>x now</th>"+
    "<th>x recorded</th><th>z</th><th>w</th><th>&#966;</th></tr>";
  const ord = NAMES.map((_,j)=>j).sort((a,b)=>Math.abs(phi[b])-Math.abs(phi[a]));
  ord.slice(0,40).forEach(j => {
    h += "<tr><td>"+j+"</td><td>"+NAMES[j]+"</td><td class='note'>"+kindOf(j)+
      "</td><td class='num'>"+sigfmt(xCur[j],5)+"</td><td class='num'>"+sigfmt(c.x[j],5)+
      "</td><td class='num'>"+sigfmt((xCur[j]-H.mu[j])/H.sd[j],4)+"</td><td class='num'>"+
      sigfmt(H.coef[j],4)+"</td><td class='num'>"+sigfmt(phi[j],4)+"</td></tr>"; });
  h += "</table><p class='note'>Top 40 of "+D+" by |&#966;|. intercept "+
    sigfmt(H.intercept,5)+" · logit "+sigfmt(logitOf(xCur),6)+" · L* "+
    L_STAR.toFixed(6)+"</p><button id='copyJson'>Copy case as JSON</button>"+
    "<button id='copyCsv'>Copy attributions as CSV</button>"+
    "<span class='note' id='copied' style='display:none'> copied ✓</span>";
  return h; }

function hospitalsHTML() {
  if (!DATA.per_site) return "<p class='note'>No hospital ids were supplied to this build.</p>";
  let h = "<p class='note'>The hospital is the unit the guarantee is stated over. "+
    "Coverage and answered-error are computed over ALL cases at this hospital, "+
    "not just the ones embedded above."+(DATA.has_oracle?" Error columns are "+
    "RETROSPECTIVE (oracle labels).":"")+"</p><table><tr><th>hospital</th><th>n</th>"+
    "<th>answered</th><th>coverage</th>"+(DATA.has_oracle?
    "<th>answered error</th><th>answered positives</th>":"")+"</tr>";
  DATA.per_site.slice(0,40).forEach(r => {
    h += "<tr><td>"+r.site+"</td><td class='num'>"+r.n+"</td><td class='num'>"+
      r.n_answered+"</td><td class='num'>"+fmt(r.coverage)+"</td>"+
      (DATA.has_oracle ? "<td class='num'>"+fmt(r.answered_err)+"</td><td class='num'>"+
        fmt(r.answered_pos_frac)+"</td>" : "")+"</tr>"; });
  return h+"</table><p class='note'>Showing "+Math.min(40,DATA.per_site.length)+
    " of "+DATA.per_site.length+" hospitals, largest first.</p>"; }

function calibrationHTML() {
  if (!DATA.reliability) return "<p class='note'>No outcome labels in this build — "+
    "a reliability curve needs them, and they exist only retrospectively.</p>";
  const R = DATA.reliability.filter(b => b.n > 0);
  const W = 620, Hh = 250, PX = 46, PY = 16;
  const X = v => PX+v*(W-PX-14), Y = v => Hh-30-v*(Hh-30-PY);
  let s = "<p class='note'>Reliability on ANSWERED cases: predicted risk vs observed "+
    "outcome rate. RETROSPECTIVE — a deployment has no such instrument. The "+
    "diagonal is perfect calibration.</p><svg viewBox='0 0 "+W+" "+Hh+
    "' style='max-width:100%'>";
  s += "<line class='axis' x1='"+PX+"' y1='"+(Hh-30)+"' x2='"+(W-10)+"' y2='"+(Hh-30)+"'/>"+
    "<line class='axis' x1='"+PX+"' y1='"+PY+"' x2='"+PX+"' y2='"+(Hh-30)+"'/>"+
    "<line class='tauline' x1='"+X(0)+"' y1='"+Y(0)+"' x2='"+X(1)+"' y2='"+Y(1)+"'/>";
  const mx = Math.max(...R.map(b => Math.max(b.mean_predicted, b.observed)), 0.05);
  let path = "";
  R.forEach((b,i) => { const px = X(b.mean_predicted/mx), py = Y(b.observed/mx);
    path += (i?"L":"M")+px.toFixed(1)+" "+py.toFixed(1);
    s += "<circle cx='"+px+"' cy='"+py+"' r='4' fill='var(--pos)'><title>"+b.n+
      " cases · predicted "+(b.mean_predicted*100).toFixed(1)+"% · observed "+
      (b.observed*100).toFixed(1)+"%</title></circle>"; });
  s += "<path class='curve' d='"+path+"'/>";
  s += "<text x='"+(W/2)+"' y='"+(Hh-6)+"' text-anchor='middle'>mean predicted risk "+
    "(axis max "+(mx*100).toFixed(0)+"%)</text></svg>";
  s += "<table><tr><th>predicted band</th><th>n answered</th><th>mean predicted</th>"+
    "<th>observed</th></tr>";
  R.forEach(b => { s += "<tr><td>"+(b.lo*100).toFixed(0)+"–"+(b.hi*100).toFixed(0)+
    "%</td><td class='num'>"+b.n+"</td><td class='num'>"+(b.mean_predicted*100).toFixed(1)+
    "%</td><td class='num'>"+(b.observed*100).toFixed(1)+"%</td></tr>"; });
  return s+"</table>"; }

function redrawAdvanced() {
  if (!order.length || xCur === null) return;
  const wf = document.getElementById("tab-waterfall");
  if (wf) wf.innerHTML = "<p class='note'>Cumulative build-up of the decision logit "+
    "from the intercept, largest |&#966;| first; dashed lines are the answering bars "+
    "&#177;L*.</p>"+waterfallSVG();
  const rc = document.getElementById("rcplot"); if (rc) rc.innerHTML = responseHTML(selFeat);
  const nm = document.getElementById("tab-numbers"); if (nm) { nm.innerHTML = numbersHTML(); wireCopy(); }
  const hp = document.getElementById("tab-hospitals"); if (hp) hp.innerHTML = hospitalsHTML();
  const cb = document.getElementById("tab-calibration"); if (cb) cb.innerHTML = calibrationHTML();
  const sb = document.getElementById("statusbar");
  if (sb) { const lg = logitOf(xCur), c = DATA.cases[order[cur]];
    let dz = 0; for (let j = 0; j < D; j++) { const t = (xCur[j]-c.x[j])/H.sd[j]; dz += t*t; }
    sb.innerHTML = "<span>logit <b>"+sigfmt(lg,6)+"</b></span><span>|logit| <b>"+
      sigfmt(Math.abs(lg),6)+"</b></span><span>L* <b>"+L_STAR.toFixed(6)+
      "</b></span><span>margin <b>"+sigfmt(L_STAR-Math.abs(lg),6)+
      "</b></span><span>&#916;z from recorded <b>"+sigfmt(Math.sqrt(dz),5)+
      "</b></span><span>deployed rule <b>score "+scoreOf(xCur).toFixed(6)+
      (scoreOf(xCur) >= TAU ? " ≥ " : " < ")+TAU+"</b></span>"+
      (c.site ? "<span>hospital <b>"+c.site+"</b></span>" : ""); } }

function wireCopy() {
  const done = () => { const e = document.getElementById("copied");
    if (e) { e.style.display = "inline"; setTimeout(() => e.style.display = "none", 1500); } };
  const put = txt => { if (navigator.clipboard && navigator.clipboard.writeText)
      navigator.clipboard.writeText(txt).then(done, done);
    else { const ta = document.createElement("textarea"); ta.value = txt;
      document.body.appendChild(ta); ta.select(); document.execCommand("copy");
      ta.remove(); done(); } };
  const b = document.getElementById("copyJson");
  if (b) b.onclick = () => { const c = DATA.cases[order[cur]];
    put(JSON.stringify({case:c.idx, hospital:c.site||null, tau_star:TAU,
      x_current:xCur, x_recorded:c.x, logit:logitOf(xCur), score:scoreOf(xCur),
      phi:phiOf(xCur), deployed_rule_answers:scoreOf(xCur)>=TAU,
      counterfactuals:c.counterfactuals,
      note:"score-space description of the gate; not clinical advice"}, null, 2)); };
  const b2 = document.getElementById("copyCsv");
  if (b2) b2.onclick = () => { const phi = phiOf(xCur), c = DATA.cases[order[cur]];
    let out = "feature,kind,x_now,x_recorded,z,w,phi\n";
    NAMES.forEach((nm,j) => { out += '"'+nm+'",'+kindOf(j)+","+xCur[j]+","+c.x[j]+","+
      ((xCur[j]-H.mu[j])/H.sd[j])+","+H.coef[j]+","+phi[j]+"\n"; });
    put(out); }; }

function selectTab(t) {
  ["decision","waterfall","response","numbers","hospitals","calibration"].forEach(k => {
    const p = document.getElementById("tab-"+k), b = document.getElementById("tb-"+k);
    if (p) p.classList.toggle("on", k === t);
    if (b) b.classList.toggle("on", k === t); });
  redrawAdvanced(); }

// ---- detail panel ----
function setControls() {
  document.querySelectorAll("#detail [data-j]").forEach(el => {
    const j = +el.dataset.j;
    if (el.type === "checkbox") el.checked = xCur[j] >= 0.5;
    else if (el.type === "range") { el.value = xCur[j]; el.dataset.last = xCur[j]; } });
  Object.keys(ONEHOT).forEach(g => {
    const sel = document.getElementById("oh_"+g.replace(/\W/g,"_"));
    if (!sel) return;
    const on = ONEHOT[g].find(([jj]) => xCur[jj] >= 0.5);
    if (on) sel.value = String(on[0]); }); }

function updateLive() {
  const c = DATA.cases[order[cur]];
  const lg = logitOf(xCur), p = sigmoid(lg), score = Math.max(p,1-p);
  const answered = score >= TAU;
  const modified = xCur.some((v,j) => v !== c.x[j]);
  const pill = document.getElementById("verdictPill");
  pill.innerHTML = answered ? "ANSWERED" : dual("HANDED TO A PERSON","DECLINED");
  pill.className = "verdict "+(answered?"answered":"declined");
  document.getElementById("modBadge").style.display = modified ? "inline-block" : "none";
  document.getElementById("leanS").textContent = lg >= 0 ? "higher risk" : "lower risk";
  document.getElementById("riskS").textContent = (p*100).toFixed(1)+"%";
  document.getElementById("needS").textContent = answered ? "" :
    " — but it is not sure enough to answer";
  document.getElementById("leanTxt").textContent = lg >= 0 ? "positive" : "negative";
  document.getElementById("riskTxt").textContent = p.toFixed(4);
  document.getElementById("needTxt").textContent = answered ? "" :
    " · needs "+sigfmt(L_STAR-Math.abs(lg))+" more logit-confidence";
  document.getElementById("needle").style.left =
    "calc("+((Math.min(Math.max(score,0.5),1)-0.5)/0.5*100).toFixed(2)+"% - 4px)";
  document.getElementById("gscore").innerHTML =
    dual("how sure: "+(score*100).toFixed(1)+"%","score "+score.toFixed(4));
  document.getElementById("phibars").innerHTML = bars(phiOf(xCur), lg>=0?1:-1, visIdx);
  document.getElementById("btnReset").classList.toggle("attn", modified);
  visIdx.forEach(j => {
    const sv = document.getElementById("sv"+j);
    if (sv) { sv.textContent = sigfmt(xCur[j],4);
      const f = FLAG_OF[String(j)];
      sv.className = "v num" + (f !== undefined && xCur[f] >= 0.5 ? " imp" : ""); }
    const rs = document.getElementById("rs"+j);
    if (rs) rs.className = "rst"+(xCur[j] !== c.x[j] ? " on" : "");
    const lb = document.getElementById("lb"+j);
    if (lb) { const f = FLAG_OF[String(j)];
      lb.className = (f !== undefined && xCur[f] >= 0.5) ? "notrec" : ""; } });
  if (document.body.classList.contains("adv")) redrawAdvanced(); }

let raf = null;
function updateLiveThrottled() {
  raf = raf || requestAnimationFrame(() => { raf = null; updateLive(); }); }

function renderDetail() {
  const c = DATA.cases[order[cur]];
  visIdx = computeVisIdx();
  let h = "<p><span class='verdict' id='verdictPill'></span>"+
    "<span class='badge' id='modBadge' style='display:none'>"+
    dual("you changed the inputs — a what-if, not the real case",
         "inputs modified — live what-if")+"</span>"+
    (c.site ? " <span class='note'>hospital "+c.site+"</span>" : "")+
    ((showOutcomes && c.outcome !== undefined) ?
      " <span class='outc "+(c.outcome?"d":"s")+"'>"+
      (c.outcome?"actually died":"actually survived")+"</span> "+
      "<span class='note'>(retrospective)</span>" : "")+
    "<span class='simponly'> · the program leans <b id='leanS'></b> — it "+
    "estimates a <span class='num' id='riskS'></span> chance of the outcome"+
    "<span id='needS'></span></span>"+
    "<span class='advonly'> · leans <b id='leanTxt'></b> · risk "+
    "<span class='num' id='riskTxt'></span><span id='needTxt'></span></span></p>";
  h += "<div class='gauge'><div class='tau' data-l='bar' style='left:"+
    ((TAU-0.5)/0.5*100).toFixed(2)+"%'></div><div class='needle' id='needle'></div></div>"+
    "<div class='gaxis'><span>0.50</span><span id='gscore'></span><span>1.00</span></div>";
  h += "<p style='margin:10px 0 4px'>";
  if (c.declined && c.delta_x_min) {
    h += "<button class='primary' id='btnFlip'>"+
      dual("Show the smallest change that makes it answer","Apply smallest flip")+"</button>";
    if (c.counterfactuals.length) h += "<button id='btnFlip1'>"+
      dual("Change just one measurement","Apply top single-input flip")+"</button>"; }
  h += "<button id='btnReset'>"+dual("Back to the real values","Reset to recorded inputs")+
    "</button></p>";
  h += "<div class='tabs advonly'>"+
    "<span class='tabbtn on' id='tb-decision'>Decision</span>"+
    "<span class='tabbtn' id='tb-waterfall'>Waterfall</span>"+
    "<span class='tabbtn' id='tb-response'>Response</span>"+
    "<span class='tabbtn' id='tb-numbers'>Numbers</span>"+
    "<span class='tabbtn' id='tb-hospitals'>Hospitals</span>"+
    "<span class='tabbtn' id='tb-calibration'>Calibration</span></div>";
  h += "<div class='tabpane on' id='tab-decision'>";
  h += "<h2 style='margin-top:6px'>"+dual("Try it yourself: change a value, the program re-decides",
       "What-if: change an input, the gate re-decides")+"</h2><p class='note'>"+
       dual("These controls only ask the program a question — they say nothing "+
            "about a real patient. Values marked <i>not recorded</i> were never "+
            "measured; the number shown is a stand-in the model fills in.",
            "Every control is live and re-runs the deployed rule. Categoricals are "+
            "dropdowns so each what-if stays a LEGAL one-hot vector; a parent whose "+
            "recording flag is set shows its imputed placeholder, not a measurement.")+
       "</p>";
  // one-hot dropdowns
  Object.keys(ONEHOT).sort().forEach(g => {
    const id = "oh_"+g.replace(/\W/g,"_");
    const on = ONEHOT[g].find(([jj]) => xCur[jj] >= 0.5);
    const orig = ONEHOT[g].find(([jj]) => c.x[jj] >= 0.5);
    h += "<div class='srow'><label title='"+g+"'>"+g+"</label>"+
      "<select id='"+id+"' data-g='"+g+"' aria-label='what-if level for "+g+"'>"+
      ONEHOT[g].map(([jj,lv]) => "<option value='"+jj+"'"+
        (on && on[0]===jj ? " selected" : "")+">"+lv+"</option>").join("")+
      "</select><span class='v note'>"+(orig?"":"none")+"</span>"+
      "<span class='rst"+((on&&orig&&on[0]!==orig[0])?" on":"")+"' data-g='"+g+
      "' id='rsg_"+id+"' title='restore recorded level'>&#8634;</span></div>"; });
  // grouped numeric / binary controls
  const byGroup = {};
  visIdx.forEach(j => (byGroup[DATA.groups[j]] = byGroup[DATA.groups[j]] || []).push(j));
  if (visIdx.length > 20 || featQuery) {
    h += "<div style='display:flex;gap:8px;margin:6px 0'><input type='text' id='featQ' "+
      "placeholder='search inputs…' value='"+featQuery.replace(/'/g,"")+
      "' style='max-width:240px' aria-label='search inputs'><button id='featAll'>"+
      (featShowAll?"show top contributors only":"show all inputs")+"</button></div>"; }
  Object.keys(byGroup).sort().forEach(g => {
    h += "<div class='grphead'>"+g+" <span class='note'>("+byGroup[g].length+")</span></div>";
    byGroup[g].forEach(j => {
      const f = FLAG_OF[String(j)], notrec = f !== undefined && xCur[f] >= 0.5;
      const lab = "<label id='lb"+j+"' class='"+(notrec?"notrec":"")+"' data-j='"+j+
        "' title='"+NAMES[j]+"'>"+NAMES[j]+"</label>";
      if (DATA.binary[j]) {
        h += "<div class='srow'>"+lab+"<span><input type='checkbox' data-j='"+j+"'"+
          (xCur[j]>=0.5?" checked":"")+" aria-label='toggle "+NAMES[j]+
          "'> <span class='note'>yes / no</span></span>"+
          "<span class='v num' id='sv"+j+"'></span><span class='rst' id='rs"+j+
          "' data-j='"+j+"' title='recorded: "+sigfmt(c.x[j],4)+"'>&#8634;</span></div>";
      } else {
        const lo = H.mu[j]-4*H.sd[j], hi = H.mu[j]+4*H.sd[j];
        h += "<div class='srow'>"+lab+"<input type='range' data-j='"+j+"' min='"+lo+
          "' max='"+hi+"' step='"+((hi-lo)/400)+"' value='"+xCur[j]+
          "' aria-label='what-if value for "+NAMES[j]+"'><span class='v num' id='sv"+j+
          "'></span><span class='rst' id='rs"+j+"' data-j='"+j+"' title='recorded: "+
          sigfmt(c.x[j],4)+"'>&#8634;</span></div>"; } }); });
  h += "<details style='margin-top:8px'><summary>"+dual("What you tried (log)","What-if log")+
    "</summary><div id='logbox' class='note'></div></details>";
  h += "<h2 style='margin-top:12px'>"+dual("What pushed its confidence up or down",
       "What drives the confidence")+"</h2><p class='note'>"+
    dual("Bars right push toward the program's leaning; bars left pull against it. "+
         "When they cancel out, it hands the case over.",
         "Right of the line builds confidence toward the leaned class; left erodes it "+
         "— cancellation causes the decline.")+"</p><div id='phibars'></div>";
  if (c.declined && c.counterfactuals.length) {
    h += "<h2 style='margin-top:12px'>"+dual("What would have to be different for it to answer",
      "Smallest single-input changes that would make the gate answer")+"</h2><p class='note'>"+
      dual("Each row is the smallest change to ONE value that would let the program "+
           "answer — and even then it would only just clear the bar.",
           "Ranked by standardized magnitude; each clears the bar by the documented "+
           "headroom, so the answer carries the weakest allowed confidence, "+
           fmt(c.confidence_at_flip)+".")+"</p><table><tr><th>"+
      dual("what","input")+"</th><th>"+dual("change needed","raw &#916;")+"</th>"+
      "<th class='advonly'>std &#916;z</th><th>"+dual("kind","kind")+"</th><th>"+
      dual("it would then say","answers as")+"</th></tr>";
    c.counterfactuals.forEach(cf => {
      h += "<tr><td>"+NAMES[cf.j]+"</td><td class='num'>"+signed(cf.delta_x)+
        "</td><td class='num advonly'>"+signed(cf.delta_z)+"</td><td>"+
        (kindTag(cf.j) || "<span class='tag'>"+dual("measurement","clinical")+"</span>")+
        "</td><td>"+dual(cf.answers_as==="predicted-positive"?"higher risk":"lower risk",
          cf.answers_as)+"</td></tr>"; });
    h += "</table><p class='note'>"+dual(
      "Rows tagged <i>about record-keeping</i> are not clinical changes at all — "+
      "they are about whether a measurement was written down. All of these describe "+
      "the computer program, never the patient.",
      "Recording-artifact rows are not clinical interventions: they change whether a "+
      "value was recorded, not the patient. Smallest whole-profile change (standardized "+
      "L2): "+fmt(c.l2_distance_z)+".")+"</p>"; }
  h += "</div>";
  ["waterfall","response","numbers","hospitals","calibration"].forEach(k => {
    h += "<div class='tabpane advonly' id='tab-"+k+"'>"+
      (k === "response" ? "<select id='rcsel' style='max-width:280px' "+
        "aria-label='feature for response view'></select><div id='rcplot' "+
        "style='margin-top:8px'></div>" : "")+"</div>"; });
  h += "<div class='statusbar advonly' id='statusbar'></div>";
  const box = document.getElementById("detail");
  box.innerHTML = h;

  box.querySelectorAll("input[type=range][data-j]").forEach(sl => {
    sl.dataset.last = xCur[+sl.dataset.j];
    sl.addEventListener("input", () => { xCur[+sl.dataset.j] = +sl.value; updateLiveThrottled(); });
    sl.addEventListener("change", () => { const j = +sl.dataset.j;
      logEvt(NAMES[j]+": "+sigfmt(+sl.dataset.last,4)+" → "+sigfmt(+sl.value,4));
      sl.dataset.last = sl.value; }); });
  box.querySelectorAll("input[type=checkbox][data-j]").forEach(cb => {
    cb.addEventListener("change", () => { const j = +cb.dataset.j;
      xCur[j] = cb.checked ? 1 : 0;
      const par = PARENT_OF[j];
      logEvt(NAMES[j]+": "+(cb.checked?"no → yes":"yes → no")+
        (par !== undefined ? " (“"+NAMES[par]+"” is now "+
          (cb.checked?"an imputed placeholder":"treated as measured")+")" : ""));
      renderDetail(); }); });
  box.querySelectorAll("select[data-g]").forEach(sel => {
    sel.addEventListener("change", () => { const g = sel.dataset.g, pick = +sel.value;
      ONEHOT[g].forEach(([jj]) => xCur[jj] = 0);
      xCur[pick] = 1;
      logEvt(g+" → "+NAMES[pick].split("=").pop());
      renderDetail(); }); });
  box.querySelectorAll(".rst[data-j]").forEach(rs => {
    rs.addEventListener("click", () => { const j = +rs.dataset.j;
      xCur[j] = c.x[j]; logEvt(NAMES[j]+": restored"); setControls(); updateLive(); }); });
  box.querySelectorAll(".rst[data-g]").forEach(rs => {
    rs.addEventListener("click", () => { const g = rs.dataset.g;
      ONEHOT[g].forEach(([jj]) => xCur[jj] = c.x[jj]);
      logEvt(g+": restored"); renderDetail(); }); });
  box.querySelectorAll("label[data-j]").forEach(lb => {
    lb.addEventListener("click", () => { selFeat = +lb.dataset.j;
      const rs = document.getElementById("rcsel"); if (rs) rs.value = selFeat;
      if (document.body.classList.contains("adv")) selectTab("response"); }); });
  const fq = document.getElementById("featQ");
  if (fq) fq.addEventListener("input", () => { featQuery = fq.value.trim(); renderDetail();
    const nf = document.getElementById("featQ"); nf.focus();
    nf.setSelectionRange(nf.value.length, nf.value.length); });
  const fa = document.getElementById("featAll");
  if (fa) fa.onclick = () => { featShowAll = !featShowAll; renderDetail(); };
  const bF = document.getElementById("btnFlip");
  if (bF) bF.onclick = () => { xCur = c.x.map((v,j) => v + c.delta_x_min[j]);
    logEvt("applied smallest whole-profile flip"); renderDetail(); };
  const b1 = document.getElementById("btnFlip1");
  if (b1) b1.onclick = () => { const cf = c.counterfactuals[0];
    xCur = c.x.slice(); xCur[cf.j] += cf.delta_x;
    logEvt("applied single-input flip ("+NAMES[cf.j]+")"); renderDetail(); };
  document.getElementById("btnReset").onclick = () => { xCur = c.x.slice();
    logEvt("reset all inputs to recorded values"); renderDetail(); };
  ["decision","waterfall","response","numbers","hospitals","calibration"].forEach(k => {
    const b = document.getElementById("tb-"+k); if (b) b.onclick = () => selectTab(k); });
  const rsel = document.getElementById("rcsel");
  if (rsel) { NAMES.forEach((nm,j) => { const o = document.createElement("option");
      o.value = j; o.textContent = nm + (MEMBER_GROUP[j]!==undefined?"  (category)":"");
      rsel.appendChild(o); });
    rsel.value = selFeat;
    rsel.onchange = () => { selFeat = +rsel.value; redrawAdvanced(); }; }
  const lb0 = document.getElementById("logbox");
  if (lb0) lb0.innerHTML = wlog.map(e => "<div>"+e+"</div>").join("");
  updateLive(); }

// ---- controls ----
document.querySelectorAll(".side .chip[data-f]").forEach(ch => ch.onclick = () => {
  document.querySelectorAll(".side .chip[data-f]").forEach(c => c.classList.remove("on"));
  ch.classList.add("on"); filter = ch.dataset.f; rebuildList(); });
document.getElementById("search").addEventListener("input", e => {
  query = e.target.value.trim(); rebuildList(); });
document.getElementById("sortSel").addEventListener("change", e => {
  sortBy = e.target.value; rebuildList(order[cur]); });
document.getElementById("jmpContested").onclick = () => {
  let best = 0, bv = Infinity;
  order.forEach((i,k) => { const m = Math.abs(DATA.cases[i].margin_to_answer);
    if (m < bv) { bv = m; best = k; } });
  cur = best; selectCase(); };
document.getElementById("jmpRandom").onclick = () => {
  if (order.length) { cur = Math.floor(Math.random()*order.length); selectCase(); } };
const helpov = document.getElementById("helpov");
document.getElementById("helpclose").onclick = () => helpov.classList.remove("on");
document.addEventListener("keydown", e => {
  if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT") return;
  if (e.key === "ArrowRight" && cur < order.length-1) { cur++; selectCase(); }
  if (e.key === "ArrowLeft" && cur > 0) { cur--; selectCase(); }
  if (e.key === "o") outcChip.click();
  if (!document.body.classList.contains("adv")) return;
  if (e.key === "?") helpov.classList.toggle("on");
  const tabs = {"1":"decision","2":"waterfall","3":"response","4":"numbers",
                "5":"hospitals","6":"calibration"};
  if (tabs[e.key]) selectTab(tabs[e.key]);
  if (e.key === "f") { const b = document.getElementById("btnFlip"); if (b) b.click(); }
  if (e.key === "r") { const b = document.getElementById("btnReset"); if (b) b.click(); } });

const tX = document.getElementById("tauX"), tXv = document.getElementById("tauXv");
tX.value = TAU;
function exploreUpdate() {
  const t = +tX.value, n = DATA.all_scores.length;
  const ans = DATA.all_scores.filter(s => s >= t).length;
  tXv.innerHTML = dual("bar "+t.toFixed(2)+" → answers "+(ans/n*100).toFixed(1)+
      "% ("+(n-ans).toLocaleString()+" handed over)",
    "bar "+t.toFixed(2)+" → coverage "+(ans/n*100).toFixed(1)+"% ("+
      (n-ans).toLocaleString()+" declined)"); }
tX.addEventListener("input", exploreUpdate);
exploreUpdate();
rebuildList();
</script>
</body>
</html>
"""


def main():
    rng = np.random.default_rng(SEED)
    cfg = SimConfig()
    coh = draw_cohort(cfg, 40, rng)
    train, _, _ = split_sites(coh, rng)
    head = fit_head(train)
    pool = draw_cohort(cfg, 4, rng, site_label_prefix="demo")
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "explain_dashboard.html")
    path = build_dashboard(head, pool.x, tau_star=0.77, out_path=out,
                           oracle_y=pool.y, site_ids=list(pool.site_id))
    n_declined = int((head.score(pool.x) < 0.77).sum())
    print(f"[dashboard] wrote {path} ({pool.n} cases, {n_declined} declined)")


if __name__ == "__main__":
    main()
