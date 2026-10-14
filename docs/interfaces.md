# Endpoints and source mappings

These files make the reviewed interfaces concrete. They remain ordinary YAML descriptions, not an executable DSL, OpenAPI specification or promise of full provider coverage. The [fixed Kamchatka demo](kamchatka_demo.md) implements a small subset directly in Python; it does not interpret these descriptions or the ordered notation in `ontology.yaml`.

`endpoints/` records provider URLs, native query parameters, formats, coverage and access constraints. `mappings/` records how returned scientific output fits the ontology. Workflow code will choose queries and perform selection or comparisons; neither layer inserts selection frames or matching rules into the ontology.

## Profiles

| Provider | Endpoint description | Mapping | Reviewed scope |
| --- | --- | --- | --- |
| USGS | [usgs.yaml](../endpoints/usgs.yaml) | [GeoJSON](../mappings/usgs.yaml), [shared QuakeML](../mappings/earthquake-quakeml.yaml) | Catalogue summaries and returned alternative estimates |
| EMSC | [emsc.yaml](../endpoints/emsc.yaml) | [JSON](../mappings/emsc.yaml), [shared QuakeML](../mappings/earthquake-quakeml.yaml) | Separate identifier schemes; summary depth sign; alternative estimates |
| GEOFON | [geofon.yaml](../endpoints/geofon.yaml) | [shared QuakeML](../mappings/earthquake-quakeml.yaml) | Separate seismic catalogue product, not the GFZ Kp/ap product |
| GFZ | [gfz.yaml](../endpoints/gfz.yaml) | [JSON](../mappings/gfz.yaml) | Aligned Kp or ap arrays and their complete three-hour intervals |
| GIRO/DIDBase | [giro.yaml](../endpoints/giro.yaml) | [historical form](../mappings/giro-form.yaml), [pending latest-route bindings](../mappings/giro.yaml) | Historical POST and Version 1.1 table inspected; latest GET remains a separate unbound route |
| GOES XRS | [goes.yaml](../endpoints/goes.yaml) | [recent and historical profiles](../mappings/goes.yaml) | Historical NetCDF fields/support/flags reviewed; recent-feed operational producer still unresolved |
| CollisionDB | [collisiondb.yaml](../endpoints/collisiondb.yaml) | [Python objects](../mappings/collisiondb.yaml) | Two oxygen reference datasets through pycollisiondb 0.1.6; native tables, fit metadata and DOI citations |

The shared QuakeML mapping takes catalogue producer, channel and URL from the selected USGS/EMSC/GEOFON endpoint. It nests magnitudes under their explicitly associated origins while retaining their own IDs, metadata and event-wide preferences. Missing/unresolved origin associations use `unassociated_magnitude`; JSON summary preference alone does not establish association. All six CreationInfo fields are retained independently at each reported resource scope. An XML publicID is not assumed equal to a service lookup ID. JSON summaries and XML bulletins are alternative representations, not additional independent evidence.

## Reading a mapping

- `record` names the concrete output container; its generic parent remains available through the documented `$is` rules. No parent container is inserted in the path.
- `selection` identifies response records. JSON root selections use `$`, `[*]` and `$.features[*]`; field paths such as `properties.time` are relative to the selected object. XML selections use XPath with explicit QuakeML namespaces.
- `containers` names output containers relative to the record. A container's `fields` use paths relative to it; source paths use that group's selected source object. Without a new selection, it shares the enclosing source object. A `points` group produces array items, not standalone qualified records.
- A field entry states a `source`, `literal`, `binding` or `context`, its `target`, and any required `conversion`. Conversions and grouping rules are plain descriptions to implement later, not expressions to execute.
- GFZ's `i` means an aligned parallel-array index. GOES `{band}` is a documented binding to `xrs_a` or `xrs_b`. These describe source-specific normalization; they do not change metamodel parameter syntax.
- `qualifiers` supplies proposed first-level producer/channel aliases. Catalogue producers here mean the catalogue-entry product, not all its estimate authors. A null producer marks unresolved attribution, not a literal producer named "null" and not a completed qualified record.
- `unbound_targets` identifies useful semantic destinations without claiming known provider columns/variables. `retain_unmapped` lists evidence outside the current projection; it does not invent ontology fields or implement raw-response retention.

Field units are the target units declared in the ontology. A different native unit needs an explicit conversion: QuakeML depth is metres, while the model uses kilometres. GFZ's ap values retain their **2 nT scale**; they are not multiplied into a different physical quantity. GOES band limits are nm and irradiance is W m-2. Quantity containers compose common fields; no quantity inheritance is introduced here.

Use the source timestamp's precision and actual time scale. Query boundaries are not record support: GFZ returns starts with three-hour support. The recent GOES JSON `time_tag` remains an average label with unverified exact bounds; its mapping uses `time.label` and `time.duration`. The inspected historical NetCDF time variable explicitly reports record start time and supports complete one-minute intervals. Neither product is falsely represented as an instantaneous reading. The mapping produces no additional summary by calculating aggregates.

## Missing values, failures and provenance

Absent or null numeric fields produce no numeric semantic value; zero remains a real supplied value. Preserve raw missing tokens for review where a workflow retains the response. Unknown sentinels, malformed timestamps, unresolved identity references, mismatched parallel arrays and unknown band labels require review rather than guessed normalization. Optional missing quality metadata does not mean good, definitive, manual or false.

Handle HTTP no-data responses separately from transport/service failures. An empty query does not prove that no physical event occurred or that a station was operating. A failed retrieval does not become a scientific quality flag. The descriptors list representative controls; omitted provider parameters and output fields are outside this review, not declared invalid by a complete schema.

Channel aliases distinguish actual routes (`usgs-fdsn`, `emsc-fdsn`, `geofon-fdsn`, `gfz-kp-json`, `giro-fastchar`, `giro-fastchar-form`, `swpc-json`, `ncei-exis`). Protocol/version is separate metadata. Producer aliases are local identifiers with the roles stated in each profile, not provider-standard identifiers. Preserve supplied estimate authorship at estimate scope and station/platform/instrument information in acquisition provenance. Do not infer duplication, independence, identity edges or causality from qualifiers alone.

Dataset attribution belongs to the provider. The endpoint descriptions link known terms/citations; they do not turn those terms into ontology fields or make the repository licence apply to retrieved data.

## Verification and next small step

On 2026-10-13, bounded anonymous requests returned HTTP 200 for the USGS/EMSC JSON and XML examples, GFZ Kp/ap and the recent GOES feed. Both event lookup responses were single Features; the bounded catalogue queries returned FeatureCollections. USGS returned one origin/magnitude; EMSC returned ten of each. GFZ returned two aligned starts, including the requested end label. GOES returned the reviewed band/correction keys, including the provider spelling `electron_contaminaton`.

These checks cover representative payloads, not full schema validation, completeness or continuous access. The subsequent Kamchatka run also inspected GEOFON QuakeML, a successful historical GIRO POST response and GOES daily NetCDF contents. Its 93 output records and separate retrieval report can now be inspected in the [live demo](kamchatka_demo.md). The latest GIRO GET profile and operational GOES producer attribution remain separate unresolved questions.

## CollisionDB Python access

The separate [reference example](collisiondb_demo.md) uses a fixed library call and the shared viewer. It carries native argument/value units as data, unlike the fixed-unit geophysical quantities above. E on a rate curve is not relabelled as temperature. One qualified record represents each dataset ID, without observation time or location. Retrieval/client/schema versions stay in `run`; insertion time and DOI citations belong in provenance.

Live retrieval returned D110743 and D111118, each with 50 points, fit-generated tables and a reported 10% uncertainty. The bibliography endpoint returned HTTP 404, so source DOIs are retained without invented authors/titles. This adds neither a generic adapter nor metamodel syntax.
