# Robot Policy Evidence Contracts

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21477786.svg)](https://doi.org/10.5281/zenodo.21477786)

Public companion materials for the manuscript **“Evidence Sufficiency for AI-Based Robot Policy Evaluation: From Physics Simulators to Learned World Models.”**

The project develops a claim–contract–witness framework for assessing what physics simulators, reconstructed digital twins, and learned world models can support when they are used to evaluate, rank, select, optimize, or safety-screen robot policies.

## Repository contents

- `manuscript.md` — current *Artificial Intelligence Review*-targeted internal manuscript draft;
- `review_protocol.md` — scope, search, screening, and evidence-coding protocol;
- `evidence_matrix.md` — claim-relative literature and source ledger;
- `claim_map.md` — mapping between manuscript claims, contracts, and evidence;
- `figures/` — conceptual figures in SVG and PNG plus deterministic generation source.

## Evidence boundary

This repository contains a structured critical review and theoretical framework. It does not contain new robot experiments, and the framework is not an empirically validated certification standard. The current literature corpus is purposive and remains subject to a targeted update and author-level full-text verification before journal submission.

## Reproducibility

The conceptual figures can be regenerated with Node.js:

```powershell
node figures/generate_review_figures.js
```

The SVG files are the vector sources; PNG files are review copies.

## Authors

Yuan Liao, Hui Liu, Jiliang Tu, Jing Jiang, Zaihong Wan, Jianbo Gao, Ting Fang, and Zhiwei Hu — School of Information Engineering, Nanchang Hangkong University, China.

## Status

Internal review release. No journal submission or acceptance is implied.

## Archival release

- GitHub release: [v0.1.0](https://github.com/yongganzuoziji0818/robot-policy-evidence-contracts/releases/tag/v0.1.0)
- Version DOI: [10.5281/zenodo.21477786](https://doi.org/10.5281/zenodo.21477786)
- Concept DOI (all versions): [10.5281/zenodo.21477785](https://doi.org/10.5281/zenodo.21477785)

## License

The manuscript, review protocol, evidence matrix, claim map, and figure files are licensed under [CC BY 4.0](LICENSE-CONTENT.md). The figure-generation source code is licensed under the [MIT License](LICENSE-CODE.md). See [LICENSE.md](LICENSE.md) for the file-level allocation.
