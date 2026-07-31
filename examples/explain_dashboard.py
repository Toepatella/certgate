"""Self-contained HTML dashboard for the explanation layer (demonstration).

Renders, for a scored cohort at one operating threshold, what a non-technical
reader sees per case: the answer/decline verdict, the exact additive
attributions (interventional Shapley values of the linear head), and -- for
declined cases -- the exact contrastive counterfactuals from
``certgate.explain.counterfactual_to_answer``: the smallest single-feature
changes that would make the case answerable, each stated with the class the
gate would then answer and the (weakest-possible) confidence tau* it would
carry.

The output is ONE .html file with no external assets, scripts or network
access -- it can be opened from disk by anyone with a browser. The embedded
data is a demonstration cohort from the synthetic generator; for real data,
call ``build_dashboard`` on your own fitted head and cohort LOCALLY. Nothing
here touches the certified path, and record-level displays of restricted data
(e.g. an eICU extract) must stay on the analyst's machine per the DUA -- this
script never writes into ``experiments/out``.

Honesty constraints carried into the page itself (SPEC explain.py):
- counterfactuals are SCORE-SPACE recourse ("what would the gate need"),
  never causal or clinical advice; the caveat box is not removable.
- the minimal flip lands exactly ON the bar, so it is the WEAKEST answerable
  answer, at confidence exactly tau*.
- the certificate is a site-population-average guarantee; no single record
  carries a certified property, and the page says so.

Run:  python -m examples.explain_dashboard   (writes examples/explain_dashboard.html)
"""
from __future__ import annotations

import json
import os

import numpy as np

from certgate.constants import SEED
from certgate.data import SimConfig, draw_cohort, split_sites
from certgate.explain import (abstention_explanation, composition,
                              counterfactual_to_answer)
from certgate.model import fit_head

_MAX_ANSWERED_SHOWN = 20      # every declined case is shown; answered are sampled


def _case_payload(head, x_row, idx, tau_star, feature_names):
    exp = abstention_explanation(head, x_row, tau_star)
    cf = counterfactual_to_answer(head, x_row, tau_star)
    lean_positive = bool(exp["logit"] >= 0)
    cfs = []
    if cf["declined"] and cf["flip_verified"]:
        for j in cf["single_feature_ranking"][:5]:
            j = int(j)
            cfs.append({
                "feature": feature_names[j],
                "delta_x": float(cf["single_feature_delta_x"][j]),
                "delta_z": float(cf["single_feature_delta_z"][j]),
                "answers_as": "predicted-positive" if cf["answered_class_on_flip"]
                              else "predicted-negative",
            })
    return {
        "idx": int(idx),
        "declined": bool(exp["declined"]),
        "p1": round(exp["p1"], 4),
        "confidence": round(max(exp["p1"], 1.0 - exp["p1"]), 4),
        "margin_to_answer": round(exp["margin_to_answer"], 4),
        "lean": "positive" if lean_positive else "negative",
        "phi_toward": [round(float(v), 4) for v in exp["toward_confidence"]],
        "counterfactuals": cfs,
        "l2_distance_z": (round(cf["l2_distance_z"], 4)
                          if np.isfinite(cf["l2_distance_z"]) else None),
        "confidence_at_flip": (round(cf["confidence_at_flip"], 4)
                               if cf["confidence_at_flip"] is not None else None),
    }


def build_dashboard(head, x, tau_star, out_path, feature_names=None,
                    oracle_y=None, cohort_label="synthetic demonstration cohort"):
    """Write a self-contained explanation dashboard for ``x`` at ``tau_star``.

    Every declined case is included; answered cases are truncated to the first
    ``_MAX_ANSWERED_SHOWN`` so the file stays small. Returns ``out_path``.
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
    comp = composition(head, x, answered,
                       oracle_y=oracle_y if oracle_y is not None else None)
    payload = {
        "tau_star": float(tau_star),
        "cohort_label": cohort_label,
        "n_total": int(x.shape[0]),
        "n_answered": int(answered.sum()),
        "n_declined": int((~answered).sum()),
        "coverage": round(float(answered.mean()), 4),
        "feature_names": list(feature_names),
        "predicted_positive_fraction":
            round(comp["predicted_class"]["positive_fraction"], 4),
        "oracle_positive_fraction":
            (round(comp["oracle_true_class"]["positive_fraction"], 4)
             if "oracle_true_class" in comp else None),
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
<title>CertGate — explanation dashboard (demonstration)</title>
<style>
  :root { --ink:#1a2233; --mut:#5b6572; --line:#d8dee7; --bg:#f6f8fb;
          --card:#ffffff; --pos:#2563eb; --neg:#b45309; --dec:#b91c1c;
          --ans:#15803d; }
  * { box-sizing:border-box; }
  body { margin:0; font:15px/1.5 system-ui,Segoe UI,Roboto,sans-serif;
         color:var(--ink); background:var(--bg); }
  header { padding:18px 24px 6px; }
  h1 { font-size:19px; margin:0 0 2px; }
  .sub { color:var(--mut); font-size:13px; }
  main { max-width:900px; margin:0 auto; padding:12px 24px 40px; }
  .card { background:var(--card); border:1px solid var(--line);
          border-radius:10px; padding:16px 18px; margin:14px 0; }
  .caveat { border-left:4px solid var(--dec); font-size:13.5px; }
  .caveat b { color:var(--dec); }
  .strip { display:flex; gap:18px; flex-wrap:wrap; font-size:13.5px; }
  .strip div b { display:block; font-size:17px; }
  select { font:inherit; padding:6px 8px; border:1px solid var(--line);
           border-radius:8px; max-width:100%; }
  .verdict { display:inline-block; padding:2px 10px; border-radius:999px;
             color:#fff; font-weight:600; font-size:13px; }
  .verdict.declined { background:var(--dec); }
  .verdict.answered { background:var(--ans); }
  table { border-collapse:collapse; width:100%; font-size:13.5px; }
  th,td { text-align:left; padding:5px 8px; border-bottom:1px solid var(--line); }
  th { color:var(--mut); font-weight:600; }
  .barrow { display:flex; align-items:center; gap:8px; margin:3px 0; }
  .barlab { width:110px; font-size:12.5px; color:var(--mut); text-align:right; }
  .barbox { flex:1; display:flex; height:14px; position:relative; }
  .barbox .mid { position:absolute; left:50%; top:-2px; bottom:-2px;
                 width:1px; background:var(--line); }
  .bar { height:14px; border-radius:3px; }
  .bar.pos { background:var(--pos); margin-left:50%; }
  .bar.neg { background:var(--neg); }
  .barval { width:64px; font-size:12px; color:var(--mut); }
  .num { font-variant-numeric:tabular-nums; }
  footer { color:var(--mut); font-size:12.5px; max-width:900px;
           margin:0 auto; padding:0 24px 30px; }
</style>
</head>
<body>
<header>
  <h1>CertGate — why this case was answered or declined</h1>
  <div class="sub" id="subtitle"></div>
</header>
<main>
  <div class="card caveat">
    <b>Read this first.</b> The "what would need to change" statements below are
    <b>score-space</b> descriptions of the gate — <i>what the model's inputs would
    need to be</i> for the case to clear the answering bar. They are <b>not</b>
    causal claims, not treatment suggestions, and not clinically achievable
    actions (features are not independently changeable). A case flipped by the
    minimal change is answered at the <b>weakest possible confidence</b>, a hair
    above the bar itself. The error-rate certificate is a <b>site-population-average</b>
    guarantee over answered cases: no individual record carries a certified
    property of its own. This page shows a <span id="cohortlabel"></span>.
  </div>

  <div class="card">
    <div class="strip" id="cohortstrip"></div>
  </div>

  <div class="card">
    <label for="caseSel"><b>Case</b> (declined cases listed first):</label><br>
    <select id="caseSel"></select>
    <div id="casebox"></div>
  </div>
</main>
<footer>
  Generated by <code>examples/explain_dashboard.py</code>. Attributions are exact
  interventional Shapley values of the linear head; counterfactuals are exact
  closed-form minimal moves (SPEC "explain.py"). Self-contained file, no network
  access.
</footer>
<script>
const DATA = __PAYLOAD__;
const fmt = (v) => (v === null || v === undefined) ? "—" : v;
document.getElementById("subtitle").textContent =
  "Operating threshold τ* = " + DATA.tau_star + " · " + DATA.cohort_label;
document.getElementById("cohortlabel").textContent = DATA.cohort_label;
const strip = document.getElementById("cohortstrip");
const stat = (label, val) => {
  const el = document.createElement("div");
  el.innerHTML = "<b class='num'>" + fmt(val) + "</b>" + label;
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

const sel = document.getElementById("caseSel");
DATA.cases.forEach((c, i) => {
  const o = document.createElement("option");
  o.value = i;
  o.textContent = "case " + c.idx + " — " +
    (c.declined ? "DECLINED (margin " + c.margin_to_answer + ")"
                : "answered (confidence " + c.confidence + ")");
  sel.appendChild(o);
});

function bars(phi, names) {
  const mx = Math.max(...phi.map(Math.abs), 1e-9);
  return phi.map((v, j) => {
    const w = Math.abs(v) / mx * 50;
    const bar = v >= 0
      ? "<div class='bar pos' style='width:" + w + "%'></div>"
      : "<div class='bar neg' style='width:" + w + "%;margin-left:" + (50 - w) + "%'></div>";
    return "<div class='barrow'><div class='barlab'>" + names[j] + "</div>" +
           "<div class='barbox'><div class='mid'></div>" + bar + "</div>" +
           "<div class='barval num'>" + v.toFixed(3) + "</div></div>";
  }).join("");
}

function render(i) {
  const c = DATA.cases[i];
  const box = document.getElementById("casebox");
  let h = "<p><span class='verdict " + (c.declined ? "declined" : "answered") +
    "'>" + (c.declined ? "DECLINED" : "ANSWERED") + "</span> · model leans " +
    "<b>" + c.lean + "</b> · risk score " + c.p1 +
    " · confidence " + c.confidence +
    (c.declined ? " · needs " + c.margin_to_answer +
                  " more logit-confidence to answer" : "") + "</p>";
  h += "<p><b>What drove the confidence</b> (bars right of the line build " +
       "confidence toward the leaned class; bars left erode it — cancellation " +
       "is what causes a decline):</p>";
  h += bars(c.phi_toward, DATA.feature_names);
  if (c.declined && c.counterfactuals.length) {
    h += "<p style='margin-top:14px'><b>Smallest single-input changes that " +
         "would make the gate answer</b>, ranked by standardized magnitude " +
         "(each clears the bar by a hair, so the answer would carry the " +
         "weakest allowed confidence, " + c.confidence_at_flip +
         "):</p><table><tr><th>input</th>" +
         "<th>change needed (raw units)</th><th>(standardized)</th>" +
         "<th>gate would then answer</th></tr>";
    c.counterfactuals.forEach(cf => {
      h += "<tr><td>" + cf.feature + "</td><td class='num'>" +
           (cf.delta_x >= 0 ? "+" : "") + cf.delta_x.toFixed(3) +
           "</td><td class='num'>" +
           (cf.delta_z >= 0 ? "+" : "") + cf.delta_z.toFixed(3) +
           "</td><td>" + cf.answers_as + "</td></tr>";
    });
    h += "</table><p class='sub' style='color:var(--mut);font-size:12.5px'>" +
         "Smallest whole-profile change (standardized L2): " +
         fmt(c.l2_distance_z) + ". These describe the gate, not the patient.</p>";
  }
  box.innerHTML = h;
}
sel.addEventListener("change", () => render(+sel.value));
render(0);
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
