# out-settled/ -- POST-HOC settlement of the seven registered predictions

**Status: POST-HOC (2026-09-04).** The protocol (`EICU-PROTOCOL.md` section 9)
registered seven predictions before any eICU byte was read; the preflight
wrote them into `experiments/out/EICU_preflight.json`. The runner never scored
them, and the manuscript's hand-written settlement read P7 as confirmed when
its 208-site clause failed (207). This directory holds the clause-by-clause
settlement, derived read-only from the released files
(`EICU_preflight.json`, `EICU_pooled.csv`, `EICU_per_site.csv`,
`EICU_diagnostics.json`, `EICU_attrition.csv`).

Produced by `experiments/settle_predictions.py`:

    python -m experiments.settle_predictions

Files: `EICU-PREDICTIONS-SETTLED.md` (readable) and `.json` (the same content
with a `_run` block: UTC, git sha, sha256 of every input). Tally: 3 confirmed
(P1, P3, P6) / 1 partly (P7) / 3 falsified (P2, P4, P5). The verdict rule is
printed in both files; P3's modal-reason clause is reported as it came out.
The script refuses to write under any frozen output directory and never
targets `EICU-SUMMARY.md`, whose section list is an append-only pin.
