# Seismosaic

Seismosaic brings earthquake catalogue entries, ionospheric observations, geomagnetic indices and solar measurements into a shared semantic model. It reuses the [Alertissimo metamodel](metamodel.md) and defines a geophysical vocabulary that preserves each source's quantities, temporal support, units, quality and provenance.

The project combines a draft ontology, documented source interfaces and a working prototype with fixed requests. A `study` collects heterogeneous scientific records for inspection and comparison. Selection rules and analysis belong to the workflow layer; collection membership and proximity in time or space do not establish correlation or causation.

## A working example: Kamchatka

The [Kamchatka demo](docs/kamchatka_demo.md) builds a study around the magnitude 8.8 earthquake of 29 July 2025. It retrieves historical data through the providers' programmatic access routes and presents the output in an expandable, JSON-like browser view.

| Source | Data represented |
| --- | --- |
| USGS, EMSC and GFZ GEOFON | Earthquake catalogue reports with origin and magnitude estimates |
| GIRO/DIDBase | Ionogram-derived foF2 and hmF2: F2-layer critical frequency and peak height |
| GFZ | Kp and ap geomagnetic activity indices over three-hour intervals |
| NOAA GOES-18 | X-ray Sensor (XRS) irradiance in two wavelength bands |
| IAEA CollisionDB | Two oxygen electron-impact ionization reference datasets: cross-sections and rate coefficients |

Each source has its own retrieval result. Missing values, gaps, unavailable stations and partial responses remain visible. Live results may change as providers revise their products; retained responses support replay.

The [study visuals](docs/visuals.md) provide an example of using the semantic output:

- Coordinated UTC panels show earthquake reports, foF2/hmF2, Kp/ap and GOES XRS, retaining their separate units and temporal support.
- Separate CollisionDB curves show native X/Y coordinates, reported uncertainties, fit domains and citations.
- A coverage table and source-record pickers connect the figures to the underlying records. PNG and SVG exports support reuse outside the viewer.

Figures can be regenerated from a saved study without provider requests. They show the retrieved context, without interpolation across gaps or a computed correlation result.

### Where collisional data fits

CollisionDB data is included provisionally as physical reference material. It is **not yet correlated with the earthquake, ionospheric or space-weather observations**, and its presence in a study does not mean a physical model has used it.

These curves describe a collision process as a function of a native coordinate, rather than an Earth observation at a time and place. Connecting them to the observations would require a specified physical model, appropriate atmospheric inputs and documented derivation of its outputs. That calculation is not implemented. The [standalone reference demo](docs/collisiondb_demo.md) also retrieves the same datasets through the official `pycollisiondb` client.

## The semantic model

The model follows established source concepts: a focused QuakeML projection for seismic estimates, SAO/URSI conventions for ionospheric characteristics, and the definitions of GFZ's Kp/ap products. [Standards alignment](docs/standards.md) documents the boundaries of these projections.

The `study` root collects event, observation, time-series, summary and reference-data record forms. Concrete specializations retain domain names such as `seismic_event`, `ionospheric_observation`, `geomagnetic_index` and `solar_observation`.

- Seismic entries retain multiple origins, with associated magnitudes nested under each origin. Missing or unresolved associations remain explicit. Preferred origin and magnitude choices are independent, and creation metadata stays at its reported event or estimate scope.
- Named quantities such as foF2, hmF2, Kp and ap compose shared scalar contents while retaining their definitions and units. GOES XRS uses a parameterized wavelength-band namespace.
- Concrete series specialize `time_series`, allowing a study to reference a common series form. Container inheritance is an explicit local metamodel extension.
- Station, satellite and instrument details describe acquisition provenance. Producer and delivery-channel qualifiers distinguish scientific responsibility from the route through which data arrived.
- Collision datasets specialize `reference_data`; their tables declare X/Y axes and preserve native coordinates, units, uncertainty, citations and fit metadata. They have no Earth-observation time axis.

The ontology is a draft declaration of scientific output. The fixed demos implement small provider projections; they do not interpret the ontology or provide a generic workflow planner or analysis engine.

## Repository guide

| File or directory | Purpose |
| --- | --- |
| [ontology.yaml](ontology.yaml) | Draft domain vocabulary and output structure |
| [metamodel.md](metamodel.md) | Notation, composition and specialization rules |
| [endpoints/](endpoints/) and [mappings/](mappings/) | Declarative access profiles and source-to-output paths |
| [demo/](demo/) | Fixed retrieval scenarios, saved-output handling and browser viewer |
| [Source notes](docs/sources.md) and [interfaces](docs/interfaces.md) | Reviewed access routes, constraints and unresolved bindings |
| [Modelling decisions](docs/model_decisions.md) | Design choices and open questions |
| [UPSTREAM.md](UPSTREAM.md) | Alertissimo metamodel provenance and local extensions |

The ontology uses ordered YAML-like notation: repeated directives and scope are meaningful, so it must not be round-tripped through an ordinary YAML loader. Endpoint and mapping files use ordinary YAML and are documentation, not an executable mapping language.

## Development

Keep ontology declarations, source mappings and accompanying notes consistent. Document shared metamodel changes separately from domain choices. The [contributor instructions](AGENTS.md) define the current scope; the demo guides provide setup, run and local validation commands.

## Licence

BSD 3-Clause; see [LICENCE](LICENCE). The metamodel is derived from Alertissimo. Scientific datasets retain their providers' own licences, citations and acknowledgement requirements.
