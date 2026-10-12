# Seismosaic contributor instructions

## Goal

Develop a small semantic model for seismic and ionospheric data using the existing Alertissimo metamodel.

## Current scope

- Work on domain declarations, source mapping notes and modelling decisions.
- Do not add runtime classes, an ontology parser or iterator, API adapters, orchestration, a DSL or statistical analysis without an explicit change of scope.
- Seismosaic defines its own structural root and record families; do not assume an Alertissimo Portfolio.
- Keep source mappings distinct from the semantic vocabulary.
- Preserve physical distinctions between earthquake events, measured or derived ionospheric characteristics, contextual indices and possible future physical-model inputs.
- Record temporal support, coordinate or depth references where known, units, quality and provenance.
- An association or comparison edge does not establish causality.

## Metamodel

- Follow metamodel.md. See UPSTREAM.md for its source and the one local link adjustment.
- The notation is ordered and YAML-like. Repeated directives and scope are meaningful. Do not round-trip ontology.yaml through an ordinary YAML loader or dumper.
- Do not invent a metamodel import directive or change notation rules to accommodate a domain-specific modelling choice.
- Propose changes to generic notation separately and document their upstream relationship.
- The initial ontology is a draft, not an executable or fully validated schema.

## Verification

Review model and mapping changes for consistent paths, source meanings and units. Do not introduce a test or CI framework solely for these documentation and model files.
