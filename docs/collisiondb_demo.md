# Fixed CollisionDB reference-data example

The official `pycollisiondb` client retrieves two oxygen ionization datasets for the shared expandable study viewer. Requests are fixed. This example represents physical reference inputs; it computes no ionospheric model or earthquake association.

## Run locally

Use your already active Python environment:

```bash
python -m pip install -r demo/requirements.txt
python -m unittest discover -s tests -v
python -m demo.collisiondb --port 8765
```

Open <http://127.0.0.1:8765> and click **Fetch live study**. Stop another server on that port first, or use `--port 8766`. Stop with Ctrl-C. The loopback server accepts no source/query parameters.

For standalone output and explicit source-cache replay:

```bash
python -m demo.collisiondb --once
python -m demo.collisiondb --once --reuse-cache
```

Output is in `build/collisiondb/`: `index.html`, `study.json`, `run.json` and managed `raw/` archives, ignored by Git. Reuse is labelled and preserves original retrieval time. With no retained receipt, `--reuse-cache` fetches initially; an invalid retained cache fails rather than silently fetching afresh.

## Reviewed datasets

Both report `e- + O → O+ + 2e-`, code `EIN` (ionization), with a semi-empirical method:

| Dataset | Native columns | DOI | Inspected table |
| --- | --- | --- | --- |
| D111118 | E / eV; sigma / cm2 | [10.1063/1.555809](https://doi.org/10.1063/1.555809) | 50 points; BELI fit; bounds 13.6–20000 |
| D110743 | E / eV; rate / cm3.s-1 | [10.2172/6679044](https://doi.org/10.2172/6679044) | 50 points; CHEB fit; bounds 1–20000 |

Counts/bounds describe the inspected response, not immutable provider content. Both reported 10% uncertainty and `data_from_fit: true`. Fit coefficients, source validity bounds and samples remain separate; no fit is evaluated. No independent threshold was supplied: fit lower bounds are not mapped to thresholds.

The rate coordinate is labelled **E in eV**. Its temperature/distribution interpretation remains unresolved pending its publication. We keep the native label without inventing a temperature namespace, common grid or equivalence with another source.

## Representation and limits

`study.collision_dataset@collisiondb:collisiondb-api` has one record per dataset ID, with process/participants, method, DOI citations and a concrete cross-section or rate curve. `reference_data` is its inherited record form, not another JSON wrapper. Curves compose table contents; they do not inherit `time_series` or create an observation per point. Reference records have no fabricated Earth-observation time, location or event-selection edges.

The producer alias denotes the curated CollisionDB product; original scientific attribution remains in citations/method. The channel denotes the actual API, while the client/version belongs in `run`. Database insertion time maps to `provenance.database.added_at`, distinct from observations, revisions and QuakeML creation. `metadata_version: M1.0` is a format version retained in `run`. No timezone is invented for archive-generation timestamps; retrieval times are UTC. Native archives and SHA-256 receipts support replay.

The pinned client is `pycollisiondb==0.1.6`. It automatically retrieves/extracts a query-specific ZIP, with no manual downloads. The demo validates archive members and 4 MB compressed/expanded bounds before extraction/replay; compressed size is checked after transfer. A child process gives its otherwise unbounded HTTP calls a 120-second deadline. This is a fixed demo, not a generic adapter.

The library initializes unspecified uncertainty arrays to zero. Native table tokens let the projection distinguish absence, explicit zero, symmetric/asymmetric point uncertainties and dataset percentages. Invalid/non-finite values, unsupported tokens, unexpected IDs and array mismatches fail visibly. The separate `resolve_refs` endpoint returned HTTP 404 and `bibliography.json` was empty: supplied DOIs are kept without invented titles/authors. Additional ALADDIN import and fit metadata remain in the source archive.

Empty results, partial returns and failures have distinct source statuses. `--once` exits nonzero for missing requested IDs or failures. Offline tests cover projection/replay; live verification exercises the client separately. These datasets are possible modelling inputs whose applicability requires atmospheric state, an electron distribution and a reaction network. Initial exact molecular-pair queries returned zero; species listings alone do not establish process coverage.

Data are CC BY 4.0; retain original citations. See the [paper](https://doi.org/10.3390/atoms12040020), [official client](https://github.com/IAEA-NDS/pycollisiondb), [metadata conventions](https://db-amdis.org/collisiondb/submitting-data/), [access profile](../endpoints/collisiondb.yaml) and [mapping](../mappings/collisiondb.yaml).
