# Research basis

Pinjia He, Jieming Zhu, Zibin Zheng, and Michael R. Lyu. **Drain: An Online Log
Parsing Approach with Fixed Depth Tree.** Proceedings of the 2017 IEEE 24th
International Conference on Web Services (ICWS), pp. 33–40.
[DOI: 10.1109/ICWS.2017.13](https://doi.org/10.1109/ICWS.2017.13).

- [Author-hosted paper](https://pinjiahe.github.io/files/pdf/research/ICWS17.pdf)
- [CUHK publication record, classified as peer-reviewed](https://research.cuhk.edu.hk/en/publications/drain-an-online-log-parsing-approach-with-fixed-depth-tree-2/)
- [Copied implementation: Drain3](https://github.com/logpai/Drain3/tree/0fb6d6e1828838fa05c8f6fa5cda878e02ea79c7)

The paper motivates grouping free-text log messages into templates through a
fixed-depth parsing tree. This repository executes a copied Drain3 core based on
that method. The service/level extraction, batch comparison, report formats and
offline interface are additions in this repository.

The publication includes a separate downstream anomaly-detection case study.
This repository implements template grouping and count comparison only. A new
template group means it was not observed in the selected baseline; it is a cue
for human review, not an anomaly judgment.

The paper's dataset evaluation is not a measurement of this repository. Local
tests validate defined examples and source behavior; they do not establish
production-log grouping accuracy, detection precision or incident outcomes.

