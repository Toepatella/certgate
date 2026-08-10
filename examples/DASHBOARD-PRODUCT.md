# Product — CertGate Explain dashboard

Who `examples/explain_dashboard.py`'s page is for and what it may not do.
Companion to `DASHBOARD-DESIGN.md`, which describes how it looks.

## Register

product

## Users

Two audiences share one page, switched by an explicit register toggle:

1. **Plain-language readers** — clinicians, ward staff, governance and ethics
   reviewers, patients' advocates. They did not build the model and must not be
   asked to trust it on charisma. They need to understand *why the safety gate
   answered or handed a case to a person*, in everyday words, with the
   guardrail caveats impossible to miss.
2. **Advanced readers** — ML engineers, auditors, statisticians validating a
   selective-prediction deployment. They want the head's actual arithmetic:
   logits, margins, Shapley attributions, counterfactuals, per-site coverage,
   reliability curves, and a live what-if workbench that re-runs the deployed
   rule `score >= τ*` in float64.

Both read the page during long, focused desk sessions. It is also printed and
attached to review documents.

## Product Purpose

CertGate Explain is the explanation surface for a **certified selective
classifier**: a safety gate in front of a risk model that answers only when
confident enough (score ≥ τ*) and abstains to a human otherwise, with a
certificate bounding the site-population-average error rate among answered
cases. The page is a **local, self-contained instrument**: it embeds the model
head and recomputes every number live — the confidence meter, sliders,
waterfall, smallest-change flip, threshold explorer all run the deployed rule's
own float64 arithmetic. Success: a reader leaves knowing (1) what the gate
decided on a case and what drove it, (2) what would have to change for it to
answer, (3) exactly what the certificate does and does not promise.

## Truth constraints (uninventable)

- Every displayed number is real payload arithmetic; nothing may be invented,
  smoothed, or dramatized. Numbers are the content.
- The caveats are product truth, not copy to tighten: score-space not clinical
  advice; the certificate is population-average, never per-case; retrospective
  outcomes are labelled retrospective; the threshold explorer confers no
  guarantee; the UNCERTIFIED banner must be unmissable when no certificate
  attaches.
- Degraded builds are first-class: no-certificate, no-outcomes, no-oracle,
  no-sites variants must all lay out cleanly from the same template.
- The artifact is one self-contained HTML file, offline, no network, no
  webfont downloads, stdlib-rendered. It must survive being embedded in a
  Python raw string (no `"""`, no trailing backslash, LF endings, exactly one
  `__PAYLOAD__`, and the machine-managed `const DATA = ` line).

## Brand Personality

An **instrument, not a pitch**. The register of a calibration certificate or a
test-bench report: precise, unhurried, every figure carrying its unit and its
caveat. Three words: **calibrated, candid, legible**. The page's authority
comes from showing its own arithmetic, so the design must feel measured and
verifiable — never promotional, never alarming, never decorated.

## Anti-references

- Analytics-SaaS dashboard chrome: KPI hero tiles, sparkline garnish, card
  grids, glassmorphism, gradient headers.
- "AI product" styling: neon on black, glow, purple gradients.
- Safety theater: oversized warning iconography, red everywhere, alarm
  aesthetics that numb the one banner that matters (UNCERTIFIED).
- Medical-brand softness: friendly rounded pastel "health app" styling would
  miscast a governance instrument as a consumer product.

## Accessibility & Inclusion

WCAG 2.1 AA floor, already partially built and non-negotiable in any redesign:
≥4.5:1 body contrast, visible focus on every interactive element (including
role=button spans), Enter/Space activation, 44px touch targets, reduced-motion
honored, print stylesheet, dark mode, color never the only channel (legends
carry words; outcome pills carry text). Plain-language register targets
everyday reading level; jargon lives only in the Advanced register.
