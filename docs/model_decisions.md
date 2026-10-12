# Initial modelling decisions

## Reused notation

Seismosaic keeps Alertissimo's containers, fields, projections, permissive references, repeated references, producer/channel qualification and separate connection plane. It introduces domain vocabulary rather than runtime structures.

## Provisional root

The draft uses `study` as a research-context collection of records. It is not an earthquake identity, a station identity or an implementation of a workflow. No record becomes scientifically associated with another merely because both occur in a study.

The root remains a design question. Event-centred, station-centred and interval-centred views may all be useful. A single compulsory wrapper should not be imposed before the intended comparisons are understood.

## Seismic information

An `event` represents a source's catalogue entry. It carries a preferred origin and magnitude estimate in this first fragment. Multiple origins, magnitude estimates and revisions require further discussion; this draft does not claim to represent a full seismic bulletin.

Event time, epicentral position and depth belong to the origin estimate. Magnitude value and magnitude scale stay together. Catalogue identifiers are provider identifiers, not cross-provider identity guarantees.

## Ionospheric information

An `ionospheric_observation` describes an ionogram-derived characteristic at a station and time. The first explicit quantities are foF2 and hmF2. Their derivation or scaling information and quality should remain available.

An ionogram is the underlying data product, not interchangeable with its derived characteristic. Linking to ionograms can be added once the required representation is agreed.

Quality and provenance can be described at the observation or characteristic level. If the source supplies different quality or derivation information for foF2 and hmF2, retain it with the corresponding quantity.

The station identifier in an observation is the provider's reported station identifier. An `observed_at` edge can express a connection to a separately described station.

## Context indices

A `geomagnetic_index` carries its index name, value, unit interpretation and time interval. Kp and ap are related representations of geomagnetic activity, not independent measurements. Daily Ap is a different time product and is outside the initial fragment.

An index interval is not an instantaneous sample or a station-local measurement. The model does not interpolate indices or prescribe a common sampling grid.

## Comparison connections

The optional `selected_for_comparison_with` edge records a selection of an observation for comparison with a seismic event. Its basis and provenance belong to the connection. It makes no claim of an anomaly, statistical correlation, precursor or physical coupling.

Time windows, distance criteria, background selection and control periods need scientific agreement before this edge is populated. There is no correlation implementation in this repository.

## Open questions for the visit

- Which ionospheric characteristic and station/event sample have suitable overlapping coverage and programmatic access?
- What should a study group, and do we need a root at all for the first examples?
- How should preferred and alternative origin/magnitude estimates and revisions be represented?
- Which coordinate and vertical reference information is available from each selected source?
- What spatial footprint does the selected ionospheric characteristic represent, and how should it enter a comparison with an epicentre?
- How should autoscaling confidence, manual scaling and missing or unavailable values be represented?
- Is a level vocabulary useful here? No level profile is assigned in the initial draft.
- Which solar-context product, if any, is needed alongside geomagnetic context?

GOES remains a possible solar-context source. LXCat remains a possible input to later physical interpretation or modelling; neither is assigned an implemented integration or a committed model branch.
