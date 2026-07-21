# Claim–contract–witness map for simulator/world-model robot-policy evaluation

**Version:** 0.1  
**Status:** conceptual synthesis; no empirical validation claimed.

## 1. Formal object

An **evaluation claim** is represented as

\[
\mathcal C=(\mathcal E,\Pi,\mathcal Z,q,L,\epsilon,\alpha,D),
\]

where \(\mathcal E\) is the evaluator, \(\Pi\) the prespecified policy set or class, \(\mathcal Z\) the target context distribution, \(q\) the target quantity (success, return, violation probability, or another outcome), \(L\) the loss incurred when the evaluator-supported conclusion is wrong, \(\epsilon\) the tolerated error, \(\alpha\) the tolerated error probability, and \(D\) the downstream decision (report, rank, select, optimize, screen, or deploy).

An evaluator is not “valid” without qualification. It is adequate only relative to \(\mathcal C\).

Let \(E\) be a collection of public evidence and \(\mathfrak W(E)\) the set of evaluator/target mechanisms not ruled out by that evidence. We call the evidence **decision-sufficient** for \(\mathcal C\) only if the stated assumptions plus evidence constrain every admissible mechanism enough that

\[
\sup_{W\in\mathfrak W(E)}
\Pr_W\!\left[L(D_E,D_\star)>\epsilon\right]\leq \alpha.
\]

This is an organizing definition, not a newly proved universal bound. Its purpose is to force a reviewable answer to four questions: What decision is being supported? What mechanisms remain compatible with the evidence? What error matters? What assumptions close the gap?

## 2. Evaluation-claim ladder

| Level | Claim | Example | Why it is stronger than the previous level |
|---|---|---|---|
| C0 | trace or artifact plausibility | generated robot video looks realistic | no policy-value inference yet |
| C1 | fixed-policy value estimation | estimate success of one frozen policy in one task distribution | requires calibrated outcomes, not only plausible traces |
| C2 | prespecified pairwise/full ranking | order a frozen list of policies or checkpoints | requires error small relative to value margins across policies |
| C3 | policy selection | choose the best member of a finite or structured class | selection amplifies evaluator error and requires simultaneous validity |
| C4 | policy optimization | repeatedly update a policy using evaluator feedback | the policy distribution becomes evaluator-dependent and can exploit model errors |
| C5 | safety screening or deployment support | rule out hazardous policies or justify bounded deployment | false negatives, rare events, and consequence-weighted uncertainty dominate mean performance |

The ladder is not a scalar score. Passing C2 does not automatically pass C1 (ranking may be right while values are biased), and passing C1 for one policy does not imply C3 for a selected policy.

## 3. Evidence contracts

| Contract | Question | Minimum witness examples | Failure if absent |
|---|---|---|---|
| K1 Execution identity | What exact evaluator was run, and are its numerical/event/interface semantics stable enough for this claim? | version/hash closure; solver and step policy; determinism audit; convergence or perturbation envelope; checkpoint/interface specification | policy outcome may be an artifact of implementation or scheduling |
| K2 Intervention fidelity | Does changing the policy action change the evaluator trajectory in the correct direction and magnitude? | action-following tests; counterfactual action pairs; open-loop replay plus closed-loop intervention; contact/event response checks | visually plausible but action-insensitive or causally wrong rollouts |
| K3 Outcome/label validity | Is the success, reward, cost, or safety label itself accurate? | human agreement; calibrated classifier/VLM; scripted evaluator tests; label uncertainty propagated to policy estimates | evaluator dynamics may be adequate while the reward judge reverses policy order |
| K4 Support and coverage | Are target states, actions, tasks, disturbances, and policy-induced trajectories represented? | coverage table; OOD axes; density/uncertainty diagnostic; overlap analysis; partial-identification bounds | extrapolation is presented as measurement |
| K5 Decision alignment | Does evidence directly address the claimed value, order, regret, or violation loss? | paired target/evaluator policy outcomes; value error; MMRV/rank intervals; regret bounds; safety false-negative analysis | predictive or visual metrics substitute for the downstream quantity |
| K6 Selection-valid uncertainty | Is inference valid for the number of policies compared and for any adaptive reuse? | simultaneous intervals; family-wise/FDR control where relevant; uniform convergence; held-out target anchor; preregistered policy set | winner's curse, benchmark overfitting, or simulator exploitation |
| K7 Transport and CoU | Why should the conclusion hold in the named robot/task/environment context? | independent target-domain anchor; discrepancy model; bounded shift; task/embodiment scope; explicit consequences and acceptance limits | internal simulator evidence is mistaken for a real-domain claim |

## 4. Contract requirements by claim

Legend: `R` required, `C` conditional on system/decision, `D` diagnostic but not sufficient alone.

| Claim | K1 | K2 | K3 | K4 | K5 | K6 | K7 |
|---|---:|---:|---:|---:|---:|---:|---:|
| C0 trace plausibility | C | D | – | C | – | C | – |
| C1 fixed-policy value | R | R | R | R | R | C | R |
| C2 ranking | R | R | R | R | R | R for multiple policies | R |
| C3 selection | R | R | R | R | R | R | R |
| C4 optimization | R | R | R | R under induced distribution | R | R under adaptive reuse | R |
| C5 safety/deployment | R | R | R | R including tails | R with consequence-weighted loss | R | R with explicit CoU |

## 5. Proxy-to-claim insufficiency map

| Observed evidence proxy | Tempting but unsupported inference | Counterexample family | Missing witness |
|---|---|---|---|
| low image/video prediction error | evaluator preserves policy values | errors concentrated at contact or terminal events can be small perceptually and large in return | K2, K3, K5 |
| action-following on recorded trajectories | closed-loop policy evaluation is valid | small state errors change future policy actions and leave replay support | K4, K5, K7 |
| high Pearson correlation across a few policies | new/tuned policies will be ranked correctly | monotone bias on tested policies plus reversal outside their support | K4, K6, K7 |
| perfect ordering of a finite policy set | absolute success rates are calibrated | any strictly increasing transformation preserves ranks but changes values | K5 for C1 |
| accurate fixed-policy confidence intervals | the evaluator can select the best policy | the maximum of many noisy estimates is optimistically biased | K6 |
| simulator-only robustness across perturbations | target-domain robustness is established | all perturbations share the same omitted mechanism | K7 |
| conservation/numerical residual is small | policy ranking is stable | phase, event-order, or force-direction errors can preserve the monitored invariant | K1 plus ranking-margin bound |
| compliant execution interface | alternative execution modes are equivalent | solver ownership and event scheduling change trajectories while API calls remain valid | K1 semantic witness |
| target-domain fit after calibration | unobserved policy QoI is validated | calibration-equivalent models disagree on intervention outcomes | K5, K7 discrepancy/identification witness |
| uncertainty heat map | uncertainty protects the decision | uncertainty is not propagated into ranking, selection, or safety threshold | K5/K6 decision rule |

## 6. Four review-level propositions

These propositions are intended as concise theoretical statements to be proved with elementary constructions in a later appendix. They do not require new experimental data.

### Proposition 1 — Observational fidelity is insufficient for intervention validity

There exist two evaluators that induce the same distribution of observations on a logged behavior policy yet produce opposite action effects, and therefore opposite rankings for an intervention policy. Consequently, observational or video fidelity under one behavior distribution cannot by itself establish C1–C5 claims.

**Literature anchors:** objective mismatch; value equivalence; action-conditioned world-model evaluation.

### Proposition 2 — Finite-set rank agreement is not closed under policy selection

For any finite tested policy set with perfect evaluator/target ordering, there exists an untested policy outside the tested support whose evaluator advantage is a target-domain disadvantage. Therefore, a fixed-set ranking result cannot support C3 or C4 without a policy-class restriction, coverage assumption, or uniform error control.

**Literature anchors:** SIMPLER/MMRV; adaptive data analysis; uniform OPE; simulation optimization bias.

### Proposition 3 — Internal verification cannot establish transport

For any evaluator whose implementation is deterministic, converged, and internally consistent, there exists a target domain with an omitted mechanism that matches all internal checks but reverses a policy conclusion. Thus K1 is necessary for reproducible evidence but cannot substitute for K7.

**Literature anchors:** context-of-use V&V; discrepancy and unobserved-QoI validation; co-simulation semantics.

### Proposition 4 — Ranking stability requires margin-aware error control

If each policy-value discrepancy between evaluator and target is bounded by \(\delta\), a pairwise order is certified only when the evaluator value gap exceeds \(2\delta\). Aggregate correlation without policy-pair margin analysis can therefore hide consequential rank reversals.

**Literature anchors:** simulation lemma/value-error bounds; MMRV; finite-sample intervals.

## 7. Claim–evidence status map for the planned manuscript

| Manuscript claim | Current evidence | Status | Required closure before submission |
|---|---|---|---|
| simulator/world-model evaluation is a rapidly growing alternative to real-robot testing | SIMPLER, WorldEval, WorldGym, PolaRiS, RobotArena, Gemini/Veo | supported for trend, not universal effectiveness | full-text coding and archival-status update |
| visual/predictive fidelity and downstream decision fidelity are distinct | Lambert et al.; Grimm et al.; world-model action/OOD findings | supported | cite primary sources and retain bounded wording |
| policy ranking is weaker than policy selection/optimization | adaptive data analysis, uniform OPE, SPOTA/model exploitation | supported as a theoretical synthesis | formalize Proposition 2 and distinguish fixed versus adaptive policy sets |
| credibility must be tied to a context of use and consequence | ASME V&V 40 and model-discrepancy literature | supported outside robotics | justify transfer of the principle, not direct empirical effectiveness in robotics |
| numerical/execution semantics are an overlooked evidence layer in robot-policy evaluator papers | FMI/co-simulation sources plus preliminary coding | inferred, not yet systematically established | code reporting frequency in the included direct evaluator corpus |
| the seven-contract framework is useful for authors/reviewers | conceptual design only | needs evidence; cannot be written as validated | present as proposed synthesis and invite prospective validation |
| no prior review unifies these domains in this exact way | preliminary search only | not yet supported | complete database and citation-chaining novelty audit; avoid `first` |

## 8. Reporting checklist derived from the map

Every future evaluator paper should report at minimum:

1. exact evaluation claim and downstream decision;
2. prespecified policy set/class and whether it was tuned with evaluator feedback;
3. target context, task distribution, embodiment, horizon, and acceptance loss;
4. evaluator version, execution configuration, and reproducibility artifacts;
5. action-intervention and reward/label validation;
6. coverage and explicit OOD/support boundaries;
7. paired target-domain evidence or explicit transport assumptions;
8. uncertainty intervals matched to ranking/selection multiplicity;
9. failure cases capable of reversing conclusions, not only degrading visuals;
10. claim-specific conclusion that does not exceed the evidence tier.

