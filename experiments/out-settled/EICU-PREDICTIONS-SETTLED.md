# eICU-CRD v2.0 -- the seven registered predictions, settled

[MEASURE] POST-HOC (2026-09-04): clause-level settlement of the seven registered predictions, derived from the released artifacts after the fact; certifies nothing and changes no certified quantity. The registered wording is quoted from EICU_preflight.json verbatim.

**Tally: 3 confirmed / 1 partly / 3 falsified.** Before this file the manuscript read: four confirmed (P1, P3, P6, P7), three falsified (P2, P4, P5); P7's site clause was not scored.

**Rule.** A prediction whose protocol entry states its own falsification rule is confirmed unless that rule fires; its other clauses are reported beside it. Otherwise: confirmed when every clause holds; falsified when the clause on the registered settling quantity fails; partly when that clause holds but another registered count does not. Per-re-split quantities are scored on the majority of the twenty; the published split (replicate 0) is shown separately.

| id | verdict | registered (verbatim) | settled by |
|---|---|---|---|
| P1 | **confirmed** | At 208 hospitals (75 calibration sites), alpha = 0.10 certifies on the pooled arm and alpha = 0.05 does not, in >= 15 of the 20 replicates. Basis: E4's synthetic frontier -- alpha=0.10 certifies from ~150 sites, alpha=0.05 first appears ~300 and is reliable only by 400. | EICU_pooled.csv `certified` by `alpha` |
| P2 | **falsified** | The per-site dispersion diagnostic on the pooled target pool at the deployed tau (_per_site_exceed_frac) is > 0.02 and lands in [0.05, 0.30] -- real hospitals are more heterogeneous than the synthetic generator at s_u = 0.5 (which gave 0.02) and closer to its s_u = 2.0 arm (0.10). | EICU_pooled.csv `per_site_exceed_frac` |
| P3 | **confirmed** | BBSE contributes no certificate: it declines on >= 90% of the 25 pools per replicate, with bbse-misspecified or bbse-ill-conditioned the modal reason. Basis: E2's 200/200 declines, plus the coarse 2000-draw q_t tail widening the 16-corner box. Falsified if BBSE certifies a tau the baseline walk does not. | `decline_reason` / `mode_outcomes` columns |
| P4 | **falsified** | APACHE-absence features (aps_present, apv_present, or an aps_*__missing / apv_*__missing sibling) appear in the top 3 of the abstention gap_ranking on the pooled arm. Basis: absence is site-correlated by the dataset authors' own account. | EICU_diagnostics.json `abstention_gap_ranking` |
| P5 | **falsified** | The per-hospital arm returns pool-too-small for >= 1 and <= 6 of the 24 target hospitals (heavy-tailed hospital sizes; ~78% of hospitals have < 500 stays). | EICU_per_site.csv `reason` |
| P6 | **confirmed** | Mean coverage at the operative rung on the pooled arm is in [0.60, 0.95]. | EICU_pooled.csv `coverage` |
| P7 | **partly** | Primary-cohort size lands in [130 000, 175 000] stays across 208 sites, and apache-result-linked retains <= 195 sites -- i.e. the APACHE-result restriction visibly deletes >= 13 hospitals. | EICU_attrition.csv |

## P1 -- confirmed

| clause | registered | observed | met |
|---|---|---|---|
| alpha = 0.10 certifies on the pooled arm | >= 15 of 20 | 20 of 20 | yes |
| alpha = 0.05 does not certify on the pooled arm | >= 15 of 20 | 20 of 20 | yes |
| both hold in the same re-split | >= 15 of 20 | 20 of 20 | yes |

## P2 -- falsified

| clause | registered | observed | met |
|---|---|---|---|
| per-site dispersion diagnostic at the deployed tau, pooled arm, exceeds 0.02 | > 0.02 (direction) | 11 of 20 re-splits; mean 0.0271; published split 0.0417 | yes |
| ... and lands inside the registered interval | [0.05, 0.30] (settling quantity) | 2 of 20 re-splits; range [0.0000, 0.0833] | NO |

Note: real hospitals were LESS dispersed at the deployed tau than the registered floor; the synthetic s_u = 0.5 arm gave 0.02

## P3 -- confirmed

| clause | registered | observed | met |
|---|---|---|---|
| BBSE declines on the pools of each re-split | >= 90% of the 25 pools per re-split | 20 of 20 re-splits at >= 0.90 (min share 1.0) | yes |
| the modal BBSE decline reason | bbse-misspecified or bbse-ill-conditioned | modal reason met in 7 of 20 re-splits; failsafe is modal in 13 (characterisation clause) | NO |
| falsification rule: BBSE certifies a tau the baseline walk does not | 0 pools | 0 pools over 20 re-splits | yes |

Note: P3 carries its own falsification rule in the protocol, which did not fire; the modal-reason phrase is a characterisation of the mechanism and is reported as it came out (bbse-misspecified modal in 7 of 20 re-splits; failsafe, meaning the mode fit but certified no threshold at both endpoints, modal in 13). Under a stricter every-clause reading this would be 'partly'.

## P4 -- falsified

| clause | registered | observed | met |
|---|---|---|---|
| an APACHE-absence feature (aps_present, apv_present or a *__missing sibling) sits in the top 3 of the abstention gap ranking, pooled arm (registered unsigned rule) | top 3 (every re-split) | 2 of 20 re-splits | NO |
| ... with the registered leak sign (more attribution on declined stays, gap < 0) -- the signed reading | gap < 0 | 0 of 20 re-splits; the 2 unsigned hits all carry positive gaps | NO |
| amendment A1 precondition: every F-D leg clear and the prevalence-ratio gate silent, so a hit would read as confirmation and not as the leak signature | 0 alarms, gate not fired | 0 leak alarms, 0 flagged screens, gate fired=False | yes |

Note: the unsigned rule holds on 2 of 20 re-splits (re-split 2: aps_heartrate__missing +0.126; re-split 5: aps_heartrate__missing +0.105); both hits pull harder on ANSWERED stays, the opposite direction from the registered leak signature, so under a signed reading P4 holds on 0 of 20

## P5 -- falsified

| clause | registered | observed | met |
|---|---|---|---|
| the per-hospital arm returns pool-too-small for some of the 24 target hospitals | >= 1 and <= 6 of 24, per re-split | in range on 3 of 20 re-splits; counts [(0, 17), (1, 3)] (published split 0; total 3 of 480) | NO |

Note: the floor bit on fewer hospitals than registered: 3 pools of 480 over the 20 re-splits, never more than one per re-split

## P6 -- confirmed

| clause | registered | observed | met |
|---|---|---|---|
| mean coverage at the operative rung, pooled arm | [0.60, 0.95] | 20 of 20 re-splits inside; mean 0.8904, range [0.8080, 0.9257] | yes |

## P7 -- partly

| clause | registered | observed | met |
|---|---|---|---|
| primary-cohort size (settling quantity) | [130 000, 175 000] stays | 164,322 | yes |
| primary-cohort hospital count | 208 sites | 207 (208 in the raw unit-stay table; one hospital carries no stay with a known outcome) | NO |
| apache-result-linked hospital count | <= 195 sites (>= 13 hospitals deleted) | 190 (17 deleted from the primary cohort) | yes |

## Provenance

- utc: 2026-09-07T01:29:12+00:00
- git sha: f48d3b4ec5b7f7d92021e4ec75f8127bf83de34d
- inputs (sha256):
    - `experiments/out/EICU_preflight.json` 5b36918850ff4545580f56110ac425fd5b729670ae7756c953164a30cfab4c1a
    - `experiments/out/EICU_pooled.csv` 3036ae120d70a8bf1d048f998ab710d36b6bdd0f3148893d109185778ff58f18
    - `experiments/out/EICU_per_site.csv` c85ea2c17fb878a14dd02837cfd8c22b42dc7d6862c03e82d1a9fca4ebadb00a
    - `experiments/out/EICU_diagnostics.json` c357e8a7e873f7b1d974df055790f07aad062894d3ac11d8c57559e0dd12f04d
    - `experiments/out/EICU_attrition.csv` 51784a55d02d5d03580f4e50b270ecc156c760307a8f6c9e6619b191c34a2ea9
