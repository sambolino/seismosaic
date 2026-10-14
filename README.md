# Seismosaic

Seismosaic is an early semantic modelling project for seismic events, ionospheric observations and their geophysical context. It reuses the [Alertissimo metamodel](metamodel.md) while defining its own domain vocabulary.

The initial work concerns how these different kinds of scientific output can be described together, with their quantities, time support, acquisition context, quality and provenance intact. Selection patterns and comparison windows belong to the workflow layer. Membership in the output collection does not establish a physical or causal relationship.

Established domain concepts guide the model: a small QuakeML projection for seismic estimates, SAO/URSI conventions for ionospheric information, and the definitions of GFZ's official Kp/ap products. The focus is their representation together and the explicit basis for comparisons across these data families.

## Start here

- [ontology.yaml](ontology.yaml): a small draft domain model for discussion.
- [metamodel.md](metamodel.md): the reused notation and composition specification.
- [Source notes](docs/sources.md): candidate interfaces and illustrative field mappings.
- [Endpoints and mappings](docs/interfaces.md): declarative access profiles and source-to-output paths, with unresolved bindings labelled.
- [Fixed live Kamchatka demo](docs/kamchatka_demo.md): historical live retrieval and an expandable HTML view of a `study`.
- [Fixed CollisionDB reference demo](docs/collisiondb_demo.md): two oxygen datasets through the official Python client, in the same viewer.
- [Standards alignment](docs/standards.md): reused concepts, format boundaries and projection limits.
- [Modelling decisions](docs/model_decisions.md): the initial choices and questions still open.
- [Upstream provenance](UPSTREAM.md): the exact Alertissimo source of the metamodel.

This repository starts with model declarations, endpoint/mapping descriptions and documentation. The ontology is ordered YAML-like notation with meaningful repeated directives. It is not an ordinary YAML configuration file. The separate `endpoints/` and `mappings/` files use ordinary YAML; they describe reviewed interfaces without implementing an adapter or mapping interpreter.

## Initial scope

The `study` root collects generic event, observation, time-series and summary record forms. Their concrete specializations retain domain names: `seismic_event`, `ionospheric_observation`, `geomagnetic_index`, `solar_observation`, and the corresponding series. Seismic entries keep multiple origins, each containing its associated magnitudes. Missing associations remain explicit, while event and estimate creation metadata retain their own scope. Station, satellite and instrument information is acquisition provenance rather than a compulsory station registry.

Named quantities such as foF2, hmF2, Kp and ap compose shared scalar contents while retaining their definitions and units. GOES XRS irradiance uses a parameterized wavelength-band namespace. Series specialize a common `time_series` form, so the root can reference that form without listing every concrete series. This uses a separately documented local metamodel extension; it does not add runtime inheritance or a parser.

USGS, EMSC and GEOFON supply earthquake catalogue entries; GFZ supplies Kp/ap intervals. The fixed Kamchatka demo also retrieves ionogram-derived foF2/hmF2 through GIRO's historical form and GOES-18 science-quality XRS daily products. Source coverage, missing values and product context remain explicit.

The root also collects `reference_data`, specialized as `collision_dataset`. Its cross-section/rate curves compose shared table contents and retain native coordinates, units, uncertainty, citations and fit metadata. These physical reference inputs have no Earth-observation time axis; no model calculation or Kamchatka association is asserted.

The short-visit work is to refine this fragment with the host, review a small number of source mappings and record unresolved questions. A small fixed-request runtime demo now tests these output declarations. There is no generic planner, ontology interpreter, DSL, statistical analysis or correlation result.

## Development

Edit the ontology and accompanying notes together. Keep changes to the shared metamodel explicit and separate from domain modelling. The [contributor instructions](AGENTS.md) define the current project scope.

## Licence

BSD 3-Clause; see [LICENCE](LICENCE). The metamodel is derived from Alertissimo. Scientific datasets retain their providers' own licences and acknowledgement requirements.
