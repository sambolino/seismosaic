# Seismosaic

Seismosaic is an early semantic modelling project for seismic events, ionospheric observations and their geophysical context. It reuses the [Alertissimo metamodel](metamodel.md) while defining its own domain vocabulary.

The initial work concerns how these different kinds of scientific data can be described together, with their quantities, time support, locations, quality and provenance intact. Temporal or spatial selection for comparison does not establish a physical or causal relationship.

Established domain concepts guide the model: a small QuakeML projection for seismic estimates, SAO/URSI conventions for ionospheric information, and the definitions of GFZ's official Kp/ap products. The focus is their representation together and the explicit basis for comparisons across these data families.

## Start here

- [ontology.yaml](ontology.yaml): a small draft domain model for discussion.
- [metamodel.md](metamodel.md): the reused notation and composition specification.
- [Source notes](docs/sources.md): candidate interfaces and illustrative field mappings.
- [Standards alignment](docs/standards.md): reused concepts, format boundaries and projection limits.
- [Modelling decisions](docs/model_decisions.md): the initial choices and questions still open.
- [Upstream provenance](UPSTREAM.md): the exact Alertissimo source of the metamodel.

This repository starts with model declarations and documentation. The ontology is ordered YAML-like notation with meaningful repeated directives. It is not an ordinary YAML configuration file.

## Initial scope

The draft describes seismic catalogue entries with multiple origin and magnitude estimates, observing stations, ionogram-derived ionospheric characteristics, and geomagnetic indices. A provisional `study` root collects source-qualified records for a research comparison. Its role and name remain open for review.

USGS and EMSC supply the reviewed earthquake examples; GFZ supplies a concrete geomagnetic interval example. GIRO/DIDBase is the candidate ionospheric source, with a successful response and station coverage still to be confirmed. GOES XRS remains complementary solar context.

The short-visit work is to refine this fragment with the host, review a small number of source mappings and record unresolved questions. No runtime, ontology interpreter, API adapters, DSL, analysis pipeline or correlation result is implemented here.

## Development

Edit the ontology and accompanying notes together. Keep changes to the shared metamodel explicit and separate from domain modelling. The [contributor instructions](AGENTS.md) define the current project scope.

## Licence

BSD 3-Clause; see [LICENCE](LICENCE). The metamodel is derived from Alertissimo. Scientific datasets retain their providers' own licences and acknowledgement requirements.
