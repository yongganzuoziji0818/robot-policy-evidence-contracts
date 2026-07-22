# Robot Policy Evidence Contracts

Python research code for auditable robot-policy risk analysis, continual adaptation, finite-sample certification, and pre-execution feasibility checks.

This repository is the public code distribution extracted from the continual-risk-adaptation project. It contains implementation modules and their unit tests. Manuscripts, review protocols, evidence ledgers, submission figures, private data, checkpoints, results, experiment runners, and execution-authorization files are intentionally excluded.

## Packages

- `agc_aerotrace`: deterministic terrain and analytic trace primitives.
- `agc_basil`: asset validation and static pre-execution feasibility checks.
- `agc_bastion`: finite-cover certificates and deterministic development models.
- `agc_continual`: PyTorch continual-adaptation environments and training utilities.
- `agc_fence`: information-contract auditing with numerical evaluation utilities.
- `agc_flux`: source/deposition identifiability models and synthetic simulators.
- `agc_rlrd`: protocol objects, safety-debt metrics, planning, guards, and certificates.
- `agc_saver`: PyTorch hazard-memory environments and diagnostics.
- `agc_scope`: deterministic capacity and theory utilities.

The code is research software. It is not validated deployment software, a robot-safety certification standard, or evidence of empirical superiority.

## Installation

Python 3.10 or newer is required.

```bash
python -m pip install -e .
```

The continual-learning and SAVER modules additionally require PyTorch:

```bash
python -m pip install -e ".[torch]"
```

For development and tests:

```bash
python -m pip install -e ".[test,torch]"
python -m pytest
```

## Repository layout

```text
src/       Python packages
tests/     Unit and invariant tests
```

## Scientific boundary

The BASIL package exposes a static feasibility audit; it does not include a runner. The frozen BASIL-v9.4 empirical route remains at `N0_PREEXECUTION_SCIENTIFIC_FAIL_STOP_IMPOSSIBLE_SUPERIORITY_GATE`. Publishing or testing this source code does not authorize replay, N0 execution, threshold changes, pair substitution, or a new empirical run.

## Citation

Software citation metadata is provided in [`CITATION.cff`](CITATION.cff). Earlier Zenodo releases archived manuscript-oriented companion materials and should not be interpreted as archives of this corrected code-only tree. A new code-only release should be minted before assigning a software-version DOI.

## License

The code in this repository is released under the [MIT License](LICENSE).
