# SPEC — engineering contract (builders: follow exactly; deviations require editing this file first)

Reference implementation for the audited statistical core lives in `../testbed/` (certify.py, modes.py) — port the *math* from there (it survived adversarial review), but this SPEC's interfaces, hardening, and constants override v1 everywhere they differ. Python 3.13 / numpy 2.5 / scikit-learn 1.9. All sklearn/scipy imports at module top level (never inside functions — audit F16).

**2026-07-25 audit revision (CODE-AUDIT.md V1–V27).** This revision corrects two defects this SPEC itself mandated: (V1) the guarantee text claimed a per-target-site bound where the certified estimand is the influence-weighted answered risk *averaged over the site population* — the statement now names the population-average estimand and carries a mandatory between-site-dispersion clause; (V2) BBSE treated the target predicted-positive rate `q_t` as exact — it now receives a confidence share (`BBSE_BONFERRONI = 4`, 16-corner box). Also: the WSR permutation seed no longer depends on the target label (V3 — restores the true shared-event property in baseline mode), site identity is canonicalized and near-duplicate ids are rejected loudly (V4/V5/V10), and the provenance block binds labels, site partitions, shape, and dtype (V11).

## Module DAG

```
constants.py                      (no deps)
validate.py    -> constants       (Cohort container + loud input contract)
data.py        -> constants, validate      (synthetic generator + site splits)
model.py       -> constants                (logistic head, internal guarded standardization)
certify.py     -> constants                (atoms, WSR, walk, floor, seed rule)
shift.py       -> constants, certify, validate, model   (BBSE mode)
explain.py     -> model                    (attributions, abstention explanations, composition)
harness.py     -> constants                (Wilson LCB, hard-violation scoring, binomial reference)
report.py      -> constants, certify, explain            (tiers, guarantee text, provenance)
pipeline.py    -> everything               (run_certgate orchestration)
```

## Frozen constants (`constants.py`) — every value pinned literally by `tests/test_constants.py`

```python
SEED = 20260721
SPLIT_FRACTIONS = (0.40, 0.20, 0.40)     # S_train / S_aux / S_cal, site-disjoint
ALPHA_LADDER = (0.05, 0.10)
DELTA = 0.05
BBSE_DELTA_CONF = 0.025                  # BBSE box confidence share
BBSE_DELTA_BET = 0.025                   # BBSE betting-test share (sum = DELTA)
BBSE_BONFERRONI = 4                      # box covers (c0, c1, pi_source, q_target) — audit V2
BBSE_MIN_TARGET_SITES = 10               # q cluster-bootstrap floor (verification F1): a
                                         # percentile bootstrap over 2-9 target sites cannot
                                         # approach nominal coverage (measured rho-miss up to
                                         # 46% at K=2 vs nominal 2.5%); 2 <= K < floor
                                         # declines "bbse-target-clustering"; K=1/None takes
                                         # the exact Clopper-Pearson path
M_INFLUENCE = 100
TAU_GRID = np.linspace(0.55, 0.99, 23)
WSR_LAMBDA_CAP = 0.9                     # lambda cap = 0.9 / (1 - alpha)
WSR_VAR_FLOOR = 1e-8
WSR_MU0, WSR_S2_0 = 0.5, 0.25
MIN_CAL_CLUSTERS = 50                    # RECORD-CARRYING calibration clusters (audit B-5)
MIN_ANSWERABLE = 10                      # registered target-pool floor (audit B-6)
BBSE_GAP_FLOOR = 0.10                    # worst-case (c1 - c0) below this -> decline
BBSE_BOOT = 2000                         # required VALID resamples
BBSE_BOOT_MAX_ATTEMPTS = 4000            # total attempts before declining (audit B-8)
PI_CLIP = 1e-4
SD_REL_TOL = 1e-9                        # guarded standardization (audit F06: relative, not ==0)
HEAD_C = 1.0
HEAD_MAX_ITER = 2000
MODE_BASELINE, MODE_BBSE = 0, 1
```

**Basis for the values (panel item S2-13).** Pinning attests only that a value was fixed before any result was read. The per-constant rationale is tabulated in `paper/draft.md` Table 5 and must stay consistent with this block. Only `M_INFLUENCE` materially moves the certificate, and its sensitivity is measured, not asserted: re-running E1's `s_u=0.5` arm in baseline mode at M ∈ {25, 50, 100, 200, 500, 1000, 5000} (walk order and calibration walk re-derived at each M, each certificate rescored against R_M *at that same M*) gives certify rates 1.0/1.0/1.0/1.0/1.0/0.03/0.0 at α=0.10 and 0.0 everywhere at α=0.05 — a plateau over M ≤ 200 and a collapse above it, with every larger M certifying LESS. See `paper/draft.md` §4.9 / Table 6. Any change to `M_INFLUENCE` must re-run that sweep.

## `validate.py`

```python
class CohortError(ValueError): ...       # every rejection is loud, typed, and message-named

@dataclass(frozen=True)
class Cohort:
    x: np.ndarray          # (n, d) float64, all finite
    y: np.ndarray          # (n,) dtype bool STRICTLY
    site_id: np.ndarray    # (n,) int64, dense 0..n_sites-1, every index present
    site_labels: tuple[str, ...]   # original identifiers, index-aligned to dense ids, UNIQUE
    # properties: n, d, n_sites, site_sizes (ALWAYS np.bincount(site_id, minlength=n_sites)
    #             — never an independent input; audit F38)
    # __post_init__ (audit V15): the documented contract is enforced on DIRECT construction
    # too, not only through make_cohort — x 2-D float64 finite; y 1-D bool; site_id 1-D
    # int64 with 0 <= site_id < len(site_labels); lengths aligned; site_labels unique
    # (a repeated label declares one physical site spanning two clusters — V5) and str.
    # NOTE: __post_init__ does NOT require every dense index to carry records — a Cohort
    # with trailing empty sites is a legitimate state (how the record-carrying cluster
    # gate is exercised; see test_pipeline). Density-with-every-index-present remains a
    # make_cohort INPUT rule. This keeps the carrying gate real on the direct path (V12).

def coerce_labels(raw, positive_label, allow_absent_positive=False) -> np.ndarray[bool]
    # explicit two-value map; raises CohortError on any value outside {positive, the one other
    # observed value}, on NaN, and on missing values. Never guesses. (audit F05/F35/F37)
    # allow_absent_positive (opt-in; wired from from_raw require_both_classes=False, TARGET
    # pools ONLY): when the positive label is ABSENT *and* exactly one other value is observed,
    # return all-False instead of raising -- a legitimately all-negative target pool at ~9.5%
    # prevalence (the same relaxation make_cohort's require_both_classes grants). The strict
    # default stays strict (typo protection); >1 distinct observed value, NaN, and None still
    # raise even when opted in.

def densify_sites(raw_site_ids) -> tuple[np.ndarray, tuple[str, ...]]
    # canonical order = np.unique over CANONICALIZED id forms; returns dense ids + labels
    # (audit F39; hardened by audit V4/V10 — site identity is the unit of statistical
    # independence, so cosmetic noise in the site column must never fabricate clusters):
    #  - REJECT (CohortError) None, float NaN, empty/whitespace-only string ids, and float
    #    ids at or beyond 2**53 (integer resolution lost — a lossy label must never be
    #    emitted silently; verification F3) — missing or ambiguous site identity must never
    #    become a bona fide pseudo-cluster (V10);
    #  - canonical form (verification F1: Unicode-hardened): NFKC-normalize, delete every
    #    format-category (Cf) character (ZWSP/BOM/soft-hyphen/ZWJ/LRM/word-joiner — the
    #    invisible-suffix channel that silently split sites), THEN strip surrounding
    #    whitespace; integral numeric ids (int, or float with integral value below 2**53)
    #    map to the integer string, so 0 and 0.0 collide as one site (the pandas
    #    float-dtype column case);
    #  - COLLISION CHECK (V4): normalize each canonical label further (casefold + numeric-
    #    lexeme collapse using EXACT integer arithmetic for integer lexemes — float64
    #    round-tripping falsely collided distinct 18+-digit surrogate keys, verification
    #    N4); if two DISTINCT canonical labels share a normalized form ('H1' vs 'h1 ',
    #    '1' vs '1.0' as strings), raise CohortError naming the colliding ids — the caller's
    #    site column is dirty and the code never guesses which merge was intended. Loud,
    #    because the cluster count feeds MIN_CAL_CLUSTERS and the WSR effective n.
    # The same normal form governs CROSS-cohort identity (verification F2): dirt that is
    # loud inside one cohort must not slip between cohorts.

def make_cohort(x, y, site_id, site_labels=None, expect_features=None,
                require_both_classes=True) -> Cohort
    # loud checks, in order: length alignment; x 2D float64-convertible & np.isfinite all;
    # y bool dtype (else "use coerce_labels") AND 1-D (audit V17 — an (n,1) bool column must
    # be a typed CohortError at the boundary, not a broadcast MemoryError downstream);
    # site_id integer AND 1-D, >=0, dense with every index 0..max present (else "use
    # densify_sites"); site_labels UNIQUE (audit V5 — a repeated label is the caller
    # declaring two dense clusters are one physical site; the library must refuse, not
    # silently hold the declaration and ignore it); expect_features match; both classes present.
    # require_both_classes=False exempts the both-classes check ONLY: fitting cohorts
    # (train/aux/cal) keep the strict default because single-class data breaks the head fit
    # and BBSE site stats; a TARGET POOL may legitimately be all-negative at ~9.5%
    # prevalence (small single-site pools) and must flow through, not crash — its labels
    # are oracle/harness-only and never fitted on.

def from_raw(x, y_raw, positive_label, site_ids_raw, *, require_both_classes=True) -> Cohort
    # coerce + densify + make. require_both_classes passes through to make_cohort AND opts
    # coerce_labels into allow_absent_positive (= not require_both_classes): the sole sanctioned
    # path for an all-negative TARGET pool to flow in from raw inputs. Fitting cohorts keep the
    # strict default (single-class data breaks the head fit / BBSE site stats); a target pool
    # may legitimately be all-negative and must flow through, not crash.

def assert_site_disjoint(**named) -> None
    # pairwise-disjoint site_labels across named cohorts, compared under the SAME
    # canonical+normalized form densify_sites uses (verification F2 — raw string equality
    # let a case-variant respelling of S_cal pass as S_aux, voiding the walk order's
    # S_cal-independence); raises CohortError naming the RAW overlapping labels
    # (audit F03 — this is the assertion v1 promised and never had)
```

## `data.py` — simplified generator (port v1 semantics; drop covariate/missingness/policy paths)

```python
@dataclass SimConfig: d=8; sep=2.2; base_rate=0.095; s_u=0.5;
                      size_mu=6.0; size_sigma=1.1; size_lo=20; size_hi=5000
# direction v = normalized ones on first d//2 dims; mu_y = (+/- sep/2) * v
# site: n_c ~ clipped LogNormal(size_mu, size_sigma); u_c ~ N(0, s_u^2);
#       pi_c = sigmoid(logit(base) + u_c)

def draw_cohort(cfg, n_sites, rng, *, label_base_rate=None, concept_intercept=0.0,
                concept_slope=None, site_label_prefix="s",
                require_both_classes=True) -> Cohort
    # require_both_classes passes through to make_cohort; experiments drawing single-site
    # TARGET pools set it False (an all-negative target batch is a legitimate scenario).
    # label-shift path (class-conditional, exact) when no concept tilt;
    # marginal-then-posterior path for concept tilt (v1 generator.py:130-159 semantics);
    # label_base_rate composing with concept tilt raises ValueError (unidentifiable regime).
    # site_labels = f"{prefix}-{i:04d}" -> guarantees disjointness across prefixes.

def split_sites(cohort, rng) -> (train, aux, cal)   # SPLIT_FRACTIONS by site count, disjoint
def subset_sites(cohort, keep_dense_ids) -> Cohort  # renumbers densely, keeps labels
```

## `model.py`

```python
@dataclass Head: coef (d,); intercept: float; mu (d,); sd (d,)   # sd pre-guarded
    def logit(x): return intercept + ((x - mu) / sd) @ coef
    def predict_proba(x) -> p1;  predict(x) -> bool (p1 >= 0.5);  score(x) -> np.maximum(p1, 1-p1)

def fit_head(train: Cohort) -> Head
    # z-standardize with mu/sd from train; sd_safe = np.where(sd > SD_REL_TOL * np.maximum(1.0,
    # np.abs(mu)), sd, 1.0)   <- relative-tolerance guard (audit F06);
    # sklearn LogisticRegression(C=HEAD_C, max_iter=HEAD_MAX_ITER) on z.
```

## `certify.py` — port the audited v1 math with hardening

```python
def influence_atoms(score, err, site_id, n_sites, tau_grid, alpha, M, weights=None, wmax=1.0)
    # v1 testbed/certify.py:16-49 math verbatim (neutral atoms Z=alpha for empty sites) PLUS:
    # raise ValueError if weights is not None and (not np.isfinite(weights).all()
    # or min<0 or max>wmax+1e-12)          <- NaN bypass closed (audit F08)
    # raise ValueError if not np.isfinite(score).all()  <- NaN scores loud (audit F36)

def wsr_reject(z, alpha, delta, rng) -> bool          # v1 constants exactly (WSR_* above)
def margin_floor(n, delta, alpha) -> float            # ln(1/delta) * (1-alpha) / n
def walk_order(atoms_aux) -> np.ndarray               # argsort of mean atom (ascending)
def fixed_sequence_walk(atoms, order, alpha, delta, tau_grid, rng) -> (list[int], int|None)
    # deployed = maximum-coverage = LOWEST tau in the certified prefix. This names no
    # pool and needs none: {x : s(x) >= tau} is nested and decreasing in tau, so the
    # lowest certified tau maximises coverage on EVERY pool at once (panel item S2-2).
    # Three-level deployment rule, stated here once because the paper asserts it:
    #   within a mode  -> lowest certified tau      (this function)
    #   across modes   -> LARGEST of the modes' own deployed taus  (report._combine_alpha)
    #   across rungs   -> strictest certified alpha (report.build_report, ladder order)
    # The first two do not conflict: max-coverage inside each mode, most-conservative
    # between them, so the deployed tau is never laxer than a certifying mode alone.
    # Reported coverage is a DIFFERENT quantity, measured on the target pool after
    # tau* is fixed (report.build_report: (score_t >= tau).mean()).

def certification_rng(alpha, mode_idx, stream="") -> np.random.Generator
    # sha256 ONLY (audit B-10): h = sha256(str(stream).encode()).digest();
    # SeedSequence([SEED, ALPHA_LADDER.index(alpha), mode_idx,
    #               int.from_bytes(h[:4]), int.from_bytes(h[4:8])])
    # No int() fast path exists -> no numeric aliasing, no OverflowError (audit F43/F57).
    # The TARGET LABEL is NOT part of the seed (audit V3): baseline atoms are
    # target-independent, so seeding the permutation from the target label gave every
    # target a separately-randomized test of identical calibration data — the deployed
    # threshold moved with the spelling of a free-text identifier, and the printed
    # shared-1-delta-event clause was false. `stream` distinguishes only the BBSE
    # endpoint walks ("lo" / "hi"); baseline passes the default "". One calibration
    # draw now yields literally one shared event across all target pools (baseline mode).
```

## `shift.py` — BBSE with the three declines

```python
@dataclass BBSEFit: declined: bool; reason: str; rho_lo, rho_hi, rho_point: float;
                    diagnostics: dict; walk_orders: dict[float, np.ndarray]

# DIAGNOSTICS KEY STABILITY (fixture audit 2026-07-25 — audit-V25's stable-key
# discipline extended to the bbse sub-dict): EVERY BBSEFit.diagnostics — full
# fit, every decline path, and pipeline's not-run placeholder — carries the
# SAME 17-key set {n_target, n_target_sites, min_target_sites, q_target, q_ci,
# c0, c1, pi_s, c0_ci, c1_ci, pi_s_ci, gap_lo, n_boot, n_attempts, rho_lo,
# rho_hi, rho_point}, with None for whatever that branch did not compute — a
# consumer indexing any key gets None, never KeyError. Constructed only via
# the bbse_diagnostics(**known) helper, which rejects unknown keys loudly.

def bbse_diagnostics(**known) -> dict     # stable-key template; unknown keys raise

def fit_bbse(head, aux: Cohort, target_x, rng, target_site_id=None) -> BBSEFit
    # per-site stats (n, pos, pred1&pos, pred1&neg) via bincount weights (y bool guaranteed).
    # point (c0, c1, pi_s) from pooled aux. Bootstrap: loop drawing site-index resamples;
    # a resample is VALID iff pooled pos>=1 and neg>=1; collect until BBSE_BOOT valid or
    # BBSE_BOOT_MAX_ATTEMPTS total -> declined, reason="bbse-degenerate-bootstrap"
    # (never quantile over a reduced count — audit F40/B-8). diagnostics records n_attempts.
    #
    # q_t (audit V2 — THE V2 LESSON: q_t is a noisy ESTIMATE of the target population
    # predicted-positive rate, not an observed constant; treating it as exact issued false
    # certificates at up to 3x delta under pure label shift, attributable to q_t sampling
    # error by control). Empty target pool -> decline "bbse-empty-target" immediately (V14).
    # q_t gets its own confidence share at level (BBSE_DELTA_CONF / BBSE_BONFERRONI):
    #  - target_site_id is None or names ONE site: exact two-sided Clopper-Pearson on
    #    k = predict(target_x).sum() (finite-sample; valid for records iid within one site).
    #    None is the caller DECLARING the pool is a single site — a multi-site pool with
    #    unknown clustering under-covers here and MUST supply target_site_id.
    #  - 2 <= K < BBSE_MIN_TARGET_SITES sites: decline "bbse-target-clustering"
    #    (verification F1 — a percentile bootstrap over so few clusters cannot approach
    #    nominal coverage: measured rho-miss up to 46% at K=2 and 10% at K=3 against a
    #    nominal 2.5%, producing certify-and-violate at 3.4x delta where the bet has power).
    #  - K >= BBSE_MIN_TARGET_SITES: cluster bootstrap over target sites (BBSE_BOOT
    #    resamples, percentile interval; asymptotic like the S_aux box) — q needs no
    #    validity constraint, every resample counts.
    # Box: per-parameter percentiles at level (BBSE_DELTA_CONF / BBSE_BONFERRONI) over
    # FOUR parameters (c0, c1, pi_source, q_target); joint miscoverage <= BBSE_DELTA_CONF
    # by Bonferroni.
    # Decline order: bbse-empty-target -> bbse-target-clustering -> degenerate-bootstrap
    # -> "bbse-ill-conditioned"
    # if lo_c1 - hi_c0 < BBSE_GAP_FLOOR -> "bbse-misspecified" unless the WHOLE q interval
    # sits inside the box range: (lo_c0 <= q_lo and q_hi <= hi_c1) (audit F41/B-9, widened
    # by V2; the `not (...)` form is NaN-safe — a NaN q declines instead of flowing through).
    # Then rho interval = min/max over the 16 corners of rho(c0,c1,pi_s; q) for
    # q in {q_lo, q_hi} x the 8 (c0,c1,pi_s) corners, with pi_t clipped to
    # [PI_CLIP, 1-PI_CLIP]. Corner coverage of the box interior: pi_t=(q-c0)/(c1-c0) is
    # monotone in each of q, c0, c1 on the gated region (c1-c0 >= BBSE_GAP_FLOOR > 0), rho
    # is monotone in pi_t and pi_s, and the clip preserves monotonicity, so extremes over
    # the 4-D box are attained at corners. The clip's effect (verification F2-bbse,
    # precision): coverage of the unclipped odds ratio holds whenever the true pi_t lies in
    # [PI_CLIP, 1-PI_CLIP]; outside that range the exposure is bounded at the PI_CLIP odds
    # scale (~1e-4 shift in an affine-in-rho statistic — no realistic certificate moves).
    # walk_orders per alpha from aux atoms weighted
    # w=(1 if ~y else rho_point), wmax=max(1, rho_point).
    # diagnostics additionally records q_ci, n_target, n_target_sites.

def certify_bbse(head, fit, cal: Cohort, alpha) -> dict   # target_label removed (audit V3)
    # decline passthrough; else dual-endpoint walk at BBSE_DELTA_BET: per threshold, reject
    # must hold at BOTH rho_lo and rho_hi atom sets. Soundness (R1, REDTEAM.md): under the
    # per-endpoint normalization wmax=max(1,rho) the atom mean is PIECEWISE in rho (kink at
    # rho=1; an interior max is possible), but the statistic is scale-invariant, so
    # sign(E[Z]-alpha) = sign(A + rho*B) with (A,B) rho-free — affine in rho. Hence
    # {rho: E[Z] <= alpha} is convex: both endpoints certifying covers every interior rho,
    # and any violating rho in the box forces a violating endpoint whose level-delta_bet
    # test controls false certification — pinned by tests incl. an interval straddling
    # rho=1 on the production wmax path.
    # Endpoint rngs: certification_rng(alpha, MODE_BBSE, "lo") and "hi" (deterministic,
    # order-independent, target-label-free — audit V3; the fit itself remains legitimately
    # target-dependent through the q_t interval, which is why the shared-event clause is
    # claimed for baseline mode only).
    # Result dict: alpha, tau, tau_idx, certified(list), reason(None|str), n_cal,
    # n_cal_carrying, diagnostics.
```

## `explain.py`

```python
def global_importance(head) -> np.ndarray          # standardized coefs = head.coef (already std-space)
def local_attribution(head, x_row) -> dict(base, phi, logit, p1)
    # phi_j = coef_j * z_j: exact INTERVENTIONAL Shapley values for the linear head with
    # the S_train-mean baseline (Linear SHAP; audit V20). The value function and baseline
    # MUST be named wherever exactness is claimed: under correlated features the
    # CONDITIONAL Shapley values differ, and the efficiency identity
    # sum(phi)+base == logit does not distinguish the two (both satisfy it).
def abstention_explanation(head, x_row, tau_star) -> dict
    # answering requires |logit| >= logit(tau_star/(1-tau_star))... define L* = np.log(tau_star/(1-tau_star));
    # margin_to_answer = L* - abs(logit(x)); >0 iff declined; signed contributions toward/away from confidence.
def cohort_abstention_profile(head, x, answered_mask) -> dict
    # mean |phi_j| answered vs declined + gap ranking. When EITHER population is empty the
    # gap is undefined: gap_ranking is an EMPTY array, never argsort of all-NaN (which
    # returns the identity permutation and fabricates feature 0 as top driver — audit V22).
def counterfactual_to_answer(head, x_row, tau_star) -> dict
    # Minimal counterfactuals into the answer region (2026-07-31; the contrastive
    # form the reject-explanation literature is ahead on — R3-15/R3-16). The head is
    # linear in z = (x-mu)/sd, so the smallest standardized-L2 move that makes a declined
    # case answerable on its current side (s = sign(logit), tie at 0 -> +1; s is also
    # returned as `direction`) is closed-form:
    #   delta_z* = s*m*coef/||coef||^2, distance m/||coef||_2, m = max(L* - |logit|, 0);
    # the single-feature counterfactual is delta_z_j = s*m/coef_j (raw delta_x_j =
    # sd_j*delta_z_j), +/-inf where coef_j == 0, ranked ascending |delta_z_j| over the
    # finite entries. The REPORTED distances (l2_distance_z, single_feature_delta_*)
    # are these exact real-arithmetic minima. The RETURNED delta vectors carry an
    # additional _EPS_ANSWER_LOGIT = 1e-9 of logit-space headroom (i.e. they are
    # computed from m + 1e-9), because a delta that lands EXACTLY on |logit| = L* is
    # DECLINED by the deployed float64 answering rule head.score(x) >= tau on a
    # measurable fraction of cases: sigmoid(log(tau/(1-tau))) < tau in float64 for 6 of
    # the 23 frozen TAU_GRID thresholds (each by 1 ULP), summation-order noise between
    # the attribution sum and Head.logit's BLAS dot reaches ~3e-14, and the raw-space
    # round trip adds ~1e-12 — an exact landing failed the deployed rule on 18.2% of
    # the fixture head's declined cases (adversarial verification 2026-07-31). The
    # 1e-9 headroom dominates every measured shortfall while moving the realized
    # confidence by < 3e-10. flip_verified re-evaluates THE DEPLOYED RULE
    # head.score(x + delta_x_min_l2) >= tau_star with NO tolerance — the exact
    # comparison pipeline.py answers with; a permissive |logit|-with-tolerance check
    # is exactly what let the boundary defect through. confidence_at_flip is the
    # REALIZED head.score at the flipped point (>= tau_star, within ~3e-10 above it:
    # still the weakest answerable answer, and saying so is part of the artifact's
    # honesty) and answered_class_on_flip the current side's predicted class; BOTH are
    # None unless (declined and flip_verified). opposite_side_distance_z =
    # (L* + |logit|)/||coef|| (formula pinned by test) is reported so the same-side
    # minimum is visibly minimal (crossing sides answers as the OTHER class).
    # Answered cases return zero deltas, distance 0, and an EMPTY ranking — never the
    # argsort-of-degenerate identity permutation (audit V22 pattern); an all-zero head
    # (coef == 0) cannot flip: distance inf, flip_verified False, empty ranking.
    # These are SCORE-SPACE recourse statements about the gate, never causal or
    # clinically achievable actions: features are not independently manipulable (a
    # __missing indicator cannot "move 0.4"), and the artifact answers "what would the
    # gate need", not "what should the clinician do". That caveat travels with the
    # artifact wherever it is displayed.
def composition(head, target_x, answered_mask, rho_point=None, oracle_y=None) -> dict
    # three tagged objects (audit F25): predicted-class (estimated);
    # BBSE-implied true-class from (c0,c1,q) inversion if rho given (estimated, tagged);
    # oracle (diagnostic) if oracle_y given.
    # build_report supplies rho_point whenever the BBSE fit did NOT decline, regardless of
    # which mode won deployment (verification N5): the BBSE-implied view is an estimated/
    # diagnostic quantity, not part of the certificate, and gating it on deploy_mode=="bbse"
    # silently degraded the documented three-way composition to two-way everywhere BBSE
    # declines-but-fits or loses the OR-combination.
```

## `harness.py` (validation instrumentation — labels say exactly what is computed; audit F29 lesson)

```python
def wilson_lcb(k, n, level=0.95) -> float          # one-sided lower bound on binomial p
def hard_violation(err_answered: np.ndarray, alpha) -> bool   # wilson_lcb(sum, len) > alpha
def exceedance_reference(n_answered, alpha) -> float   # binomial P(rate > alpha) at boundary p=alpha
SIZE_BINS = ((0,30), (30,100), (100,300), (300, np.inf))
```

## `report.py`

```python
def provenance(**arrays_and_meta) -> dict
    # package versions (importlib.metadata: numpy, scipy, scikit-learn), python version,
    # SEED, sha256 content hash of each input array, UTC timestamp (audit F49).
    # CONTENT BINDING (audit V11): the digest of every ndarray covers dtype.str + shape +
    # raw bytes (a reshaped/transposed matrix must not be provenance-identical), and the
    # pipeline passes EVERY array the certificate depends on: the three cohorts' x, y AND
    # site_id, plus target_x (and, when supplied, the dense target_site_id AND its
    # canonical labels — two different labelings share the same dense array) — flipping one
    # calibration label must change the recorded hashes. The RUN CONFIGURATION binds too
    # (verification N8): modes and alphas go into provenance meta, since two runs whose
    # certified tiers differ must never share a byte-identical reproducibility record.
    # The BBSE bootstrap seed (pipeline._bbse_seed_rng) derives from sha256 of the TARGET
    # DATA (dtype + shape + bytes of target_x, plus the dense target site partition when
    # supplied), NEVER from the free-text target label (verification G-2 — label-seeding
    # moved the deployed threshold and 2.3% of answered records under a cosmetic
    # respelling of byte-identical data). Byte-identical pools get byte-identical fits;
    # distinct pools get distinct streams.
def build_report(...) -> dict   # tiers: certified rows per alpha (status/tau/modes/statement/
    # mode_outcomes — a per-mode outcome map {mode: 'covering' | 'certified-not-covering' |
    # <decline reason>} present on CERTIFIED rows too, so a certified row still records why
    # the non-deploying mode did not contribute; on real data BBSE silently not contributing
    # is the interesting signal — fixture audit 2026-07-25),
    # estimated (deploy-mode-weighted cluster-bootstrap risk CI — v1 report.py:14-35 pattern,
    # labeled with its weighting; top-up-or-decline resampling per audit F40/B-8 — never
    # quantile over a silently reduced draw count — and NaN, never 0.0, for an empty
    # answered set (audit V21)), diagnostic (coverage, feasibility margin/floor AT TRUE
    # n_cal_carrying per rung (audit F51; margin/ratio are None — JSON null — when no
    # threshold attains coverage, never -inf (audit V16)), capped-influence record share +
    # R_M-vs-unweighted-risk gap (audit F26), composition, abstention profile), decline
    # partition {answered, below_tau, failsafe | pool-too-small | insufficient-clusters}
    # summing exactly to n_target. GATED EXITS emit the SAME diagnostic key set as full
    # reports, with None for what is uncomputable without a head (audit V25);
    # capped_influence_share IS computable there and is computed.
    # GUARANTEE TEXT (audit F01/F02 lessons, corrected by audit V1/V3/V13/V27 and
    # verification G-1/G-3/G-7 — these clauses are verbatim requirements and
    # tests/test_report.py freezes the exact string PER MODE COMBINATION):
    #  - the certified estimand is MODE-DEPENDENT (G-1 — naming the calibration-population
    #    unweighted risk on a BBSE row emitted a demonstrably false certificate under a
    #    downward prevalence shift): under exchangeability, the M-influence-weighted
    #    answered-set risk averaged over the site population from which the calibration
    #    sites were drawn, probability over the calibration draw; under label shift, the
    #    SAME population risk REWEIGHTED to the target class prevalence identified by the
    #    BBSE correction, probability over the JOINT draw of the calibration sites, the
    #    auxiliary split and the target pool (G-3). Never "at this target site" (V1).
    #  - MANDATORY dispersion clause (V1), with the same force as the binomial clause:
    #    the bound is a site-population average and does NOT bound any individual site's
    #    answered error rate; under between-site heterogeneity the fraction of sites
    #    exceeding alpha is governed by that dispersion, which the certificate neither
    #    measures nor bounds
    #  - not a bound on this batch's realized error count (unchanged)
    #  - baseline-only (V3, narrowed by G-7): the CERTIFIED THRESHOLDS are a function of
    #    the calibration draw alone — one shared 1-delta event across all target pools
    #    (the report object as a whole is target-dependent through coverage/diagnostics;
    #    the clause claims only the thresholds). OMITTED whenever BBSE covers the row (the
    #    fit depends on the target pool through q_t — no shared event exists)
    #  - operative-rung selection clause (V27): the operative rung is the strictest
    #    certified alpha, a data-driven selection over the two-rung ladder; the selected
    #    claim holds jointly at probability >= 1 - 2*DELTA = 0.90
    #  - "under the tagged assumption (exchangeability | label shift)"; concept/combined shift
    #    OUT OF SCOPE and undetectable from unlabeled data — certificate void there
    #  - BBSE rows add (V2/V13 — the old "single non-finite-sample step" claim was false
    #    while q_t was unbudgeted): the [rho_lo, rho_hi] box covers FOUR estimated
    #    parameters (c0, c1, pi_source, q_target) at Bonferroni delta_conf; the
    #    (c0, c1, pi_source) intervals are percentile cluster bootstraps over S_aux —
    #    asymptotic, with realized joint coverage at small cluster counts measurably below
    #    nominal (METHODS reports the measured value); the q_target interval is
    #    finite-sample Clopper-Pearson for single-site pools (cluster bootstrap for
    #    multi-site pools); delta_conf is spent on these boxes, not on the calibration draw
def render_text(report) -> str   # surfaces n_boot alongside the estimated-tier CI (V21)
```

## `pipeline.py`

```python
def run_certgate(train, aux, cal, target_x, *, target_label="target",
                 target_site_id=None, alphas=ALPHA_LADDER, oracle_target_y=None,
                 modes=("baseline","bbse")) -> dict
    # 0. loud boundary validation (audit V18/V19/V23):
    #    - modes: non-empty subset of ("baseline","bbse"), else ValueError — a misspelled
    #      mode must never yield an all-declined report indistinguishable from a
    #      statistical decline;
    #    - train/aux/cal each contain both classes (CohortError otherwise) — the
    #      require_both_classes=False relaxation is sanctioned for TARGET pools only and
    #      this is where roles are known;
    #    - target_x must be a feature MATRIX, not a Cohort (the natural mistake —
    #      the other three positional args ARE Cohorts): typed ValueError
    #      "(reason=target-is-cohort)" telling the caller to pass target.x; any
    #      other non-numeric target_x raises "(reason=target-not-numeric)" —
    #      never a raw numpy float()-conversion TypeError (fixture audit
    #      2026-07-25);
    #    - oracle_target_y, when supplied: 1-D, bool dtype, length == n_target, else
    #      ValueError — never np.asarray-coerced (a float probability array silently
    #      became an all-True composition).
    # 1. assert_site_disjoint(train=train, aux=aux, cal=cal)      (audit F03)
    # 1b. TARGET disjointness (audit V9; hardened by verification F2/F4/N3): target_site_id,
    #    when supplied, must be 1-D and length-aligned with target_x (typed error at the
    #    boundary, BEFORE any densify/fit — the only alignment check previously lived inside
    #    fit_bbse and fired on the BBSE path only). The canonical+normalized form of
    #    str(target_label) must not match any cohort site label under the SAME normal form
    #    densify_sites uses (raw equality let 's-0000 ' and case variants slip); when
    #    target_site_id is supplied its normalized labels are likewise asserted disjoint
    #    from all three cohorts. The diagnostic tier records target_site_id_supplied so a
    #    report whose record-level target identity was never checked is distinguishable.
    #    A target whose own records sit in S_cal gets a threshold selected partly on
    #    itself — the exact leak F03 exists to prevent, on the one split F03 did not cover.
    # 2. np.isfinite(target_x).all() or raise                     (audit F36)
    # 2b. feature-column alignment: target_x is 2-D AND target_x.shape[1] == train.d; aux.d
    #    and cal.d also == train.d (all scored by the head fit on train). Loud ValueError
    #    "(reason=feature-width-mismatch)", else a mismatch surfaces only as a raw numpy
    #    broadcast error inside head.score. (real-data column alignment)
    # 3. carrying = (cal.site_sizes > 0).sum(); if carrying < MIN_CAL_CLUSTERS ->
    #    report reason "insufficient-clusters" (record-carrying count — audit B-5)
    # 4. if len(target_x) < MIN_ANSWERABLE -> report reason "pool-too-small" (audit B-6)
    # 5. fit_head(train); aux atoms -> walk_order + feasibility (margin, floor@n_carrying,
    #    ratio) per alpha — the feasibility dict is keyed by str(alpha) ("0.05"/"0.1"),
    #    not float, so a saved report JSON-round-trips without key-type drift (fixture
    #    audit 2026-07-25); fit_bbse once (passing the densified target_site_id for the
    #    q_t interval — audit V2)
    # 6. per alpha: baseline walk (certification_rng(alpha, MODE_BASELINE) — target-label-
    #    free, audit V3); bbse dual-endpoint walk; OR-rule: deployed = max tau among
    #    certifying modes; a mode is listed only if it certified the deployed tau_idx
    #    (v1 M1, native here)
    # 7. operative rung = strictest certified alpha; answered = score >= tau*;
    #    decline partition; explain artifacts; build_report with provenance
```

## Tests (`tests/`) — suite must run < ~3 min

The 2026-07-25 audit (V6) demonstrated that 14 of 14 load-bearing mutations outside the
betting statistic survived the then-69-test suite. The suite now also pins the accounting,
the data discipline, the guarantee text, and the harness — the specific killers are listed
per file below; regressions to any of them are regressions to V6.

- `test_constants.py` — literal equality for EVERY constant above (tuples compared to literal
  tuples; TAU_GRID: len==23, first==0.55, last==0.99). This is audit F13's fix, native.
  ALSO pins (audit V7 lesson — undeclared generator parameters): the experiment-grid
  constants in `experiments/run_synthetic.py` (SHIFT_BASE, CONCEPT_INTERCEPT, ANCHOR_SITES,
  E1_SU_SWEEP, QUICK_SWEEP, FULL_SWEEP, E2_SHIFT_SWEEP, E7_RECORD_SAMPLE, E7_SU_ARM), the
  ABSENCE of any experiment-local `sep` override
  (no SHIFT_SEP attribute — every experiment runs the documented SimConfig generator), and
  the SimConfig generator defaults (d=8, sep=2.2, base_rate=0.095, s_u=0.5).
- `test_harness.py` — (audit V6 #6/#7: harness.py computes every violation number in the
  paper and had zero tests) `wilson_lcb` against the closed form and monotonicity in k;
  `hard_violation` boundary cases including the empty answered set; `exceedance_reference`
  against brute-force binomial enumeration including integer-boundary alpha*n.
- `test_validate.py` — each loud rejection: NaN x; float y; {1,2} labels rejected by make_cohort
  but mapped by coerce_labels(pos=2); NaN in raw labels raises; gappy site ids rejected +
  densify_sites round-trip; length mismatch; disjointness assert catches an overlap and
  passes on disjoint; site_sizes always equals bincount.
- `test_certify.py` — atom range [0,1] with empty-site neutral atoms == alpha; the v1 Hole-1
  regression (140 clean + 10 heavy/20%-error sites: truncated-contribution reading certifies,
  influence weighting refuses — port from ../tests/test_certify.py); the M-cap boundedness
  killer (audit V6 #1): with site sizes spanning ~20..3000 against M=100, atoms stay in
  [0,1] — removing np.minimum(sizes, M) drives atoms negative and breaks the [0,1]
  boundedness Ville's inequality requires, and this test fails; WSR boundary type-I at
  (n=80, 800 reps, fixed seed) <= 0.08 and power > 0.9 under a clear margin; walk stops at
  first failure; NaN weight raises; NaN score raises; certification_rng: identical streams
  for repeated calls, distinct streams across alphas / mode indices / "lo" vs "hi",
  and NO dependence on any target identifier (audit V3).
- `test_shift.py` — pure label shift (base 0.095 -> 0.22): rho interval covers true rho and
  certify_bbse certifies-or-declines but the *baseline* walk certifies-and-violates
  (falsifiability first — verify the shift moves answered risk above alpha before counting);
  degenerate 3-site pool -> "bbse-degenerate-bootstrap"; weak head -> "bbse-ill-conditioned";
  q_t forced outside box -> "bbse-misspecified"; linearity: statistic affine in rho at fixed
  wmax to ~1e-12; dual-endpoint soundness on the production wmax=max(1,rho) path across an
  interval straddling rho=1 ((mean-alpha)*max(1,rho) affine; raw atom mean visibly kinked).
  The certify_bbse dual-endpoint LOOP is pinned directly (REVIEW-FABLE B-1): with one endpoint
  favorable and the other poisonous the walk must decline in BOTH orientations (catches a
  single-endpoint regression on either side), while collapsing the interval onto the favorable
  endpoint certifies (power check -- the decline is attributable to the other endpoint);
  the loop fixture supplies a MULTI-element walk order so break-vs-continue is
  distinguishable (V6 #8). Audit-V2 additions: empty target pool -> "bbse-empty-target";
  the q-interval->rho propagation regression — with the (c0, c1, pi_s) box held degenerate
  at truth, >= 400 simulated pools' Clopper-Pearson q intervals propagated through the
  16-corner rho interval miss rho_true at most at the nominal per-parameter level + MC
  tolerance (fails against the old point-q_t code, whose miss rate is ~10x nominal);
  the certified-BBSE row in the pure-label-shift test asserts NO certify-and-violate on
  the fixture draw (replacing the assertion V6 found vacuous). Stable-diagnostics killer
  (fixture audit 2026-07-25): full fit, empty-target and target-clustering declines all
  emit bbse_diagnostics()'s exact key set.
- `test_explain.py` — sum(phi) + base == logit to 1e-10; abstention margin > 0 iff declined;
  composition three objects present with correct tags; counterfactual_to_answer: the
  minimal-L2 and top single-feature deltas FLIP the case under the DEPLOYED rule
  head.score(x_cf) >= tau (no tolerance) — including at the float64-hostile grid
  thresholds 0.63 and 0.93 where sigmoid(L*) < tau, the regression for the 2026-07-31
  boundary finding — while (1 - 1e-4) of either delta still declines under the same
  rule; no standardized move of norm below the reported exact minimum flips in ANY
  direction (Cauchy–Schwarz, checked over random directions); the delta's norm exceeds
  the reported exact minimum by exactly the documented headroom; coef_j == 0 gives inf
  and is excluded from the ranking; answered cases return zero deltas, an EMPTY ranking
  and None flip fields; the all-zero head reports distance inf with flip_verified
  False; opposite_side_distance_z equals (L* + |logit|)/||coef|| to 1e-12 (formula
  pinned, not just the ordering).
- `test_report.py` — unit-pins `_combine_alpha`'s OR-rule delta accounting (REVIEW-FABLE A-1)
  against DIVERGENT mode results: deploy = max tau across modes' own deployed thresholds; a
  mode appears in `modes` ONLY if the deployed tau_idx is in its own certified list (subset-
  prefix -> both covered; declined-with-None -> excluded; disjoint-prefix -> deploy mode alone
  even though the other mode certified something); no certifying mode -> status "declined"
  with per-mode reasons. mode_outcomes is pinned against the SAME divergent fixtures
  (covering / certified-not-covering / decline-reason passthrough — fixture audit 2026-07-25).
- `test_fixture_integration.py` — the HOSTILE-EXTRACT fixture (fixture audit 2026-07-25):
  `experiments/synth_fixture.py` (10-table gzip-CSV corpus with every documented wart:
  signed-minute offsets, '> 89' ordinal trap, per-column text booleans, NOT-NULL-empty
  fields, heavy-tailed sessions-per-site, exact+near duplicates, embedded newlines;
  `--signal` plants a latent severity z driving entry metrics / attr_band / measurement
  values AND close_state at ~9% prevalence with u_site ~ N(0, 0.5^2)) feeds
  `experiments/fixture_etl.py` (hostile CSV -> finite float64 features + raw site labels)
  into `from_raw` -> `run_certgate`. Always-on smoke (~seconds, small scale): the pipeline
  reaches an HONEST outcome — certified-with-valid-oracle or declined — with the partition
  summing and the report rendering. Full-scale arm (20800 sessions / 208 heavy-tailed
  sites) is gated behind CERTGATE_FIXTURE=1 so the default suite stays fast. The fixture
  generator is byte-deterministic (gzip mtime=0; per-(table,session) RNG streams make
  --tables a byte-identical projection).
- `test_realdata_path.py` — first end-to-end exercise of the RAW loader: draw synthetic sites,
  DE-STRUCTURE to raw string/int labels + raw string site ids, rebuild each split through
  `from_raw`, assert per-record (y, site-label) equivalence + site-disjointness, then
  `run_certgate` to a certified rung (alpha=0.10) with the partition summing to n_target.
  Covers the {1,2}/positive_label=2 int variant, the wrong-width target hitting the GAP-1
  `feature-width-mismatch` gate, and the all-negative TARGET pool flowing via
  `from_raw(..., require_both_classes=False)`. Unit tests pin coerce_labels' opt-in:
  strict default still raises on absent positive; opt-in returns all-False on a single observed
  value; opt-in still raises on >1 distinct value and on NaN.
- `test_pipeline.py` — end-to-end at 208 sites in-dist: alpha=0.10 certifies with coverage
  > 0.5, report partition sums to n; overlapping cal/train raises CohortError; two identical
  runs -> byte-identical certified tiers (determinism); cal with 45 carrying + 20 empty sites
  -> "insufficient-clusters" (gate counts carrying only); 5-record target -> "pool-too-small";
  provenance block present with all keys (x, y, site_id for all three cohorts + target)
  AND content-bound: flipping one calibration label changes the recorded hashes (V6 #9/V11).
  Audit-V6 killers: TARGET-LABEL INVARIANCE — baseline-mode reports are byte-identical
  across target_label spellings (V3; fails on the old label-seeded permutation);
  DELTA-ACCOUNTING SPY — a recording wrapper around wsr_reject observes exactly {DELTA}
  spent on the baseline path and {BBSE_DELTA_BET} on the BBSE path (V6 #2/#3);
  WALK-ORDER PROVENANCE — the order handed to fixed_sequence_walk equals the S_aux-derived
  walk_order recomputed independently (V6 #5). Boundary killers: unknown/empty modes raise;
  single-class fitting cohort raises; malformed oracle_target_y raises; a target_label
  colliding with a calibration site raises (V9); GUARANTEE-TEXT FREEZE — the emitted
  statement for a known (alpha, modes) pair is compared as an EXACT string, so any silent
  weakening of a mandated clause fails (V6 #13/#14). Fixture-audit killers (2026-07-25):
  target_x passed as a Cohort raises "(reason=target-is-cohort)"; feasibility is keyed by
  str(alpha) and JSON-round-trips unchanged; diagnostic['bbse'] carries bbse_diagnostics()'s
  exact key set under both modes=("baseline","bbse") and modes=("baseline",).

## Experiments (`experiments/run_synthetic.py`)

**Companion: `experiments/panel_s2_tables.py`** (panel items S2-13, S2-28). Read-only analysis
producing `paper/draft.md` Tables 6 (influence-cap sensitivity) and 7 (answered/declined
operating characteristics), plus Section 3.3's cap arithmetic and the record-level-vs-`R_M`
gaps. CLI: `python -m experiments.panel_s2_tables [R]`; prints JSON, writes nothing into
`experiments/out/`. Reseeds every draw through the same rule `run_synthetic._rng` uses, so it
reproduces the grid's cohorts without re-running it, and self-checks against the released
`E1_validity.csv` (at M=100 it must reproduce every baseline-deploying draw's tau exactly —
currently 194/194, 0 mismatches). OPEN: not yet folded into `run_synthetic.py`'s CSV/summary
writers, so `python -m experiments.run_synthetic` alone does NOT regenerate Tables 6 and 7;
Appendix A.3's one-command claim covers Tables 1-4 and Figures 1-7 only until it does.

CLI: `python -m experiments.run_synthetic [--quick] [--only E1,E4] [--out experiments/out]`.
`--quick`: R=10 draws, sweep {60, 208, 400}. Full: R=200, sweep {60, 100, 150, 208, 300, 400}.

**One generator (audit V7).** EVERY experiment runs the documented `SimConfig()` defaults
(sep=2.2 etc.); experiment-local generator overrides are limited to the shift/tilt parameters
each experiment is *about* (`SHIFT_BASE`, `CONCEPT_INTERCEPT`) plus E1's declared `E1_SU_SWEEP`,
all pinned by `tests/test_constants.py`. A separation constant that silently differs between
experiments made two headline numbers non-reproducible from the stated setup — never again.

E1 validity (in-dist), rescored per audit V1: the CONFORMANCE metric is the aggregate one the
test actually certifies — per draw, the certified tau is applied to a fresh 200-site eval pool
and the influence-weighted answered risk R_M is computed on it; conformance = fraction of
draws with R_M > alpha (target <= DELTA). The single-fresh-site hard-violation rate
(harness.hard_violation) is RETAINED but relabeled a PER-SITE DISPERSION DIAGNOSTIC with no
delta target attached — under between-site heterogeneity it rises with s_u while the
certified aggregate stays within budget, which is exactly what E1's s_u sensitivity arm
(`E1_SU_SWEEP = (0.5, 1.0, 2.0)`) reports. Exceedance vs binomial reference by SIZE_BINS
unchanged. · E2 label shift (baseline fails / BBSE corrects-or-declines; targets are single-site
pools, so target_site_id stays None — the caller's declaration of a single site — and
the q_t interval takes its finite-sample Clopper-Pearson path). E2 additionally sweeps the
shift magnitude (panel S2-6/S2-7): `E2_SHIFT_SWEEP = (0.095, 0.13, 0.16, 0.19, 0.22)` at
R//2 draws per non-anchor magnitude on DISTINCT seed streams (`_rng(2, m, r)`), so the
0.22 anchor keeps its full-R `_rng(2, r)` stream and its published numbers byte-identical;
the 0.095 point is the null-shift arm (BBSE behaviour when nothing is wrong). CSV rows
carry `target_base`. E2 AND E3 are additionally rescored to the aggregate estimand the
way E1 was (draft-sync flag, 2026-07-30): each certified tau is scored against a fresh
`E1_EVAL_SITES`-site pool drawn under the SAME shift (label-shifted for E2, concept-tilted
for E3) — `rm_fresh`/`rm_exceed` columns beside the per-site Wilson diagnostic. The eval
pool is drawn AFTER each draw's pre-existing stream consumption, so every anchor number
stays byte-identical.
· E3 concept-shift negative control (tilt chosen + VERIFIED to push true answered risk > alpha
at certifiable coverage before counting violations; ENFORCED -- a tilt failing verification
aborts E3 loudly with reason=e3-control-not-poisonous rather than emitting violation rates)
· E4 site-count sweep (certify rate +
coverage per alpha rung vs n_sites) · E5 explainability case studies (JSON + one figure;
NaN-free payload, empty-population gap ranking emitted as null — audit V22). E5 adds a
REPLICATION arm (panel S1-4): R draws on the distinct stream `_rng(5, r)` (the single-draw
case-study stream `_rng(5)` is untouched, so its published numbers stay byte-identical);
per draw, the abstention profile is computed at that draw's deployed tau on its target
pool; the summary reports the pooled declined count, per-feature answered-vs-declined gap
means with normal 95% CIs over the gap-defined draws, and the top-gap-feature frequency.
A NULL RESULT — no stable single driver — is the expected outcome for the symmetric
generator (features 0-3 share one signal direction) and must be reported as such, never
dressed up. · E6 per-site fairness table + composition (multi-site target passes
target_site_id) · E7 record-as-unit comparator (panel S1-13): on its own draws
(`_rng(7, su_idx, r)`, arms `E7_SU_ARM = (0.5, 2.0)`), certify the SAME calibration data
two ways — (i) the site-unit walk, and (ii) a record-as-unit walk: influence_atoms over an
`E7_RECORD_SAMPLE = 2000`-record subsample of S_cal with per-record ids and M=1 (the plain
record-level betting certifier; walk order from an equal-size S_aux record subsample) —
then score BOTH at their deployed taus against the influence-weighted R_M of one shared
fresh 200-site pool. The record-unit certifier treats within-site-correlated records as
independent draws — the exact anti-conservatism the site-as-unit design exists to prevent;
the deliverable is certify rate + R_M-exceed rate per unit x rung x s_u arm.
Outputs: CSV per experiment + PNG figures (matplotlib, no seaborn) + a summary.md.
SERIALIZATION (panel S1-11/S2-24): every per-draw CSV carries `decline_reason`; E2 bbse
rows carry the fit diagnostics (rho_lo/rho_hi/rho_point/gap_lo/q_target/n_target_sites);
each run writes `out/provenance.json` (python + package versions, protocol seed, selected
experiments, run mode, UTC stamp) beside summary.md.
summary.md (audit V26): every experiment block records its own run mode, R, and a UTC
timestamp; sections preserved from an earlier run are visibly marked "(preserved)" in the
section header; the summary is written in a finally block so an aborted run cannot leave
fresh CSVs beside a silently stale summary. Everything seeded from constants.SEED; runs
deterministically; full grid target < ~45 min (E1's eval pools and s_u arm added ~50%).

## Real-data protocol (eICU-CRD v2.0) — `experiments/eicu_*.py`

The full frozen protocol is `EICU-PROTOCOL.md` (pre-registration: written and
committed BEFORE the extract was read; its scientific value depends entirely on
that ordering). This section is the binding engineering contract.

```
eicu_mock.py  -> (stdlib only)             schema-faithful mock corpus, byte-deterministic
eicu_etl.py   -> constants (SEED, SPLIT_FRACTIONS, MIN_CAL_CLUSTERS) + numpy
run_eicu.py   -> eicu_etl, run_synthetic (_rm_on_pool/_per_site_exceed_frac/_write_csv/_rate),
                 pipeline, validate, model, harness, report, explain
```

**Dependency rule (audit F16).** `eicu_etl.py` is **stdlib + numpy ONLY**; `eicu_mock.py`
is **stdlib only**. `pandas` and `pyarrow` are installed in the dev environment and are
NOT in `requirements.txt`; importing either is a hard test failure. All third-party
imports at module top level. Because `eicu_mock.py` may not import `eicu_etl` (that would
pull numpy into a stdlib-only module), the five `EICU_LEVELS_*` tuples and
`EICU_MIN_TOTAL_SITES` are DUPLICATED there as `EICU_MOCK_LEVELS_*` /
`EICU_MOCK_MIN_TOTAL_SITES`, and `tests/test_eicu_path.py` asserts the copies equal the
ETL's. The duplication is sanctioned because it is tested.

**Protocol constants** live at module top of `experiments/eicu_etl.py` (mock generator
parameters at module top of `experiments/eicu_mock.py`), and every one is pinned
literally by `tests/test_constants.py` — the `run_synthetic.py` precedent, extended.
`certgate/constants.py` is NOT touched: no eICU constant enters the core package.

```python
EICU_N_FEATURES = 161            # exact feature width; FEATURE_NAMES is built by
                                 # concatenating the same tuples used to one-hot, so
                                 # names and columns cannot drift
EICU_N_TARGET_SITES = 24         # >= 2 * BBSE_MIN_TARGET_SITES for the pooled arm;
                                 # leaves 184 -> cal = 75 at 208 hospitals
EICU_MIN_TOTAL_SITES = 149       # SUFFICIENT floor: at and above it the 40/20/40
                                 # remainder always yields MIN_CAL_CLUSTERS = 50
                                 # calibration sites. Not the TIGHT floor -- int()
                                 # truncation makes the count non-monotone in the
                                 # total (148 -> 51, 149 -> 50); the tight
                                 # breakpoint is 146, so this keeps 3 sites of slack
EICU_SPLIT_NAMESPACE = 9         # SeedSequence([SEED, 9, replicate]) -- the split rng
EICU_SPLIT_REPLICATES = 20       # independent re-splits for the validity-replication arm
EICU_MAX_OTHER_SHARE = 0.05      # frozen categorical vocabulary: drift past this raises
EICU_SENTINEL_MISSING = -1.0     # the UNDOCUMENTED APACHE sentinel (the column docs say
                                 # "set to NULL when not present"; the released CSVs use -1)
EICU_MIN_AGE = 18 ; EICU_AGE_MASK_TOKEN = "> 89" ; EICU_AGE_MASK_VALUE = 90.0
EICU_POSITIVE_LABEL = "Expired" ; EICU_LABEL_COLUMN = "hospitaldischargestatus"
EICU_SITE_PREFIX = "hosp-" ; EICU_POOLED_TARGET_LABEL = "eicu-target-pool"
EICU_APACHE_VERSION_PREFERENCE = ("IVa", "IV")
EICU_ARMS = ("primary", "apache-linked", "apache-complete")
EICU_MAX_UNPARSEABLE_SHARE = 0.01          # a NULL token that is not '' (Postgres text
                                 # format writes \N) turns 43 APACHE numerics into 100%
                                 # missing; build_raw ABORTS above this share
EICU_MAX_OUTCOME_PREVALENCE_RATIO = 2.0    # APACHE-row PRESENCE is jointly site- AND
                                 # OUTCOME-informative (day-1 rows do not exist for stays
                                 # that end before the window closes); above this contrast
                                 # the presence flags are an outcome proxy and build_raw
                                 # ABORTS in the primary arm
EICU_MIN_OUTCOME_STRATUM = 100   # the ratio gate needs both strata populated to mean anything
EICU_ATTRITION_STEPS, EICU_LEAK_DENYLIST, EICU_LEVELS_*, EICU_WINDOW_*,
EICU_APS_NUMERIC (24), EICU_APV_NUMERIC (19), EICU_REFERENCE_ROW_COUNTS
```

**Reason tags are a CLOSED set** (`EicuError`'s docstring is the vocabulary; tests match on
the substrings): `missing-table` · `duplicate-header` · `missing-column` ·
`undecodable-table` · `truncated-table` · `unknown-outcome-level` · `unknown-arm` ·
`categorical-level-drift` · `unexpected-negative-sentinel` · `unrecognised-null-token` ·
`unparseable-join-key` · `apache-coverage-collapse` ·
`outcome-informative-missingness` · `duplicate-stay-id` ·
`reference-row-count-mismatch` · `too-few-sites` · `too-few-cal-clusters` ·
`impute-fit-empty` · `nonfinite-after-impute` · `leak-column-in-features` ·
`feature-width-mismatch` · `record-level-output` · `hospitalid-unparseable` ·
`empty-cohort`. **Every read-boundary failure is typed**: a non-UTF-8 byte
(`undecodable-table`) and a truncated/corrupt gzip (`truncated-table`) are caught in
`read_table`/`_read_header` and re-raised naming the table and the path — a bare
`UnicodeDecodeError` names neither, and on a five-table extract the operator cannot tell
which file failed.

**Cohort (executable predicates, in order).** site-parseable → outcome-known
(`hospitaldischargestatus in {'Alive','Expired'}`; `''` DROPS, any third value raises
`reason=unknown-outcome-level`) → adult (`age >= 18`, with `'> 89'` KEPT as `90.0` plus
an `age_masked` indicator — dropping it removes a mortality-enriched, SITE-CORRELATED
stratum) → first ICU stay per `patienthealthsystemstayid` (min `unitvisitnumber`,
tie-broken by **max** `hospitaladmitoffset` — the offsets are NEGATIVE and the earliest
stay has the HIGHEST one, then min `patientunitstayid` for determinism). `patientunitstayid`
is the PRIMARY KEY of `patient`: a repeat raises `reason=duplicate-stay-id`. Silently
resolving it is not an option, because the two cohort scans resolve a duplicate
differently — scan A's `stay_meta[stay_id] = ...` keeps the LAST row's label and site while
scan B's `if stay_id in row_of: continue` keeps the FIRST row's features — so one patient's
covariates would be filed under another row's outcome and another row's hospital, with the
collapse mis-accounted as a first-stay drop. **No LOS floor**
(immortal-time selection, site-heterogeneous, and not neutralised by the feature
denylist). **No minimum-stays-per-hospital filter** (a `>= 500` filter leaves ~46
hospitals → ~18 calibration clusters → `insufficient-clusters`). **No APACHE filter in
the primary arm** — see below.

**Label** is `patient.hospitaldischargestatus`, positive `"Expired"`, emitted as raw
two-valued strings and mapped by `coerce_labels`/`from_raw`. Never a hand-built bool
array. `require_both_classes=False` is used for TARGET pools only.

**Site = `patient.hospitalid`**, emitted as `f"hosp-{int(hospitalid)}"` — one canonical
spelling per hospital, so `densify_sites`' cosmetic-collision raise cannot fire on our own
output. `hospitalid` and `wardid` are on the feature denylist: a head that can read the
site off the feature vector destroys the between-site generalisation the certificate
rests on.

**Features: deny by default.** An explicit allowlist of source columns (`patient`
admission-time; `apacheApsVar` 24 day-1 physiology; `apachePredVar` 19 day-1
comorbidity/treatment), each numeric imputed with an immediately-adjacent 0/1
`<name>__missing` sibling, each categorical one-hot over a FROZEN level tuple ending in
an `OTHER` bucket. `EICU_LEAK_DENYLIST` is a tuple of `(column, reason)` pairs and
`assert_no_leak_columns` is a TEST, not a comment — it additionally runs at IMPORT over
`FEATURE_NAMES`, so a leak cannot even be imported, let alone certified.

**`apachePatientResult` and `hospital` contribute NO features.** `apachePatientResult` is
the APACHE-IVa comparator and a coverage diagnostic only: 8.65% of the 208 hospitals have
ZERO rows in it, so any feature drawn from it forces either a cohort restricted to
APACHE-covered stays — which DELETES ~18 hospitals and CHANGES THE SITE POPULATION the
certificate's site-population-average estimand refers to (audit V1's estimand is a
population average; silently changing the population silently changes the claim) — or a
column that is a perfect site indicator. `hospital`'s `numbedscategory`/`teachingstatus`/
`region` are site-CONSTANT: their coefficients would be identified from ~75 between-site
observations, and they are the cleanest available site proxies. Both are reported as
strata and as an ATTRITION LEDGER (`EICU_ATTRITION_STEPS`, recording `n_stays` AND
`n_sites` per step), never applied as a filter.

**The `-1` sentinel is dual-channel and first-class.** For every allowlisted APACHE
numeric, BOTH `''` (the documented SQL NULL: the MIT-LCP loader is `NULL ''`) AND the
literal `-1` map to missing. Handling only one poisons the matrix with a finite `-1`.
Any negative mass NOT at exactly `-1.0` raises `reason=unexpected-negative-sentinel` —
every allowlisted column has non-negative physiological support, so an unrecognised
negative is a new sentinel and must abort, not flow. `fio2` and `temperature` carry the
two frozen, NON-OVERLAPPING unit normalisations (fraction/percent; Celsius/Fahrenheit),
counted in `meta["unit_conversions"]`; anything outside both windows becomes missing.
**The `fio2` windows are lower-CLOSED** — `EICU_WINDOW_FIO2_FRAC = (0.21, 1.0)` and
`EICU_WINDOW_FIO2_PCT = (21.0, 100.0)` applied as `lo <= v <= hi`, the percent branch
tested after the fraction branch so `21.0` is unambiguous. `fio2 = 0.21` (equivalently
`21`) is ROOM AIR: a physiologically valid, modal observation, and discarding it as
missing would convert the commonest value of a ventilation-linked column — and
ventilation status is site-correlated — into exactly the informative-missingness channel
this protocol undertakes to guard. The temperature windows stay lower-OPEN (`25.0 < v <
45.0`; there is no convention value at either endpoint, only implausible physiology), and
`preflight` warns when out-of-both-windows mass is non-trivial rather than leaving the
loss buried in a `unit_conversions` counter.

**A NULL token that is not `''` must ABORT, not flow — in EVERY allowlisted numeric, not
only the APACHE block.** The `-1` gate protects one direction; the opposite direction had
no guard. A re-export whose NULL token is Postgres text-format `\N` (or `NULL`/`NA`)
parses as `unparseable` in every allowlisted numeric, so all 43 APACHE parents become
100% NaN, all 43 `__missing` siblings become the constant 1.0, `model.SD_REL_TOL`'s
guard zeroes 86 of 161 coefficients, and a certificate is issued about a model that saw
no physiology at all — with an empty `warnings` list. `_parse_apache_cell` AND
`_parse_windowed` therefore retain a bounded counter of the offending TOKENS, and
`build_raw` raises `reason=unrecognised-null-token` when ANY allowlisted numeric's
unparseable share exceeds `EICU_MAX_UNPARSEABLE_SHARE = 0.01`, naming `'\\N'` rather than
a count. The first version of this gate was APACHE-scoped (`aps_`/`apv_` keys only): the
identical token in a `patient` numeric (`admissionheight`, `admissionweight`,
`hospitaladmitoffset` → the `pre_icu_hours` feature) flowed silently to a column constant
at the imputation fallback — and because `hospitaladmitoffset` doubles as §2.1's
first-stay tie-breaker, its loss also silently changed WHICH stays entered the cohort,
with no trace in the attrition ledger (2026-07-31 arrival-day audit, E-22). `preflight`
reports the same shares for both blocks and lists them in `invalid_conditions`.

**An absent or UNLINKED APACHE block must ABORT, not certify.** The null-token gate is
token-shaped: it fires only when cells are READ and fail to parse. The identical end
state — 89 of 161 feature columns constant, both presence flags dead — is reachable
through doors that read nothing at all: a `patientunitstayid` join key re-exported as
`141258.0` (the single commonest pandas/Postgres float round-trip artifact) or in
scientific notation; a header-only child table; a key shift that leaves every row count
intact while nothing joins — the last invisible to `EICU_REFERENCE_ROW_COUNTS` by
construction. Each route was demonstrated to certify with an EMPTY warnings list,
`preflight` at 0 blocking conditions, and BOTH E-9 legs silent — `gate_applies` false
because the present stratum was empty, so TOTAL absence bypassed the
outcome-informative-missingness gate that partial absence trips (2026-07-31 arrival-day
audit, E-21). Two legs close it: (1) `build_raw` and `preflight` count non-empty
`patientunitstayid` tokens that fail integer parse in each child table and raise
`reason=unparseable-join-key` past `EICU_MAX_UNPARSEABLE_SHARE`, naming the table and
the offending tokens; (2) in the primary arm, when the cohort is large enough that the
E-9 gate is supposed to be evaluable (`n_cohort ≥ EICU_MIN_OUTCOME_STRATUM`) but a
presence stratum cannot reach the floor (`n_present < EICU_MIN_OUTCOME_STRATUM`),
`build_raw` raises `reason=apache-coverage-collapse` — E-9 may never again be bypassed
by total absence. No new constant is introduced: both legs reuse the frozen
`EICU_MAX_UNPARSEABLE_SHARE` and `EICU_MIN_OUTCOME_STRATUM`, and the scale condition is
what keeps the gate silent on the tiny single-trap corpora whose semantics other tests
own. `preflight` projects both raises in `invalid_conditions`.

**APACHE missingness is jointly SITE- and OUTCOME-informative, and the outcome half is a
LEAK.** This is the load-bearing correction of the 2026-07-30 audit. The day-1 APACHE
variables are defined over the first 24 hours, so a stay that ends *because the patient
died* before the window closes carries no `apacheApsVar`/`apachePredVar` row at all.
`aps_present`/`apv_present` and the 43 `__missing` siblings are therefore not merely a
site proxy (threat T-3) — they are a partial outcome proxy, and NONE of the declared
defenses sees it: the 36-entry denylist is by column NAME and absence has no column, the
`-1` gate is about values, the drift gate is about categoricals, and the old F-D
(`alpha == 0.05` AND `coverage > 0.90` AND `R_M < 0.01`) passes underneath a leak that
certifies `alpha = 0.10` at coverage 0.86. Measured in-harness on a mock corpus with
outcome-correlated APACHE-row absence planted at rate `p` and nothing else changed
(180 hospitals / 9000 stays; out-of-sample calibration-split AUC, and the AUC of the same
head with the 49 missingness/presence columns ablated):

| corpus | aps coverage | prevalence ratio absent : present | head AUC | ablated AUC | drop |
|---|---|---|---|---|---|
| clean | 0.862 | 1.11 | 0.597 | 0.613 | −0.016 |
| p = 0.10 | 0.853 | 1.87 | 0.608 | 0.600 | +0.008 |
| p = 0.20 | 0.845 | 2.66 | 0.631 | 0.595 | +0.035 |
| p = 0.30 | 0.835 | 3.86 | 0.671 | 0.589 | +0.082 |
| p = 0.75 | 0.803 | 14.51 | 0.835 | 0.587 | +0.248 |

Coverage — the only quantity the old protocol printed — moves by 0.06 across the whole
range and is indistinguishable from the released extract's 171177/200859 = 0.852. Three
gates at three sensitivities replace it, and all three are pre-registered:

1. **Outcome-stratified missingness, measured** (preflight and `meta`). `preflight` gains
   `outcome_stratified_missingness`: for `aps_present`, `apv_present` and every
   allowlisted APACHE column's missing indicator, the cohort outcome prevalence in the
   missing and non-missing strata and their ratio. Every `EICU_ATTRITION_STEPS` entry
   additionally records **`n_positive`** (hence the step's prevalence), so the ledger
   itself shows the `apache-aps-linked` prevalence collapse.
2. **Abort** (`build_raw`, primary arm). If either presence flag's absent:present
   prevalence ratio exceeds `EICU_MAX_OUTCOME_PREVALENCE_RATIO = 2.0` with both strata at
   least `EICU_MIN_OUTCOME_STRATUM = 100` stays, raise
   `reason=outcome-informative-missingness`. The message names both remedies rather than
   inviting a threshold edit: run the declared `apache-linked` arm, or drop the flags.
3. **Runtime leak alarm** (`run_eicu`, criterion F-D, rewritten). F-D no longer depends on
   `alpha` or `coverage`. It fires on the head's own out-of-sample discrimination against
   `EICU_LEAK_AUC_CEILING = 0.90` (APACHE-IVa, a purpose-built day-1 score, reaches
   ~0.87 on this outcome; a 161-column logistic head that beats 0.90 from the same inputs
   is a leak before it is a result), and on the missingness-ablation delta against
   `EICU_LEAK_ABLATION_MAX_DROP = 0.05`. Both numbers are computed every replicate and
   written to `EICU_pooled.csv` and `EICU_diagnostics.json`, so the check exists on the
   real extract and not only inside pytest.

**The declared `apache-linked` arm** (`EICU_ARMS[1]`) is the escape that pays the cost
explicitly: restrict to stays carrying BOTH APACHE tables, so the presence flags are
constant and information-free. It is an immortal-time-selected cohort — that is the price,
it is stated, and its `n_sites` and prevalence are reported beside the primary arm's
wherever it appears. It is never the headline. (`apache-complete` remains the stricter
comparator-availability arm and additionally deletes the ~18 zero-coverage hospitals.)

**Prediction P4 is a LEAK SIGNATURE, not a confirmation.** P4 predicted `aps_present` /
`apv_present` in the top 3 of the abstention `gap_ranking`. On the leaked corpus that is
exactly what `EICU_diagnostics.json` returns (`aps_present` gap −1.21 at rank 1). P4 is
therefore reported jointly with gates 1–3 and is settled as CONFIRMED only when those pass;
otherwise it is reported as evidence FOR the leak.

**Site-informative missingness is MEASURED, never imputed away.** CertGate v2 scope-cut
covariate-shift mode; the dataset authors state that data completion varies by hospital.
`preflight` therefore emits `sentinel_site_dispersion` (per-site `-1` rate: mean, sd,
p10/p50/p90) and `apache_coverage_by_site` per table, plus the length-of-stay distribution
of APACHE-absent versus APACHE-present stays (`apache_absent_los`) — the measurement that
distinguishes the site channel from the outcome channel — and the protocol registers both
as stated threats to validity.

**Every allowlisted feature is screened against the outcome before certification.** The
denylist applies a "leak-suspect: timing relative to outcome unverified" standard to two
`apachePatientResult` columns, so it must apply it to the nine `apachePredVar`
treatment/intervention flags too (`activetx`, `thrombolytics`, `graftcount`,
`electivesurgery`, `ventday1`, `oobventday1`, `oobintubday1`, `ima`, `midur`) — `activetx`
most of all, since active-treatment-versus-comfort-measures is a decision made during the
stay and adjacent to death by definition. Resolving that from DDL comments is not
available on a dataset whose sentinel convention the DDL already gets wrong, so it is
resolved from the DATA, before any certificate: `eicu_etl.outcome_screen(x_raw, meta)`
returns, per feature, the outcome prevalence by stratum (binary) or top-vs-bottom decile
(continuous) and a univariate AUC, and `run_eicu` writes it to `EICU_diagnostics.json` and
flags every feature past `EICU_FEATURE_AUC_REVIEW = 0.75` for re-audit before the numbers
are reported. Columns whose timing cannot be cited carry that fact in
`EICU-PROTOCOL.md` §5.4a, not in silence.

**Imputation is fit on S_train rows ONLY** (`impute(x_raw, fit_idx=idx['train'])`).
Pooled-matrix means would let the target pool's covariate distribution into the training
features — a transductive leak no downstream gate catches. An all-NaN-within-train column
falls back to `EICU_IMPUTE_FALLBACK = 0.0`, counted.

**Split is BY SITE** (`SPLIT_FRACTIONS` imported, never re-literalled): hold out
`EICU_N_TARGET_SITES = 24`, then 40/20/40 on the remainder. At 208 hospitals that is
train 73 / aux 36 / **cal 75** against `MIN_CAL_CLUSTERS = 50`. `site_split` raises
`reason=too-few-sites` below `EICU_MIN_TOTAL_SITES` and `reason=too-few-cal-clusters` if
the calibration count falls short, and asserts PAIRWISE disjointness (a triple-intersection
assert is strictly weaker). `replicate` indexes an independent re-split from
`SeedSequence([SEED, EICU_SPLIT_NAMESPACE, replicate])`; `replicate=0` is the published
primary split.

**Target pools, two arms, both run.** (i) Per-hospital: one pool per held-out hospital,
`target_site_id` SUPPLIED with K == 1 — statistically the same exact Clopper–Pearson `q_t`
path `None` takes, plus full id validation, record-level disjointness against
train/aux/cal, and provenance binding. (ii) Pooled: all 24 hospitals,
`target_site_id` supplied with K = 24 >= `BBSE_MIN_TARGET_SITES`, so `q_t` takes the
cluster bootstrap. `target_site_id` is NEVER omitted: omitting it declares a single site
and silently substitutes an interval that under-covers a multi-hospital pool.

**Aggregate-only outputs.** `run_eicu.assert_aggregate_only` refuses any payload carrying
`EICU_FORBIDDEN_OUT_KEYS` or any array longer than `EICU_MAX_OUTPUT_LEN = 512`, and every
write goes through it. The data directory is gitignored; no record-level artifact may
reach `experiments/out/` (PhysioNet Credentialed Health Data License 1.5.0 + DUA 1.5.0
restrict derived record-level artifacts). `run_eicu` writes its own `EICU-SUMMARY.md`
with sections `## EICU-<NAME>` and NEVER writes `summary.md` — `_existing_summary_blocks`'
regex is `^## (E\d)`, a single digit, so an eICU section there would be silently clobbered.
eICU CSVs are written ASCII-STRICT (deliberate deviation from `run_synthetic._write_csv`'s
locale default): every eICU cell is ASCII by construction, so a non-ASCII cell is an
upstream protocol violation and a crash is correct where a mojibake cell is not.

**Preflight is mandatory and non-certifying.** `python -m experiments.run_eicu --data DIR
--preflight` validates row counts against `EICU_REFERENCE_ROW_COUNTS` / 208 sites /
139,367 patients (`expect_reference=True` turns a mismatch into
`reason=reference-row-count-mismatch`), profiles every sentinel channel, measures the
attrition ledger and the per-site missingness dispersion, tabulates the categorical
level sets against the frozen tuples, and WRITES THE A-PRIORI PREDICTIONS — before any
certificate exists. It builds no features and certifies nothing.

**The reference-identity quantities are counted at S0, over EVERY `patient` row, before
any predicate.** `EICU_REFERENCE_PATIENTS = 139367` / `EICU_REFERENCE_SITES = 208` /
`EICU_REFERENCE_UNIT_STAYS = 200859` are the dataset's WHOLE-TABLE headline counts, so
comparing them against post-filter counts makes `preflight(expect_reference=True)` — the
mandatory first command on arrival day — abort on the genuine, correct extract (~1751
stays carry a blank outcome, and at 1.44 stays/patient most of those patients lose every
stay, so the post-filter patient count lands ~1.7% low). On abort NOTHING is written: no
`EICU_preflight.json`, no ledger, no histograms; and the natural workaround
`--no-reference-check` disables the entire T-6 wrong-download guard. `preflight` therefore
reports `n_uniquepid` / `n_hospitals` / `n_rows` as RAW S0 counts and the post-filter
counts under the distinct keys `n_uniquepid_cohort` / `n_hospitals_cohort` — dataset
identity and cohort diagnostic are different quantities and are named differently.

**Preflight never aborts on a condition it exists to PROFILE.** A single unexpected
`hospitaldischargestatus` token used to raise `unknown-outcome-level` from inside the row
loop, discarding the value counts already accumulated — so the step whose job is to
tabulate value sets against the frozen expectations produced no profile at all, and the
operator learned the token but not its count, its site distribution, or anything else in
the file. `_select_cohort` takes `strict_outcome` (default `True`); `preflight` passes
`False`, collects unknown levels into a bounded counter, counts those stays as an
`outcome-unknown-level` drop, and emits them in `patient.hospitaldischargestatus`, a
`[MEASURE]` warning and an `invalid_conditions` entry naming the raise `build_raw` WILL
make. `build_raw`'s raise is unchanged. Error messages name the function that actually
raised, never a hard-coded `build_raw`.

**`header_case_as_read` is a DECIDABLE verdict.** The old rule ("camel iff every name
carries an uppercase character") called a fully camelCase header `mixed` on four of five
tables, because single-token names (`age`, `gender`, `ph`, `urine`, `region`) cannot
express case — and `mixed` reads as "some columns were re-cased and some were not", a
materially different and misleading diagnosis in the exact direction T-6 exists to detect.
The verdict is now: `lower` iff no name carries an uppercase character (the released
extract); `camel` iff at least one does and every name is alphanumeric (a case-varied
rendering of the same names); `mixed` iff at least one name carries an uppercase character
AND at least one carries a separator (`_`), i.e. a re-export from a different tool. The
raw header and `n_names_with_uppercase` are reported beside the verdict so the operator
sees the evidence, and `tests/test_eicu_path.py` pins the expected value PER TABLE for
both mock header modes rather than accepting any of the three.

**Tests** (`tests/test_eicu_path.py`, mirroring `test_fixture_integration.py`): an
always-on small arm (180 mock hospitals / 9000 stays) asserting an HONEST outcome — a
certificate whose oracle-checked answered risk respects its own alpha, or a decline —
never asserting that certification happens; plus a full-scale arm (208 hospitals /
200,859 stays) gated behind `CERTGATE_EICU=1`. The split arithmetic leaves 63
RECORD-CARRYING calibration clusters (`EICU_MOCK_MIN_STAYS_PER_SITE = 12` guarantees no
empty calibration site), so the `MIN_CAL_CLUSTERS = 50` gate is deterministically
satisfied and the walk is reached rather than gated. **The mock corpus does not certify AT
THE FROZEN CORPUS SIZES, and this is arithmetic rather than accident — but the scope of
that claim is the frozen sizes, not "any corpus size".** At the frozen
`EICU_MOCK_SIGNAL_B = 0.85` the outcome's Bayes-optimal AUC is `Phi(B/sqrt(2)) = 0.73` and
the fitted head reaches 0.60 out of sample; the best margin `max_tau cov*(alpha - risk)`
an ORACLE ranking by true risk achieves is 0.0354 at alpha = 0.10, against
`certify.margin_floor(n_carrying, DELTA, 0.10)` = 0.0428 at the small arm's 63 calibration
clusters and 0.0359 at the 75 a 208-hospital split yields — so `run_certgate` declines
every rung at `EICU_MOCK_SMALL_SITES = 180` and at `EICU_MOCK_FULL_SITES = 208`, and the
default suite exercises the DECLINE branch. **`margin_floor` scales as 1/n_carrying, so the
comparison does NOT generalise:** the floor first drops below 0.0354 at
`n_carrying = 77` (≈ 217 hospitals), and a mock generated at 900 or 1500 hospitals
certifies alpha = 0.10 with the pre-registered constant untouched. Any text telling an
operator to "expect a decline" must name the corpus size it means; an operator who runs a
larger mock, sees a certificate, and concludes the pipeline is broken has been misled by
the documentation, not by the code. The certified branch is therefore reached in the
suite by an off-default large-site arm (`CERTGATE_EICU_LARGE=1`) rather than left
unexercised, and raising `EICU_MOCK_SIGNAL_B` toward `synth_fixture.SIGNAL_B = 2.0` is one
further option, not the only one; either is a SPEC + `test_constants` decision, not one
the generator may make on its own. The mock (`experiments/eicu_mock.py`)
uses REAL eICU column names and DDL column order and plants every documented wart (dual
`-1`/`''` sentinels, `'> 89'`, negative admit offsets with the earliest stay highest,
multi-row `apachePatientResult` across `'IV'`/`'IVa'`, site-correlated APACHE coverage
including zero-coverage hospitals, heavy-tailed hospital sizes, duplicate stay ids,
cross-hospital `uniquepid`, BOM, embedded newlines, mixed `fio2`/temperature units, mixed
`teachingstatus` renderings). It is byte-deterministic: `gzip.GzipFile(filename="",
mtime=0, fileobj=...)` + `io.TextIOWrapper(newline="")`, per-`(table, stay)` RNG streams
and per-table id counters, so a `--tables` subset is a byte-identical projection.

## Audit-lesson conformance (verifier checklist)

F01→BBSE-asymptotic disclosure in guarantee text (per V13: four-parameter box named; the
"single non-finite-sample step" phrasing is RETIRED) · F02→concept-shift out-of-scope wording ·
F03→assert_site_disjoint at entry (extended to the target split by V9) ·
F05/F35/F37→strict bool labels + coerce_labels ·
F06→relative-tol sd guard · F07/B-5→record-carrying cluster gate · F08→isfinite weights ·
F13→test_constants literal pins · F15/F34→40/20/40 split + {0.05,0.10} ladder + E4 frontier +
expectation documented · F16→top-level imports + pinned requirements · F25→3-way composition ·
F26→capped-influence share + weighting-gap diagnostic · F36→isfinite scores/features loud ·
F38→site_sizes derived only · F39→densify + dense assertion · F40/B-8→bootstrap top-up-or-
decline · F41/B-9→q_t range decline · F42/B-6→MIN_ANSWERABLE registered + "pool-too-small" ·
F43/B-10→sha256-only seed rule · F49→provenance block (content-bound per V11) ·
F51→floor at true carrying n per rung · F57→no int() path.

2026-07-25 audit (CODE-AUDIT.md) conformance:
V1→population-average estimand named + mandatory dispersion clause + E1 rescored with s_u
sensitivity · V2→q_t confidence share, BBSE_BONFERRONI=4, 16 corners, widened NaN-safe gate ·
V3→target-label-free permutation seed + baseline-only shared-event clause ·
V4/V10→site-id canonicalization, missing-id rejection, near-duplicate collision raise ·
V5→unique site_labels enforced · V6→mutation killers: harness tests, delta spy, M-cap
boundedness, guarantee-text freeze, multi-element BBSE walk fixture, walk-order provenance,
provenance content binding · V7→one generator across all experiments, grid constants pinned ·
V8→box under-coverage disclosed with measured value in METHODS (finite-sample WSR-inversion
box remains future work) · V9→target site-disjointness · V11→provenance binds y/site_id/
shape/dtype · V14→bbse-empty-target decline · V15→Cohort.__post_init__ · V16→feasibility
None-not-inf · V17→1-D y/site_id enforced · V18→both-classes recheck at run_certgate ·
V19→oracle_target_y validated · V20→interventional Shapley named · V21→estimated-tier
top-up-or-decline + NaN-not-0.0 · V22→empty-population gap ranking empty · V23→modes
validated · V24→dead deploy_mode parameter removed from _statement · V25→stable gated-report
key set · V26→summary blocks stamped + preserved-marking + finally · V27→operative-rung
selection clause at 1-2*DELTA.

2026-07-30 real-data protocol conformance: E-1→cohort predicates executable and
pre-registered · E-2→deny-by-default feature allowlist with a tested leak denylist ·
E-3→dual (-1 / '') sentinel policy · E-4→APACHE coverage measured as attrition, never
applied as a filter in the primary arm · E-5→imputation fit on S_train only ·
E-6→categorical drift gate at EICU_MAX_OTHER_SHARE · E-7→aggregate-only outputs
(assert_aggregate_only) · E-8→per-site missingness dispersion reported, not imputed away.

2026-07-31 real-data ingest audit conformance (three adversarial verifiers):
E-9→APACHE missingness is jointly site- AND OUTCOME-informative; measured
(outcome_stratified_missingness, n_positive per attrition step, apache_absent_los),
gated (outcome-informative-missingness at EICU_MAX_OUTCOME_PREVALENCE_RATIO), and the
declared apache-linked arm pays the immortal-time cost explicitly · E-10→F-D rewritten as
an alpha- and coverage-independent runtime leak alarm (EICU_LEAK_AUC_CEILING,
EICU_LEAK_ABLATION_MAX_DROP), computed every replicate on the real extract, not only in
pytest; the mock probe's ceiling is set from the stated Bayes-optimal AUC, not 25 points
above it · E-11→patientunitstayid is a PRIMARY KEY (duplicate-stay-id); the two cohort
scans may not disagree about which duplicate wins · E-12→P4 is a LEAK SIGNATURE, reported
jointly with E-9's gates, never a standalone confirmation · E-13→reference-identity counts
taken at S0, cohort counts named separately, so the mandatory first command does not abort
on the correct extract · E-14→every read-boundary failure typed and named
(undecodable-table, truncated-table) · E-15→a NULL token that is not '' aborts
(unrecognised-null-token at EICU_MAX_UNPARSEABLE_SHARE) · E-16→preflight profiles what it
exists to profile: an unknown outcome level is collected and reported, never raised from
inside the scan · E-17→header_case_as_read is decidable and pinned per table ·
E-18→fio2 windows lower-CLOSED: room air is an observation, not a missing value ·
E-19→every allowlisted feature screened against the outcome (outcome_screen) before any
certificate, so "is this column post-hoc?" is answered from data, not from DDL comments ·
E-20→claims about what the mock does are scoped to the corpus size they were measured at
(margin_floor scales as 1/n_carrying; the crossing point is n_carrying = 77) ·
E-21→an absent or UNLINKED APACHE block aborts, never certifies (unparseable-join-key at
the read boundary; apache-coverage-collapse whenever a cohort large enough to evaluate
E-9 has a presence stratum below EICU_MIN_OUTCOME_STRATUM — total absence may not bypass
the leak gate that partial absence trips) · E-22→the unrecognised-null-token gate covers
every allowlisted numeric including the patient block, whose hospitaladmitoffset doubles
as the first-stay tie-breaker.
