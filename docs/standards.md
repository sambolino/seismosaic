# Standards alignment

Reviewed 2026-10-12. Seismosaic reuses established scientific concepts through a small domain projection in the Alertissimo notation. This note records conceptual correspondence and mapping decisions; it does not certify service conformance, validate response schemas or define an import/export implementation.

## Interfaces, formats and scientific definitions

| Selected route or product | Standards relationship | Present evidence |
| --- | --- | --- |
| USGS / EMSC event query, XML | FDSN event interface; documented QuakeML 1.2 output | Small responses parsed and inspected; no schema or full interface audit |
| USGS GeoJSON / EMSC JSON | Provider representations alongside FDSN services | Working samples; no shared FDSN event JSON schema |
| GFZ Kp/ap JSON | Official IAGA-endorsed Kp and derived ap in GFZ's JSON format | Working samples; index definitions and three-hour support retained |
| GIRO FastChar | Provider tabulation of ionogram-derived characteristics | Documentation inspected; backend access remains unresolved |
| SAO 4 / SAOXML 5 | Versioned conventions for scaled ionogram data | Specifications inspected; an actual export remains to be checked |
| GOES XRS | SWPC JSON or NOAA historical NetCDF products | Recent JSON inspected; historical product selection remains open |

[FDSN event 1.2](https://www.fdsn.org/webservices/fdsnws-event-1.2.pdf) specifies default QuakeML/XML and a simple text representation. Provider JSON options require their own mappings. GFZ's [index definitions](https://kp.gfz.de/en/about-kp) and [format documentation](https://kp.gfz.de/en/data) distinguish the scientific product from its serialization. [IAGA-2002](https://www.ncei.noaa.gov/services/world-data-system/v-dat-working-group/iaga-2002-data-exchange-format) concerns observatory magnetic-field exchange, not our Kp/ap JSON response.

## Earthquake concepts: QuakeML BED 1.2 projection

Use the [QuakeML Basic Event Description 1.2 specification](https://quake.ethz.ch/quakeml/docs/REC?action=AttachFile&do=get&target=QuakeML-BED-20130214b.pdf) as the concept reference. The following paths are relative to Seismosaic's catalogue-entry `event`:

| Native concept | Seismosaic projection |
| --- | --- |
| Event `publicID` | `identity.identifier` when additional to the service lookup ID; preserve the complete identifier |
| Repeated Origin / Magnitude | Repeated `origin` / `magnitude` |
| Estimate `publicID` | Estimate `identity.source_id`, namespace `quakeml:publicID` |
| Origin time, position, depth | `origin.time.instant`, `origin.position`, `origin.depth`; XML metres become km |
| Magnitude `mag.value`, `type` | `magnitude.value`, `magnitude.scale` |
| Magnitude `originID` | `magnitude.origin_id`; optional source reference |
| Event preferred-estimate IDs | Estimate `preferred`, derived by ID comparison |
| Estimate `evaluationMode` / `evaluationStatus` | Estimate `quality.evaluation_mode` / `quality.status` |

Catalogue-entry scope is Seismosaic's representation choice. QuakeML resource identifiers and service lookup IDs remain distinct. Preference belongs to the source entry; an absent or unresolved preferred ID establishes no preferred estimate. A magnitude need not have an origin reference.

This projection omits picks, arrivals, focal mechanisms, station magnitudes and richer uncertainty structures. Agency/author attribution and method references must retain their estimate context; fuller mappings remain open. The model is neither a complete nor a lossless QuakeML replacement.

## Ionospheric concepts: SAO and URSI

[SAO 4](https://ulcar.uml.edu/~iag/SAO-4.htm) concerns scaled ionogram data. Its scope does not standardize every instrument's raw ionogram format. The [SAOXML 5 specification](https://www.ursi.org/files/CommissionWebsites/INAG/web-66/2005/inag_sao_5_xml.pdf) supplies named characteristics, interpretation metadata and URSI conventions.

| Concept | Seismosaic use |
| --- | --- |
| URSI foF2, code 00 | `foF2.value`, MHz; ordinary-wave F-region critical frequency |
| DIDBase hmF2 | `hmF2.value`, km; derived peak-density height, distinct from virtual height h'F2; confirm exact export field and method |
| SAOXML `scalerType` | Observation `quality.scaling`; `auto` becomes `automatic`, `manual` remains `manual` |
| Characteristic QL / DL | Quantity `quality.qualifying_letter` / `quality.descriptive_letter` |
| Algorithm/version or human scaler | Provenance at the reported scope; mapping detail pending |

Record-wide interpretation and quantity-specific edit flags are different scopes. Manual review can verify an autoscaled value without changing it. Retain that distinction when an export supplies it. FastChar text is a separate representation, not SAOXML merely because the collection supports SAO exports.

### FastChar confidence token

[PITHIA's DIDBase metadata](https://esc.pithia.eu/data-collections/DataCollection_DIDBase_VerifiedCleanScaling/) documents FastChar `CS=999` for verified-clean manual scaling. The rule below is tied to that route and documentation; a working response is still required to confirm its placement and scope.

| Source case | Mapping decision |
| --- | --- |
| `CS=999` | Keep `confidence_code="999"`; interpret as `scaling=manual`, `status=verified_clean`; leave `confidence_score` absent |
| Documented numeric score in 0–100 | Keep the token in `confidence_code`; populate `confidence_score` on that source scale |
| Missing, unknown or other special code | Preserve a supplied token; leave unestablished score or interpretation absent |

These quality paths are relative to the observation or characteristic carrying the source information. `verified_clean` is our descriptive mapping label, not a universal quality rank. A score does not by itself prove automatic or manual scaling. Special codes must not be clamped into the score range or turned into probabilities.

## Cross-domain model focus

The shared model retains event-estimate instants, characteristic station/time context, planetary index intervals, and the provenance and quality of each. Comparison edges carry their selection basis and assertion provenance. Membership, interval overlap and catalogue identity are separate meanings.

Neither a shared `quality.status` path nor a shared UTC representation makes different source status vocabularies, spatial footprints or sampling supports equivalent. Standards alignment reduces repeated modelling within each family; scientific comparison criteria remain explicit domain decisions.
