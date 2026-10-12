# Initial modelling decisions

## Reused notation

Seismosaic keeps Alertissimo's containers, fields, projections, permissive references, repeated references, producer/channel qualification and separate connection plane. It introduces domain vocabulary rather than runtime structures.

## Provisional root

The draft uses `study` as a research-context collection of records. It is not an earthquake identity, a station identity or an implementation of a workflow. No record becomes scientifically associated with another merely because both occur in a study.

The root remains a design question. Event-centred, station-centred and interval-centred views may all be useful. A single compulsory wrapper should not be imposed before the intended comparisons are understood.

## Seismic information

An `event` represents a source's catalogue entry. It may contain several origins and magnitudes using repeated references. Each estimate can retain its source identifier, quality and provenance. A source-selected preferred estimate is marked by `preferred`; preference is relative to that catalogue entry and response, not a judgement of physical accuracy.

Event time, epicentral position and depth belong to the origin estimate. Magnitude value and magnitude scale stay together. `magnitude.origin_id` retains a source-reported origin reference where supplied. Several origins and magnitudes do not imply that every magnitude belongs to every origin, or that returned estimates are independent measurements. A preferred magnitude must retain its actual origin reference even when that differs from the preferred origin.

### Identity and estimate paths

The primary identifier remains at `identity.source_id`, with `identity.namespace` stating the assigning catalogue or identifier scheme. Source-supported additional identifiers use repeated `identity.identifier` entries, each carrying its own `source_id` and `namespace`. The `<_identifier>` projection imports identifier fields without adding an extra primary path segment.

For the first mappings, `usgs:event`, `emsc:unid`, `emsc:evid` and `quakeml:publicID` are descriptive namespace labels chosen in the mapping notes, not provider-declared standard vocabulary. Identifier strings remain unchanged. A delivery channel does not assign the identifier namespace.

| Semantic path, relative to an event | Meaning |
| --- | --- |
| `identity.source_id`, `identity.namespace` | Primary catalogue-entry identifier and its scope |
| `identity.identifier.source_id`, `identity.identifier.namespace` | Additional identifiers reported for that entry |
| `origin.identity.source_id` | Identifier of one origin estimate, where supplied |
| `origin.time.instant`, `origin.position.latitude`, `origin.depth` | Values belonging to that origin |
| `origin.preferred` | Source preference among the entry's origins |
| `magnitude.identity.source_id`, `magnitude.value`, `magnitude.scale` | One magnitude estimate and its source identifier |
| `magnitude.origin_id` | Source reference to its associated origin |
| `magnitude.preferred` | Source preference among the entry's magnitudes |
| `origin.provenance`, `magnitude.provenance` | Provenance of the immediately enclosing estimate |
| `provenance.updated_at` | Source-reported catalogue-entry update time |

Repeated origins and magnitudes keep singular semantic paths; public paths contain no array indexes. A summary may make only one estimate available without saying how many estimates exist in the full bulletin. Unknown identifiers, preference and estimate authorship remain unspecified.

### Two catalogue entries versus several estimates

The reviewed USGS `us7000rlzn` and EMSC `20260101_0000344` entries remain separate events. Their near-coincident times and positions make them candidates for identity review. The nondirectional `same_event_as` edge permits an explicit identity assertion with basis and provenance after that review; the example does not populate such an assertion.

Additional estimates within one EMSC entry are a different case. Its inspected QuakeML response returned ten origins and ten magnitudes, including explicit preferred identifiers and magnitude-to-origin references. These fit the repeated containers under that entry. They are not ten earthquakes.

Origin and magnitude provenance describes the estimate's reported author or agency where known. Entry-level catalogue provenance does not establish authorship of every nested estimate. No nested `@producer:channel` qualifiers are introduced; the existing metamodel uses nested provenance for this context.

Source update time is separate from origin time and retrieval time. An update timestamp alone does not reconstruct revision history. Revision connections, retractions and bulletin details remain a later discussion under the existing edge-plane rules.

## Ionospheric information

An `ionospheric_observation` describes an ionogram-derived characteristic at a station and time. The first explicit quantities are foF2 and hmF2. Their derivation or scaling information and quality should remain available.

An ionogram is the underlying data product, not interchangeable with its derived characteristic. Linking to ionograms can be added once the required representation is agreed.

Quality and provenance can be described at the observation or characteristic level. If the source supplies different quality or derivation information for foF2 and hmF2, retain it with the corresponding quantity.

The station identifier in an observation is the provider's reported station identifier. An `observed_at` edge can express a connection to a separately described station.

## Context indices

A `geomagnetic_index` carries its index name, value, unit interpretation and time interval. Kp and ap are related representations of geomagnetic activity, not independent measurements. Daily Ap is a different time product and is outside the initial fragment.

An index interval is not an instantaneous sample or a station-local measurement. The model does not interpolate indices or prescribe a common sampling grid.

### Interval example alongside the earthquake entries

The second review queried Kp and ap separately for starts from 2026-01-01T21:00:00Z through 2026-01-02T00:00:00Z. Both responded successfully with definitive values. The first returned pair was Kp 2.667 and ap 12, describing the same three-hour interval:

| Relative path in `geomagnetic_index` | Kp example | ap example |
| --- | --- | --- |
| `name` | Kp | ap |
| `value` | 2.667 | 12 |
| `unit` | dimensionless | 2 nT equivalent range |
| `time.start` | 2026-01-01T21:00:00Z | 2026-01-01T21:00:00Z |
| `time.end` | 2026-01-02T00:00:00Z | 2026-01-02T00:00:00Z |
| `quality.status` | def | def |

The source supplies the interval start; its documented three-hour support determines the end. The domain convention is a half-open interval `[start, end)`. Both reported earthquake origin times lie inside it. This is time overlap with a planetary context index, not evidence of event identity, an anomaly or physical coupling. These tables illustrate field meanings, not a runtime serialization.

The query also returned the record starting at the requested end, 00:00, whose support is 00:00–03:00. That second interval does not contain the earthquake times. Provider query boundaries and semantic interval support must be kept distinct. Lowercase ap is a related scale derived from Kp; this pair is not two independent confirmations of geomagnetic conditions.

## Comparison connections

The optional `selected_for_comparison_with` edge records a selection of an observation for comparison with a seismic event. Its basis and provenance belong to the connection. It makes no claim of an anomaly, statistical correlation, precursor or physical coupling.

Time windows, distance criteria, background selection and control periods need scientific agreement before this edge is populated. There is no correlation implementation in this repository.

## Open questions for the visit

- Which ionospheric characteristic and station/event sample have suitable overlapping coverage and programmatic access?
- What should a study group, and do we need a root at all for the first examples?
- Which evidence is sufficient to assert cross-catalogue event identity, and how should conflicting identifiers or retractions be handled?
- What further origin/magnitude uncertainty, authorship and revision information does the selected scientific comparison require?
- Which coordinate and vertical reference information is available from each selected source?
- What spatial footprint does the selected ionospheric characteristic represent, and how should it enter a comparison with an epicentre?
- How should autoscaling confidence, manual scaling and missing or unavailable values be represented?
- Is a level vocabulary useful here? No level profile is assigned in the initial draft.
- Which solar-context product, if any, is needed alongside geomagnetic context?

GOES remains a possible solar-context source. LXCat remains a possible input to later physical interpretation or modelling; neither is assigned an implemented integration or a committed model branch.
