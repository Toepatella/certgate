# out-e6-composition/ -- POST-HOC re-derivation of E6's BBSE-implied composition

**Status: POST-HOC (2026-10-29).** The released E6 composition
(`experiments/out/E6_composition.json`, Supplementary Table S9, Section 4.7)
is unchanged and stays frozen. This directory holds the BBSE-implied
answered-set true-positive fraction re-derived against the prior the head
actually carries (audit 2026-10 BBSE-1; verdicts `composition-prior#L1#0`
and `composition-prior#L2#0`). **Nothing in it is a certified quantity**: the
BBSE-implied view is an estimated, label-shift-tagged diagnostic, and no
certificate, certified or estimated tier, `rho_point`, rho box, walk order or
guarantee string moves.

Produced by `experiments/rescore_e6_composition.py`:

    python -m experiments.rescore_e6_composition

File: `E6_composition_corrected.json` (released and corrected
`bbse_true_class`, the oracle and predicted-class views, the BBSE fit's
`rho_point`, `pi_s`, `q`, `c0`, `c1` and box, the replay settings, the
self-check record, `_run` with UTC time, git sha and the sha256 of the frozen
input).

## What is computed

The released view multiplied each answered record's head posterior odds by
BBSE's `rho_point = odds(pi_t) / odds(clip(pi_source))`, with `pi_source` the
record-pooled S_aux prevalence. The logistic head is fit on S_train with an
unpenalized intercept, so its odds carry the S_train prevalence `pi_train`.
The label-shift prior correction (Saerens, Latinne and Decaestecker 2002) is

    odds_t = odds_head * odds(pi_t) / odds(pi_train)
           = odds_head * rho_point * odds(clip(pi_source)) / odds(pi_train)

with `pi_train = train.y.mean()` and `clip` to `[PI_CLIP, 1 - PI_CLIP]` as
`rho_box_interval` clips it. The released multiplier is exact only when
`pi_train == pi_source`.

| E6 answered set (25,314 records) | positive fraction | expected positives | odds multiplier |
|---|---|---|---|
| BBSE-implied, released | 0.0857576903 | 2,170.870 | 0.8296804526 (rho alone) |
| BBSE-implied, corrected | 0.0913101048 | 2,311.424 | 0.9475924166 |
| Oracle (diagnostic) | 0.0914908746 | 2,316 | -- |

`pi_train = 0.1023781383` (5,717 / 55,842), `pi_source = 0.1152509772`,
`rho_point = 0.8296804526`, implied `pi_t = 0.0975360666`. Relative error
against the oracle: -6.27% released, -0.20% corrected.

## From what, and how it is checked

E6 is replayed in memory exactly as `run_synthetic.run_E6` runs it:
`_rng(6)`, `_draw_split` on the 208 anchor sites, the 40-site `e6t` target
pool, `run_certgate` with `target_site_id` and `oracle_target_y`, `tau*` from
the operative rung. No file other than the frozen
`experiments/out/E6_composition.json` is read, and it is read only.

Before anything is written the script refuses unless the replay reproduces
the frozen file **with exact float equality** on `rho_point`, the
predicted-class `positive_fraction` / `n_positive` / `n_answered`, the
oracle-class `positive_fraction` / `n_positive` / `n_answered`, and the
released `bbse_true_class` `positive_fraction` and `expected_n_positive`
under the released rho-only formula; and unless the corrected view lands on
the two verdicts' independently derived values (fraction and multiplier to
10 dp, expected count to 3 dp). It also refuses to write into any frozen
`experiments/out*/` directory.

The eICU counterpart (`EICU_certificate.json`
`diagnostic.composition.bbse_true_class`, 0.0307) is not corrected here:
`pi_train` for the published split is in no released artifact, so the
corrected value needs the credentialed extract. A data-use-agreement holder
has computed it from the extract in `experiments/out-eicu-composition/`
(0.0307 -> 0.0323 on the published split).
