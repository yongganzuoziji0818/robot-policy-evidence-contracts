# Initial literature matrix: simulator/world-model evidence for robot-policy evaluation

**Version:** 0.1, search cutoff 2026-07-21  
**Status:** active public-literature audit  
**Interpretation:** `verified` means that title, year, and identifier were checked against an official proceedings page, DOI landing page, standard page, OpenReview, or arXiv record. It does not mean that full-text extraction is complete.

## A. Direct robot-policy evaluator studies

| ID | Source | Evaluator and target claim | Evidence used | What it supports | Main sufficiency limit | Tier / status |
|---|---|---|---|---|---|---|
| R01 | Li et al., [Evaluating Real-World Robot Manipulation Policies in Simulation](https://proceedings.mlr.press/v270/li25c.html), CoRL/PMLR 2025 (SIMPLER) | physics/visual real-to-sim evaluator; policy performance and ranking | paired real/sim trials, Pearson correlation, MMRV, distribution-shift analyses | bounded ranking agreement for tested policies/tasks | finite tested set; correlation is not absolute calibration or post-selection guarantee | E1, verified |
| R02 | Li et al., [SIMPLER project and protocol](https://simpler-env.github.io/) | same as R01 | protocol details, roughly 1,500 paired episodes, visual/control matching | reproducibility and metric interpretation | project page is supplementary, not independent validation | E4 supplement, verified |
| R03 | Li et al., [WorldEval: World Model as Real-World Robot Policies Evaluator](https://arxiv.org/abs/2505.19017), 2025 | learned video world model; policy ranking and safety detection | paired evaluations, Policy2Vec conditioning, rank correlation | feasibility of learned evaluator for tested policy/task set | archival peer review not verified; reward and action-following errors remain part of evaluator | E1/E3, verified preprint |
| R04 | Quevedo et al., [WorldGym: World Model as An Environment for Policy Evaluation](https://arxiv.org/abs/2506.00613), 2025, v3 | action-conditioned video world model; policy value/ranking | Monte Carlo policy rollouts, VLM reward, and real-policy comparisons | policy success correlation and relative ranking for the tested VLA policies | the current abstract still identifies realistic object interaction as difficult; VLM reward and policy/task coverage remain part of the evidence chain | E1/E2, verified preprint |
| R05 | Abou-Chakra et al., [Real-is-Sim](https://arxiv.org/abs/2504.03597), 2025 | dynamic digital twin; offline policy evaluation | PushT simulator/real success correlation | task-specific digital-twin evaluation | narrow task and tightly coupled deployment architecture | E1, verified preprint |
| R06 | Yu et al., [Validate on Sim, Detect on Real](https://arxiv.org/abs/2111.00765), 2021 | randomized simulator plus real OOD detector; policy model selection | simulation score combined with OOD score | selection signal can improve with a target-domain diagnostic | not a simulator-only sufficiency result; ranking depends on OOD detector validity | E2, verified preprint |
| R07 | PolaRiS, [Scalable Real-to-Sim Evaluations for Generalist Robot Policies](https://arxiv.org/abs/2512.16881), 2025 | reconstructed real-to-sim evaluator; generalist policy ranking | paired simulator/real evaluations and rank correlation | scalability of reconstructed evaluation | current record is preprint; construction and target-data reuse require selection-bias audit | E1, verified preprint |
| R08 | Jangir et al., [RobotArena Infinity](https://openreview.net/forum?id=OutljIofvS&noteId=G41zT4Zecs), ICLR 2026 | scalable real-to-sim benchmark | continuously reconstructed scenes and reproducible policy comparisons | scalable benchmark construction | benchmark scale does not itself establish target-domain transport for untested policy families | E2/E4, verified archival page |
| R09 | Yang et al., [Robot Policy Evaluation for Sim-to-Real Transfer: A Benchmarking Perspective](https://openreview.net/forum?id=WzNxyd14Sh), RSS workshop 2025 | benchmark methodology | high visual fidelity, task complexity, perturbations, sim-real alignment | useful desiderata and scope axes | perspective/workshop evidence; not a sufficiency theorem or broad paired validation | E4, verified |
| R10 | Badithela et al., [Reliably Augmenting Real-World Tests with Simulation for Scalable Robot Policy Evaluation](https://openreview.net/forum?id=x2u6sU04GZ), SAFE-ROL 2025 | hybrid real/simulation inference | non-asymptotic confidence intervals combining real and simulation evidence | directly targets finite-sample real performance inference | workshop record; assumptions and dependence structure require full-text extraction | E2, verified |
| R11 | Gemini Robotics Team, [Evaluating Gemini Robotics Policies in a Veo World Simulator](https://veo-robotics.github.io/), arXiv:2512.10675, 2025 | video world simulator; ID/OOD ranking and safety red teaming | 1,600+ real evaluations, eight checkpoints, five tasks, paired rank/degradation analyses | strong current example of policy-in-the-loop world-model evaluation | project/preprint route; closed source and narrow policy provenance may limit independence | E1/E4, official project page and arXiv identifier verified |
| R12 | Runway Robotics, [Accelerating Robot Policy Evaluation with General World Models](https://runwayml.com/research/accelerating-robot-policy-evaluation), 2026 | general world model; policy ranking | eight policies, 1,450 simulated rollouts, human progress ratings, Pearson/MMRV | current industrial evidence of rank agreement | corporate grey literature; no independent peer review; claim limited to ranking and tested embodiment/tasks | E4, verified grey literature |

## B. Direct methodological predecessors and current reviews

| ID | Source | Core contribution | Relevance to this review | Boundary for our contribution | Tier / status |
|---|---|---|---|---|---|
| M01 | Yu et al., [How Should World Models Be Evaluated for Embodied Decision-Making? A Decision-Making-Centric Position](https://arxiv.org/abs/2606.15032), 2026 | L0–L7 ladder from artifact diagnostics to policy optimization; action fidelity, ranking, exploitation, uncertainty | closest direct predecessor for decision-centered world-model evaluation | our manuscript must not reproduce a generic ladder; it must add claim-relative contracts across physics simulators and learned models, execution semantics, post-selection validity, and minimal witnesses | E4, verified preprint |
| M02 | Hou et al., [World Model for Robot Learning: A Comprehensive Survey](https://arxiv.org/abs/2605.00080), 2026 | broad taxonomy of world models for robot learning, planning, simulation, evaluation, and data generation | maps the world-model landscape and sources | our scope is narrower and inferential: when evaluator evidence is sufficient for a policy claim | E4, verified preprint |
| M03 | Yang et al., [The Reality Gap in Robotics: Challenges, Solutions, and Best Practices](https://www.annualreviews.org/content/journals/10.1146/annurev-control-031924-100130), Annual Review of Control, Robotics, and Autonomous Systems, 2026 | survey of reality-gap causes, solutions, metrics, and practice | establishes mature sim-to-real background | our review is not another transfer-technique survey; it evaluates evidence claims | E4, verified journal page |
| M04 | ASME, [V&V 40-2018](https://www.asme.org/codes-standards/find-codes-standards/assessing-credibility-of-computational-modeling-through-verification-and-validation-application-to-medical-devices) | credibility should be commensurate with model reliance, context of use, and decision consequence | foundational claim-relative credibility principle | medical-device examples do not directly specify robot-policy ranking/selection witnesses | E4 standard, verified |
| M05 | FMI, [Functional Mock-up Interface Specification](https://fmi-standard.org/docs/main/) | interfaces and execution responsibilities for model exchange, co-simulation, and scheduled execution | shows that execution semantics are part of evaluator identity | specification compliance alone does not establish target-domain policy validity | E4 standard, verified |

## C. Decision-aware models, exploitation, and model adequacy

| ID | Source | Result used in synthesis | Contract implication | Tier / status |
|---|---|---|---|---|
| T01 | Grimm et al., [The Value Equivalence Principle for Model-Based Reinforcement Learning](https://papers.nips.cc/paper/2020/hash/3bb585ea00014b0e3ebe4c6dd165a358-Abstract.html), NeurIPS 2020 | model adequacy can be defined relative to policy/function sets and Bellman updates rather than global transition fidelity | the relevant policy/function class must be named; predictive fidelity is neither necessary nor sufficient for every decision claim | E2 theory, verified |
| T02 | Lambert et al., [Objective Mismatch in Model-based Reinforcement Learning](https://proceedings.mlr.press/v120/lambert20a.html), L4DC 2020 | one-step predictive likelihood need not correlate with downstream control performance | artifact/prediction metrics cannot discharge value or ranking obligations alone | E2 empirical/conceptual, verified |
| T03 | Muratore et al., [Domain Randomization for Simulation-Based Policy Optimization with Transferability Assessment](https://proceedings.mlr.press/v87/muratore18a.html), CoRL 2018 | simulator policy search can maximize simulation optimization bias; SPOTA estimates bias and supplies a stopping rule | evaluator reuse for policy optimization creates a stronger post-selection contract than fixed-policy ranking | E2 direct robotics, verified |
| T04 | Janner et al., [When to Trust Your Model? Better Data, Better Models, Better Policy](https://proceedings.neurips.cc/paper/2019/hash/5faf461eff3099671ad63c6f3f094f7f-Abstract.html), NeurIPS 2019 | model error and rollout horizon jointly control performance error; short rollouts can reduce compounding bias | rollout horizon and uncertainty are part of the evidence scope | E2 theory/empirical, verified |
| T05 | Yu et al., [MOPO](https://proceedings.neurips.cc/paper_files/paper/2020/hash/a322852ce0df73e204b7e67cbbef0d0a-Abstract.html), NeurIPS 2020 | uncertainty penalties construct a pessimistic model objective | uncertainty must affect the decision, not only be plotted | E2 theory/algorithm, verified |
| T06 | Kidambi et al., [MOReL](https://proceedings.neurips.cc/paper/2020/hash/f7efa4f864ae9b88d43527f4b14f750f-Abstract.html), NeurIPS 2020 | unknown regions are handled through a pessimistic MDP with performance guarantees | support violations need explicit decision treatment | E2 theory/algorithm, verified |
| T07 | Sun et al., [Constrained Reinforcement Learning Under Model Mismatch](https://proceedings.mlr.press/v235/sun24d.html), ICML 2024 | mismatch can invalidate constraints satisfied in a training model; robust constrained optimization supplies worst-case guarantees | reward ranking and safety screening are distinct claims with different losses | E2 theory, verified |

## D. Statistical selection, calibration, and transport

| ID | Source | Result used in synthesis | Contract implication | Tier / status |
|---|---|---|---|---|
| S01 | Dwork et al., [Generalization in Adaptive Data Analysis and Holdout Reuse](https://proceedings.neurips.cc/paper_files/paper/2015/hash/bad5f33780c42f2588878a9d07405083-Abstract.html), NeurIPS 2015 | adaptive reuse of a holdout can overfit the holdout | repeatedly tuning policies against one evaluator/real anchor invalidates naive fixed-query uncertainty | E2 theory, verified |
| S02 | Yin et al., [Near-Optimal Provable Uniform Convergence in Off-Policy Evaluation for a Finite Policy Class](https://proceedings.mlr.press/v130/yin21a.html), AISTATS 2021 | data-dependent policy choice requires simultaneous/uniform rather than pointwise OPE control | finite policy selection requires family-wise or uniform evidence | E2 theory, verified |
| S03 | Kennedy and O'Hagan, [Bayesian Calibration of Computer Models](https://doi.org/10.1111/1467-9868.00294), JRSS B 2001 | separates calibration parameters, discrepancy, and uncertainty | fitted parameters do not erase model discrepancy | E2 foundational, DOI verified |
| S04 | Oliver et al., [Validating Predictions of Unobserved Quantities](https://doi.org/10.1016/j.cma.2014.08.023), CMAME 2015 | validation on observed quantities need not validate an unobserved quantity of interest | target policy value/risk is a QoI requiring its own transport argument | E2 theory/methodology, DOI verified |
| S05 | Williams et al., [Assessing Model Equifinality for Robust Policy Analysis](https://doi.org/10.1016/j.envsoft.2020.104831), Environmental Modelling & Software 2020 | multiple calibration-equivalent models can yield different policy conclusions | calibration fit alone cannot certify a unique policy ranking | E2 methodology, DOI verified |
| S06 | Khan et al., [Off-policy Evaluation Beyond Overlap](https://proceedings.mlr.press/v235/khan24b.html), ICML 2024 | without overlap, policy value may be partially identifiable under additional smoothness structure | support gaps must be reported as bounds/partial identification, not hidden by point estimates | E2 theory, verified |

## E. Execution and numerical semantics

| ID | Source | Result used in synthesis | Contract implication | Tier / status |
|---|---|---|---|---|
| X01 | Cremona et al., [Hybrid Co-simulation: It's About Time](https://doi.org/10.1007/s10270-017-0633-6), Software and Systems Modeling 2019 | continuous/discrete-time semantics and master coordination can be underspecified | evaluator execution semantics must be versioned and tested when event order can affect policy outcomes | E2 methodology, DOI verified |
| X02 | Hansen et al., [The FMI 3.0 Standard Interface for Clocked and Scheduled Simulations](https://doi.org/10.3390/electronics11213635), Electronics 2022 | model-exchange, co-simulation, and scheduled-execution interfaces allocate solver/scheduler responsibilities differently | interface portability is not behavioral equivalence | E2 methodology, DOI verified |
| X03 | Sadjina et al., [Energy Conservation and Power Bonds in Co-Simulations](https://doi.org/10.1007/s00366-016-0492-8), Engineering with Computers 2017 | residual power/energy exposes coupling error from exchanged variables | conservation residual is a valuable witness but not a complete policy-ranking certificate | E2 methodology, DOI verified |
| X04 | Chen et al., [Explicit Parallel Co-Simulation Approach](https://doi.org/10.1007/s11044-021-09785-x), Multibody System Dynamics 2021 | energy-preserving coupling can still produce incorrect results | one invariant cannot discharge all execution-integrity obligations | E2 methodology, DOI verified |

## F. Preliminary saturation and gap judgment

The direct literature already covers each isolated idea needed by the review: real-to-sim ranking, world-model policy evaluation, action-following diagnostics, decision-centric metric ladders, value equivalence, objective mismatch, model exploitation, context-of-use credibility, and finite-sample inference. Accordingly, publishability cannot rest on introducing any one of these concepts.

The remaining review-level gap is narrower but defensible as a synthesis question:

1. direct robot-evaluator papers usually validate one pipeline and one policy/task set;
2. world-model reviews organize architectures or metric levels;
3. V&V standards organize model credibility by context of use but do not specify robot-policy ranking and selection;
4. RL theory separates value equivalence, support, pessimism, and post-selection effects, but these results are not routinely translated into evaluator reporting obligations;
5. numerical and semantic verification is largely disconnected from learned-world-model evaluation discourse.

The manuscript should therefore organize the field by **evaluation claim and missing inference**, not by model family. The core deliverable is a falsifiable mapping from claim to required contracts and witnesses.

## G. Full-text extraction backlog

Before submission, the following must be completed:

- full-text coding of R01–R11 and M01–M05 using the extraction schema in the protocol;
- verify archival status and final author lists for R03–R07 and R11;
- extract exact policy/task/trial counts and uncertainty procedures rather than relying on abstracts/project pages;
- code whether target-domain trials were used during simulator construction or policy selection;
- check citation chaining for value-aware model learning and simulator validation in robotics;
- perform retraction/expression-of-concern screening and DOI metadata normalization;
- add a transparent flow count for records identified, screened, excluded, and retained.
