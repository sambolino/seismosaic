# Fixed live Kamchatka study

This first runtime experiment fetches a historical case from live services and displays semantic output. The requests are hardcoded in `demo/kamchatka.py`; there is no configurable recipe language, planner or ontology interpreter. The Python projections implement the inspected provider fields directly. Endpoint/mapping YAML remains reviewable documentation, not executable instructions.

## Run locally

Python 3.10+ is required. NetCDF4 reads GOES products; pycollisiondb retrieves the fixed oxygen reference inputs. From the repository root, using your active Python environment:

```bash
python -m pip install -r demo/requirements.txt
python -m demo.kamchatka
```

Open **http://127.0.0.1:8765** and click **Fetch live study**. The server listens only on loopback. Requests run in the background; the viewer reports progress and source results. The request endpoint accepts no body or query configuration. Refreshing the page reconnects to an in-progress run. Stop with Ctrl-C.

For a standalone result without a server:

```bash
python -m demo.kamchatka --once
```

This writes `build/kamchatka/index.html`, `study.json`, `run.json` and cached responses. Open the HTML directly in a browser. The HTML embeds the result and needs no external scripts or CDN. Generated scientific data and local environments are ignored by Git. A future run can explicitly reuse retained bodies with `--reuse-cache`; every reused response is labelled cached and retains its original fetch time. Without that flag, requests are live.

After the output-layout changes, rebuild existing saved output:

```bash
python -m demo.kamchatka --once --reuse-cache
python -m demo.kamchatka --port 8765
```

This renormalizes retained source bodies, recovering creation metadata absent from the old JSON; it does not guess attribution from that old output. The server declines to load older normalized snapshots and shows a rebuild notice. `run.output_version=3` identifies this demo output layout, not a metamodel version. Previously exported standalone files retain their original layout until regenerated.

## The fixed request

| Family | Selection |
| --- | --- |
| Anchor | USGS `us6000qw60`; source-selected preferred estimates remain alongside alternatives |
| Seismic | USGS, EMSC and GEOFON, reported M≥6, within 500 km of 52.4948°N / 160.2395°E; 20 July through 12 August 2025 |
| Ionospheric | Current GIRO station-list sites within 3000 km; foF2/hmF2, 15 July through 5 August |
| Geomagnetic | GFZ definitive Kp and ap, 1 July through 5 August |
| Solar | GOES-18 science-quality XRS avg1m, both bands, 15 July through 5 August; fixed daily v2-2-1 files |
| Reference inputs | CollisionDB D110743 and D111118, oxygen electron-impact ionization; fixed IDs with no earthquake time/place filtering |

All windows use UTC and half-open bounds: the named last calendar day is included in full. Requests are checked against returned timestamps/support; inclusive provider bounds do not change these selections. Catalogue thresholds use the supplied magnitude scales, not a conversion to a common Mw. A 1000-entry guard prevents claiming a possibly truncated catalogue query as complete.

The scenario coordinate/time constants identify the reviewed fixture. Retrieved scientific estimates, including revisions, are not overwritten with those constants. The anchor's USGS source time currently includes `.483` seconds. A source timestamp is kept at its supplied precision.

## Output and connections

The study holds repeated first-level containers under qualified keys such as `seismic_event@emsc:emsc-fdsn` and `solar_irradiance_series@noaa-ncei:ncei-exis`. Their arrays are storage representation for `$refs`, not new semantic namespaces. Concrete record names stay in the path; generic `event` or `time_series` parents are not inserted. No `SemanticRecord`/`SemanticEdge` class hierarchy is introduced.

Each record's `$edges` is a separate connection-plane representation. An edge carries its declared `type`, `basis`, `provenance`, and a target locator consisting of a semantic record path plus a source identity. The locator is a demo wire convention, not a new field in the target scientific container or an extension to metamodel path grammar.

The fixture explicitly associates the inspected EMSC mainshock ID `quakeml:eu.emsc/event/20250729_0000311` and GEOFON ID `smi:org.gfz-potsdam.de/geofon/gfz2025otqm` with the USGS anchor. It corroborates their reported time/location/magnitude before emitting `--same_event_as--`. This is a reviewed fixture association, with workflow assertion provenance. The code does not infer identity for all neighbours, merge alternative estimates across entries, infer independence, or declare causal relations. Other selected events and series use `--selected_for_comparison_with-->`.

`run` is outside `study`. It holds the fixed request, HTTP/cache details, station/source access results and native GOES flag definitions. No comparison frame, query recipe or retrieval failure is inserted into the scientific ontology. `run.status=complete` means all source tasks finished successfully, including explicit no-data replies; it is not a scientific completeness claim. Partial source failures leave successful scientific records inspectable. Missing fixed CollisionDB IDs also mark the run partial. Failure of the required anchor aborts the run.

## Scientific details kept intact

- QuakeML retains all returned origins and magnitudes. Each magnitude nests under the origin explicitly named by its source `originID`, which is consumed rather than repeated in associated output. Magnitudes with absent/unresolved associations remain explicit in `unassociated_magnitude`; only unresolved supplied links keep `origin_id`. No parent is guessed from preference or array order. Origin and magnitude preference are event-wide and independent; GEOFON's preferred magnitude can belong to a non-preferred origin. IDs, types and estimate quality remain intact. Depth is converted from metres to km.
- All six CreationInfo fields are retained as `provenance.creation` on each Event, Origin and Magnitude where supplied: publishing agency ID/URI, author name/URI, creation time and resource version. Agency and author remain separate; neither becomes a guessed `producer.name`. Creation timestamps retain their supplied fractional precision and are distinct from physical origin, update and retrieval times. Missing estimate metadata is not inherited from a containing origin or event; a version-only CreationInfo remains represented. The viewer labels author/publisher, origin time/depth, magnitude type/value, preference and creation metadata while keeping full IDs and metadata expandable.
- GFZ points retain complete three-hour intervals. The returned start equal to the exclusive end is excluded, not shortened. Kp and ap are separate series on their declared scales; ap stays in 2 nT scale units. Their relationship is not independent evidence.
- GIRO uses the public historical form by programmatic POST, which returns tabulated Version 1.1 text. Codes `0` and `17` select foF2 and hmF2. Station metadata is acquisition provenance. Station producer aliases identify the contributing observing site; the exact hmF2 derivation workflow remains unreported. Missing `---` values retain their quality context without numeric zeros. QD tokens remain available, confidence is not a probability, `999` is manual without an inferred verified-clean status, and `-1` is unknown. No universal cadence is asserted.
- GOES files are read through NetCDF4 in memory. Native time units/calendar, masks, shapes, band units, platform and product identity are checked. The inspected time variable says **Record start time**; points retain `[start, start+60 s)` and documented one-minute support. Masked flux remains absent, while reported zero remains zero. Band quality/correction flags remain named numeric tokens; their definitions are retained in `run`. The fixed archive version has no silent fallback.

On the first bounded GIRO check, EA653 returned measurements and several other sites reported none. Current list membership and query no-data do not tell us whether a station was operating in 2025. The demo does not call a missing observation an outage or a negative scientific result. Nor does it classify catalogue neighbours as confirmed foreshocks/aftershocks: their reported estimates and selection are shown.

Data stay subject to source terms. GIRO output includes its licence, citation and station acknowledgement reference; review [provider rules](https://giro.uml.edu/didbase/RulesOfTheRoad.html) before sharing or publication. Original data owners retain their roles. Client IP fields/comments echoed by GIRO are removed before retaining responses. The repository's BSD licence applies to code, not scientific datasets.

## Checks and limits

```bash
python -m unittest discover -s tests -v
```

Focused offline tests cover estimate nesting and independent preferences, absent/unresolved associations, all CreationInfo fields and scopes, duplicate-ID rejection, stale-output handling, units, interval-end selection, confidence special codes, missing versus zero values, NetCDF masks/flags, dateline coordinates, safe HTML embedding and cache labels. A live run is an integration check, not a deterministic unit test; source revisions and availability may change the result. The viewer builds branches lazily and pages long arrays without truncating the stored/exported data.

This is an inspection scenario, not a correlation calculation. Cross-catalogue matching of the rest of the sequence, historical GIRO operating-status metadata, alternate archive versions and interpretation of solar/geomagnetic disturbances remain separate later work. The cited ionospheric/geomagnetic-triggering papers are not ingested as facts or encoded as findings.

## Reference inputs in the same run

Kamchatka now calls the same fixed CollisionDB collector as the standalone example. Each fresh default run retrieves the two reference datasets through the Python client and places them in `study.collision_dataset@collisiondb:collisiondb-api`; source status and receipts remain in `run.sources.collisiondb`. A reference-source failure preserves the other successful records. Inclusion asserts neither applicability nor actual model use, and creates no event/derivation edge.

Reference curves declare X/Y metadata once and retain numeric X/Y sample pairs. Native units and the unresolved E/eV interpretation of the rate coordinate remain intact. The reference archive cache is under `build/kamchatka/collisiondb/raw/`. `--reuse-cache` prefers retained responses; a first combined rebuild still fetches CollisionDB if that cache does not exist. Older geophysical caches remain usable. Counts depend on returned provider data; the former captured 93-record count is not a live-run invariant.

## Figures and input coverage

The viewer now includes [offline study figures](visuals.md): temporal context when present, separate reference curves, input coverage and record inspection links. New runs create PNG/SVG exports; existing output can be refreshed with `python -m demo.visuals --output build/kamchatka` without source requests. Scientific records and source/run semantics remain unchanged. Visualization metadata has its own sidecar version/fingerprint.
