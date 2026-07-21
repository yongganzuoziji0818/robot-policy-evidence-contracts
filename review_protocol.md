# Structured review protocol: evidence sufficiency for simulator/world-model robot-policy evaluation

**Protocol version:** 0.1  
**Date frozen:** 2026-07-21  
**Review type:** structured scoping and theoretical review; not a PRISMA systematic review and not a meta-analysis.  
**Data boundary:** public bibliographic and article content only; no experimental execution.

## 1. Objective

The review will identify what kinds of evidence are used to justify robot-policy evaluation in physics simulators, real-to-sim digital twins, and learned world models; determine which inferential claims those evidence types can support; and expose the additional obligations required when moving from fixed-policy description to ranking, selection, safety screening, or target-domain deployment decisions.

## 2. Review questions

- **RQ1 — Claim:** What claim is made—trace plausibility, value estimation, pairwise ranking, policy selection, safety screening, or deployment readiness?
- **RQ2 — Evidence:** What evidence is supplied—visual/predictive fidelity, action following, paired target-domain trials, rank correlation, uncertainty calibration, stress tests, numerical verification, or formal bounds?
- **RQ3 — Sufficiency:** Which assumptions connect that evidence to the claim, and are those assumptions tested, bounded, or merely implicit?
- **RQ4 — Failure:** Which counterexamples or known failure modes show that a commonly used proxy cannot support the stronger claim by itself?
- **RQ5 — Practice:** What minimum reporting package would make a simulator/world-model evaluation reusable and falsifiable?

## 3. Scope

### 3.1 Population and systems

- robot manipulation, locomotion, navigation, and heterogeneous embodied policies;
- handcrafted physics simulators, co-simulation systems, real-to-sim/digital-twin evaluators, and learned action-conditioned world models;
- fixed policies, checkpoint sets, policy classes, or policies selected/tuned using evaluator feedback.

### 3.2 Primary date window

- 2015–2026 for robot-policy evaluation and learned world models;
- earlier work admitted when foundational for simulation validation, robust decision-making, statistical selection, or model equivalence.

### 3.3 Sources

- archival proceedings and journals: PMLR, NeurIPS, ICML, ICLR/OpenReview, CoRL, IJRR, RA-L, TRO, L4DC, and relevant simulation/V&V journals;
- official standards and specifications: ASME V&V/VVUQ, FMI;
- arXiv only when an archival version is unavailable or when documenting the current frontier;
- project pages only for protocol details not available in the archival abstract;
- corporate demonstrations and position papers retained as grey literature, never as the sole basis for a central claim.

## 4. Search strategy

Search cutoff: 2026-07-21. Search strings are combined in title/abstract/keyword fields where supported.

### Cluster A — robot policy evaluation

```text
(robot OR robotic OR manipulation OR locomotion)
AND (policy evaluation OR policy ranking OR checkpoint selection OR benchmark)
AND (simulation OR simulator OR real-to-sim OR digital twin)
```

### Cluster B — learned world-model evaluators

```text
(robot OR embodied)
AND (world model OR video world model OR learned simulator)
AND (policy evaluation OR policy ranking OR action conditioning OR closed loop)
```

### Cluster C — decision-aware model adequacy

```text
(model-based reinforcement learning OR learned dynamics)
AND (value equivalence OR value-aware OR objective mismatch OR model exploitation
     OR simulation optimization bias OR pessimism)
```

### Cluster D — validity, verification, and transport

```text
(simulation OR co-simulation OR computational model)
AND (verification OR validation OR credibility OR context of use OR uncertainty)
AND (decision OR ranking OR policy OR control)
```

### Cluster E — selection and statistical validity

```text
(policy evaluation OR benchmark OR simulator)
AND (finite sample OR confidence interval OR uniform convergence OR adaptive data analysis
     OR post-selection OR multiple comparisons OR ranking uncertainty)
```

Backward and forward citation chasing is performed from SIMPLER, WorldEval, WorldGym, the value-equivalence paper, objective-mismatch work, SPOTA, and context-of-use V&V sources.

## 5. Inclusion criteria

A source is included in the synthesis when it satisfies at least one of the following:

1. uses a simulator, digital twin, or learned world model to estimate, rank, select, diagnose, or safety-screen robot policies;
2. evaluates agreement between synthetic and target-domain policy outcomes;
3. supplies theory directly linking model error or equivalence to policy value or decision quality;
4. supplies a directly transferable validity principle for computational-model evidence, numerical/semantic correctness, uncertainty, support, or post-selection inference;
5. provides a counterexample or documented failure mode that invalidates a common evidence proxy.

## 6. Exclusion criteria

- simulation used only for training, with no evaluation-validity claim or relevant failure analysis;
- papers that compare robot policies only inside one benchmark and make no target-domain or evaluator-validity claim;
- visual-generation metrics without an embodied action or downstream-decision link, except when used as a negative/proxy example;
- secondary summaries when the primary article is available;
- vendor claims without enough methodological detail to classify policy set, target domain, intervention, and metric;
- papers whose only relevance is generic sim-to-real transfer without implications for evaluation evidence.

## 7. Screening and extraction

Each record receives the following fields:

| Field | Coding values |
|---|---|
| evaluator type | physics / co-simulation / digital twin / learned latent model / video world model / hybrid |
| target claim | trace / point value / pairwise order / full ranking / selected policy / safety screen / deployment |
| policy scope | one fixed / prespecified finite set / checkpoints / architecture family / adaptively generated class |
| target anchor | none / target observations / paired open-loop / paired closed-loop / real-policy trials |
| action intervention | absent / open-loop action replay / closed-loop policy / intervention stress test |
| support audit | none / in-distribution only / explicit OOD axes / density or uncertainty / coverage guarantee |
| metric | visual/predictive / value error / Pearson or Spearman / MMRV / regret / confidence interval / violation rate |
| uncertainty | absent / standard error / bootstrap / finite-sample interval / uniform or simultaneous bound |
| execution semantics | unreported / versioned / deterministic audit / numerical convergence / semantic contract |
| post-selection use | none / checkpoint selection / policy tuning / optimization / safety gating |
| transport scope | implicit / task-bounded / embodiment-bounded / distribution-bounded / formal assumption |
| evidence tier | E1 / E2 / E3 / E4 below |
| limitation status | author-stated / review-inferred / directly demonstrated |

## 8. Evidence tiers

- **E1 — direct target-domain decision evidence:** paired closed-loop evaluator/target trials for multiple prespecified policies, uncertainty reported, and claim scope explicit.
- **E2 — direct component or inferential evidence:** intervention tests, policy-value/ranking comparisons, finite-sample bounds, or formal guarantees that discharge one or more contract obligations but not the full transport claim.
- **E3 — indirect diagnostic evidence:** visual realism, one-step prediction, action following, simulator-only robustness, or internal numerical consistency.
- **E4 — conceptual/current-landscape evidence:** survey, position, workshop, standard, project page, or corporate report; used for framing or practice, not as sole support for effectiveness.

Evidence tier is not a global quality score. A source may provide E1 evidence for a narrow claim and no evidence for a broader one.

## 9. Bias and applicability appraisal

For every empirical evaluator paper, code:

- whether the evaluated policies were prespecified before target-domain testing;
- whether simulator development or hyperparameter selection used the same target evaluations later reported as validation;
- the number and diversity of policies, tasks, scenes, embodiments, and target trials;
- whether uncertainty accounts for task/policy dependence and multiple comparisons;
- whether reward/success labels are human, scripted, VLM-based, or learned and whether their error is separately measured;
- whether action-following and OOD behavior are directly tested;
- whether evaluator failure could change policy order without visibly degrading rollouts;
- whether code, environment versions, seeds, and protocol are available.

## 10. Synthesis method

The review uses argument-based narrative synthesis rather than pooled effect sizes because evaluator types, policy sets, tasks, metrics, and target anchors are not commensurate. Sources are organized by the evaluation claim they attempt to support, not by simulator brand or paper chronology.

The synthesis has four products:

1. a claim taxonomy from trace plausibility to deployment decisions;
2. an evidence-contract matrix stating the obligations associated with each claim;
3. an insufficiency map linking common proxies to counterexamples and missing witnesses;
4. a reporting checklist for future robot-policy evaluation studies.

## 11. Protocol deviations and update rule

Any later change to inclusion criteria, evidence tiers, or the central claim must be versioned in this non-authoritative protocol with a reason and date. The manuscript must report the search cutoff and describe the review as structured/scoping rather than systematic unless database-complete screening, duplicate review, and a reproducible flow record are later added.

