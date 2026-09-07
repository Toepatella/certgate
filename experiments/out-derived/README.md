# out-derived/ -- POST-HOC, read-only derivation

**Status: POST-HOC (2026-09-04).** Nothing here is a certified quantity. This
directory holds one file, `fixpass_numbers.json`, derived read-only from the
released artifacts under `experiments/out/`, `out-panel/`, `out-sens/`,
`out-subgroups/` and `out-faithfulness/` and, when they exist, from the four
post-hoc sidecars (`out-e9a-rescore/`, `out-e9b-positives/`, `out-bbse-probe/`,
`out-settled/`) and lane C's re-emitted eICU run (`out-rev2/`). It is the
single file the manuscript's pasted numbers are checked against.

Produced by `experiments/derive_fixpass_numbers.py`:

    python -m experiments.derive_fixpass_numbers

Seven values are pinned inside the script (composition mean 0.0524, head AUC
on S_cal 0.8618, 63 positive calls on the published split, 8 of 570 fairness
cells over budget, Spearman 0.636, 194 baseline-mode E1 draws). If any stops
reproducing, nothing is written. The JSON's `_run` block records the UTC time,
the git sha and the sha256 of every input read. No pipeline is re-run and the
restricted extract is never touched.
