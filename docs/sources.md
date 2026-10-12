# Candidate sources and illustrative mappings

These are source descriptions and proposed mappings for model review. No adapter is implemented and the repository has not tested end-to-end retrieval. Programmatic access is a selection criterion; manually downloaded files are not the proposed workflow.

## Candidate roles

| Source | Proposed role | Access basis |
| --- | --- | --- |
| [USGS earthquake event service](https://earthquake.usgs.gov/fdsnws/event/1/) | Seismic catalogue entries | Documented FDSN HTTP service; GeoJSON and QuakeML representations |
| [EMSC seismic portal](https://www.seismicportal.eu/webservices.html) | Alternative seismic catalogue | Documented event web service; overlapping catalogue entries need an identity policy |
| [GIRO/DIDBase](https://giro.uml.edu/didbase/scaled.php) | Station-based ionogram-derived characteristics | HTTP retrieval is described in the [GIRO resource metadata](https://spase-metadata.org/ISWI/NumericalData/GIRO/CHARS/PT15M.html); station coverage and usable access still need checking |
| [GFZ Kp/ap](https://kp.gfz.de/en/data) | Geomagnetic context | Documented JSON web service and Python client |

The producer qualifier identifies the producer of the represented scientific record or catalogue product; the channel identifies its delivery route. A service name alone must not overwrite reported scientific authorship or contributor information.

## USGS GeoJSON catalogue entry

A Feature can provide the starter event entry's preferred origin and magnitude estimate. This proposal is for a catalogue representation; detailed alternative estimates would need a richer model and source inspection.

Paths below are relative to an `event` record.

| Provider field | Proposed semantic path | Mapping consideration |
| --- | --- | --- |
| `id` | `identity.source_id` | Retain the catalogue identifier |
| `properties.time` | `origin.time.instant` | Express the epoch-millisecond event time as UTC |
| `geometry.coordinates[0]` | `origin.position.longitude` | GeoJSON longitude; degrees |
| `geometry.coordinates[1]` | `origin.position.latitude` | GeoJSON latitude; degrees |
| `geometry.coordinates[2]` | `origin.depth` | Reported depth; kilometres; do not infer an unreported depth reference |
| `properties.mag` | `magnitude.value` | Preserve an unavailable magnitude as unavailable rather than substituting zero |
| `properties.magType` | `magnitude.scale` | Preserve the supplied magnitude type |

This is one catalogue entry. Adding EMSC entries would not create independent earthquake events merely because a second provider reports them. Cross-provider identification and revisions remain open modelling questions.

## GFZ Kp or ap

The documented service takes a start, end and index name. Its timestamps refer to the starts of index intervals. Kp and ap have three-hour time support; lowercase ap must be distinguished from daily Ap.

Paths below are relative to a `geomagnetic_index` record.

| Source meaning | Proposed semantic path | Mapping consideration |
| --- | --- | --- |
| Requested/reported index | `name` | Kp or ap |
| Index value | `value` | Retain the chosen index representation |
| Interval start | `time.start` | UTC interval start |
| Three-hour time support | `time.end` | Derive the interval end from the documented duration and retain that derivation in the mapping notes |
| Index unit interpretation | `unit` | Kp is dimensionless on its index scale; ap expresses equivalent range in units of 2 nT |
| Definitive/nowcast status | `quality.status` | Preserve the source's reported status |
| GFZ attribution and service | `provenance` | Retain producer and delivery context |

The observation time can later be associated with a relevant interval under explicit comparison rules. This mapping does not create additional temporal resolution or imply that Kp and ap are independent predictors.

The [GFZ index definitions](https://www.gfz.de/en/section/geomagnetism/data-products-services/kp-index/related-indices) describe the relationship between Kp, ap and daily Ap and the ap unit interpretation.

## GIRO/DIDBase questions

The first domain quantities are foF2 in MHz and hmF2 in km. Confirm the selected characteristic identifiers, station identifiers, available cadence, coverage, scaling information and quality fields against representative service responses before committing a mapping.

The resource documentation describes manual or automatic ionogram interpretation and confidence/quality information. An interpretation method, confidence score and station/time context belong with the derived characteristic. They should not be discarded while constructing a common representation.

## Deferred candidates

GOES solar observations need a specific product and purpose before a mapping is proposed. LXCat cross-sections or reaction data would feed a separately chosen physical model; they are not another observation series to align directly with earthquakes.
