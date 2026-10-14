# Figures from the existing study

The viewer adds a coordinated UTC timeline, a geographic view, separate CollisionDB reference curves and a coverage table. Figures are generated with Matplotlib from the existing `study` and `run` objects. No provider requests, fit evaluation, common-grid interpolation or correlation analysis are added.

## Generate locally without retrieving data

After installing the dependencies, build figures from your saved output:

```bash
python -m pip install -r demo/requirements.txt
python -m unittest discover -s tests -v
python -m demo.visuals --output build/kamchatka
```

Open `build/kamchatka/index.html` directly, or start `python -m demo.kamchatka --port 8765` and inspect the saved study at <http://127.0.0.1:8765>. Opening a saved study does not fetch provider data. **Fetch live study** still explicitly runs the existing retrieval scenario.

The standalone subset works the same way:

```bash
python -m demo.visuals --output build/collisiondb
```

The offline command preserves the existing `study.json` and `run.json` bytes. It writes `figures/*.png`, `figures/*.svg`, `visuals.json` and a refreshed `index.html`. These outputs remain ignored by Git. New live/cache builds also create figures after assembling the study. A plotting failure leaves successful scientific data inspectable and reports the visual error separately.

The input must be an existing saved study. Collision curves require the X/Y layout from the axis patch. An older normalized layout needs rebuilding with the corresponding scenario; `--reuse-cache` prefers available responses but may fetch missing caches. The visualization command itself has no retrieval path.

## Reading the timeline

- Panels retain separate magnitude, foF2/MHz, hmF2/km, Kp, ap/2 nT and XRS/W m−2 scales. XRS bands share their physical unit and use a logarithmic ordinate.
- All panels use the same UTC range, covering represented times and requested windows. Tinted regions show requests; they do not claim continuous data availability. The anchor line comes from the returned USGS preferred origin, resolved through the run's anchor locator.
- Each earthquake catalogue report is a marker using its independently preferred origin time and preferred magnitude. Legends retain source qualification and magnitude scale. Reports are not deduplicated into physical events, magnitudes are not converted, and alternative estimates remain inspectable in the original record.
- Instant/label-only values use markers; explicitly interval-supported values use horizontal segments with their actual start/end. Missing points and temporal gaps are not filled or connected.
- Nonpositive XRS values cannot appear on a log axis. Their omission count is visible and those original values remain in the study. Missing values/times are counted separately. Native quality metadata is retained without imposing a display acceptance filter.
- Dense point/interval artists are rasterized inside SVG to keep large series practical; axes/text remain vector. PNG and SVG represent the same input values.

The picture describes temporal context. It makes no statistical association, causal finding or independence claim.

## Reading the geographic view

The regional panel shows catalogue reports and GIRO sites; the detail panel makes the cluster of seismic reports easier to inspect. A spherical azimuthal equidistant projection centred on the recorded request anchor handles the international date line without splitting nearby sites across the page. Axes are east/north distances in kilometres, with a latitude/longitude graticule. Radial distances use the same 6371.0088 km Earth radius as the demo's selection calculation. No coastline, map tiles or additional dependency is fetched; this is a regional coverage view rather than an ellipsoidal survey.

- Request rings come from the saved seismic and ionospheric radii (500 km and 3000 km in the fixed scenario), centred on the request coordinates. The returned USGS preferred-origin position has a separate star. If request coordinates are absent, the returned anchor can centre the view, but request rings are omitted rather than silently recentered.
- Each catalogue report uses its source-preferred origin position. Reports from different agencies remain separate even when they overlap; no jitter, merging or magnitude conversion is applied. Alternative origins remain available in the underlying record.
- GIRO sites use saved retrieval-list coordinates, with acquisition provenance as a fallback. Marker shapes distinguish returned measurements, no data reported, failed access and other/unreported outcomes. Current station-list membership does not prove historical operation. Source-wide failure and omitted-position counts remain explicit.
- Click a marker to choose among nearby records. The expandable spatial list provides the same inspection by keyboard. Seismic selections open the scientific record; GIRO selections show the native retrieval result and any linked observation series. Empty/failed retrievals never become fabricated observations.
- Global Kp/ap, GOES irradiance and CollisionDB reference curves are not assigned station positions on this map. Selection radii do not represent physical influence, applicability or a correlation result.

Both panels are included in `figures/geography.png` and `figures/geography.svg`. The visual sidecar now uses version 2; regenerate older figures offline with the command above. Scientific output versions and saved scientific JSON remain unchanged.

## Reading the reference curves

Each dataset has its own figure with native X/Y names and units, reaction, dataset ID, fit-generated status and source DOI. The rate coordinate E/eV retains its unresolved physical interpretation. X is logarithmic only when all represented coordinates are positive; Y is linear, preserving zeros.

Lines join tabulated points for display, without evaluating a fit or extrapolating. Error marks use explicit per-point absolute uncertainty first, otherwise the dataset's reported percentage. No confidence level is inferred. Fit shading uses reported bounds only when their unit matches X; bounds are not inferred from the sample grid or treated as physical thresholds.

## Traceability and coverage

Use **Inspect source record** to open the exact underlying record in the expanded view. **Enlarge** provides a larger scrollable picture; **Download SVG/PNG** saves the figure with its embedded attribution. The source picker uses the existing record key/identity and a separate runtime index fallback, not a new ontology path syntax.

The table reports source/qualified group, requested selection, returned temporal extent, record/sample counts, availability of quality metadata and retrieval status. No-data GIRO sites remain visible. Returned extent includes gaps and missing-valued samples; quality counts are metadata availability rather than a universal quality score. Reference records have no observation-time extent. Counts do not measure unique earthquakes or independent evidence.

Visual metadata lives in a sidecar outside the scientific model. Its version and SHA-256 of the study/run input prevent displaying stale figures for changed saved data. Scientific output versions and the metamodel are unchanged. The study export continues to contain only scientific records.

## Local validation

The tests and browser checklist are supplied for the researcher to execute; they were not executed while preparing this patch.

1. Run the offline tests and the generator above. Check that `visuals.json` reports `status: ok` and PNG/SVG files exist.
2. Inspect the timeline's shared UTC axis, preferred-origin anchor, native units, explicit three-hour/minute support and visible gaps.
3. Inspect reference X/Y labels, the first zero cross-section point, uncertainties, fit domain, DOI and unresolved rate-coordinate note.
4. Select a catalogue, station/series and reference record from the figure/table pickers. Check each against its expanded original content.
5. Export SVG, PNG and study JSON. Check that a standalone HTML result works without network access and that a narrow browser viewport remains usable.
6. Inspect the geographic request rings and returned-anchor star. Select overlapping catalogue markers and GIRO sites with different outcomes, then compare the inspector with the saved study/run entries. Check the keyboard spatial list and marker selection after enlargement and at a narrow viewport.

Do not require a fixed total record count: provider results may change. Data retain their existing provider licences and acknowledgements, including GFZ CC BY 4.0, GIRO CC BY-NC-SA 4.0 and CollisionDB CC BY 4.0 with original DOI citations.
