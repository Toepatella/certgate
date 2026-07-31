"""Self-contained interactive HTML dashboard for the explanation layer (demo).

Renders, for a scored cohort at one operating threshold, what a reader sees
per case — and lets them interrogate it live. Two audiences, one toggle, two
genuinely different UIs:

PLAIN LANGUAGE (default) — an airy clinician view with no jargon: verdicts in
everyday words, percentages instead of logits, a "how to read this page"
walkthrough, live what-if sliders, one-click smallest-change flips, and a
printable case summary.

ADVANCED — an analyst workbench: a tabbed detail panel (Decision / Waterfall /
Response curve / Numbers), a live status bar carrying the raw quantities
(logit, L*, margin, standardized deviation from the recorded inputs), a
waterfall attribution chart, an exact per-feature response curve with the
single-feature counterfactual crossings marked, a full-precision numbers
table, copy-case-as-JSON, a click-to-filter cohort histogram, the FULL-COHORT
abstention profile (the E5 artifact, computed at build time by
``certgate.explain.cohort_abstention_profile``), and keyboard shortcuts with a
help overlay. Both modes get dark mode and print styling.

Both variants of every sentence are rendered into the file; the toggle flips
CSS classes, so switching is instant and never interrupts a slider drag. The
page recomputes the head's own arithmetic (float64) locally — sliders, flip
buttons, curves and waterfalls all re-run the actual deployed rule
``score >= tau``, not an approximation of it.

The output is ONE .html file with no external assets, scripts or network
access — it can be opened from disk by anyone with a browser. The embedded
data is a demonstration cohort from the synthetic generator; for real data,
call ``build_dashboard`` on your own fitted head and cohort LOCALLY. Nothing
here touches the certified path, and record-level displays of restricted data
(e.g. an eICU extract) must stay on the analyst's machine per the DUA — this
script never writes into ``experiments/out``.

Honesty constraints carried into the page itself (SPEC explain.py):
- counterfactuals, sliders, curves and waterfalls are SCORE-SPACE questions to
  the gate ("what would the gate need"), never causal or clinical advice; the
  caveat box is not removable and both registers carry it.
- the minimal flip clears the bar by the documented 1e-9 logit headroom, so it
  is the WEAKEST answerable answer, at confidence a hair above tau*.
- the certificate is a site-population-average guarantee; no single record
  carries a certified property, and the page says so.
- the threshold explorer is fenced as intuition-only; the abstention-profile
  panel states the replicated E5 null (no stable single-feature driver —
  abstention is cancellation) rather than inviting a driver reading.

Run:  python -m examples.explain_dashboard   (writes examples/explain_dashboard.html)
"""
from __future__ import annotations

import json
import os

import numpy as np

from certgate.constants import SEED
from certgate.data import SimConfig, draw_cohort, split_sites
from certgate.explain import cohort_abstention_profile, counterfactual_to_answer
from certgate.model import fit_head

_MAX_ANSWERED_SHOWN = 40      # every declined case is shown; answered are sampled


def _case_payload(head, x_row, idx, tau_star, feature_names):
    cf = counterfactual_to_answer(head, x_row, tau_star)
    out = {
        "idx": int(idx),
        "declined": bool(cf["declined"]),
        "margin_to_answer": round(cf["margin_to_answer"], 4),
        "x": [float(v) for v in np.asarray(x_row, dtype=np.float64)],
        "counterfactuals": [],
        "delta_x_min": None,
        "l2_distance_z": (round(cf["l2_distance_z"], 4)
                          if np.isfinite(cf["l2_distance_z"]) else None),
        "confidence_at_flip": (round(cf["confidence_at_flip"], 4)
                               if cf["confidence_at_flip"] is not None else None),
    }
    if cf["declined"] and cf["flip_verified"]:
        out["delta_x_min"] = [float(v) for v in cf["delta_x_min_l2"]]
        for j in cf["single_feature_ranking"][:5]:
            j = int(j)
            out["counterfactuals"].append({
                "j": j,
                "feature": feature_names[j],
                "delta_x": float(cf["single_feature_delta_x"][j]),
                "delta_z": round(float(cf["single_feature_delta_z"][j]), 4),
                "answers_as": "predicted-positive" if cf["answered_class_on_flip"]
                              else "predicted-negative",
            })
    return out


def build_dashboard(head, x, tau_star, out_path, feature_names=None,
                    oracle_y=None, cohort_label="synthetic demonstration cohort"):
    """Write a self-contained interactive explanation dashboard for ``x``.

    Every declined case is browsable; answered cases are truncated to the
    first ``_MAX_ANSWERED_SHOWN``. The cohort histogram and the abstention
    profile cover ALL cases. Returns ``out_path``.
    """
    x = np.asarray(x, dtype=np.float64)
    d = x.shape[1]
    if feature_names is None:
        feature_names = [f"feature {j}" for j in range(d)]
    scores = head.score(x)
    answered = scores >= tau_star
    declined_idx = np.flatnonzero(~answered)
    answered_idx = np.flatnonzero(answered)[:_MAX_ANSWERED_SHOWN]

    cases = [_case_payload(head, x[i], i, tau_star, feature_names)
             for i in np.concatenate([declined_idx, answered_idx])]
    n_ans = int(answered.sum())
    pred_pos = int((np.asarray(head.predict(x), dtype=bool) & answered).sum())

    prof = cohort_abstention_profile(head, x, answered)

    def _clean(arr):
        return [None if not np.isfinite(v) else round(float(v), 4) for v in arr]

    payload = {
        "tau_star": float(tau_star),
        "cohort_label": cohort_label,
        "n_total": int(x.shape[0]),
        "n_answered": n_ans,
        "n_declined": int((~answered).sum()),
        "coverage": round(float(answered.mean()), 4),
        "feature_names": list(feature_names),
        "head": {"coef": [float(v) for v in head.coef],
                 "mu": [float(v) for v in head.mu],
                 "sd": [float(v) for v in head.sd],
                 "intercept": float(head.intercept)},
        "all_scores": [round(float(s), 4) for s in scores],
        "predicted_positive_fraction": round(pred_pos / n_ans, 4) if n_ans else None,
        "oracle_positive_fraction":
            (round(float((np.asarray(oracle_y, dtype=bool) & answered).sum()
                         / n_ans), 4)
             if oracle_y is not None and n_ans else None),
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


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CertGate Explain — interactive explanation dashboard (demonstration)</title>
<style>
  :root { --ink:#1a2233; --mut:#5b6572; --line:#d8dee7; --bg:#f4f6fa;
          --card:#ffffff; --pos:#2563eb; --neg:#b45309; --dec:#b91c1c;
          --ans:#15803d; --chip:#e8edf5; --hl:#eef4ff; --histbar:#c7d4e8;
          --histdec:#f3b8b8; --fence:#fffbf5; --amber:#fef3c7; --ambert:#92400e;
          --shadow:0 1px 3px rgba(16,24,40,.07); }
  body.dark { --ink:#e6ebf3; --mut:#98a2b3; --line:#2a3446; --bg:#0f1520;
          --card:#171e2b; --pos:#5b8def; --neg:#d98f3d; --dec:#e05d5d;
          --ans:#3fae6a; --chip:#232c3d; --hl:#1d2a44; --histbar:#33415c;
          --histdec:#5c3434; --fence:#1c1a14;
          --amber:#3a300f; --ambert:#f4d47c; --shadow:0 1px 3px rgba(0,0,0,.4); }
  * { box-sizing:border-box; }
  body { margin:0; font:15px/1.55 system-ui,Segoe UI,Roboto,sans-serif;
         color:var(--ink); background:var(--bg);
         transition:background .2s, color .2s; }
  body.adv { font-size:13.5px; }
  header { padding:16px 22px 4px; max-width:1180px; margin:0 auto; }
  h1 { font-size:19px; margin:0 0 2px; }
  body.adv h1 { font-size:17px; }
  h2 { font-size:14px; margin:0 0 8px; }
  .sub { color:var(--mut); font-size:13px; }
  main { max-width:1180px; margin:0 auto; padding:10px 22px 30px; }
  .card { background:var(--card); border:1px solid var(--line);
          border-radius:12px; padding:15px 17px; margin:12px 0;
          box-shadow:var(--shadow); }
  body.adv .card { border-radius:8px; padding:12px 14px; }
  .caveat { border-left:4px solid var(--dec); font-size:13px; }
  .caveat b { color:var(--dec); }
  .strip { display:flex; gap:18px; flex-wrap:wrap; font-size:13px; }
  .strip div b { display:block; font-size:17px; }
  .cols { display:flex; gap:12px; align-items:flex-start; flex-wrap:wrap; }
  .side { flex:0 0 272px; max-width:100%; }
  .detail { flex:1 1 500px; min-width:320px; }
  .chip { display:inline-block; padding:3px 10px; border-radius:999px;
          background:var(--chip); cursor:pointer; font-size:12.5px;
          border:1px solid transparent; user-select:none; }
  .chip.on { background:var(--hl); border-color:var(--pos); color:var(--pos);
             font-weight:600; }
  input[type=text], select { font:inherit; padding:5px 8px; color:var(--ink);
          background:var(--card); border:1px solid var(--line);
          border-radius:8px; width:100%; }
  .cl { margin-top:8px; max-height:430px; overflow-y:auto;
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
           #fee2e2, #fef9c3 55%, #dcfce7); border-radius:6px;
           border:1px solid var(--line); margin:8px 0 2px; }
  body.dark .gauge { background:linear-gradient(90deg,#3d1d1d,#3a300f 55%,#15321f); }
  .gauge .tau { position:absolute; top:-4px; bottom:-4px; width:2px;
                background:var(--ink); }
  .gauge .tau::after { content:attr(data-l); position:absolute; top:-16px;
                left:-14px; font-size:11px; color:var(--ink); }
  .gauge .needle { position:absolute; top:2px; bottom:2px; width:8px;
                   border-radius:4px; background:var(--pos);
                   transition:left .15s; }
  .gaxis { display:flex; justify-content:space-between; font-size:11px;
           color:var(--mut); }
  .srow { display:grid; grid-template-columns:104px 1fr 66px 18px; gap:8px;
          align-items:center; margin:2px 0; }
  .srow label { font-size:12px; color:var(--mut); text-align:right;
                white-space:nowrap; overflow:hidden; cursor:pointer; }
  .srow label:hover { color:var(--pos); }
  .srow input[type=range] { width:100%; accent-color:var(--pos); }
  .srow .v { font-size:12px; font-variant-numeric:tabular-nums; }
  .rst { color:var(--dec); cursor:pointer; font-size:14px; line-height:1;
         user-select:none; visibility:hidden; }
  .rst.on { visibility:visible; }
  table { border-collapse:collapse; width:100%; font-size:13px; }
  th,td { text-align:left; padding:4px 8px; border-bottom:1px solid var(--line); }
  th { color:var(--mut); font-weight:600; }
  .barrow { display:flex; align-items:center; gap:8px; margin:2px 0; }
  .barlab { width:104px; font-size:12px; color:var(--mut); text-align:right; }
  .barbox { flex:1; display:flex; height:13px; position:relative; }
  .barbox .mid { position:absolute; left:50%; top:-2px; bottom:-2px;
                 width:1px; background:var(--line); }
  .bar { height:13px; border-radius:3px; transition:width .15s; }
  .bar.pos { background:var(--pos); margin-left:50%; }
  .bar.neg { background:var(--neg); }
  .barval { width:58px; font-size:11.5px; color:var(--mut);
            font-variant-numeric:tabular-nums; }
  .hist { display:flex; align-items:flex-end; height:90px; gap:1px;
          position:relative; margin-top:6px; }
  .hist .hb { flex:1; background:var(--histbar); border-radius:2px 2px 0 0;
              min-height:1px; }
  .hist .hb.dec { background:var(--histdec); }
  body.adv .hist .hb { cursor:pointer; }
  body.adv .hist .hb:hover { outline:1.5px solid var(--pos); }
  .hist .hb.hsel { outline:2px solid var(--pos); }
  .hist .tau { position:absolute; top:-4px; bottom:-14px; width:2px;
               background:var(--ink); }
  .num { font-variant-numeric:tabular-nums; }
  .note { color:var(--mut); font-size:12px; }
  .fence { border:1.5px dashed var(--neg); border-radius:10px;
           padding:12px 16px; margin:12px 0; background:var(--fence); }
  .fence b.t { color:var(--neg); }
  footer { color:var(--mut); font-size:12px; max-width:1180px;
           margin:0 auto; padding:0 22px 26px; }
  kbd { background:var(--chip); border-radius:4px; padding:0 5px;
        font-size:11px; }
  details { margin:8px 0; }
  summary { cursor:pointer; color:var(--pos); font-size:13px; }
  .steps li { margin:5px 0; }
  /* two-audience text */
  body.simple .advonly { display:none !important; }
  body.adv .simponly { display:none !important; }
  .modebar { float:right; margin-top:2px; display:flex; gap:6px; }
  /* advanced workbench */
  .tabs { display:flex; gap:4px; border-bottom:1px solid var(--line);
          margin:10px 0 10px; }
  .tabbtn { padding:5px 12px; font-size:12.5px; cursor:pointer;
            border:1px solid transparent; border-bottom:none;
            border-radius:8px 8px 0 0; color:var(--mut); user-select:none; }
  .tabbtn.on { background:var(--hl); border-color:var(--line);
               color:var(--pos); font-weight:600; }
  .tabpane { display:none; }
  .tabpane.on { display:block; }
  /* simple mode has no tabs: the decision pane is always the page */
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
  .wfbar { transition:none; }
  .helpov { position:fixed; inset:0; background:rgba(10,14,20,.55);
            display:none; z-index:50; }
  .helpov.on { display:flex; align-items:center; justify-content:center; }
  .helpov .card { max-width:420px; }
  .profrow { display:flex; align-items:center; gap:8px; margin:2px 0; }
  .profrow .plab { width:104px; font-size:12px; color:var(--mut); text-align:right; }
  .profrow .pbox { flex:1; height:12px; display:flex; gap:2px; }
  .profrow .pa { background:var(--ans); height:12px; border-radius:2px; }
  .profrow .pd { background:var(--dec); height:12px; border-radius:2px; }
  .profrow .pval { width:120px; font-size:11px; color:var(--mut);
                   font-variant-numeric:tabular-nums; }
  @media print {
    .side, .fence, .modebar, .hist, .gaxis, footer, .tabs, .statusbar,
    #cohortstrip, .helpov, button, .sub { display:none !important; }
    .card { box-shadow:none; border-color:#bbb; page-break-inside:avoid; }
    body { background:#fff; }
  }
</style>
</head>
<body class="simple">
<header>
  <div class="modebar">
    <span class="chip on" id="modeSimple" title="everyday language, no jargon">Plain language</span>
    <span class="chip" id="modeAdv" title="analyst workbench: tabs, waterfall, response curves, raw numbers">Advanced</span>
    <span class="chip" id="darkT" title="toggle dark mode">&#9789;</span>
    <span class="chip" id="printT" title="print a summary of the selected case">Print</span>
  </div>
  <h1>CertGate Explain <span class="note">demo</span></h1>
  <div class="sub">
    <span class="simponly">A safety gate sits in front of this computer model:
      it only answers when it is confident enough, and hands everything else to
      a person. Pick a case below to see why it decided the way it did — and
      try changing the inputs yourself.</span>
    <span class="advonly" id="subtitleAdv"></span>
  </div>
</header>
<main>
  <div class="card caveat">
    <span class="simponly">
      <b>Read this first.</b> This page describes the <b>computer program</b>,
      never the patient. When it shows "what would need to change for the
      computer to answer", that is a fact about how the program decides —
      <b>not</b> medical advice, <b>not</b> a treatment suggestion, and not
      something anyone could actually do to a patient (you can't change one
      measurement and keep everything else the same). Any case flipped by the
      smallest change is answered with the <b>lowest confidence the program is
      allowed to have</b> — barely over the line. And the program's safety
      promise is about its <b>average</b> mistakes across many hospitals, not a
      promise about any one case on this page. The data here is a
      <span id="cohortlabelS"></span>.
    </span>
    <span class="advonly">
      <b>Read this first.</b> Everything interactive on this page — sliders,
      flip buttons, curves, waterfalls, the threshold explorer — asks a
      <b>score-space</b> question of the gate: <i>what would the model's inputs
      need to be</i> for the case to clear the answering bar. These are
      <b>not</b> causal claims, not treatment suggestions, and not clinically
      achievable actions (features are not independently changeable). A case
      flipped by the minimal change is answered at the <b>weakest possible
      confidence</b>, a hair above the bar itself. The error-rate certificate
      is a <b>site-population-average</b> guarantee over answered cases: no
      individual record carries a certified property of its own. This page
      shows a <span id="cohortlabel"></span>.
    </span>
  </div>

  <details class="simponly card" style="margin-top:0">
    <summary>How to read this page (30 seconds)</summary>
    <ol class="steps note">
      <li><b>Pick a case</b> on the left. Green means the program answered;
        red means it wasn't sure enough and handed the case to a person.</li>
      <li><b>The meter</b> shows how sure the program was. It must clear the
        dark line (the bar) to answer.</li>
      <li><b>The bars</b> show what pushed its confidence up or down. When
        pushes and pulls cancel out, it hands the case over.</li>
      <li><b>Try the sliders</b> — move a value and watch it re-decide. The
        red buttons put everything back to the real values.</li>
    </ol>
  </details>

  <div class="card">
    <div class="strip" id="cohortstrip"></div>
    <div class="hist" id="hist"></div>
    <div class="gaxis">
      <span><span class="simponly">totally unsure (50/50)</span><span
        class="advonly">score 0.50 (maximally contested)</span></span>
      <span><span class="simponly">completely certain</span><span
        class="advonly">1.00 (maximally confident)</span></span></div>
    <div class="note">
      <span class="simponly">Every case the program looked at, grouped by how
        sure it was. Red bars: not sure enough — handed to a person. The dark
        line is the confidence bar it must clear to answer.</span>
      <span class="advonly">Cohort confidence-score distribution. Red bars sit
        below the answering bar (declined); the dark line is the deployed bar
        τ* = <span id="taulab"></span>. Click a bin to filter the case list;
        click it again to clear.</span></div>
    <div class="advonly" id="profpanel" style="margin-top:12px"></div>
  </div>

  <div class="cols">
    <div class="side card">
      <h2>Cases <span class="note">(<kbd>&#8592;</kbd>/<kbd>&#8594;</kbd> to
        step<span class="advonly">, <kbd>?</kbd> for shortcuts</span>)</span></h2>
      <span class="chip" data-f="all">all</span>
      <span class="chip on" data-f="declined"><span class="simponly">handed
        to a person</span><span class="advonly">declined</span></span>
      <span class="chip" data-f="answered">answered</span>
      <span class="chip" id="binclear" style="display:none"
        title="clear the histogram score filter">score filter &#10005;</span>
      <div style="margin:8px 0 4px"><input type="text" id="search"
        placeholder="search case number&#8230;"></div>
      <select id="sortSel">
        <option value="margin_asc">most borderline first</option>
        <option value="margin_desc">least borderline first</option>
        <option value="idx">by case number</option>
      </select>
      <div class="cl" id="caselist"></div>
    </div>

    <div class="detail card" id="detail"></div>
  </div>

  <div class="fence" id="explorer">
    <b class="t"><span class="simponly">What if the bar were set differently? —
      just for understanding.</span><span class="advonly">Threshold explorer —
      for intuition only.</span></b>
    <span class="note"><span class="simponly">In real use the bar is set by the
      safety certificate, never by hand. Sliding it here changes nothing above
      and promises nothing — it only shows how many cases the program would
      answer at a stricter or looser bar.</span><span class="advonly">Deployed
      thresholds are selected by the certificate, never by hand; moving this
      slider confers no guarantee and does not change the verdicts
      above.</span></span><br>
    <div class="srow" style="grid-template-columns:104px 1fr 220px">
      <label><span class="simponly">try a bar</span><span
        class="advonly">explore bar</span></label>
      <input type="range" id="tauX" min="0.55" max="0.99" step="0.01">
      <span class="v" id="tauXv"></span>
    </div>
  </div>
</main>
<div class="helpov" id="helpov">
  <div class="card">
    <h2>Keyboard shortcuts</h2>
    <table>
      <tr><td><kbd>&#8592;</kbd> / <kbd>&#8594;</kbd></td><td>previous / next case</td></tr>
      <tr><td><kbd>1</kbd>&#8211;<kbd>4</kbd></td><td>Decision / Waterfall / Response / Numbers tab</td></tr>
      <tr><td><kbd>f</kbd></td><td>apply smallest flip (declined cases)</td></tr>
      <tr><td><kbd>r</kbd></td><td>reset to recorded inputs</td></tr>
      <tr><td><kbd>?</kbd></td><td>toggle this panel</td></tr>
    </table>
    <p class="note">Shortcuts are ignored while typing in the search box.</p>
    <button id="helpclose">Close</button>
  </div>
</div>
<footer>
  <span class="simponly">This page works entirely on your computer — nothing is
    sent anywhere. It re-runs the program's own arithmetic, so what you see is
    the real decision rule, not a picture of it. Switch to
    <b>Advanced</b> (top right) for the full technical detail.</span>
  <span class="advonly">CertGate Explain (demonstration build). Generated by
    <code>examples/explain_dashboard.py</code>. The page recomputes the head's
    own arithmetic (float64) locally: sliders, flip buttons, response curves
    and waterfalls re-run the deployed answering rule, so what you see is the
    gate itself, not a visualization of it. Attributions are exact
    interventional Shapley values of the linear head; counterfactual deltas
    come from <code>certgate.explain.counterfactual_to_answer</code>; the
    cohort abstention profile from
    <code>certgate.explain.cohort_abstention_profile</code> (SPEC
    "explain.py"). Self-contained file, no network access.</span>
</footer>
<script>
"use strict";
const DATA = __PAYLOAD__;
const H = DATA.head, TAU = DATA.tau_star, NAMES = DATA.feature_names;
const D = NAMES.length;
const L_STAR = Math.log(TAU/(1-TAU));
const fmt = (v, n=4) => (v === null || v === undefined) ? "&#8212;" : (+v).toFixed(n);

// ---- the head's own arithmetic, in the same float64 the pipeline uses ----
const sigmoid = z => z >= 0 ? 1/(1+Math.exp(-z)) : (e => e/(1+e))(Math.exp(z));
const logitOf = x => {
  let s = H.intercept;
  for (let j = 0; j < x.length; j++) s += H.coef[j]*(x[j]-H.mu[j])/H.sd[j];
  return s;
};
const scoreOf = x => { const p = sigmoid(logitOf(x)); return Math.max(p, 1-p); };
const phiOf = x => H.coef.map((c,j) => c*(x[j]-H.mu[j])/H.sd[j]);

// ---- mode / theme / print ----
function setMode(m) {
  document.body.classList.remove("simple", "adv");
  document.body.classList.add(m);
  document.getElementById("modeSimple").classList.toggle("on", m === "simple");
  document.getElementById("modeAdv").classList.toggle("on", m === "adv");
  if (m === "adv") redrawAdvanced();
}
document.getElementById("modeSimple").onclick = () => setMode("simple");
document.getElementById("modeAdv").onclick = () => setMode("adv");
document.getElementById("darkT").onclick = () => {
  document.body.classList.toggle("dark");
  document.getElementById("darkT").classList.toggle("on");
};
document.getElementById("printT").onclick = () => window.print();
const dual = (s, a) => "<span class='simponly'>" + s +
                       "</span><span class='advonly'>" + a + "</span>";

// ---- static chrome ----
document.getElementById("subtitleAdv").textContent =
  "Operating threshold τ* = " + TAU + " (L* = " + L_STAR.toFixed(6) + ") · " +
  DATA.cohort_label + " · every number recomputed live by the head's own formula";
document.getElementById("cohortlabel").textContent = DATA.cohort_label;
document.getElementById("cohortlabelS").textContent = DATA.cohort_label;
document.getElementById("taulab").textContent = TAU;
const strip = document.getElementById("cohortstrip");
const stat = (labelS, labelA, val, pct) => {
  const el = document.createElement("div");
  const shown = (typeof val === "number" && val % 1)
    ? dual(pct ? (val*100).toFixed(1) + "%" : fmt(val), fmt(val))
    : fmt(val, 0);
  el.innerHTML = "<b class='num'>" + shown + "</b>" + dual(labelS, labelA);
  strip.appendChild(el);
};
stat("cases reviewed", "cases scored", DATA.n_total);
stat("answered", "answered", DATA.n_answered);
stat("handed to a person", "declined", DATA.n_declined);
stat("share answered", "coverage", DATA.coverage, true);
stat("of answered: flagged higher-risk", "answered predicted-positive fraction",
     DATA.predicted_positive_fraction, true);
if (DATA.oracle_positive_fraction !== null)
  stat("of answered: truly higher-risk (known only in this test setting)",
       "answered true-positive fraction (oracle, harness only)",
       DATA.oracle_positive_fraction, true);

// ---- cohort histogram (advanced: click a bin to filter the case list) ----
const NB = 50, bins = new Array(NB).fill(0);
DATA.all_scores.forEach(s => {
  const b = Math.min(NB-1, Math.floor((s-0.5)/0.5*NB));
  bins[b]++;
});
let binSel = null;              // [lo, hi) score filter or null
const hist = document.getElementById("hist");
const bmax = Math.max(...bins);
bins.forEach((n, b) => {
  const lo = 0.5 + b*0.5/NB, hi = lo + 0.5/NB;
  const el = document.createElement("div");
  el.className = "hb" + (hi <= TAU ? " dec" : "");
  el.style.height = (n/bmax*100).toFixed(1) + "%";
  el.title = n + " cases with score in [" + lo.toFixed(3) + ", " +
             hi.toFixed(3) + ")";
  el.onclick = () => {
    if (!document.body.classList.contains("adv")) return;
    const same = binSel && binSel[0] === lo;
    [...hist.children].forEach(c => c.classList && c.classList.remove("hsel"));
    binSel = same ? null : [lo, hi];
    if (!same) el.classList.add("hsel");
    document.getElementById("binclear").style.display =
      binSel ? "inline-block" : "none";
    rebuildList();
  };
  hist.appendChild(el);
});
const tl = document.createElement("div");
tl.className = "tau";
tl.style.left = ((TAU-0.5)/0.5*100).toFixed(2) + "%";
hist.appendChild(tl);
document.getElementById("binclear").onclick = () => {
  binSel = null;
  [...hist.children].forEach(c => c.classList && c.classList.remove("hsel"));
  document.getElementById("binclear").style.display = "none";
  rebuildList();
};

// ---- cohort abstention profile (advanced; full cohort, build-time) ----
(function(){
  const P = DATA.abstention_profile;
  if (!P || P.mean_abs_phi_declined.some(v => v === null)) return;
  const mx = Math.max(...P.mean_abs_phi_answered, ...P.mean_abs_phi_declined, 1e-9);
  let h = "<h2>Cohort abstention profile <span class='note'>mean |&#966;| per " +
    "feature — answered (" + P.n_answered + ") vs declined (" + P.n_declined +
    "), full cohort, computed at build time</span></h2>";
  for (let j = 0; j < D; j++) {
    const a = P.mean_abs_phi_answered[j], d = P.mean_abs_phi_declined[j];
    h += "<div class='profrow'><div class='plab'>" + NAMES[j] + "</div>" +
      "<div class='pbox'><div class='pa' title='answered' style='width:" +
      (a/mx*50).toFixed(1) + "%'></div><div class='pd' title='declined' " +
      "style='width:" + (d/mx*50).toFixed(1) + "%'></div></div>" +
      "<div class='pval'>ans " + a.toFixed(3) + " · dec " + d.toFixed(3) +
      "</div></div>";
  }
  h += "<p class='note'>Interpretation caution (replicated E5 null, R=200): no " +
    "single feature is a stable abstention driver — a decline is a " +
    "CANCELLATION of signed contributions, a configuration property no " +
    "per-feature magnitude can localize. Read gaps descriptively, never " +
    "causally.</p>";
  document.getElementById("profpanel").innerHTML = h;
})();

// ---- case browser ----
let filter = "declined", query = "", sortBy = "margin_asc";
let order = [], cur = 0;
let xCur = null;
let selFeat = 0;                // response-curve feature
const caseList = document.getElementById("caselist");
function rebuildList(keepCase) {
  const kept = keepCase === undefined ? null : DATA.cases[keepCase].idx;
  order = DATA.cases.map((c,i) => i).filter(i => {
    const c = DATA.cases[i];
    if (filter === "declined" && !c.declined) return false;
    if (filter === "answered" && c.declined) return false;
    if (query && !String(c.idx).includes(query)) return false;
    if (binSel) {
      const s = scoreOf(c.x);
      if (s < binSel[0] || s >= binSel[1]) return false;
    }
    return true;
  });
  order.sort((a,b) => {
    const A = DATA.cases[a], B = DATA.cases[b];
    if (sortBy === "idx") return A.idx - B.idx;
    const d = Math.abs(A.margin_to_answer) - Math.abs(B.margin_to_answer);
    return sortBy === "margin_asc" ? d : -d;
  });
  cur = Math.max(0, order.findIndex(i => DATA.cases[i].idx === kept));
  caseList.innerHTML = "";
  order.forEach((i, k) => {
    const c = DATA.cases[i];
    const row = document.createElement("div");
    row.innerHTML = "case " + c.idx + " <span class='m'>" +
      (c.declined
        ? dual(Math.abs(c.margin_to_answer) < 0.1
                 ? "handed over &#183; a whisker from answering"
                 : "handed to a person",
               "declined &#183; margin " + c.margin_to_answer)
        : "answered") + "</span>";
    if (k === cur) row.className = "sel";
    row.onclick = () => { cur = k; selectCase(); };
    caseList.appendChild(row);
  });
  if (order.length) selectCase(); else
    document.getElementById("detail").innerHTML =
      "<p class='note'>No cases match the current filter.</p>";
}
function selectCase() {
  [...caseList.children].forEach((el,k) => el.className = k === cur ? "sel" : "");
  const el = caseList.children[cur];
  if (el) el.scrollIntoView({block: "nearest"});
  xCur = DATA.cases[order[cur]].x.slice();
  renderDetail();
}

// ---- advanced visualizations (all recomputed from xCur, exact) ----
function waterfallSVG() {
  const phi = phiOf(xCur);
  const ord = phi.map((v,j) => j).sort((a,b) => Math.abs(phi[b]) - Math.abs(phi[a]));
  const steps = [["base", H.intercept]];
  ord.forEach(j => steps.push([NAMES[j], phi[j]]));
  let cum = 0;
  const pts = steps.map(([lab, v]) => { const from = cum; cum += v; return [lab, from, cum]; });
  const lo = Math.min(-L_STAR, ...pts.map(p => Math.min(p[1], p[2]))) - 0.3;
  const hi = Math.max(L_STAR, ...pts.map(p => Math.max(p[1], p[2]))) + 0.3;
  const W = 640, Hh = 40 + 24*pts.length, X = v => 130 + (v-lo)/(hi-lo)*(W-150);
  let s = "<svg viewBox='0 0 " + W + " " + Hh + "' style='max-width:100%'>";
  [[L_STAR, "+L*"], [-L_STAR, "&#8722;L*"], [0, "0"]].forEach(([v, lab]) => {
    s += "<line class='tauline' x1='" + X(v) + "' y1='14' x2='" + X(v) +
      "' y2='" + (Hh-16) + "'/><text x='" + (X(v)-8) + "' y='11'>" + lab + "</text>";
  });
  pts.forEach(([lab, a, b], i) => {
    const y = 22 + 24*i;
    const x0 = X(Math.min(a,b)), w = Math.max(Math.abs(X(b)-X(a)), 1.5);
    const col = (b-a) >= 0 ? "var(--pos)" : "var(--neg)";
    s += "<text x='124' y='" + (y+10) + "' text-anchor='end'>" + lab + "</text>" +
      "<rect class='wfbar' x='" + x0 + "' y='" + y + "' width='" + w +
      "' height='13' rx='2' fill='" + (i === 0 ? "var(--mut)" : col) + "'/>" +
      "<text x='" + (X(Math.max(a,b))+4) + "' y='" + (y+10) + "'>" +
      (i === 0 ? a.toFixed(3) : ((b-a) >= 0 ? "+" : "") + (b-a).toFixed(3)) +
      "</text>";
  });
  const fx = X(pts[pts.length-1][2]);
  s += "<line x1='" + fx + "' y1='14' x2='" + fx + "' y2='" + (Hh-16) +
    "' stroke='var(--pos)' stroke-width='2'/><text x='" + (fx+4) + "' y='" +
    (Hh-4) + "'>logit " + pts[pts.length-1][2].toFixed(4) + "</text>";
  return s + "</svg>";
}
function responseSVG(j) {
  const lo = H.mu[j]-4*H.sd[j], hi = H.mu[j]+4*H.sd[j];
  const W = 640, Hh = 190, PX = 46, PY = 16;
  const X = t => PX + (t-lo)/(hi-lo)*(W-PX-10);
  const Y = s => Hh-24 - (s-0.5)/0.5*(Hh-24-PY);
  const xa = xCur.slice();
  let path = "";
  for (let k = 0; k <= 160; k++) {
    const t = lo + (hi-lo)*k/160;
    xa[j] = t;
    path += (k ? "L" : "M") + X(t).toFixed(1) + " " + Y(scoreOf(xa)).toFixed(1);
  }
  let s = "<svg viewBox='0 0 " + W + " " + Hh + "' style='max-width:100%'>";
  s += "<line class='axis' x1='" + PX + "' y1='" + (Hh-24) + "' x2='" + (W-8) +
    "' y2='" + (Hh-24) + "'/><line class='axis' x1='" + PX + "' y1='" + PY +
    "' x2='" + PX + "' y2='" + (Hh-24) + "'/>";
  s += "<line class='tauline' x1='" + PX + "' y1='" + Y(TAU) + "' x2='" + (W-8) +
    "' y2='" + Y(TAU) + "'/><text x='" + (PX+2) + "' y='" + (Y(TAU)-3) +
    "'>bar &#964;* = " + TAU + "</text>";
  ["0.5","0.75","1.0"].forEach(v => {
    s += "<text x='" + (PX-6) + "' y='" + (Y(+v)+4) +
      "' text-anchor='end'>" + v + "</text>";
  });
  s += "<path class='curve' d='" + path + "'/>";
  // exact single-feature crossings of the bar, from the affine identity
  const base = logitOf(xCur) - H.coef[j]*(xCur[j]-H.mu[j])/H.sd[j];
  if (H.coef[j] !== 0) {
    [L_STAR, -L_STAR].forEach(tgt => {
      const t = H.mu[j] + H.sd[j]*(tgt - base)/H.coef[j];
      if (t >= lo && t <= hi)
        s += "<circle class='cross' cx='" + X(t) + "' cy='" + Y(TAU) +
          "' r='4'><title>gate answers if " + NAMES[j] + " = " +
          t.toFixed(3) + "</title></circle>";
    });
  }
  s += "<circle class='nowpt' cx='" + X(xCur[j]) + "' cy='" +
    Y(scoreOf(xCur)) + "' r='4.5'><title>current value</title></circle>";
  s += "<text x='" + (W/2) + "' y='" + (Hh-6) + "' text-anchor='middle'>" +
    NAMES[j] + " (all other inputs held at their current what-if values)</text>";
  return s + "</svg>";
}
function numbersHTML() {
  const c = DATA.cases[order[cur]];
  const phi = phiOf(xCur);
  let h = "<table><tr><th>j</th><th>feature</th><th>x (current)</th>" +
    "<th>x (recorded)</th><th>&#956;</th><th>sd</th><th>z</th><th>w</th>" +
    "<th>&#966; = w&#183;z</th></tr>";
  for (let j = 0; j < D; j++) {
    h += "<tr><td>" + j + "</td><td>" + NAMES[j] + "</td><td class='num'>" +
      xCur[j].toFixed(6) + "</td><td class='num'>" + c.x[j].toFixed(6) +
      "</td><td class='num'>" + H.mu[j].toFixed(6) + "</td><td class='num'>" +
      H.sd[j].toFixed(6) + "</td><td class='num'>" +
      ((xCur[j]-H.mu[j])/H.sd[j]).toFixed(6) + "</td><td class='num'>" +
      H.coef[j].toFixed(6) + "</td><td class='num'>" + phi[j].toFixed(6) +
      "</td></tr>";
  }
  h += "</table><p class='note'>intercept " + H.intercept.toFixed(6) +
    " · logit = intercept + &#931;&#966; = " + logitOf(xCur).toFixed(6) +
    " · L* = " + L_STAR.toFixed(6) + "</p>" +
    "<button id='copyJson'>Copy case as JSON</button>" +
    "<span class='note' id='copied' style='display:none'> copied &#10003;</span>";
  return h;
}
function redrawAdvanced() {
  if (!order.length || xCur === null) return;
  const wf = document.getElementById("tab-waterfall");
  if (wf) wf.innerHTML =
    "<p class='note'>Cumulative build-up of the decision logit from the " +
    "intercept, largest |&#966;| first. The dashed lines are the answering " +
    "bars &#177;L*; the final marker is the case's logit.</p>" + waterfallSVG();
  const rc = document.getElementById("rcplot");
  if (rc) rc.innerHTML = responseSVG(selFeat);
  const nm = document.getElementById("tab-numbers");
  if (nm) { nm.innerHTML = numbersHTML(); wireCopy(); }
  const sb = document.getElementById("statusbar");
  if (sb) {
    const lg = logitOf(xCur);
    const c = DATA.cases[order[cur]];
    let dz = 0;
    for (let j = 0; j < D; j++) {
      const d = (xCur[j]-c.x[j])/H.sd[j];
      dz += d*d;
    }
    sb.innerHTML = "<span>logit <b>" + lg.toFixed(6) + "</b></span>" +
      "<span>|logit| <b>" + Math.abs(lg).toFixed(6) + "</b></span>" +
      "<span>L* <b>" + L_STAR.toFixed(6) + "</b></span>" +
      "<span>margin-to-answer <b>" + (L_STAR-Math.abs(lg)).toFixed(6) +
      "</b></span><span>&#916;z from recorded (L2) <b>" +
      Math.sqrt(dz).toFixed(6) + "</b></span>" +
      "<span>deployed rule <b>score " + scoreOf(xCur).toFixed(6) +
      (scoreOf(xCur) >= TAU ? " &#8805; " : " &lt; ") + TAU + "</b></span>";
  }
}
function wireCopy() {
  const b = document.getElementById("copyJson");
  if (!b) return;
  b.onclick = () => {
    const c = DATA.cases[order[cur]];
    const obj = {case: c.idx, tau_star: TAU, x_current: xCur,
                 x_recorded: c.x, logit: logitOf(xCur),
                 score: scoreOf(xCur), phi: phiOf(xCur),
                 deployed_rule_answers: scoreOf(xCur) >= TAU,
                 counterfactuals: c.counterfactuals,
                 note: "score-space description of the gate; not clinical advice"};
    const txt = JSON.stringify(obj, null, 2);
    const done = () => {
      const el = document.getElementById("copied");
      el.style.display = "inline";
      setTimeout(() => el.style.display = "none", 1500);
    };
    if (navigator.clipboard && navigator.clipboard.writeText)
      navigator.clipboard.writeText(txt).then(done, done);
    else {
      const ta = document.createElement("textarea");
      ta.value = txt; document.body.appendChild(ta); ta.select();
      document.execCommand("copy"); ta.remove(); done();
    }
  };
}
function selectTab(t) {
  ["decision","waterfall","response","numbers"].forEach(k => {
    const pane = document.getElementById("tab-" + k);
    const btn = document.getElementById("tb-" + k);
    if (pane) pane.classList.toggle("on", k === t);
    if (btn) btn.classList.toggle("on", k === t);
  });
  redrawAdvanced();
}

// ---- detail panel: built ONCE per case, then patched in place ----
function bars(phi, lead) {
  const t = phi.map(v => v*lead);
  const mx = Math.max(...t.map(Math.abs), 1e-9);
  return t.map((v,j) => {
    const w = Math.abs(v)/mx*50;
    const bar = v >= 0
      ? "<div class='bar pos' style='width:" + w + "%'></div>"
      : "<div class='bar neg' style='width:" + w + "%;margin-left:" + (50-w) + "%'></div>";
    return "<div class='barrow'><div class='barlab'>" + NAMES[j] + "</div>" +
      "<div class='barbox'><div class='mid'></div>" + bar + "</div>" +
      "<div class='barval num'>" + v.toFixed(3) + "</div></div>";
  }).join("");
}
function setSliders() {
  document.querySelectorAll("#detail input[type=range]").forEach(sl => {
    sl.value = xCur[+sl.dataset.j];
  });
}
function updateLive() {
  const c = DATA.cases[order[cur]];
  const lg = logitOf(xCur), p = sigmoid(lg), score = Math.max(p, 1-p);
  const answered = score >= TAU;                    // THE deployed rule
  const modified = xCur.some((v,j) => v !== c.x[j]);
  const pill = document.getElementById("verdictPill");
  pill.innerHTML = answered ? "ANSWERED"
    : dual("HANDED TO A PERSON", "DECLINED");
  pill.className = "verdict " + (answered ? "answered" : "declined");
  document.getElementById("modBadge").style.display =
    modified ? "inline-block" : "none";
  document.getElementById("leanS").textContent =
    lg >= 0 ? "higher risk" : "lower risk";
  document.getElementById("riskS").textContent = (p*100).toFixed(1) + "%";
  document.getElementById("needS").textContent = answered ? "" :
    " \\u2014 but it is not sure enough to answer";
  document.getElementById("leanTxt").textContent =
    lg >= 0 ? "positive" : "negative";
  document.getElementById("riskTxt").textContent = p.toFixed(4);
  document.getElementById("needTxt").textContent = answered ? "" :
    " \\u00b7 needs " + (L_STAR - Math.abs(lg)).toFixed(4) +
    " more logit-confidence";
  const left = ((Math.min(Math.max(score,0.5),1.0)-0.5)/0.5*100);
  document.getElementById("needle").style.left =
    "calc(" + left.toFixed(2) + "% - 4px)";
  document.getElementById("gscore").innerHTML =
    dual("how sure: " + (score*100).toFixed(1) + "%",
         "score " + score.toFixed(4));
  document.getElementById("phibars").innerHTML = bars(phiOf(xCur), lg >= 0 ? 1 : -1);
  document.getElementById("btnReset").classList.toggle("attn", modified);
  xCur.forEach((v,j) => {
    document.getElementById("sv"+j).textContent = (+v).toFixed(3);
    document.getElementById("rs"+j).className =
      "rst" + (v !== c.x[j] ? " on" : "");
  });
  if (document.body.classList.contains("adv")) redrawAdvanced();
}
let rafPending = null;
function updateLiveThrottled() {
  rafPending = rafPending || requestAnimationFrame(() => {
    rafPending = null;
    updateLive();
  });
}
function renderDetail() {
  const c = DATA.cases[order[cur]];
  let h = "<p><span class='verdict' id='verdictPill'></span>" +
    "<span class='badge' id='modBadge' style='display:none'>" +
    dual("you changed the inputs \\u2014 this is a what-if, not the real case",
         "inputs modified \\u2014 live what-if") + "</span>" +
    "<span class='simponly'> \\u00b7 the program leans <b id='leanS'></b> \\u2014 it " +
    "estimates a <span class='num' id='riskS'></span> chance of the " +
    "outcome<span id='needS'></span></span>" +
    "<span class='advonly'> \\u00b7 model leans <b id='leanTxt'></b>" +
    " \\u00b7 risk score <span class='num' id='riskTxt'></span>" +
    "<span id='needTxt'></span></span></p>";
  h += "<div class='gauge'>" +
    "<div class='tau' data-l='bar' style='left:" +
    ((TAU-0.5)/0.5*100).toFixed(2) + "%'></div>" +
    "<div class='needle' id='needle'></div></div>" +
    "<div class='gaxis'><span>0.50</span><span id='gscore'></span>" +
    "<span>1.00</span></div>";
  h += "<p style='margin:10px 0 4px'>";
  if (c.declined && c.delta_x_min) {
    h += "<button class='primary' id='btnFlip'>" +
      dual("Show the smallest change that makes it answer",
           "Apply smallest flip") + "</button>";
    if (c.counterfactuals.length)
      h += "<button id='btnFlip1'>" +
        dual("Change just one measurement", "Apply top single-input flip") +
        "</button>";
  }
  h += "<button id='btnReset' title='discard every what-if change and return " +
       "to the values this case was actually scored on'>" +
       dual("Back to the real values", "Reset to recorded inputs") +
       "</button></p>";
  // advanced workbench tabs (hidden entirely in simple mode)
  h += "<div class='tabs advonly'>" +
    "<span class='tabbtn on' id='tb-decision'>Decision</span>" +
    "<span class='tabbtn' id='tb-waterfall'>Waterfall</span>" +
    "<span class='tabbtn' id='tb-response'>Response curve</span>" +
    "<span class='tabbtn' id='tb-numbers'>Numbers</span></div>";
  h += "<div class='tabpane on' id='tab-decision'>";
  h += "<h2 style='margin-top:6px'>" +
       dual("Try it yourself: move a value, the program re-decides",
            "What-if: move an input, the gate re-decides") +
       "</h2><p class='note'>" +
       dual("Every slider is live. Moving one only asks the program a " +
            "question \\u2014 it says nothing about a real patient. A " +
            "<span style='color:var(--dec)'>&#8634;</span> appears next to " +
            "anything you have changed; click it to put that value back.",
            "Every slider is live and re-runs the deployed rule. Click a " +
            "feature name to plot its response curve. " +
            "<span style='color:var(--dec)'>&#8634;</span> restores one " +
            "input; the reset button restores all.") + "</p>";
  xCur.forEach((v,j) => {
    const lo = H.mu[j]-4*H.sd[j], hi = H.mu[j]+4*H.sd[j];
    h += "<div class='srow'><label data-j='" + j + "' title='" + NAMES[j] +
      " \\u2014 click to plot response curve'>" + NAMES[j] +
      "</label><input type='range' data-j='" + j + "' min='" + lo +
      "' max='" + hi + "' step='" + ((hi-lo)/400) + "' value='" + v +
      "'><span class='v num' id='sv" + j + "'></span>" +
      "<span class='rst' id='rs" + j + "' data-j='" + j +
      "' title='recorded value: " + (+c.x[j]).toFixed(3) +
      " \\u2014 click to restore'>&#8634;</span></div>";
  });
  h += "<h2 style='margin-top:12px'>" +
    dual("What pushed its confidence up or down",
         "What drives the confidence") + "</h2>" +
    "<p class='note'>" +
    dual("Bars pointing right push toward the program's leaning; bars " +
         "pointing left pull against it. When the pushes and pulls cancel " +
         "out, it is not sure enough \\u2014 and hands the case to a person.",
         "Bars right of the line build confidence toward the leaned class; " +
         "bars left erode it \\u2014 cancellation is what causes a decline.") +
    "</p><div id='phibars'></div>";
  if (c.declined && c.counterfactuals.length) {
    h += "<h2 style='margin-top:12px'>" +
      dual("What would have to be different for it to answer",
           "Smallest single-input changes that would make the gate answer") +
      "</h2><p class='note'>" +
      dual("Each row is the smallest change to ONE value that would let the " +
           "program answer \\u2014 and even then it would only just clear the " +
           "bar (the least-confident answer it is allowed to give).",
           "Ranked by standardized magnitude; each clears the bar by a hair, " +
           "so the answer would carry the weakest allowed confidence, " +
           fmt(c.confidence_at_flip) + ".") +
      "</p><table><tr><th>" + dual("measurement", "input") + "</th>" +
      "<th>" + dual("change needed", "change needed (raw units)") + "</th>" +
      "<th class='advonly'>(standardized)</th>" +
      "<th>" + dual("it would then say", "gate would then answer") +
      "</th></tr>";
    c.counterfactuals.forEach(cf => {
      h += "<tr><td>" + cf.feature + "</td><td class='num'>" +
        (cf.delta_x >= 0 ? "+" : "") + cf.delta_x.toFixed(3) +
        "</td><td class='num advonly'>" + (cf.delta_z >= 0 ? "+" : "") +
        cf.delta_z.toFixed(3) + "</td><td>" +
        dual(cf.answers_as === "predicted-positive"
               ? "higher risk" : "lower risk", cf.answers_as) +
        "</td></tr>";
    });
    h += "</table><p class='note'>" +
      dual("Remember: these rows describe the computer program, never the " +
           "patient.",
           "Smallest whole-profile change (standardized L2): " +
           fmt(c.l2_distance_z) +
           ". These describe the gate, not the patient.") + "</p>";
  }
  h += "</div>";   // end tab-decision
  h += "<div class='tabpane advonly' id='tab-waterfall'></div>";
  h += "<div class='tabpane advonly' id='tab-response'>" +
    "<p class='note'>Exact score response to ONE input with every other input " +
    "held at its current what-if value; red dots are the single-feature bar " +
    "crossings (the gate answers exactly there). Pick the input:</p>" +
    "<select id='rcsel' style='max-width:240px'></select>" +
    "<div id='rcplot' style='margin-top:8px'></div></div>";
  h += "<div class='tabpane advonly' id='tab-numbers'></div>";
  h += "<div class='statusbar advonly' id='statusbar'></div>";
  const box = document.getElementById("detail");
  box.innerHTML = h;
  box.querySelectorAll("input[type=range]").forEach(sl => {
    sl.addEventListener("input", () => {
      xCur[+sl.dataset.j] = +sl.value;
      updateLiveThrottled();
    });
  });
  box.querySelectorAll(".srow label").forEach(lb => {
    lb.addEventListener("click", () => {
      selFeat = +lb.dataset.j;
      const rs = document.getElementById("rcsel");
      if (rs) rs.value = selFeat;
      if (document.body.classList.contains("adv")) selectTab("response");
    });
  });
  box.querySelectorAll(".rst").forEach(rs => {
    rs.addEventListener("click", () => {
      const j = +rs.dataset.j;
      xCur[j] = c.x[j];
      setSliders();
      updateLive();
    });
  });
  const bF = document.getElementById("btnFlip");
  if (bF) bF.onclick = () => {
    xCur = c.x.map((v,j) => v + c.delta_x_min[j]);
    setSliders();
    updateLive();
  };
  const b1 = document.getElementById("btnFlip1");
  if (b1) b1.onclick = () => {
    const cf = c.counterfactuals[0];
    xCur = c.x.slice();
    xCur[cf.j] += cf.delta_x;
    setSliders();
    updateLive();
  };
  document.getElementById("btnReset").onclick = () => {
    xCur = c.x.slice();
    setSliders();
    updateLive();
  };
  ["decision","waterfall","response","numbers"].forEach(k => {
    const btn = document.getElementById("tb-" + k);
    if (btn) btn.onclick = () => selectTab(k);
  });
  const rsel = document.getElementById("rcsel");
  NAMES.forEach((nm, j) => {
    const o = document.createElement("option");
    o.value = j; o.textContent = nm;
    rsel.appendChild(o);
  });
  rsel.value = selFeat;
  rsel.onchange = () => { selFeat = +rsel.value; redrawAdvanced(); };
  updateLive();
}

// ---- filters, search, sort, keyboard ----
document.querySelectorAll(".side .chip[data-f]").forEach(ch => ch.onclick = () => {
  document.querySelectorAll(".side .chip[data-f]").forEach(c =>
    c.classList.remove("on"));
  ch.classList.add("on");
  filter = ch.dataset.f;
  rebuildList();
});
document.getElementById("search").addEventListener("input", e => {
  query = e.target.value.trim();
  rebuildList();
});
document.getElementById("sortSel").addEventListener("change", e => {
  sortBy = e.target.value;
  rebuildList(order[cur]);
});
const helpov = document.getElementById("helpov");
document.getElementById("helpclose").onclick = () => helpov.classList.remove("on");
document.addEventListener("keydown", e => {
  if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT") return;
  if (e.key === "ArrowRight" && cur < order.length-1) { cur++; selectCase(); }
  if (e.key === "ArrowLeft" && cur > 0) { cur--; selectCase(); }
  if (!document.body.classList.contains("adv")) return;
  if (e.key === "?") helpov.classList.toggle("on");
  if (e.key === "1") selectTab("decision");
  if (e.key === "2") selectTab("waterfall");
  if (e.key === "3") selectTab("response");
  if (e.key === "4") selectTab("numbers");
  if (e.key === "f") { const b = document.getElementById("btnFlip"); if (b) b.click(); }
  if (e.key === "r") { const b = document.getElementById("btnReset"); if (b) b.click(); }
});

// ---- threshold explorer (intuition only; changes nothing above) ----
const tX = document.getElementById("tauX"), tXv = document.getElementById("tauXv");
tX.value = TAU;
function exploreUpdate() {
  const t = +tX.value;
  const n = DATA.all_scores.length;
  const ans = DATA.all_scores.filter(s => s >= t).length;
  tXv.innerHTML = dual(
    "bar " + t.toFixed(2) + " \\u2192 answers " + (ans/n*100).toFixed(1) +
      "% (" + (n-ans) + " handed over)",
    "bar " + t.toFixed(2) + " \\u2192 coverage " + (ans/n*100).toFixed(1) +
      "% (" + (n-ans) + " declined)");
}
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
                           oracle_y=pool.y)
    n_declined = int((head.score(pool.x) < 0.77).sum())
    print(f"[dashboard] wrote {path} ({pool.n} cases, {n_declined} declined)")


if __name__ == "__main__":
    main()
