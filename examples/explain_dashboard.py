"""Self-contained interactive HTML dashboard for the explanation layer (demo).

Renders, for a scored cohort at one operating threshold, what a non-technical
reader sees per case — and lets them interrogate it live:

- a case browser (filter answered/declined, search, sort by margin);
- a live score gauge against the answering bar, plus WHAT-IF sliders: the
  head is linear, so the page recomputes ``logit = intercept + sum(coef*z)``
  in the browser in the same float64 the pipeline uses — dragging a slider
  re-runs the actual deployed rule ``score >= tau``, not an approximation;
- one-click "apply smallest flip" / "apply top single-input flip" buttons
  that apply the exact counterfactuals from
  ``certgate.explain.counterfactual_to_answer`` and let the viewer WATCH the
  verdict flip — the functionally-grounded check, performable by a human;
- exact additive attribution bars (interventional Shapley values of the
  linear head), recomputed live as sliders move;
- a cohort score histogram with the bar marked, and a threshold EXPLORER
  fenced as intuition-only (deployment thresholds are selected by the
  certificate, never by hand — the explorer confers no guarantee).

The output is ONE .html file with no external assets, scripts or network
access — it can be opened from disk by anyone with a browser. The embedded
data is a demonstration cohort from the synthetic generator; for real data,
call ``build_dashboard`` on your own fitted head and cohort LOCALLY. Nothing
here touches the certified path, and record-level displays of restricted data
(e.g. an eICU extract) must stay on the analyst's machine per the DUA — this
script never writes into ``experiments/out``.

Honesty constraints carried into the page itself (SPEC explain.py):
- counterfactuals and slider what-ifs are SCORE-SPACE questions to the gate
  ("what would the gate need"), never causal or clinical advice; the caveat
  box is not removable, and the slider panel repeats it.
- the minimal flip clears the bar by the documented 1e-9 logit headroom, so
  it is the WEAKEST answerable answer, at confidence a hair above tau*.
- the certificate is a site-population-average guarantee; no single record
  carries a certified property, and the page says so.
- the threshold explorer is labeled as understanding-only and shows no
  certificate language.

Run:  python -m examples.explain_dashboard   (writes examples/explain_dashboard.html)
"""
from __future__ import annotations

import json
import os

import numpy as np

from certgate.constants import SEED
from certgate.data import SimConfig, draw_cohort, split_sites
from certgate.explain import counterfactual_to_answer
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
    first ``_MAX_ANSWERED_SHOWN``. The cohort histogram covers ALL cases.
    Returns ``out_path``.
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
<title>CertGate — interactive explanation dashboard (demonstration)</title>
<style>
  :root { --ink:#1a2233; --mut:#5b6572; --line:#d8dee7; --bg:#f4f6fa;
          --card:#ffffff; --pos:#2563eb; --neg:#b45309; --dec:#b91c1c;
          --ans:#15803d; --chip:#e8edf5; --hl:#eef4ff; }
  * { box-sizing:border-box; }
  body { margin:0; font:14.5px/1.5 system-ui,Segoe UI,Roboto,sans-serif;
         color:var(--ink); background:var(--bg); }
  header { padding:16px 22px 4px; }
  h1 { font-size:19px; margin:0 0 2px; }
  h2 { font-size:14px; margin:0 0 8px; }
  .sub { color:var(--mut); font-size:13px; }
  main { max-width:1120px; margin:0 auto; padding:10px 22px 30px; }
  .card { background:var(--card); border:1px solid var(--line);
          border-radius:10px; padding:14px 16px; margin:12px 0; }
  .caveat { border-left:4px solid var(--dec); font-size:13px; }
  .caveat b { color:var(--dec); }
  .strip { display:flex; gap:16px; flex-wrap:wrap; font-size:13px; }
  .strip div b { display:block; font-size:16px; }
  .cols { display:flex; gap:12px; align-items:flex-start; flex-wrap:wrap; }
  .side { flex:0 0 270px; max-width:100%; }
  .detail { flex:1 1 480px; min-width:320px; }
  .chip { display:inline-block; padding:3px 10px; border-radius:999px;
          background:var(--chip); cursor:pointer; font-size:12.5px;
          border:1px solid transparent; user-select:none; }
  .chip.on { background:var(--hl); border-color:var(--pos); color:var(--pos);
             font-weight:600; }
  input[type=text], select { font:inherit; padding:5px 8px;
          border:1px solid var(--line); border-radius:8px; width:100%; }
  .cl { margin-top:8px; max-height:430px; overflow-y:auto;
        border:1px solid var(--line); border-radius:8px; }
  .cl div { padding:5px 9px; cursor:pointer; font-size:12.5px;
            border-bottom:1px solid var(--line); }
  .cl div:last-child { border-bottom:none; }
  .cl div.sel { background:var(--hl); font-weight:600; }
  .cl .m { color:var(--mut); }
  .verdict { display:inline-block; padding:2px 10px; border-radius:999px;
             color:#fff; font-weight:600; font-size:13px; }
  .verdict.declined { background:var(--dec); }
  .verdict.answered { background:var(--ans); }
  .badge { display:inline-block; padding:1px 8px; border-radius:999px;
           background:#fef3c7; color:#92400e; font-size:11.5px;
           font-weight:600; margin-left:8px; }
  button { font:inherit; font-size:12.5px; padding:6px 10px; margin:2px 4px 2px 0;
           border:1px solid var(--line); border-radius:8px; background:#fff;
           cursor:pointer; }
  button:hover { background:var(--hl); }
  button.primary { border-color:var(--pos); color:var(--pos); font-weight:600; }
  .gauge { position:relative; height:26px; background:linear-gradient(90deg,
           #fee2e2, #fef9c3 55%, #dcfce7); border-radius:6px;
           border:1px solid var(--line); margin:8px 0 2px; }
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
                white-space:nowrap; overflow:hidden; }
  .srow input[type=range] { width:100%; accent-color:var(--pos); }
  .srow .v { font-size:12px; font-variant-numeric:tabular-nums; }
  .rst { color:var(--dec); cursor:pointer; font-size:14px; line-height:1;
         user-select:none; visibility:hidden; }
  .rst.on { visibility:visible; }
  button.attn { border-color:var(--dec); color:var(--dec); font-weight:600; }
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
  .hist .hb { flex:1; background:#c7d4e8; border-radius:2px 2px 0 0;
              min-height:1px; }
  .hist .hb.dec { background:#f3b8b8; }
  .hist .tau { position:absolute; top:-4px; bottom:-14px; width:2px;
               background:var(--ink); }
  .num { font-variant-numeric:tabular-nums; }
  .note { color:var(--mut); font-size:12px; }
  .fence { border:1.5px dashed var(--neg); border-radius:10px;
           padding:12px 16px; margin:12px 0; background:#fffbf5; }
  .fence b.t { color:var(--neg); }
  footer { color:var(--mut); font-size:12px; max-width:1120px;
           margin:0 auto; padding:0 22px 26px; }
  kbd { background:var(--chip); border-radius:4px; padding:0 5px;
        font-size:11px; }
</style>
</head>
<body>
<header>
  <h1>CertGate — why this case was answered or declined</h1>
  <div class="sub" id="subtitle"></div>
</header>
<main>
  <div class="card caveat">
    <b>Read this first.</b> Everything interactive on this page — sliders,
    flip buttons, the threshold explorer — asks a <b>score-space</b> question of
    the gate: <i>what would the model's inputs need to be</i> for the case to
    clear the answering bar. These are <b>not</b> causal claims, not treatment
    suggestions, and not clinically achievable actions (features are not
    independently changeable). A case flipped by the minimal change is answered
    at the <b>weakest possible confidence</b>, a hair above the bar itself. The
    error-rate certificate is a <b>site-population-average</b> guarantee over
    answered cases: no individual record carries a certified property of its
    own. This page shows a <span id="cohortlabel"></span>.
  </div>

  <div class="card">
    <div class="strip" id="cohortstrip"></div>
    <div class="hist" id="hist"></div>
    <div class="gaxis"><span>score 0.50 (maximally contested)</span>
      <span>1.00 (maximally confident)</span></div>
    <div class="note">Cohort confidence-score distribution. Red bars sit below
      the answering bar (declined); the dark line is the deployed bar
      τ* = <span id="taulab"></span>.</div>
  </div>

  <div class="cols">
    <div class="side card">
      <h2>Cases <span class="note">(<kbd>←</kbd>/<kbd>→</kbd> to step)</span></h2>
      <span class="chip" data-f="all">all</span>
      <span class="chip on" data-f="declined">declined</span>
      <span class="chip" data-f="answered">answered</span>
      <div style="margin:8px 0 4px"><input type="text" id="search"
        placeholder="search case number…"></div>
      <select id="sortSel">
        <option value="margin_asc">closest to answering first</option>
        <option value="margin_desc">farthest from answering first</option>
        <option value="idx">by case number</option>
      </select>
      <div class="cl" id="caselist"></div>
    </div>

    <div class="detail card" id="detail"></div>
  </div>

  <div class="fence" id="explorer">
    <b class="t">Threshold explorer — for intuition only.</b>
    <span class="note">Deployed thresholds are selected by the certificate,
    never by hand; moving this slider confers no guarantee and does not change
    the verdicts above.</span><br>
    <div class="srow" style="grid-template-columns:104px 1fr 200px">
      <label>explore bar</label>
      <input type="range" id="tauX" min="0.55" max="0.99" step="0.01">
      <span class="v" id="tauXv"></span>
    </div>
  </div>
</main>
<footer>
  Generated by <code>examples/explain_dashboard.py</code>. The page recomputes
  the head's own arithmetic (float64) locally: sliders and flip buttons re-run
  the deployed answering rule, so what you see is the gate itself, not a
  visualization of it. Attributions are exact interventional Shapley values of
  the linear head; counterfactual deltas come from
  <code>certgate.explain.counterfactual_to_answer</code> (SPEC "explain.py").
  Self-contained file, no network access.
</footer>
<script>
"use strict";
const DATA = __PAYLOAD__;
const H = DATA.head, TAU = DATA.tau_star, NAMES = DATA.feature_names;
const fmt = (v, n=4) => (v === null || v === undefined) ? "—" : (+v).toFixed(n);

// ---- the head's own arithmetic, in the same float64 the pipeline uses ----
const sigmoid = z => z >= 0 ? 1/(1+Math.exp(-z)) : (e => e/(1+e))(Math.exp(z));
const logitOf = x => {
  let s = H.intercept;
  for (let j = 0; j < x.length; j++) s += H.coef[j]*(x[j]-H.mu[j])/H.sd[j];
  return s;
};
const scoreOf = x => { const p = sigmoid(logitOf(x)); return Math.max(p, 1-p); };
const phiOf = x => H.coef.map((c,j) => c*(x[j]-H.mu[j])/H.sd[j]);

// ---- static chrome ----
document.getElementById("subtitle").textContent =
  "Operating threshold τ* = " + TAU + " · " + DATA.cohort_label +
  " · interactive: every number on this page is recomputed live by the head's own formula";
document.getElementById("cohortlabel").textContent = DATA.cohort_label;
document.getElementById("taulab").textContent = TAU;
const strip = document.getElementById("cohortstrip");
const stat = (label, val) => {
  const el = document.createElement("div");
  el.innerHTML = "<b class='num'>" + fmt(val, (typeof val === "number" && val % 1) ? 4 : 0) + "</b>" + label;
  strip.appendChild(el);
};
stat("cases scored", DATA.n_total);
stat("answered", DATA.n_answered);
stat("declined", DATA.n_declined);
stat("coverage", DATA.coverage);
stat("answered predicted-positive fraction", DATA.predicted_positive_fraction);
if (DATA.oracle_positive_fraction !== null)
  stat("answered true-positive fraction (oracle, harness only)",
       DATA.oracle_positive_fraction);

// ---- cohort histogram ----
const NB = 50, bins = new Array(NB).fill(0);
DATA.all_scores.forEach(s => {
  const b = Math.min(NB-1, Math.floor((s-0.5)/0.5*NB));
  bins[b]++;
});
const hist = document.getElementById("hist");
const bmax = Math.max(...bins);
bins.forEach((n, b) => {
  const lo = 0.5 + b*0.5/NB;
  const el = document.createElement("div");
  el.className = "hb" + (lo + 0.5/NB <= TAU ? " dec" : "");
  el.style.height = (n/bmax*100).toFixed(1) + "%";
  el.title = n + " cases with score in [" + lo.toFixed(3) + ", " +
             (lo+0.5/NB).toFixed(3) + ")";
  hist.appendChild(el);
});
const tl = document.createElement("div");
tl.className = "tau";
tl.style.left = ((TAU-0.5)/0.5*100).toFixed(2) + "%";
hist.appendChild(tl);

// ---- case browser ----
let filter = "declined", query = "", sortBy = "margin_asc";
let order = [], cur = 0;
let xCur = null;                                   // live (possibly modified) inputs
const caseList = document.getElementById("caselist");
function rebuildList(keepCase) {
  const kept = keepCase === undefined ? null : DATA.cases[keepCase].idx;
  order = DATA.cases.map((c,i) => i).filter(i => {
    const c = DATA.cases[i];
    if (filter === "declined" && !c.declined) return false;
    if (filter === "answered" && c.declined) return false;
    if (query && !String(c.idx).includes(query)) return false;
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
      (c.declined ? "declined · margin " + c.margin_to_answer
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

// ---- detail panel: built ONCE per case, then patched in place so a slider
// ---- drag is never interrupted by a DOM rebuild ----
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
function setSliders(c) {          // push xCur into the slider DOM (reset/flip paths)
  document.querySelectorAll("#detail input[type=range]").forEach(sl => {
    const j = +sl.dataset.j;
    sl.value = xCur[j];
  });
}
function updateLive() {
  const c = DATA.cases[order[cur]];
  const lg = logitOf(xCur), p = sigmoid(lg), score = Math.max(p, 1-p);
  const answered = score >= TAU;                    // THE deployed rule
  const modified = xCur.some((v,j) => v !== c.x[j]);
  const pill = document.getElementById("verdictPill");
  pill.textContent = answered ? "ANSWERED" : "DECLINED";
  pill.className = "verdict " + (answered ? "answered" : "declined");
  document.getElementById("modBadge").style.display =
    modified ? "inline-block" : "none";
  document.getElementById("leanTxt").textContent =
    lg >= 0 ? "positive" : "negative";
  document.getElementById("riskTxt").textContent = p.toFixed(4);
  document.getElementById("needTxt").textContent = answered ? "" :
    " · needs " + (Math.log(TAU/(1-TAU)) - Math.abs(lg)).toFixed(4) +
    " more logit-confidence";
  const left = ((Math.min(Math.max(score,0.5),1.0)-0.5)/0.5*100);
  document.getElementById("needle").style.left =
    "calc(" + left.toFixed(2) + "% - 4px)";
  document.getElementById("gscore").textContent = "score " + score.toFixed(4);
  document.getElementById("phibars").innerHTML = bars(phiOf(xCur), lg >= 0 ? 1 : -1);
  const bR = document.getElementById("btnReset");
  bR.classList.toggle("attn", modified);
  xCur.forEach((v,j) => {
    document.getElementById("sv"+j).textContent = (+v).toFixed(3);
    document.getElementById("rs"+j).className =
      "rst" + (v !== c.x[j] ? " on" : "");
  });
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
    "<span class='badge' id='modBadge' style='display:none'>inputs modified " +
    "— live what-if</span>" +
    " · model leans <b id='leanTxt'></b>" +
    " · risk score <span class='num' id='riskTxt'></span>" +
    "<span id='needTxt'></span></p>";
  h += "<div class='gauge'>" +
    "<div class='tau' data-l='bar' style='left:" +
    ((TAU-0.5)/0.5*100).toFixed(2) + "%'></div>" +
    "<div class='needle' id='needle'></div></div>" +
    "<div class='gaxis'><span>0.50</span><span id='gscore'></span>" +
    "<span>1.00</span></div>";
  h += "<p style='margin:10px 0 4px'>";
  if (c.declined && c.delta_x_min) {
    h += "<button class='primary' id='btnFlip'>Apply smallest flip</button>";
    if (c.counterfactuals.length)
      h += "<button id='btnFlip1'>Apply top single-input flip</button>";
  }
  h += "<button id='btnReset' title='discard every what-if change and return " +
       "to the values this case was actually scored on'>Reset to recorded " +
       "inputs</button></p>";
  h += "<h2 style='margin-top:10px'>What-if: move an input, the gate re-decides" +
       "</h2><p class='note'>Every slider is live. Moving one asks the gate a " +
       "question; it does not model the patient. A <span style='color:var(--dec)'>" +
       "&#8634;</span> appears on any changed input — click it to restore that " +
       "input's recorded value.</p>";
  xCur.forEach((v,j) => {
    const lo = H.mu[j]-4*H.sd[j], hi = H.mu[j]+4*H.sd[j];
    h += "<div class='srow'><label title='" + NAMES[j] + "'>" + NAMES[j] +
      "</label><input type='range' data-j='" + j + "' min='" + lo +
      "' max='" + hi + "' step='" + ((hi-lo)/400) + "' value='" + v +
      "'><span class='v num' id='sv" + j + "'></span>" +
      "<span class='rst' id='rs" + j + "' data-j='" + j +
      "' title='recorded value: " + (+c.x[j]).toFixed(3) +
      " — click to restore'>&#8634;</span></div>";
  });
  h += "<h2 style='margin-top:12px'>What drives the confidence</h2>" +
    "<p class='note'>Bars right of the line build confidence toward the leaned " +
    "class; bars left erode it — cancellation is what causes a decline.</p>" +
    "<div id='phibars'></div>";
  if (c.declined && c.counterfactuals.length) {
    h += "<h2 style='margin-top:12px'>Smallest single-input changes that would " +
      "make the gate answer</h2><p class='note'>Ranked by standardized " +
      "magnitude; each clears the bar by a hair, so the answer would carry the " +
      "weakest allowed confidence, " + fmt(c.confidence_at_flip) +
      ".</p><table><tr><th>input</th><th>change needed (raw units)</th>" +
      "<th>(standardized)</th><th>gate would then answer</th></tr>";
    c.counterfactuals.forEach(cf => {
      h += "<tr><td>" + cf.feature + "</td><td class='num'>" +
        (cf.delta_x >= 0 ? "+" : "") + cf.delta_x.toFixed(3) +
        "</td><td class='num'>" + (cf.delta_z >= 0 ? "+" : "") +
        cf.delta_z.toFixed(3) + "</td><td>" + cf.answers_as + "</td></tr>";
    });
    h += "</table><p class='note'>Smallest whole-profile change (standardized " +
      "L2): " + fmt(c.l2_distance_z) +
      ". These describe the gate, not the patient.</p>";
  }
  const box = document.getElementById("detail");
  box.innerHTML = h;
  box.querySelectorAll("input[type=range]").forEach(sl => {
    sl.addEventListener("input", () => {
      xCur[+sl.dataset.j] = +sl.value;
      updateLiveThrottled();
    });
  });
  box.querySelectorAll(".rst").forEach(rs => {
    rs.addEventListener("click", () => {
      const j = +rs.dataset.j;
      xCur[j] = c.x[j];
      setSliders(c);
      updateLive();
    });
  });
  const bF = document.getElementById("btnFlip");
  if (bF) bF.onclick = () => {
    xCur = c.x.map((v,j) => v + c.delta_x_min[j]);
    setSliders(c);
    updateLive();
  };
  const b1 = document.getElementById("btnFlip1");
  if (b1) b1.onclick = () => {
    const cf = c.counterfactuals[0];
    xCur = c.x.slice();
    xCur[cf.j] += cf.delta_x;
    setSliders(c);
    updateLive();
  };
  document.getElementById("btnReset").onclick = () => {
    xCur = c.x.slice();
    setSliders(c);
    updateLive();
  };
  updateLive();
}

// ---- filters, search, sort, keyboard ----
document.querySelectorAll(".chip").forEach(ch => ch.onclick = () => {
  document.querySelectorAll(".chip").forEach(c => c.classList.remove("on"));
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
document.addEventListener("keydown", e => {
  if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT") return;
  if (e.key === "ArrowRight" && cur < order.length-1) { cur++; selectCase(); }
  if (e.key === "ArrowLeft" && cur > 0) { cur--; selectCase(); }
});

// ---- threshold explorer (intuition only; changes nothing above) ----
const tX = document.getElementById("tauX"), tXv = document.getElementById("tauXv");
tX.value = TAU;
function exploreUpdate() {
  const t = +tX.value;
  const n = DATA.all_scores.length;
  const ans = DATA.all_scores.filter(s => s >= t).length;
  tXv.innerHTML = "bar " + t.toFixed(2) + " → coverage " +
    (ans/n*100).toFixed(1) + "% (" + (n-ans) + " declined)";
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
