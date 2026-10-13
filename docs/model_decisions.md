# Modelling decisions

## Scope and notation

This ontology describes scientific output. Selection patterns, comparison windows, thresholds and analysis instructions belong to the workflow layer. The `study` root collects returned records; membership and time overlap make no scientific association claim.

Composition, parameterization and specialization have separate meanings. Quantity containers compose `<_quantity>` contents. GOES band names parameterize a shared irradiance structure. Record families specialize event, observation, time-series or summary forms with `$is`. The local metamodel extension defines polymorphic references and non-conflicting refinement; see [metamodel](../metamodel.md) and [upstream provenance](../UPSTREAM.md). No interpreter is implemented.

## Record forms

| Form | Concrete examples | Scientific contents |
| --- | --- | --- |
| `event` | `seismic_event` | Catalogue identity, source-qualified origin/magnitude estimates |
| `observation` | `ionospheric_observation`, `geomagnetic_index`, `solar_observation` | Values sharing one acquisition or product context and temporal support |
| `time_series` | `ionospheric_series`, `geomagnetic_series`, `solar_irradiance_series` | Point arrays with shared sample context and domain quantity containers |
| `summary` | `ionospheric_summary`, `solar_irradiance_summary` | Already reported aggregates, with statistic and derivation provenance |

The root references these generic forms. Concrete names stay in output paths. This is semantic specialization, not projection: `study.geomagnetic_series` does not acquire a `time_series` path segment.

The `<_sample_context>` projection shares identity, time, quality and provenance between observations and series points. Concrete series refine the inherited `points.items` content with named quantity references. That declares compatible contents; it does not require creating or reconstructing standalone observation records from an array.

A record or point should group only values with a genuinely shared context. Values with different acquisition times, support intervals or product provenance must not silently be combined. A multi-characteristic ionospheric acquisition or simultaneous XRS bands can retain quantity-specific quality and provenance.

## Scientific quantities and paths

foF2, hmF2, Kp and ap remain first-class named containers. They share scalar contents by composition, not a quantity inheritance hierarchy. Their definitions and units stay in the ontology. A local unit declaration refines an otherwise unspecified unit of the shared value/uncertainty field.

| Example path | Meaning |
| --- | --- |
| `study.seismic_event@producer:channel.origin.depth` | One source-reported origin depth, km |
| `study.ionospheric_observation@producer:channel.foF2.value` | Critical frequency, MHz |
| `study.geomagnetic_index@producer:channel.ap.value` | Equivalent-range index on the 2 nT scale |
| `study.ionospheric_series@producer:channel.points.hmF2.value` | Derived peak height in one series point, km |
| `study.solar_irradiance_series@producer:channel.points.irradiance.xrs_b.value` | Band-specific reported irradiance, W m-2 |
| `study.ionospheric_summary@producer:channel.foF2.statistic` | Meaning of a reported aggregate value, such as mean |

GOES `<{band}>` supplies a namespace for a common irradiance structure. It does not automatically resolve a quantity schema by name. The local aliases `xrs_a` and `xrs_b` have documented wavelength mappings in [source notes](sources.md); the original band label and limits can be retained. Unknown bands require their source definitions before being treated as a known canonical band.

A reported `statistic` describes the output value, not an instruction to calculate it. Counts belong in `summary.sample_count`, not in a frequency-valued field. No Kp averaging, magnitude conversion or other scientific calculation is implied by structural reuse.

## Seismic catalogue entries and estimates

`seismic_event` keeps the small QuakeML BED 1.2 projection: multiple origins and magnitudes, source-selected preference, optional magnitude-to-origin references, estimate quality and provenance. The generic `event` form does not force a common timestamp: seismic event times belong to their origin estimates.

Primary identifiers use `identity.source_id` and `identity.namespace`. Additional source-supported identifiers use repeated `identity.identifier` entries. Local namespace labels `usgs:event`, `emsc:unid`, `emsc:evid` and `quakeml:publicID` identify the reviewed schemes; they are not claimed to be provider-declared standard vocabulary.

The reviewed USGS `us7000rlzn` and EMSC `20260101_0000344` entries remain separate catalogue records. EMSC's detailed response supplied ten origins and ten magnitudes within its entry; these are estimates, not ten earthquakes. A source preference is not a judgement of physical accuracy. Preserve each magnitude's supplied origin reference.

Estimate provenance describes the immediately enclosing estimate. Entry-level catalogue provenance does not establish every estimate's authorship. Nested estimates do not receive ordinary nested qualifiers. Separately qualified estimate records remain a possible next extension when their independent addressability is needed.

Source update time in `provenance.updated_at` differs from physical event time and retrieval time. A timestamp alone does not reconstruct a revision history.

## Acquisition provenance and scientific authorship

Station, platform and instrument information sits in `provenance.acquisition`. The reusable `station` container retains identity, location and elevation metadata without an independent provenance reference, avoiding a recursive station/provenance structure. There is no compulsory first-level station registry or duplicate `station_id`/station-edge representation.

A record may therefore carry `provenance.acquisition.station.identity.source_id` or `provenance.acquisition.platform.name`. The product producer is the author of the addressed scientific content; the acquisition instrument and the delivery route are separate roles. `provenance.product` retains product name, edition, processing level and version when known.

Qualifier equality does not establish duplicate record identity. Different producers can process the same inputs, so differing qualifiers do not establish independent evidence. Preserve scientific identifiers, acquisition context, product versions and supplied lineage evidence. A channel identifies an actual route, such as `usgs-fdsn`, not merely a protocol version such as FDSN event 1.2.

## Time support and quality

`time.instant` represents an instant; `time.start/end` give a half-open support interval. A source timestamp labelling an average can use `time.label`, with documented `time.duration` even when exact interval bounds are not established. A label and interval may coexist. A series' outer time context describes its reported extent; point times describe the values.

Nominal `cadence` is sample spacing, not support duration or a promise of gap-free observations. Three-hour Kp/ap values remain intervals; GOES one-minute means remain averaged values. No common grid, interpolation or implied zero-width support is imposed.

URSI qualifying/descriptive letters remain distinct fields. Seismic `quality.evaluation_mode` and ionogram `quality.scaling` have distinct meanings. The documented FastChar `CS=999` token is preserved in `confidence_code`, interpreted for that route as verified-clean manual scaling, with no numeric confidence score. Actual response placement and scope remain to be confirmed.

Shared quality paths do not imply a universal quality ranking. Missing values remain unavailable, not zero. Uncertainties and flags retain their reported meaning and scope.

## Output connections

`same_event_as` asserts catalogue-entry identity with evidence and provenance. The reviewed candidate pair is not automatically linked. `selected_for_comparison_with` records an output selection relationship; its basis may describe supplied evidence, but the workflow pattern is not copied into the ontology.

`derived_from` is allowed for summaries only where the inputs and derivation are actually supported by source information. A producer-supplied aggregate does not force its input observations to be materialized. Derivation is not independence or causation. A workflow identifier or reference can be retained in provenance without modelling the workflow itself.

Temporal relation edges can be added for concrete output needs later. This fragment does not introduce comparison frames, the full Allen relation vocabulary, an anomaly result model, runtime storage or an analysis pipeline.

## Next bounded checks

- Confirm a GIRO response and the station/characteristic coverage and quality scope.
- Inspect one historical GOES science-quality product, its actual metadata, time support and flags.
- Review which independently addressable seismic estimates and output connections are needed.
- Retain licences and attribution with the selected product; richer citation/lineage fields remain open.

GOES is complementary solar context. GNSS TEC and LXCat remain outside this first output subset.
