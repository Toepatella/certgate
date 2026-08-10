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

from certgate import reliability as rp
from certgate.explain import cohort_abstention_profile, counterfactual_to_answer
from certgate.constants import SEED
from certgate.data import SimConfig, draw_cohort, split_sites
from certgate.model import fit_head

_MAX_ANSWERED_SHOWN = 60
_MAX_DECLINED_SHOWN = 500
_MISSING_SUFFIXES = ("__missing", " (not recorded)")

# The nine APACHE flags whose MEASUREMENT TIMING could not be verified from the
# source documentation (EICU-PROTOCOL amendment A3, §5.4a). They are settled
# from data by `outcome_screen`, not from DDL comments -- and the glossary says
# so rather than inventing a confident definition.
_TIMING_UNVERIFIED = {
    "activetx", "thrombolytics", "graftcount", "electivesurgery", "ventday1",
    "oobventday1", "oobintubday1", "ima", "midur",
}

# Plain-English meanings. `d` is what a clinician-facing reader sees; `t` adds
# units / normal ranges for the analyst view. Entries are keyed by the RAW stem
# (block prefix and missingness suffix stripped). Anything not listed simply
# shows no tooltip -- an absent gloss is better than a guessed one.
_GLOSSARY = {
    # ---- admission / demographics ----
    "age": ("Age in years at ICU admission.",
            "Ages over 89 arrive as the token '> 89' and are stored as 90.0 "
            "(HIPAA top-coding); see age_masked."),
    "age_masked": ("Marker: this patient's age was recorded as 'over 89' "
                   "rather than an exact number, for privacy.", ""),
    "admissionheight": ("Height measured at admission.", "cm."),
    "admissionweight": ("Weight measured at admission.", "kg."),
    "pre_icu_hours": ("How long the patient was in the hospital before "
                      "arriving in the ICU.",
                      "Hours, derived from hospitaladmitoffset."),
    "gender": ("Sex as recorded in the hospital record.", ""),
    "ethnicity": ("Ethnicity as recorded in the hospital record.", ""),
    "hospitaladmitsource": ("Where the patient came from when admitted to the "
                            "hospital (emergency department, another floor, "
                            "another hospital…).", ""),
    "unitadmitsource": ("Where the patient came from when admitted to this "
                        "ICU.", ""),
    "unittype": ("What kind of ICU this is (medical, surgical, cardiac, "
                 "neurological…).", ""),
    "unitstaytype": ("Whether this ICU stay was a first admission, a "
                     "readmission, or a transfer.", ""),
    # ---- day-1 physiology (APACHE APS) ----
    "intubated": ("A breathing tube was in place.", "0/1 on day 1."),
    "vent": ("The patient was on a mechanical ventilator.", "0/1 on day 1."),
    "dialysis": ("The patient received dialysis (machine support for failing "
                 "kidneys).", "0/1 on day 1."),
    "eyes": ("Coma scale — eye opening. 1 means none, 4 means opens "
             "spontaneously. Lower is worse.",
             "Glasgow Coma Scale eye component, 1–4."),
    "motor": ("Coma scale — best movement response. 1 means none, 6 means "
              "follows commands. Lower is worse.",
              "Glasgow Coma Scale motor component, 1–6."),
    "verbal": ("Coma scale — speech response. 1 means none, 5 means fully "
               "oriented. Lower is worse.",
               "Glasgow Coma Scale verbal component, 1–5."),
    "meds": ("Medication flag recorded alongside the coma-scale assessment "
             "(e.g. sedation that affects the score).", ""),
    "urine": ("How much urine the patient produced on the first day. Very "
              "little can mean the kidneys are struggling.", "mL over 24h."),
    "wbc": ("White blood cell count — the infection-fighting cells. Very high "
            "or very low can signal serious infection.", "×10⁹/L."),
    "temperature": ("Body temperature.", "°C after unit normalisation "
                    "(Fahrenheit values are converted)."),
    "respiratoryrate": ("Breaths per minute.", "breaths/min."),
    "sodium": ("Sodium level in the blood — a basic salt balance measure.",
               "mEq/L."),
    "heartrate": ("Heart beats per minute.", "beats/min."),
    "meanbp": ("Average blood pressure. Low values mean organs may not be "
               "getting enough blood.", "Mean arterial pressure, mmHg."),
    "ph": ("How acidic the blood is. Normal is roughly 7.35–7.45; lower is "
           "usually a sign of serious illness.", "Arterial pH."),
    "hematocrit": ("The share of blood made up of red cells.", "%."),
    "creatinine": ("A waste product the kidneys clear. Higher means the "
                   "kidneys are working less well.", "mg/dL."),
    "albumin": ("A blood protein. Low levels go with poor nutrition or liver "
                "disease.", "g/dL."),
    "pao2": ("How much oxygen is dissolved in the arterial blood.", "mmHg."),
    "pco2": ("How much carbon dioxide is in the arterial blood.", "mmHg."),
    "bun": ("Blood urea nitrogen — another measure of kidney function.",
            "mg/dL."),
    "glucose": ("Blood sugar.", "mg/dL."),
    "bilirubin": ("A pigment the liver clears. High levels suggest the liver "
                  "is struggling.", "mg/dL."),
    "fio2": ("How much oxygen the patient is being given. 0.21 is ordinary "
             "room air; 1.0 is pure oxygen.",
             "Fraction, 0.21–1.0; percent values are normalised."),
    # ---- chronic conditions / treatment (APACHE predictor variables) ----
    "aids": ("Recorded chronic condition: AIDS.", "0/1."),
    "hepaticfailure": ("Recorded chronic condition: liver failure.", "0/1."),
    "lymphoma": ("Recorded chronic condition: lymphoma.", "0/1."),
    "metastaticcancer": ("Recorded chronic condition: cancer that has spread.",
                         "0/1."),
    "leukemia": ("Recorded chronic condition: leukaemia.", "0/1."),
    "immunosuppression": ("Immune system weakened, by disease or by "
                          "treatment.", "0/1."),
    "cirrhosis": ("Recorded chronic condition: cirrhosis of the liver.", "0/1."),
    "diabetes": ("Recorded chronic condition: diabetes.", "0/1."),
    "ejectfx": ("How much blood the heart's main chamber pumps out with each "
                "beat.", "Ejection fraction, %."),
    "readmit": ("This ICU stay was a readmission.", "0/1."),
    "electivesurgery": ("Admitted for planned (not emergency) surgery.", "0/1."),
    "activetx": ("Recorded as receiving active treatment.", "0/1."),
    "thrombolytics": ("Clot-dissolving drugs were given.", "0/1."),
    "graftcount": ("Number of bypass grafts (heart surgery).", "count."),
    "ventday1": ("Recorded as ventilated on day 1.", "0/1."),
    "oobventday1": ("An APACHE ventilation field.", ""),
    "oobintubday1": ("An APACHE intubation field.", ""),
    "ima": ("Internal mammary artery graft used (heart surgery).", "0/1."),
    "midur": ("An APACHE duration field.", ""),
}


def _pretty(name):
    """Display name: drop the block prefix, say 'not recorded' in words."""
    out = _deprefix(name)
    if out.endswith("__missing"):
        out = out[: -len("__missing")] + " (not recorded)"
    return out


def _stem(name):
    for suf in _MISSING_SUFFIXES:
        if name.lower().endswith(suf):
            return name[: -len(suf)].strip()
    return None


def _deprefix(name):
    """Strip the `aps_` / `apv_` block prefix, returning the bare stem.

    NOT ``str.lstrip("aps_apv_")``: that takes a character SET, so it eats any
    leading run of {a, p, s, v, _} and turns "vent" into "ent" and "aps_ph"
    into "h". The bug was inert here — mangled stems simply failed the
    `demo` membership test and fell through to the same group they belong in —
    but it reads as correct and is not.
    """
    for pre in ("aps_", "apv_"):
        if name.startswith(pre):
            return name[len(pre):]
    return name


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
        elif _deprefix(nm.lower()) in demo:
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
                    certificate=None, site_ids=None, include_outcomes=False,
                    provenance=None):
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

    ``provenance`` answers the first question a reader asks — *why are there
    only N cases when the dataset has far more?* — by stating where this pool
    sits in the site-level split, e.g. ``dict(pool="24 held-out hospitals",
    cohort_total=164322, cohort_sites=207,
    splits="73 train / 36 aux / 74 calibration", replicate=0)``. Omitted, the
    page says nothing rather than guessing.

    Display caps are disclosed on the page, never silent. Returns ``out_path``.
    """
    x = np.asarray(x, dtype=np.float64)
    n, d = x.shape
    if feature_names is None:
        feature_names = [f"feature {j}" for j in range(d)]
    feature_names = list(feature_names)
    display = [_pretty(nm) for nm in feature_names]
    groups, onehot, flag_of = _classify(feature_names)

    def _gloss(raw):
        """(plain meaning, technical note) for one feature, or None."""
        base = _deprefix(raw)
        is_flag = _stem(base) is not None
        if is_flag:
            base = _stem(base)
        if "=" in base:
            base = base.split("=", 1)[0]
        e = _GLOSSARY.get(base.strip().lower())
        if e is None:
            return None
        plain, tech = e
        if is_flag:
            plain = ("Marker: this value was never recorded for this patient. "
                     "The number shown beside it is a stand-in the model fills "
                     "in — not a measurement. (" + plain + ")")
            tech = ("Missingness indicator; parent imputed from the training "
                    "split. " + tech).strip()
        if base.strip().lower() in _TIMING_UNVERIFIED:
            tech = (tech + " MEASUREMENT TIMING NOT VERIFIED from the source "
                    "documentation (protocol A3): settled from data by "
                    "outcome_screen, not from a DDL comment.").strip()
        return [plain, tech]

    glossary = {}
    for j, raw in enumerate(feature_names):
        g = _gloss(raw)
        if g is not None:
            glossary[str(j)] = g
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
        # IMPORTED, not restated: this page and certgate/reliability.py's panel
        # are two instruments reading the same probabilities, and they must bin
        # them identically. A literal here made that a claim a test had to
        # verify by PARSING this file's source; importing the tuple makes it
        # true by construction. The 1.01 top edge is a SENTINEL, never a bound
        # -- it is what lets p == 1.0 land in the last bin under the strict `<`
        # test below, and `min(hi, 1.0)` clamps it back for display.
        edges = rp.DEFAULT_BIN_EDGES
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
        "provenance": provenance,
        "certificate": certificate,
        "n_total": int(n),
        "n_answered": int(answered.sum()),
        "n_declined": int((~answered).sum()),
        "coverage": round(float(answered.mean()), 4),
        "feature_names": display,
        "raw_names": feature_names,
        "groups": groups,
        "glossary": glossary,
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
  /* ================= tokens — the bench-instrument world ================= */
  :root {
    --bg:#e8ebec;            /* bench ground */
    --panel:#f2f4f4;         /* second neutral: rails, table heads, readouts */
    --card:#fcfcfb;          /* instrument plate */
    --ink:#1c2325;
    --mut:#556063;
    --line:#d3d8d8;          /* hairline */
    --rule:#9aa3a3;          /* graduation rule */
    --pos:#2757a8;           /* cobalt: interactive accent + positive deflection */
    --neg:#9a5410;           /* burnt orange: negative deflection */
    --ans:#15673c;           /* in-spec green: answered */
    --dec:#b3261e;           /* out-of-spec red: declined */
    --redline:#c62f21;       /* the red-line at tau*; text on plate 5.34:1 (AA >=4.5) */
    --band:#e0efe6;          /* green answering band on scales */
    --chip:#eceff0;
    --hl:#e7eef9;            /* selection tint (cobalt) */
    --histbar:#66808e;       /* answered mass: plate 4.06:1, band 3.50:1 (>=3:1) */
    --histdec:#c66b5b;       /* declined mass: plate 3.62:1, band 3.12:1 (>=3:1) */
    --fence:#f8f5ea;         /* bench-mat: the no-guarantee test area */
    --fenceline:#c9b98a;
    --amber:#f6ecce; --ambert:#6f4d05; --amberline:#e0d1a2;
    --certbg:#f3faf6; --certline:#b9d6c5; --certink:#124f30;
    --uncbg:#fbebe8; --uncline:#d8918a; --uncink:#a1201a;
    --died-bg:#f7dcd9; --died-fg:#8f1d16;
    --surv-bg:#ddefe4; --surv-fg:#125234;
  }
  body.dark {
    --bg:#14181a; --panel:#181e20; --card:#1c2225;
    --ink:#e6eae8; --mut:#9fa9a6; --line:#313a3d; --rule:#5b6668;
    --pos:#7ba4e8; --neg:#d99a56; --ans:#54b47c; --dec:#e2685c;
    --redline:#e66055; --band:#1d3527; /* red-line text on plate 4.73:1 (AA >=4.5) */
    --chip:#242b2e; --hl:#223550;
    --histbar:#6a8290; --histdec:#b76552; /* plate 3.99/3.83, band 3.27/3.14 (>=3:1) */
    --fence:#242015; --fenceline:#5a4c22;
    --amber:#3a2f12; --ambert:#ecc86a; --amberline:#57451c;
    --certbg:#17251c; --certline:#2c4636; --certink:#7fc79c;
    --uncbg:#2e1a17; --uncline:#6b2f28; --uncink:#f1948a;
    --died-bg:#4a1d1d; --died-fg:#f3a9a2; --surv-bg:#14351f; --surv-fg:#8fd8ac;
  }

  /* ================= base ================= */
  * { box-sizing:border-box; }
  body { margin:0; color:var(--ink); background:var(--bg);
         font:16px/1.55 system-ui,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif; }
  body.adv { font-size:14px; }
  body.simple { font-size:16.5px; }
  h1 { font-size:21px; font-weight:650; letter-spacing:-0.01em; margin:0;
       display:flex; align-items:center; gap:10px; }
  h1 .mark { color:var(--ink); flex:0 0 auto; }
  body.adv h1 { font-size:19px; }
  /* section labels: engraved caps with a trailing graduation rule */
  h2 { display:flex; align-items:baseline; gap:10px; flex-wrap:wrap; margin:0 0 10px;
       font-size:12.5px; font-weight:650; text-transform:uppercase;
       letter-spacing:.07em; color:var(--ink); }
  h2::after { content:""; flex:1 1 40px; border-top:1px solid var(--line);
              align-self:center; min-width:24px; }
  h2 .note { text-transform:none; letter-spacing:0; font-weight:400; }
  .sub { color:var(--mut); font-size:13.5px; max-width:74ch; }
  .note { color:var(--mut); font-size:12.5px; }
  details > summary::before { content:""; width:0; height:0; flex:0 0 auto;
        border-left:6px solid var(--mut); border-top:4.5px solid transparent;
        border-bottom:4.5px solid transparent; transition:transform 160ms; }
  details[open] > summary::before { transform:rotate(90deg); }
  details > summary { list-style:none; }
  details > summary::-webkit-details-marker { display:none; }
  .num { font-variant-numeric:tabular-nums; }
  main { max-width:1240px; margin:0 auto; padding:8px 24px 36px; }
  body.simple main { max-width:960px; }

  /* ================= masthead: the nameplate ================= */
  header { max-width:1240px; margin:0 auto; padding:20px 24px 0; }
  body.simple header { max-width:960px; }
  .mast { display:flex; gap:18px; align-items:flex-start; justify-content:space-between;
          flex-wrap:wrap; border-bottom:2px solid var(--ink); padding-bottom:14px; }
  .mastid { flex:1 1 380px; display:flex; flex-direction:column; gap:4px; }
  .modebar { display:flex; gap:8px; flex-wrap:wrap; align-items:center; }

  /* ================= plates ================= */
  .card { background:var(--card); border:1px solid var(--line); border-radius:6px;
          padding:18px 22px; margin:14px 0; }
  body.simple .card { padding:20px 24px; margin:16px 0; }

  /* ================= controls ================= */
  .seg { display:inline-flex; border:1px solid var(--line); border-radius:6px;
         overflow:hidden; background:var(--card); }
  .seg .chip { border:0; border-radius:0; margin:0; }
  .seg .chip + .chip { border-left:1px solid var(--line); }
  .chip { display:inline-flex; align-items:center; gap:7px; min-height:44px;
          padding:0 14px; border-radius:6px; background:var(--card);
          border:1px solid var(--line); color:var(--ink); cursor:pointer;
          font-size:12.5px; user-select:none; }
  .chip svg { flex:0 0 auto; }
  .chip:hover { background:var(--hl); }
  .chip.on { background:var(--hl); color:var(--pos); font-weight:650;
             border-color:var(--pos); }
  .seg .chip.on { border-color:transparent; box-shadow:inset 0 0 0 1.5px var(--pos); }
  .side .chip { margin:0 6px 8px 0; }
  .side label.note { display:block; margin:10px 0 4px; }
  .side select, .side input[type=text] { margin-bottom:8px; }
  button { font:inherit; font-size:12.5px; min-height:44px; padding:8px 14px;
           margin:0 8px 8px 0; border:1px solid var(--line); border-radius:6px;
           background:var(--card); color:var(--ink); cursor:pointer; }
  button:hover { background:var(--hl); }
  button.primary { border-color:var(--pos); color:var(--pos); font-weight:650; }
  button.attn { border-color:var(--dec); color:var(--dec); font-weight:650; }
  input[type=text], select { font:inherit; font-size:13.5px; min-height:44px;
          padding:6px 10px; color:var(--ink); background:var(--card);
          border:1px solid var(--line); border-radius:6px; width:100%; }
  input[type=range] { width:100%; height:44px; accent-color:var(--pos); margin:0; }
  /* every slider runs on the world's graduated rail, with a notch at the
     recorded value (the fence's notch marks the deployed bar instead) */
  .sldw { position:relative; display:block; width:100%; }
  .sldw input[type=range] { position:relative; z-index:1; display:block; }
  .sldw .srail { position:absolute; left:0; right:0; bottom:5px; height:7px;
        pointer-events:none; background:repeating-linear-gradient(90deg,
        var(--rule), var(--rule) 1px, transparent 1px, transparent 12.5%); }
  .sldw .smark { position:absolute; bottom:3px; width:2px; height:11px;
        pointer-events:none; background:var(--ink); opacity:.5; }
  .sldw .smark.bar { background:var(--redline); opacity:1; }
  input[type=checkbox] { width:22px; height:22px; accent-color:var(--pos); }
  summary { min-height:44px; display:flex; align-items:center; gap:8px;
            cursor:pointer; flex-wrap:wrap; }
  :where(a,button,select,input,summary,[role="button"]):focus-visible {
    outline:2.5px solid var(--pos); outline-offset:2px; border-radius:6px; }
  .sr-only { position:absolute; width:1px; height:1px; padding:0; margin:-1px;
             overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap; border:0; }

  /* ================= pills, tags ================= */
  .verdict { display:inline-block; padding:3px 12px; border-radius:999px;
             color:#fff; font-weight:650; font-size:13px; letter-spacing:.02em; }
  .verdict.declined { background:var(--dec); }
  .verdict.answered { background:var(--ans); }
  .badge { display:inline-block; padding:2px 9px; border-radius:999px;
           background:var(--amber); color:var(--ambert); font-size:12px;
           font-weight:600; margin-left:8px; }
  .tag { display:inline-block; padding:1px 8px; border-radius:999px;
         font-size:12px; background:var(--chip); color:var(--mut); }
  .tag.rec { background:var(--amber); color:var(--ambert); }
  .tag.cat { background:var(--hl); color:var(--pos); }
  .outc { display:inline-block; padding:1px 8px; border-radius:999px;
          font-size:12px; font-weight:600; }
  .outc.d { background:var(--died-bg); color:var(--died-fg); }
  .outc.s { background:var(--surv-bg); color:var(--surv-fg); }

  /* ================= notice plates ================= */
  /* standing caveat: a formal NOTE plate, quiet but unskippable */
  .caveat { font-size:13.5px; }
  body.simple .caveat { font-size:15px; }
  .caveat b:first-child { display:inline-block; text-transform:uppercase;
        letter-spacing:.06em; font-size:12.5px; margin-right:4px; }
  /* calibration plate (certified) and the out-of-cal tag (uncertified) */
  .certb { display:flex; gap:12px; align-items:flex-start; border-radius:6px;
           padding:12px 16px; margin:14px 0 0; font-size:13.5px; border:1px solid; }
  .certb .seal { flex:0 0 auto; margin-top:2px; }
  .certb.cert { border-color:var(--certline); background:var(--certbg); }
  .certb.cert b { color:var(--certink); }
  .certb.cert .seal { color:var(--certink); }
  .certb.uncert { border:1.5px solid var(--uncline); background:var(--uncbg);
                  color:var(--uncink); font-weight:650; font-size:14px; }
  .certb.uncert .seal { color:var(--uncink); }
  .certb .cl2 { font-weight:400; color:var(--mut); font-size:12.5px; display:block;
                margin-top:3px; }
  .certb .num { font-variant-numeric:tabular-nums; }
  /* threshold explorer: the bench mat — dashed = outside the certified path */
  .fence { border:1.5px dashed var(--fenceline); border-radius:6px;
           padding:14px 18px; margin:14px 0; background:var(--fence); }
  .fence b.t { color:var(--ambert); }

  /* ================= test summary (cohort strip) ================= */
  .strip { display:flex; flex-wrap:wrap; }
  .strip > div { padding:2px 18px 2px 0; margin:4px 18px 4px 0;
                 border-right:1px solid var(--line); }
  .strip > div:last-child { border-right:0; }
  .strip .sl { display:block; font-size:12px; text-transform:uppercase;
               letter-spacing:.05em; color:var(--mut); margin-bottom:1px; }
  .strip b { font-size:17px; font-weight:650; }

  /* ================= the meter (confidence gauge) ================= */
  .meter { position:relative; height:34px; margin:34px 0 24px;
           border-bottom:1.5px solid var(--rule); }
  .meter .mband { position:absolute; top:0; bottom:0; right:0; background:var(--band); }
  .meter i { position:absolute; bottom:0; width:1px; height:8px;
             background:var(--rule); transform:translateX(-.5px); }
  .meter i.tM { height:15px; width:1.5px; }
  .meter b { position:absolute; top:calc(100% + 5px); transform:translateX(-50%);
             font-size:12px; font-weight:500; color:var(--mut);
             font-variant-numeric:tabular-nums; }
  .meter .mline { position:absolute; top:-7px; bottom:-3px; width:2px;
                  background:var(--redline); }
  .meter .mline span { position:absolute; top:-17px; left:50%;
        transform:translateX(-50%); font-size:12px; font-weight:650;
        color:var(--redline); white-space:nowrap; }
  .meter .needle { position:absolute; top:-2px; bottom:5px; width:2px;
                   background:var(--ink); transition:left 240ms cubic-bezier(.22,.68,.36,1.04); }
  .meter .needle::after { content:""; position:absolute; top:-6px; left:-3.5px;
        border:4.5px solid transparent; border-top-color:var(--ink); }
  .gaxis { display:flex; justify-content:space-between; font-size:12.5px;
           color:var(--mut); gap:8px; flex-wrap:wrap; }
  .gaxis:only-child, .meter + .gaxis { justify-content:center; }

  /* ================= histogram: the distribution instrument ================= */
  .hist { display:flex; align-items:flex-end; height:96px; gap:1px;
          position:relative; margin-top:34px; border-bottom:1.5px solid var(--rule);
          padding-bottom:1px; }
  .hist .hband { position:absolute; top:0; bottom:0; right:0; background:var(--band); }
  .hist .hb { flex:1; position:relative; background:var(--histbar);
              border-radius:1px 1px 0 0; min-height:1px; }
  .hist .hb.dec { background:var(--histdec); }
  body.adv .hist .hb { cursor:pointer; }
  body.adv .hist .hb:hover { outline:1.5px solid var(--pos); }
  .hist .hb.hsel { outline:2px solid var(--pos); }
  .hist .tau { position:absolute; top:-6px; bottom:-2px; width:2px;
               background:var(--redline); }
  .hist .tau span { position:absolute; top:-16px; left:50%; transform:translateX(-50%);
        font-size:12px; font-weight:650; color:var(--redline); white-space:nowrap; }
  .haxis { display:flex; justify-content:space-between; font-size:12px;
           color:var(--mut); font-variant-numeric:tabular-nums; margin-top:4px; }

  /* ================= attribution bars, profile, legend ================= */
  .barrow { display:flex; align-items:center; gap:8px; margin:2px 0; }
  .barlab { width:150px; font-size:12.5px; color:var(--mut); text-align:right;
            overflow:hidden; white-space:nowrap; }
  .barbox { flex:1; display:flex; height:13px; position:relative; }
  .barbox .mid { position:absolute; left:50%; top:-2px; bottom:-2px; width:1px;
                 background:var(--rule); }
  .bar { height:13px; border-radius:2px; }
  .bar.pos { background:var(--pos); margin-left:50%; }
  .bar.neg { background:var(--neg); }
  .barval { width:66px; font-size:12px; color:var(--mut);
            font-variant-numeric:tabular-nums; }
  .profrow { display:flex; align-items:center; gap:8px; margin:2px 0; }
  .profrow .plab { width:150px; font-size:12.5px; color:var(--mut); text-align:right;
                   overflow:hidden; white-space:nowrap; }
  .profrow .pbox { flex:1; height:12px; display:flex; gap:2px; }
  .profrow .pa { background:var(--ans); height:12px; border-radius:2px; }
  .profrow .pd { background:var(--dec); height:12px; border-radius:2px; }
  .profrow .pval { width:150px; font-size:12px; color:var(--mut);
                   font-variant-numeric:tabular-nums; }
  .legend { display:flex; gap:14px; flex-wrap:wrap; margin-top:8px;
            font-size:12.5px; color:var(--mut); align-items:center; }
  .legend i { width:12px; height:12px; border-radius:2px; display:inline-block;
              margin-right:5px; vertical-align:-1px; }
  .legend i.swl { width:3px; height:13px; background:var(--redline); border-radius:0; }
  .grphead { margin:12px 0 2px; font-size:12px; font-weight:650;
             text-transform:uppercase; letter-spacing:.06em; color:var(--mut); }

  /* ================= layout: rail + bench ================= */
  .cols { display:flex; gap:14px; align-items:flex-start; flex-wrap:wrap; }
  .side { flex:0 0 292px; max-width:100%; }
  .detail { flex:1 1 520px; min-width:320px; }
  .cl { margin-top:10px; max-height:430px; overflow-y:auto;
        border:1px solid var(--line); border-radius:6px; background:var(--card); }
  .cl div { min-height:44px; display:flex; align-items:center; gap:8px;
            padding:5px 10px; cursor:pointer; font-size:12.5px;
            border-bottom:1px solid var(--line); }
  .cl div:last-child { border-bottom:none; }
  .cl div:hover { background:var(--hl); }
  .cl div.sel { background:var(--hl); font-weight:650; }
  .cl .m { color:var(--mut); font-weight:400; }
  .cl .dt { flex:0 0 auto; width:7px; height:7px; border-radius:50%; }
  .cl .dt.a { background:var(--ans); }
  .cl .dt.d { background:var(--dec); }

  /* ================= what-if rows ================= */
  .srow { display:grid; grid-template-columns:150px 1fr 82px 44px; gap:8px;
          align-items:center; margin:2px 0; }
  .srow label { font-size:12.5px; color:var(--mut); text-align:right;
                white-space:nowrap; overflow:hidden; cursor:pointer; }
  .srow label:hover { color:var(--pos); }
  .srow label.notrec { opacity:.62; font-style:italic; }
  .srow .v { font-size:12.5px; font-variant-numeric:tabular-nums; }
  .srow .v.imp { color:var(--ambert); }
  .xrow { grid-template-columns:150px 1fr 280px; }
  .rst { color:var(--dec); cursor:pointer; min-width:44px; min-height:44px;
         display:inline-flex; align-items:center; justify-content:center;
         user-select:none; visibility:hidden; border-radius:6px; }
  .rst:hover { background:var(--hl); }
  .rst.on { visibility:visible; }

  /* ================= tables ================= */
  table { border-collapse:collapse; width:100%; font-size:13.5px; }
  th,td { text-align:left; padding:5px 9px; border-bottom:1px solid var(--line); }
  th { color:var(--mut); font-weight:650; font-size:12px; text-transform:uppercase;
       letter-spacing:.05em; border-bottom:1.5px solid var(--rule); }
  td { font-variant-numeric:tabular-nums; }
  tbody tr:hover, table tr:hover td { background:var(--panel); }
  .tblwrap { overflow-x:auto; -webkit-overflow-scrolling:touch; }

  /* ================= tabs, statusbar, svg ================= */
  .tabs { display:flex; gap:2px; border-bottom:1.5px solid var(--rule);
          margin:14px 0 12px; flex-wrap:wrap; }
  .tabbtn { min-height:44px; display:inline-flex; align-items:center;
            padding:5px 13px; font-size:12.5px; cursor:pointer;
            border:1px solid transparent; border-bottom:none;
            border-radius:6px 6px 0 0; color:var(--mut); user-select:none; }
  .tabbtn:hover { color:var(--pos); }
  .tabbtn.on { background:var(--card); border-color:var(--rule); color:var(--pos);
               font-weight:650; position:relative; top:1.5px;
               border-bottom:1.5px solid var(--card); }
  .tabpane { display:none; }
  .tabpane.on { display:block; }
  body.simple #tab-decision { display:block !important; }
  .statusbar { display:flex; gap:16px; flex-wrap:wrap; margin-top:14px;
               padding:8px 12px; border:1px solid var(--line); border-radius:6px;
               background:var(--panel); font-size:12px; color:var(--mut);
               font-variant-numeric:tabular-nums; }
  .statusbar b { color:var(--ink); font-weight:650; }
  svg text { fill:var(--mut); font:12px system-ui,"Segoe UI",Roboto,sans-serif;
             font-variant-numeric:tabular-nums; }
  svg .axis { stroke:var(--rule); stroke-width:1; }
  svg .curve { stroke:var(--pos); stroke-width:2; fill:none; }
  svg .tauline { stroke:var(--redline); stroke-width:1.2; stroke-dasharray:5 3; }
  svg .cross { fill:var(--redline); }
  svg .nowpt { fill:var(--pos); }

  /* ================= overlay ================= */
  .helpov { position:fixed; inset:0; background:rgba(10,14,16,.55); display:none; z-index:50; }
  .helpov.on { display:flex; align-items:center; justify-content:center; }
  .helpov .card { max-width:480px; }
  kbd { font:12px system-ui,"Segoe UI",Roboto,sans-serif; padding:1px 6px;
        border:1px solid var(--rule); border-bottom-width:2px; border-radius:4px;
        background:var(--panel); }

  /* ================= footer ================= */
  footer { max-width:1240px; margin:0 auto; padding:16px 24px 44px;
           color:var(--mut); font-size:12.5px; }
  body.simple footer { max-width:960px; }
  footer code { font-size:12px; }

  /* TWO AUDIENCES, ONE FILE: each register is written twice and the body class
     picks one. Losing these two rules renders BOTH at once and the modes look
     identical -- exactly the regression this comment exists to prevent. */
  body.simple .advonly { display:none !important; }
  body.adv .simponly { display:none !important; }
  /* the modes should not merely read differently, they should FEEL different */
  body.simple .srow { grid-template-columns:190px 1fr 92px 44px; }
  body.simple .barlab, body.simple .srow label { font-size:13.5px; }
  body.simple .note, body.simple .cl div, body.simple button,
  body.simple .chip { font-size:13.5px; }
  body.adv .strip b { font-size:16px; }

  /* ================= responsive: structural, not fluid ================= */
  @media (max-width: 720px) {
    header, main, footer { padding-left:14px; padding-right:14px; }
    .mast { border-bottom-width:1.5px; }
    .side { flex:1 1 100%; }
    .srow, body.simple .srow, .xrow { grid-template-columns:1fr auto; gap:6px 10px; }
    .xrow .v { grid-column:1 / -1; }
    .srow .sldw { grid-column:1 / 2; }
    .srow label { text-align:left; grid-column:1 / -1; white-space:normal; }
    .srow input[type=range] { grid-column:1 / 2; }
    .srow .v { grid-column:2 / 3; }
    .srow .rst { grid-column:2 / 3; justify-self:end; }
    .barlab, .profrow .plab { width:104px; }
    .profrow .pval { width:auto; }
    .strip > div { border-right:0; padding-right:0; margin-right:16px; }
    .card { padding:14px 16px; }
  }

  /* ================= print: the attachable report ================= */
  @media print {
    .side,.fence,.modebar,.hist,.haxis,.gaxis,footer,.tabs,.statusbar,
    #cohortstrip,.helpov,button,.sub,#profpanel,#legendcard,.rst
      { display:none !important; }
    .card { border-color:#bbb; page-break-inside:avoid; }
    .mast { border-color:#000; }
    body { background:#fff; }
  }

  /* ================= motion: honour the OS ================= */
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { transition:none !important; animation:none !important;
                             scroll-behavior:auto !important; }
  }
</style>
</head>
<body class="simple">
<!--
THESIS: a certified selective classifier explained as the measuring instrument
it is — every number shown on a graduated scale with its red-line, its band,
and its caveat; refuses the analytics-dashboard arrangement of KPI tiles,
card grids and decorative charts.
OWN-WORLD: bench-instrument grammar. Cool bench-gray ground, ivory-white
plates ruled by hairlines, engraved-caps section labels, tabular numerals;
graduated tick scales with a green answering band and a red-line at tau*;
cobalt for interaction and positive deflection, burnt orange for negative,
green/red strictly for answered/declined, amber for imputation caveats.
Recognizable with all content removed: ticks, red-line, plates.
STORY: a reader sees the instrument's calibration plate, its operating point
on a scale, picks a case, watches the needle, and learns exactly what the
certificate does and does not promise.
FIRST VIEWPORT: nameplate masthead with register switches; calibration plate;
formal NOTE plate; the cohort test-summary row over the ticked score
distribution with the red-line — one glance: what this is, its operating
point, what is at stake.
FORM: bench instrument + calibration paperwork; candidate 7 of 7 on the
grounded list; seed key ef24fd77 (assigned index 7, mode operate).
FINISH: unreviewed and undocumented is unfinished; this build ends with the
finish review, the verdict, and DESIGN.md.
-->
<header>
  <div class="mast">
    <div class="mastid">
      <h1><svg class="mark" viewBox="0 0 24 24" width="22" height="22" fill="none"
        stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true">
        <path d="M3.5 19a9.5 9.5 0 0 1 17 0"/><path d="M12 19 16.5 9.5"/>
        <circle cx="12" cy="19" r="1.4" fill="currentColor" stroke="none"/></svg>
        CertGate Explain</h1>
      <div class="sub">
        <span class="simponly">A safety gate sits in front of this computer model:
          it answers only when confident enough, and hands everything else to a
          person. Pick a case to see why it decided the way it did &mdash; and try
          changing the inputs yourself.</span>
        <span class="advonly" id="subtitleAdv"></span>
      </div>
    </div>
    <div class="modebar">
      <span class="seg" role="group" aria-label="reading register">
        <span class="chip on" id="modeSimple" role="button" tabindex="0"
          aria-pressed="true" title="everyday language, no jargon">Plain language</span>
        <span class="chip" id="modeAdv" role="button" tabindex="0"
          aria-pressed="false" title="analyst workbench">Advanced</span>
      </span>
      <span class="chip" id="outcT" role="button" tabindex="0" aria-pressed="false"
        title="reveal what actually happened (retrospective)">Outcomes</span>
      <span class="chip" id="darkT" role="button" tabindex="0" aria-pressed="false"
        aria-label="Toggle dark mode" title="dark mode"><svg viewBox="0 0 16 16"
        width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.5"
        stroke-linejoin="round" aria-hidden="true">
        <path d="M13.2 9.8A5.6 5.6 0 1 1 6.2 2.8a4.6 4.6 0 0 0 7 7z"/></svg></span>
      <span class="chip" id="printT" role="button" tabindex="0"
        title="print the selected case"><svg viewBox="0 0 16 16" width="15"
        height="15" fill="none" stroke="currentColor" stroke-width="1.5"
        stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M4 6V2.5h8V6"/><rect x="2.5" y="6" width="11" height="5.5" rx="1"/>
        <path d="M4.5 9.5h7V14h-7z"/></svg>Print</span>
    </div>
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

  <div class="card">
    <h2><span class="simponly">All cases at a glance</span><span class="advonly">Operating point</span></h2>
    <div class="strip" id="cohortstrip"></div>
    <div id="provbox"></div>
    <div class="hist" id="hist"></div>
    <div class="haxis"><span>0.50</span><span>0.60</span><span>0.70</span><span>0.80</span><span>0.90</span><span>1.00</span></div>
    <div class="note" style="margin-top:6px">
      <span class="simponly">Every case, grouped by how sure the program was.
        The scale runs from totally unsure (50/50) on the left to completely
        certain on the right. Red bars: not sure enough, handed to a person.</span>
      <span class="advonly">Confidence-score distribution over all
        <span id="ntot"></span> cases; red bins sit below &#964;* =
        <span id="taulab"></span>. Click a bin to filter the case list.</span></div>
    <div class="legend"><span><i style="background:var(--histbar)"></i>answered
      (at or above the bar)</span><span><i style="background:var(--histdec)"></i>handed
      to a person (below the bar)</span><span><i class="swl"></i><span
      class="simponly">red line = the bar it must clear</span><span
      class="advonly">red line = &#964;*</span></span></div>
    <div class="advonly" id="profpanel" style="margin-top:14px"></div>
  </div>

  <details class="card" id="legendcard" style="margin-top:14px">
    <summary><b>What do these measurements mean?</b> <span class="note">plain-language
      legend for every input the model uses</span></summary>
    <div style="margin-top:8px">
      <label for="glossQ" class="note">Search the legend</label>
      <input type="text" id="glossQ" placeholder="e.g. creatinine" style="max-width:320px">
    </div>
    <div id="glossbox" style="margin-top:8px"></div>
  </details>

  <details class="simponly card" style="margin-top:14px">
    <summary>How to read this page (30 seconds)</summary>
    <ol class="note">
      <li><b>Pick a case</b> on the left. Green = the program answered; red =
        it wasn't sure enough and handed the case to a person.</li>
      <li><b>The meter</b> shows how sure it was. It must clear the red line.</li>
      <li><b>The bars</b> show what pushed confidence up or down. When pushes
        and pulls cancel out, it hands the case over.</li>
      <li><b>Try the controls</b> &mdash; change a value and watch it re-decide.
        The red button puts everything back.</li>
      <li>Values marked <i>not recorded</i> were never measured for this
        patient; the number beside them is a stand-in the model fills in.</li>
    </ol>
  </details>

  <div class="cols">
    <div class="side card">
      <h2>Cases</h2>
      <span class="chip" data-f="all" role="button" tabindex="0" aria-pressed="false">all</span>
      <span class="chip on" data-f="declined" role="button" tabindex="0" aria-pressed="true"><span class="simponly">handed over</span><span class="advonly">declined</span></span>
      <span class="chip" data-f="answered" role="button" tabindex="0" aria-pressed="false">answered</span>
      <span class="chip" id="binclear" role="button" tabindex="0" style="display:none">score filter &#10005;</span>
      <label for="search" class="note">Find a case by number</label>
      <input type="text" id="search" placeholder="e.g. 11354">
      <div id="sitewrap" style="margin-bottom:4px"></div>
      <select id="sortSel" aria-label="sort cases">
        <option value="margin_asc">most borderline first</option>
        <option value="margin_desc">least borderline first</option>
        <option value="idx">by case number</option>
      </select>
      <div style="margin-top:8px">
        <button id="jmpContested">most contested</button>
        <button id="jmpRandom">random</button>
      </div>
      <div class="cl" id="caselist"></div>
      <div class="note" id="capnote" style="margin-top:8px"></div>
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
    <div class="srow xrow">
      <label><span class="simponly">try a bar</span><span class="advonly">explore &#964;</span></label>
      <span class="sldw"><input type="range" id="tauX" min="0.55" max="0.99"
        step="0.01" aria-label="explore threshold"><i class="srail"></i><i
        class="smark bar" id="tauXmark"></i></span>
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

// one icon grammar: 1.5px stroke, currentColor, drawn inline
const IC_RESET = "<svg viewBox='0 0 16 16' width='14' height='14' fill='none' " +
  "stroke='currentColor' stroke-width='1.6' stroke-linecap='round' " +
  "stroke-linejoin='round' aria-hidden='true'><path d='M3.2 8a5 5 0 1 0 1.4-3.5'/>" +
  "<path d='M3.2 2.6v2.6h2.6'/></svg>";

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
const GLOSS = DATA.glossary || {};
function tip(j) {                       // hover text for any feature label
  const g = GLOSS[String(j)];
  if (!g) return NAMES[j];
  const adv = document.body.classList.contains("adv");
  return NAMES[j] + " — " + g[0] + (adv && g[1] ? "  [" + g[1] + "]" : "");
}
function renderLegend() {
  // A build with no glossary at all (e.g. the synthetic demo's unnamed
  // features) has no legend to search: hide the card rather than render
  // an empty search that reports 'Nothing matches ""'.
  const lc = document.getElementById("legendcard");
  if (lc && !Object.keys(GLOSS).length) { lc.style.display = "none"; return; }
  const q = (document.getElementById("glossQ") || {}).value || "";
  const ql = q.trim().toLowerCase();
  const seen = new Set(), rows = [];
  NAMES.forEach((nm, j) => {
    const g = GLOSS[String(j)];
    if (!g) return;
    const key = nm.replace(/=.*$/, "").replace(/ \(not recorded\)$/, "");
    if (seen.has(key)) return;          // one row per concept, not per level
    if (ql && !(key.toLowerCase().includes(ql) || g[0].toLowerCase().includes(ql)))
      return;
    seen.add(key);
    rows.push("<tr><td style='white-space:nowrap'><b>" + key + "</b></td><td>" +
      g[0] + (g[1] ? "<span class='advonly note'> " + g[1] + "</span>" : "") +
      "</td></tr>");
  });
  const box = document.getElementById("glossbox");
  if (!box) return;
  box.innerHTML = rows.length
    ? "<div class='tblwrap'><table>" + rows.join("") + "</table></div><p class='note'>" +
      dual("These describe what each measurement is, not what any value means " +
           "for a particular patient.",
           "Definitions are for orientation; units and normal ranges are " +
           "indicative. Fields whose measurement timing could not be verified " +
           "from source documentation are marked and are settled from data by " +
           "outcome_screen (protocol A3).") + "</p>"
    : "<p class='note'>Nothing matches “" + q + "”.</p>";
}
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
  press(document.getElementById("modeSimple"), m === "simple");
  press(document.getElementById("modeAdv"), m === "adv");
  renderLegend();
  if (m === "adv") redrawAdvanced();
}
// Enter/Space activate any role=button span, so nothing is mouse-only.
document.addEventListener("keydown", e => {
  const t = e.target;
  if ((e.key === "Enter" || e.key === " ") && t && t.getAttribute &&
      t.getAttribute("role") === "button") { e.preventDefault(); t.click(); } });
function press(el, on) { if (el) el.setAttribute("aria-pressed", on ? "true" : "false"); }
document.getElementById("modeSimple").onclick = () => setMode("simple");
document.getElementById("modeAdv").onclick = () => setMode("adv");
document.getElementById("darkT").onclick = e => {
  const el = document.getElementById("darkT");
  document.body.classList.toggle("dark"); el.classList.toggle("on");
  press(el, document.body.classList.contains("dark")); };
document.getElementById("printT").onclick = () => window.print();
let showOutcomes = false;
const outcChip = document.getElementById("outcT");
if (!DATA.include_outcomes) { outcChip.style.opacity = .4;
  outcChip.title = "per-case outcomes were not included in this build"; }
outcChip.onclick = () => {
  if (!DATA.include_outcomes) return;
  showOutcomes = !showOutcomes;
  outcChip.classList.toggle("on", showOutcomes); press(outcChip, showOutcomes);
  rebuildList(order[cur]); };

// ---- certification banner: the calibration plate / the out-of-cal tag ----
(function(){
  const el = document.getElementById("certbanner"), C = DATA.certificate;
  const warn = "<svg class='seal' viewBox='0 0 20 20' width='18' height='18' " +
    "fill='none' stroke='currentColor' stroke-width='1.6' stroke-linecap='round' " +
    "stroke-linejoin='round' aria-hidden='true'><path d='M10 3 2.5 16h15z'/>" +
    "<path d='M10 8v3.4'/><circle cx='10' cy='13.6' r='.5' fill='currentColor'/></svg>";
  const seal = "<svg class='seal' viewBox='0 0 20 20' width='18' height='18' " +
    "fill='none' stroke='currentColor' stroke-width='1.5' aria-hidden='true'>" +
    "<circle cx='10' cy='10' r='8'/><circle cx='10' cy='10' r='5.2'/>" +
    "<path d='m7.6 10.2 1.7 1.7 3.1-3.6' stroke-linecap='round' " +
    "stroke-linejoin='round'/></svg>";
  if (!C) {
    el.innerHTML = "<div class='certb uncert' role='status'>" + warn + "<div>" + dual(
      "DEMONSTRATION ONLY — this deployment carries NO safety certificate. The threshold here exists to show the displays; none of its answers carry any guarantee.",
      "UNCERTIFIED DEMONSTRATION — no certificate attaches to this operating threshold. Explanations are shown WITHOUT the guarantee that is the system's point; do not quote numbers from this page as certified.") + "</div></div>";
  } else {
    const f = Object.keys(C).sort().map(k => k + " = " + C[k]);
    el.innerHTML = "<div class='certb cert'>" + seal + "<div><b>Certified deployment</b> — " +
      "<span class='num'>" + f.join(" · ") + "</span><span class='cl2'>The certificate bounds a " +
      "site-population-average error rate among answered cases; it is not a " +
      "per-record or per-site property, and it certifies no single answer on " +
      "this page.</span></div></div>";
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
  el.innerHTML = "<span class='sl'>"+dual(s,a)+"</span><b class='num'>"+shown+"</b>";
  strip.appendChild(el); };
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

// ---- provenance: where this pool sits in the site-level split ----
(function(){
  const P = DATA.provenance, box = document.getElementById("provbox");
  if (!P || !box) return;
  const tot = P.cohort_total ? P.cohort_total.toLocaleString() : null;
  const rep = (P.replicate === undefined || P.replicate === null)
    ? "" : " (split " + P.replicate + " of the validity arm; each split holds " +
      "out a different set of hospitals)";
  box.innerHTML = "<p class='note' style='margin:6px 0 0'>" + dual(
    "These " + DATA.n_total.toLocaleString() + " cases come from <b>" + P.pool +
      "</b>" + (tot ? " — the rest of the " + tot + " patients" +
      (P.cohort_sites ? " across " + P.cohort_sites + " hospitals" : "") +
      " were used to build the model and set its safety bar, so showing them " +
      "here would flatter it" : "") + ". These hospitals the model has never " +
      "seen in any form: they stand in for a hospital adopting it tomorrow" + rep + ".",
    "Pool: <b>" + P.pool + "</b>" + (tot ? " of " + tot + " cohort stays" +
      (P.cohort_sites ? " over " + P.cohort_sites + " hospitals" : "") : "") +
      (P.splits ? "; the remainder splits " + P.splits +
       " — displaying them would be optimistic (train) or circular (calibration, " +
       "which selected τ*)" : "") + rep + ".") + "</p>";
})();

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
    document.getElementById("binclear").style.display = binSel ? "inline-flex" : "none";
    rebuildList(); };
  hist.appendChild(el); });
const hb0 = document.createElement("div"); hb0.className = "hband";
hb0.style.left = ((TAU-0.5)/0.5*100).toFixed(2)+"%";
hist.insertBefore(hb0, hist.firstChild);
const tl = document.createElement("div"); tl.className = "tau";
tl.style.left = ((TAU-0.5)/0.5*100).toFixed(2)+"%";
tl.innerHTML = "<span>"+dual("the bar","&#964;*")+"</span>";
hist.appendChild(tl);
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
    "), full cohort · top 14 by gap</span></h2>"+
    "<div class='legend'><span><i style='background:var(--ans)'></i>answered</span>"+
    "<span><i style='background:var(--dec)'></i>declined</span>"+
    "<span>each bar's value is printed beside it, so colour is never the only cue</span></div>";
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
    row.innerHTML = "<i class='dt "+(c.declined?"d":"a")+"'></i>case "+c.idx+
      " <span class='m'>"+
      (c.declined ? dual(Math.abs(c.margin_to_answer) < 0.1
          ? "handed over · a whisker away" : "handed to a person",
          "declined · margin "+sigfmt(c.margin_to_answer))
        : "answered")+extra+"</span>";
    if (k === cur) row.className = "sel";
    row.setAttribute("role", "button"); row.tabIndex = 0;
    row.setAttribute("aria-label", "case " + c.idx + (c.site ? ", hospital " + c.site : ""));
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
    return "<div class='barrow'><div class='barlab' title='"+tip(j).replace(/'/g,"&#39;")+"'>"+NAMES[j]+
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
      "<div class='tblwrap'><table><tr><th>level</th><th>risk</th><th>confidence</th><th>gate</th></tr>";
    ONEHOT[g].forEach(([jj,level]) => {
      const t = xCur.slice();
      ONEHOT[g].forEach(([kk]) => t[kk] = 0.0); t[jj] = 1.0;
      const sc = scoreOf(t), on = xCur[jj] >= 0.5;
      h += "<tr"+(on?" style='font-weight:650'":"")+"><td>"+level+(on?" ← current":"")+
        "</td><td class='num'>"+(riskOf(t)*100).toFixed(1)+"%</td><td class='num'>"+
        sc.toFixed(4)+"</td><td>"+(sc>=TAU?"answers":"declines")+"</td></tr>"; });
    return h+"</table></div>"; }
  if (DATA.binary[j]) {
    let h = "<p class='note'>Exact effect of each state of <b>"+NAMES[j]+"</b>.</p>"+
      "<div class='tblwrap'><table><tr><th>state</th><th>risk</th><th>confidence</th><th>gate</th></tr>";
    [0,1].forEach(v => { const t = xCur.slice(); t[j] = v; const sc = scoreOf(t);
      h += "<tr"+(xCur[j]===v?" style='font-weight:650'":"")+"><td>"+(v?"yes":"no")+
        (xCur[j]===v?" ← current":"")+"</td><td class='num'>"+(riskOf(t)*100).toFixed(1)+
        "%</td><td class='num'>"+sc.toFixed(4)+"</td><td>"+(sc>=TAU?"answers":"declines")+
        "</td></tr>"; });
    return h+"</table></div>"; }
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
  let h = "<div class='tblwrap'><table><tr><th>j</th><th>feature</th><th>kind</th><th>x now</th>"+
    "<th>x recorded</th><th>z</th><th>w</th><th>&#966;</th></tr>";
  const ord = NAMES.map((_,j)=>j).sort((a,b)=>Math.abs(phi[b])-Math.abs(phi[a]));
  ord.slice(0,40).forEach(j => {
    h += "<tr><td>"+j+"</td><td>"+NAMES[j]+"</td><td class='note'>"+kindOf(j)+
      "</td><td class='num'>"+sigfmt(xCur[j],5)+"</td><td class='num'>"+sigfmt(c.x[j],5)+
      "</td><td class='num'>"+sigfmt((xCur[j]-H.mu[j])/H.sd[j],4)+"</td><td class='num'>"+
      sigfmt(H.coef[j],4)+"</td><td class='num'>"+sigfmt(phi[j],4)+"</td></tr>"; });
  h += "</table></div><p class='note'>Top 40 of "+D+" by |&#966;|. intercept "+
    sigfmt(H.intercept,5)+" · logit "+sigfmt(logitOf(xCur),6)+" · L* "+
    L_STAR.toFixed(6)+"</p><button id='copyJson'>Copy case as JSON</button>"+
    "<button id='copyCsv'>Copy attributions as CSV</button>"+
    "<span class='note' id='copied' style='display:none'> copied</span>";
  return h; }

function hospitalsHTML() {
  if (!DATA.per_site) return "<p class='note'>No hospital ids were supplied to this build.</p>";
  let h = "<p class='note'>The hospital is the unit the guarantee is stated over. "+
    "Coverage and answered-error are computed over ALL cases at this hospital, "+
    "not just the ones embedded above."+(DATA.has_oracle?" Error columns are "+
    "RETROSPECTIVE (oracle labels).":"")+"</p><div class='tblwrap'><table><tr><th>hospital</th><th>n</th>"+
    "<th>answered</th><th>coverage</th>"+(DATA.has_oracle?
    "<th>answered error</th><th>answered positives</th>":"")+"</tr>";
  DATA.per_site.slice(0,40).forEach(r => {
    h += "<tr><td>"+r.site+"</td><td class='num'>"+r.n+"</td><td class='num'>"+
      r.n_answered+"</td><td class='num'>"+fmt(r.coverage)+"</td>"+
      (DATA.has_oracle ? "<td class='num'>"+fmt(r.answered_err)+"</td><td class='num'>"+
        fmt(r.answered_pos_frac)+"</td>" : "")+"</tr>"; });
  return h+"</table></div><p class='note'>Showing "+Math.min(40,DATA.per_site.length)+
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
  s += "<div class='tblwrap'><table><tr><th>predicted band</th><th>n answered</th><th>mean predicted</th>"+
    "<th>observed</th></tr>";
  R.forEach(b => { s += "<tr><td>"+(b.lo*100).toFixed(0)+"–"+(b.hi*100).toFixed(0)+
    "%</td><td class='num'>"+b.n+"</td><td class='num'>"+(b.mean_predicted*100).toFixed(1)+
    "%</td><td class='num'>"+(b.observed*100).toFixed(1)+"%</td></tr>"; });
  return s+"</table></div>"; }

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
    "calc("+((Math.min(Math.max(score,0.5),1)-0.5)/0.5*100).toFixed(2)+"% - 1px)";
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

// the confidence meter: a graduated scale with the answering band, the
// red-line at tau*, and a damped needle.
function meterTicks() {
  let t = "";
  for (let k = 0; k <= 10; k++) {
    const p = k*10, v = 0.5 + k*0.05, M = k % 2 === 0;
    t += "<i class='"+(M?"tM":"tm")+"' style='left:"+p+"%'></i>";
    if (M) t += "<b style='left:"+p+"%'>"+v.toFixed(2)+"</b>";
  }
  return t; }

function renderDetail() {
  const c = DATA.cases[order[cur]];
  visIdx = computeVisIdx();
  let h = "<p><span class='verdict' id='verdictPill' role='status' aria-live='polite'></span>"+
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
  const tp = ((TAU-0.5)/0.5*100).toFixed(2);
  h += "<div class='meter'><div class='mband' style='left:"+tp+"%'></div>"+meterTicks()+
    "<div class='mline' style='left:"+tp+"%'><span>"+dual("the bar","&#964;*")+"</span></div>"+
    "<div class='needle' id='needle'></div></div>"+
    "<div class='gaxis'><span id='gscore'></span></div>";
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
  h += "<h2 style='margin-top:8px'>"+dual("Try it yourself: change a value, the program re-decides",
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
    h += "<div class='srow'><label title='"+tip(ONEHOT[g][0][0]).replace(/'/g,"&#39;")+
      "'>"+g+"</label>"+
      "<select id='"+id+"' data-g='"+g+"' aria-label='what-if level for "+g+"'>"+
      ONEHOT[g].map(([jj,lv]) => "<option value='"+jj+"'"+
        (on && on[0]===jj ? " selected" : "")+">"+lv+"</option>").join("")+
      "</select><span class='v note'>"+(orig?"":"none")+"</span>"+
      "<span class='rst"+((on&&orig&&on[0]!==orig[0])?" on":"")+"' data-g='"+g+
      "' id='rsg_"+id+"' title='restore recorded level'>"+IC_RESET+"</span></div>"; });
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
        "' title='"+tip(j).replace(/'/g,"&#39;")+"'>"+NAMES[j]+"</label>";
      if (DATA.binary[j]) {
        h += "<div class='srow'>"+lab+"<span><input type='checkbox' data-j='"+j+"'"+
          (xCur[j]>=0.5?" checked":"")+" aria-label='toggle "+NAMES[j]+
          "'> <span class='note'>yes / no</span></span>"+
          "<span class='v num' id='sv"+j+"'></span><span class='rst' id='rs"+j+
          "' data-j='"+j+"' title='recorded: "+sigfmt(c.x[j],4)+"'>"+IC_RESET+"</span></div>";
      } else {
        const lo = H.mu[j]-4*H.sd[j], hi = H.mu[j]+4*H.sd[j];
        const rec = Math.min(100, Math.max(0, (c.x[j]-lo)/(hi-lo)*100)).toFixed(2);
        h += "<div class='srow'>"+lab+"<span class='sldw'><input type='range' data-j='"+j+
          "' min='"+lo+"' max='"+hi+"' step='"+((hi-lo)/400)+"' value='"+xCur[j]+
          "' aria-label='what-if value for "+NAMES[j]+"'><i class='srail'></i>"+
          "<i class='smark' style='left:"+rec+"%'></i></span><span class='v num' id='sv"+j+
          "'></span><span class='rst' id='rs"+j+"' data-j='"+j+"' title='recorded: "+
          sigfmt(c.x[j],4)+"'>"+IC_RESET+"</span></div>"; } }); });
  h += "<details style='margin-top:8px'><summary>"+dual("What you tried (log)","What-if log")+
    "</summary><div id='logbox' class='note'></div></details>";
  h += "<h2 style='margin-top:16px'>"+dual("What pushed its confidence up or down",
       "What drives the confidence")+"</h2><p class='note'>"+
    dual("Bars right push toward the program's leaning; bars left pull against it. "+
         "When they cancel out, it hands the case over.",
         "Right of the line builds confidence toward the leaned class; left erodes it "+
         "— cancellation causes the decline.")+"</p><div id='phibars'></div>";
  if (c.declined && c.counterfactuals.length) {
    h += "<h2 style='margin-top:16px'>"+dual("What would have to be different for it to answer",
      "Smallest single-input changes that would make the gate answer")+"</h2><p class='note'>"+
      dual("Each row is the smallest change to ONE value that would let the program "+
           "answer — and even then it would only just clear the bar.",
           "Ranked by standardized magnitude; each clears the bar by the documented "+
           "headroom, so the answer carries the weakest allowed confidence, "+
           fmt(c.confidence_at_flip)+".")+"</p><div class='tblwrap'><table><tr><th>"+
      dual("what","input")+"</th><th>"+dual("change needed","raw &#916;")+"</th>"+
      "<th class='advonly'>std &#916;z</th><th>"+dual("kind","kind")+"</th><th>"+
      dual("it would then say","answers as")+"</th></tr>";
    c.counterfactuals.forEach(cf => {
      h += "<tr><td title='"+tip(cf.j).replace(/'/g,"&#39;")+"'>"+NAMES[cf.j]+
        "</td><td class='num'>"+signed(cf.delta_x)+
        "</td><td class='num advonly'>"+signed(cf.delta_z)+"</td><td>"+
        (kindTag(cf.j) || "<span class='tag'>"+dual("measurement","clinical")+"</span>")+
        "</td><td>"+dual(cf.answers_as==="predicted-positive"?"higher risk":"lower risk",
          cf.answers_as)+"</td></tr>"; });
    h += "</table></div><p class='note'>"+dual(
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
  box.querySelectorAll(".rst[data-j],.rst[data-g]").forEach(rs => {
    rs.setAttribute("role", "button"); rs.tabIndex = 0;
    rs.setAttribute("aria-label", "restore recorded value"); });
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
  ch.classList.add("on");
  document.querySelectorAll(".side .chip[data-f]").forEach(c => press(c, c === ch));
  filter = ch.dataset.f; rebuildList(); });
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
const tXm = document.getElementById("tauXmark");
if (tXm) tXm.style.left = ((TAU-0.55)/(0.99-0.55)*100).toFixed(2)+"%";
function exploreUpdate() {
  const t = +tX.value, n = DATA.all_scores.length;
  const ans = DATA.all_scores.filter(s => s >= t).length;
  tXv.innerHTML = dual("bar "+t.toFixed(2)+" → answers "+(ans/n*100).toFixed(1)+
      "% ("+(n-ans).toLocaleString()+" handed over)",
    "bar "+t.toFixed(2)+" → coverage "+(ans/n*100).toFixed(1)+"% ("+
      (n-ans).toLocaleString()+" declined)"); }
tX.addEventListener("input", exploreUpdate);
exploreUpdate();
const gq = document.getElementById("glossQ");
if (gq) gq.addEventListener("input", renderLegend);
renderLegend();
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
                           oracle_y=pool.y, site_ids=list(pool.site_id),
                           provenance=dict(
                               pool=f"{len(set(pool.site_id))} held-out demo sites",
                               cohort_total=coh.n + pool.n,
                               cohort_sites=len(set(coh.site_id)) + len(set(pool.site_id)),
                               splits="train / aux / calibration sites"))
    n_declined = int((head.score(pool.x) < 0.77).sum())
    print(f"[dashboard] wrote {path} ({pool.n} cases, {n_declined} declined)")


if __name__ == "__main__":
    main()
