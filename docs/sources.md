# Source review and illustrative mappings

First review: 2026-10-12; identity/estimate and interval follow-up on the same date. This is a source-access and modelling note, not an adapter implementation. Public documentation and small anonymous HTTP responses were inspected. A successful sample request does not establish completeness, continuous availability or a validated ingestion workflow.

## Current assessment

| Source | Representative response | Query/format basis | Coverage and present decision |
| --- | --- | --- | --- |
| USGS | HTTP 200; one historical event in GeoJSON | FDSN event HTTP query | Global catalogue aggregation; use as the first earthquake mapping example |
| EMSC | HTTP 200; one historical event in JSON | FDSN event HTTP query | Alternative event catalogue; preserve separate estimates and identifiers |
| GFZ Kp/ap | HTTP 200; three Kp interval values | JSON service and documented Python client | Kp/ap archive is documented since 1932; retain interval and definitive/preliminary status |
| GIRO/DIDBase | Documentation/form reachable; station listing and FastChar calls returned HTTP 504 in this review | Documented HTTP services, form and SAO Explorer | Station-dependent coverage; access and a representative response remain to be confirmed locally |
| GOES XRS | HTTP 200; rolling JSON feed inspected | SWPC recent-data JSON; historical NCEI archive | Complementary solar X-ray context; a historical study needs a separately selected archive product |

No manual file-download step is proposed as the eventual workflow. A programmatic service can return JSON or text; response format alone does not determine whether access is usable.

[Standards alignment](standards.md) distinguishes FDSN interfaces, QuakeML event representations, IAGA-endorsed index definitions and SAO/URSI ionospheric conventions. The mappings below are a small semantic projection, not a standards-conformance or lossless conversion claim.

The producer qualifier identifies the producer of the represented scientific record or catalogue product. The channel identifies delivery. Retain reported author/contributor information rather than replacing it with a service's name.

## USGS earthquake event service

[API documentation](https://earthquake.usgs.gov/fdsnws/event/1/) and [GeoJSON fields](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php).

Endpoint: `https://earthquake.usgs.gov/fdsnws/event/1/query`.

| Selection/control | Representative parameters |
| --- | --- |
| Event time | `starttime`, `endtime`; explicit UTC timestamps |
| Region | Latitude/longitude bounds, or `latitude`, `longitude`, `maxradiuskm` |
| Magnitude/depth | `minmagnitude`, `maxmagnitude`, `mindepth`, `maxdepth` |
| Specific record or updates | `eventid`, `updatedafter` |
| Output size/order | `limit`, 1-based `offset`, `orderby` |
| Representation | `format=geojson`; QuakeML/XML and CSV/text are also supported |

The service limits a query to 20,000 events. A later client would need bounded selections and complete pagination, including checks for missing or duplicated results. The API searches catalogue events, not seismic station waveforms. Worldwide query support does not imply uniform detection thresholds or historical completeness. Choose a catalogue, period and magnitude range before assessing coverage.

GeoJSON returns a FeatureCollection. These paths are relative to an `event`:

| Provider field | Proposed semantic path or retention rule |
| --- | --- |
| `features[].id` | `identity.source_id`, with mapping namespace `usgs:event` |
| `properties.time` | `origin.time.instant`; convert epoch milliseconds to UTC |
| `geometry.coordinates[0]` | `origin.position.longitude`, degrees |
| `geometry.coordinates[1]` | `origin.position.latitude`, degrees |
| `geometry.coordinates[2]` | `origin.depth`, km; retain the source's depth reference |
| `properties.mag` | `magnitude.value` |
| `properties.magType` | `magnitude.scale`; preserve source spelling |
| `properties.status` | `quality.status` |
| `properties.net`, `sources`, `ids` | Retain contributor and alternate-identifier evidence; mapping individual identifier namespaces remains pending |
| `properties.updated` | `provenance.updated_at`; convert epoch milliseconds to UTC |

Absent values remain absent or unavailable, not zero. A summary contains source-selected preferred estimates; `origin.preferred` and `magnitude.preferred` record that selection. It does not establish the number of estimates in a full bulletin.

## EMSC earthquake event service

[Service demonstration](https://www.seismicportal.eu/fdsn-wsevent.html), [current OpenAPI](https://www.seismicportal.eu/fdsnws/event/1/openapi.json) and [data-product specification](https://www.emsc-csem.org/Files/epos/specifications/Specs_fdsnevent-WS.pdf).

Endpoint: `https://www.seismicportal.eu/fdsnws/event/1/query`.

Use explicit `starttime`/`endtime`, geographic bounds or radius in degrees, magnitude/depth limits, `catalog`, `contributor`, `limit`, `offset`, `orderby` and `updatedafter`. Record lookup distinguishes `eventid` from the EMSC website identifier `evid`.

Choose `format=json` for the first comparison. QuakeML/XML and text are also documented; text is a pipe-separated representation rather than a safely assumed comma-delimited file. Default output is XML. The service documents a 20,000-event response limit and supports counting matches before retrieval.

Coverage is catalogue-specific: EMSC-RTS is the near-realtime aggregate; EMSC-EMB is the older European-Mediterranean bulletin. The current API notes RTS use since 2012. Historical bounds and completeness must be checked for the selected catalogue and study interval. Dataset attribution is specified under CC BY 4.0 in the [service terms](https://www.seismicportal.eu/terms.html).

The inspected JSON contains a FeatureCollection with lower-case property names. Documentation examples do not all use identical field spelling; mappings below follow the observed response.

| Observed provider field | Proposed semantic path or retention rule |
| --- | --- |
| `features[].id`, `properties.unid` | `identity.source_id`, with mapping namespace `emsc:unid` |
| `properties.source_id` | Additional `identity.identifier.source_id`, with namespace `emsc:evid`; keep the website identifier distinct |
| `properties.time` | `origin.time.instant`; UTC timestamp string |
| `properties.lat`, `properties.lon` | `origin.position.latitude`, `origin.position.longitude` |
| `properties.depth` | `origin.depth`, km |
| `properties.mag`, `properties.magtype` | `magnitude.value`, `magnitude.scale` |
| `properties.auth`, `source_catalog` | Retain authorship/catalogue provenance |
| `properties.lastupdate` | `provenance.updated_at`; retain as a UTC timestamp |
| `properties.evtype` | Retain the source's event-type code until its controlled-value mapping is reviewed |

**Depth check:** the sample reported `properties.depth=130.1` but `geometry.coordinates[2]=-130.1`. Use the explicit depth property; do not reuse the USGS third-coordinate mapping blindly.

**Time check:** a date-only end boundary returned an event later on that calendar day in the sample. Explicit midnight timestamps returned a record within the intended one-day interval. Later clients must check returned event times against the requested window.

### A useful catalogue comparison example

The explicit one-day queries produced two candidate corresponding entries near Vanuatu:

| Source | Identifier | Origin time (UTC) | Depth (km) | Magnitude/type |
| --- | --- | --- | --- | --- |
| USGS | `us7000rlzn` | 2026-01-01T21:35:02.491Z | 139.06 | 5.2 / mb |
| EMSC | `20260101_0000344` | 2026-01-01T21:35:01.65Z | 130.1 | 5.2 / mb |

Similar time/location/magnitude makes this a useful candidate for reviewing identity and estimate representation. It is not an implemented cross-match or an independently confirmed identity link. Separate reports and estimates must survive any later association.

### QuakeML estimate follow-up

The USGS documentation supports `includeallorigins=true` and `includeallmagnitudes=true`; selecting `eventid` also implies these inclusions. EMSC documents `includeallorigins=true`. Inspect XML/QuakeML for detailed estimates instead of assuming the summary JSON contains them.

The bounded requests below both returned HTTP 200. For this entry, USGS returned one origin and magnitude; EMSC returned ten of each. Counts describe these responses only. Both returned preferred origin/magnitude IDs and magnitude `originID` references.

| QuakeML information | Draft mapping |
| --- | --- |
| Origin/magnitude `publicID` | Estimate's `identity.source_id`, namespace `quakeml:publicID`; preserve the complete string |
| Event `preferredOriginID` / `preferredMagnitudeID` | Compare with returned estimate IDs to establish `preferred`; do not select by array order |
| Origin time/latitude/longitude | `origin.time.instant`, `origin.position.latitude`, `origin.position.longitude` |
| Origin depth | `origin.depth`; these XML responses use metres, so divide by 1,000 for the model's km |
| Magnitude value/type | `magnitude.value`, `magnitude.scale`; preserve unfamiliar source types such as `m` |
| Magnitude `originID` | `magnitude.origin_id`; preserve the actual source association |
| Supplied agency/author and estimate status | Estimate-scoped provenance and quality; do not infer authorship from delivery |

For example, the EMSC preferred origin ending in `/IMBNVGIUR` reports 130.1 km depth and has a 5.2 mb magnitude. An additional origin ending in `/IMAZVGAVX` reports 120 km and has a 5.1 mb magnitude referring to that origin. This demonstrates alternative estimates within one entry, independently of cross-catalogue identity review. See [model decisions](model_decisions.md) for semantic paths and the separate identity-edge meaning.

The identifier namespace labels in these mappings are local descriptive conventions. They are not claimed to be provider-defined standards. Parsing the USGS `ids` string into fully scoped additional identifiers remains open; its `sources` list should not be paired with it by assumed array order.

## GFZ Kp and ap

[Access documentation](https://kp.gfz.de/en/data), [JSON format](https://kp.gfz.de/app/format/json.txt) and [index definitions](https://www.gfz.de/en/section/geomagnetism/data-products-services/kp-index/related-indices).

Endpoint: `https://kp.gfz.de/app/json/`.

Parameters: `start`, `end`, `index=Kp` or `index=ap`; optional `status=def` requests definitive values. The documented Python client offers the same time/index selection. JSON is sufficient for the initial mapping review.

The archive is documented since 1932. Both Kp and lowercase ap describe three-hour intervals; daily Ap is different. ap is derived from Kp on an equivalent-range scale, so the pair should not be treated as independent measurements.

| Observed/source field | Relative path in `geomagnetic_index` | Interpretation |
| --- | --- | --- |
| Selected index name | `name` | Kp or ap |
| `Kp[i]` or corresponding `ap[i]` | `value` | Preserve the chosen scale |
| `datetime[i]` | `time.start` | Start of the three-hour UTC interval |
| Documented duration | `time.end` | Start plus three hours; record this mapping derivation |
| `status[i]` | `quality.status` | `def` or `pre`, when supplied |
| `meta.source`, `meta.license` | Provenance/attribution retained for review | Observed response uses `meta`; format description calls it `metadata` |
| Index definition | `unit` | Kp is dimensionless; ap equivalent range is in units of 2 nT |

Parallel arrays must be aligned by index and checked for equal lengths. A request ending at 06:00 returned starts at 00:00, 03:00 and 06:00; the last record describes 06:00–09:00. Selection boundaries are not the same as the support of every returned interval.

The follow-up queried both Kp and ap for 2026-01-01T21:00:00Z through 2026-01-02T00:00:00Z. Each returned two starts, 21:00 and 00:00, with `def` status. Kp was 2.667 and ap was 12 for both starts. The 21:00–00:00 interval contains the two reported earthquake times; the following interval does not. The derived ends use the domain's half-open interval convention. This is a concrete temporal-context example, not an asserted scientific association.

## GIRO/DIDBase

[Characteristic form](https://giro.uml.edu/didbase/scaled.php), [HTTP service examples](https://giro.uml.edu/rix/test.html), [resource metadata](https://spase-metadata.org/ISWI/NumericalData/GIRO/CHARS/PT15M.html) and [provider rules](https://giro.uml.edu/didbase/RulesOfTheRoad.html).

For numeric characteristics, the official examples link to:

`https://lgdc.uml.edu/fastchar/getbest?ursiCode=AU930&charName=foF2,hmF2,foEs`

This is an anonymous latest-24-hour example, not a confirmed arbitrary-date query. `ursiCode` selects a station and `charName` selects characteristics. The visible form uses `location`, `chosenchars[]`, `date_start` and `date_end`; it accepts a UTC time interval. These form names must not be assumed to be FastChar servlet parameters. Resource metadata also describes a DIDBGetValues servlet returning ASCII text.

| Information to retain | Draft-model placement |
| --- | --- |
| Station identifier | `ionospheric_observation.station_id`; corresponding `station.identity.source_id` |
| Characteristic timestamp | `ionospheric_observation.time.instant` |
| foF2 value and units | `foF2.value`, MHz |
| hmF2 value and units | `hmF2.value`, km |
| Source confidence token, including special codes | Quantity- or observation-scoped `quality.confidence_code`; retain verbatim |
| Documented 0–100 scaling score | Corresponding `quality.confidence_score`; exclude special codes |
| URSI qualifying/descriptive letters | `quality.qualifying_letter`, `quality.descriptive_letter`; retain letters and their roles |
| Manual/automatic interpretation | `quality.scaling`; preserve the source's indication |
| Observatory and processing source | Corresponding provenance |

Resource metadata describes confidence from 0 to 100 and QD letters, including a `//` automatic-interpretation convention. [PITHIA's FastChar metadata](https://esc.pithia.eu/data-collections/DataCollection_DIDBase_VerifiedCleanScaling/) additionally documents `CS=999` for verified-clean manual scaling. The source token therefore cannot be treated unconditionally as a 0–100 score. Keep `confidence_code="999"`, use the documented manual/verified-clean interpretation, and leave `confidence_score` absent. Neither confidence 100 nor an ordinary score alone establishes manual or automatic scaling. Interpretation rules belong to the documented route; they are not interchangeable across SAO, SAOXML and tabulated services.

The [standards note](standards.md) records this rule and the SAOXML scaling/letter correspondence. No working FastChar payload or SAO export was inspected, so field placement, quality scope and special-code behaviour still need a bounded response check.

Coverage varies by station and characteristic. The collection metadata starts in 1987 and gives a nominal 15-minute cadence, but neither establishes a complete record at every site or a constant cadence. The station/availability service is `https://lgdc.uml.edu/ionoweb/locations`.

**Access result:** the public form and service-example page were readable; the anonymous characteristic and station-list requests returned HTTP 504 here. This does not establish that GIRO lacks a programmatic interface or that the services fail for other clients. Confirm a small local request and station coverage before treating retrieval as usable.

Ionograms themselves are available through the DIDBase portal and SAO Explorer routes. An image/raw ionogram is a separate data product from its scaled characteristics. A reproducible machine route and representative ionogram format have not been established in this review.

LGDC publishes CC BY-NC-SA 4.0 restrictions, attribution/publication requirements and account/sharing conditions. The documented SAO Explorer read-only account route is separate from the anonymous HTTP example. Source access and redistribution terms need to be checked for the chosen use; this repository's BSD licence does not cover GIRO data.

## GOES as complementary context

Choose a product, not just the satellite mission. The first concrete candidate is **GOES XRS soft X-ray irradiance**, useful as solar-flare context.

[SWPC product description](https://www.spaceweather.gov/products/goes-x-ray-flux), [rolling feed](https://services.swpc.noaa.gov/json/goes/primary/xrays-6-hour.json) and [NCEI EXIS archive](https://www.ncei.noaa.gov/products/goes-r-extreme-ultraviolet-xray-irradiance).

SWPC supplies one-minute averages for the 0.05–0.4 nm and 0.1–0.8 nm bands. The fixed feed URL returns a recent rolling window; it is not a start/end query for arbitrary historical dates.

| Inspected JSON field | Information to preserve |
| --- | --- |
| `time_tag` | UTC sample time |
| `satellite` | Actual producing satellite; do not infer it from the `primary` directory name |
| `energy` | Wavelength-band label |
| `flux` | Reported X-ray irradiance; W m−2 |
| `observed_flux`, `electron_correction` | Additional reported values; interpret against product documentation |
| `electron_contaminaton` | Observed flag spelling; retain it exactly in source notes |

The feed responded with HTTP 200 in this review. Its directory listing returned HTTP 403; that did not prevent access to the documented individual JSON feed. Instrument calibration, eclipse gaps, selected satellite and product version can affect interpretation.

NCEI provides historical operational and science-quality EXIS products in NetCDF, including XRS averages and flare products. Historical access is an archive-product task with format/library and calibration choices, not the same API contract as SWPC's recent feed. No manual-download workflow or historical adapter is selected here.

A GOES quantity/record branch has not yet been added to the ontology. LXCat likewise remains a possible input to a later physical model, outside this observational access review.

## Small local reproduction queries

These commands print responses for inspection. They do not implement ingestion or write data into the repository. Use explicit UTC boundaries and check returned fields before proposing mappings.

```bash
curl --fail --get 'https://earthquake.usgs.gov/fdsnws/event/1/query' \
  --data-urlencode 'format=geojson' \
  --data-urlencode 'starttime=2026-01-01T00:00:00' \
  --data-urlencode 'endtime=2026-01-02T00:00:00' \
  --data-urlencode 'minmagnitude=5' --data-urlencode 'limit=1'

curl --fail --get 'https://www.seismicportal.eu/fdsnws/event/1/query' \
  --data-urlencode 'format=json' \
  --data-urlencode 'starttime=2026-01-01T00:00:00' \
  --data-urlencode 'endtime=2026-01-02T00:00:00' \
  --data-urlencode 'minmagnitude=5' --data-urlencode 'limit=1'

curl --fail --get 'https://kp.gfz.de/app/json/' \
  --data-urlencode 'start=2026-01-01T00:00:00Z' \
  --data-urlencode 'end=2026-01-01T06:00:00Z' \
  --data-urlencode 'index=Kp' --data-urlencode 'status=def'

curl --fail --max-time 30 --get 'https://lgdc.uml.edu/fastchar/getbest' \
  --data-urlencode 'ursiCode=AU930' \
  --data-urlencode 'charName=foF2,hmF2,foEs'

curl --fail 'https://services.swpc.noaa.gov/json/goes/primary/xrays-6-hour.json'
```

AU930 comes from the official service example; it is not a selected study station.

Follow-up requests used for estimate and interval review:

```bash
curl --fail --get 'https://earthquake.usgs.gov/fdsnws/event/1/query' \
  --data-urlencode 'eventid=us7000rlzn' --data-urlencode 'format=xml' \
  --data-urlencode 'includeallorigins=true' \
  --data-urlencode 'includeallmagnitudes=true'

curl --fail --get 'https://www.seismicportal.eu/fdsnws/event/1/query' \
  --data-urlencode 'eventid=20260101_0000344' \
  --data-urlencode 'format=xml' --data-urlencode 'includeallorigins=true'

for index in Kp ap; do
  curl --fail --get 'https://kp.gfz.de/app/json/' \
    --data-urlencode 'start=2026-01-01T21:00:00Z' \
    --data-urlencode 'end=2026-01-02T00:00:00Z' \
    --data-urlencode "index=$index" --data-urlencode 'status=def'
done
```

## Next model discussion

The first estimate/identity iteration is recorded in the ontology and model decisions. Next, review the scientific criteria for cross-catalogue identity and the required uncertainty/provenance detail. For the ionospheric part, select one station and characteristic with verified coverage/access. The study region and scientific comparison windows are still open.
