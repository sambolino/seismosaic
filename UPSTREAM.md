# Upstream provenance

Seismosaic reuses the documentation metamodel from [sambolino/alertissimo](https://github.com/sambolino/alertissimo).

- Source commit: `7dcff34ecc7320afd1fcd97247d60abe1fde6c61`.
- [Source metamodel](https://github.com/sambolino/alertissimo/blob/7dcff34ecc7320afd1fcd97247d60abe1fde6c61/alertissimo/data_layer/semantic_model/metamodel.md).
- [Source astronomy ontology](https://github.com/sambolino/alertissimo/blob/7dcff34ecc7320afd1fcd97247d60abe1fde6c61/alertissimo/data_layer/semantic_model/ontology.yaml).
- Source metamodel Git blob: `42fd3d3f8942e8100f61091c073d9a1d429a3480`.
- [Source licence](https://github.com/sambolino/alertissimo/blob/7dcff34ecc7320afd1fcd97247d60abe1fde6c61/LICENCE).

The extracted sections of local metamodel.md preserve the upstream specification wording. Its first relative link to the astronomy ontology has been replaced by an absolute link to that ontology at the source commit. The astronomy names elsewhere remain illustrative upstream examples.

The separately labelled local extension in metamodel.md proposes single-parent container specialization, polymorphic references and non-conflicting content refinement. It also distinguishes these from projection-based composition and parameterized namespaces. This extension is documented for the Seismosaic prototype; it is not part of the pinned upstream source and has not been implemented in an interpreter or applied to the Alertissimo repository.

The reference to metamodel.md is a specification dependency. It is not a runtime import, package dependency or machine-readable metamodel.

Seismosaic's ontology.yaml is a new domain draft. It does not copy the astronomical record families, Portfolio root or L0–L8 domain profile. Changes to generic notation should be considered separately from changes to this domain model.

The BSD 3-Clause licence and upstream copyright notice are retained.
