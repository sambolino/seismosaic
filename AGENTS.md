# Seismosaic contributor instructions

## Goal

Develop a small semantic model for seismic and ionospheric data using the existing Alertissimo metamodel.

## Current scope

- Work on domain declarations, declarative endpoint/mapping descriptions, source review notes and modelling decisions.
- Model scientific output. Keep selection patterns, comparison frames and analysis instructions in the workflow layer; do not embed them in this ontology.
- Do not add runtime classes, an ontology parser or iterator, API adapters, orchestration, a DSL or statistical analysis without an explicit change of scope.
- Seismosaic defines its own structural root and record families; do not assume an Alertissimo Portfolio.
- Keep source mappings distinct from the semantic vocabulary.
- Keep provider query parameters in endpoints/ and response-to-output paths in mappings/. These are ordinary YAML descriptions, not an executable mapping DSL; mark unverified bindings explicitly.
- Preserve physical distinctions between earthquake events, measured or derived ionospheric characteristics, contextual indices and possible future physical-model inputs.
- Record temporal support, coordinate or depth references where known, units, quality and provenance.
- An association or comparison edge does not establish causality.

## Metamodel

- Follow metamodel.md. See UPSTREAM.md for its source, local link adjustment and explicitly labelled documentation extension.
- Use composition for shared quantity contents, parameterization for semantic namespaces, and container inheritance for record-form specialization. Keep these meanings distinct.
- The notation is ordered and YAML-like. Repeated directives and scope are meaningful. Do not round-trip ontology.yaml through an ordinary YAML loader or dumper.
- Do not invent a metamodel import directive or change notation rules to accommodate a domain-specific modelling choice.
- Propose changes to generic notation separately and document their upstream relationship.
- The initial ontology is a draft, not an executable or fully validated schema.

## Verification

Review model and mapping changes for consistent paths, source meanings and units. Do not introduce a test or CI framework solely for these documentation and model files.
