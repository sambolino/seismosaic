"""Two fixed oxygen reference datasets through pycollisiondb; no physical model."""
import argparse
import hashlib
import importlib.metadata
import json
import math
import subprocess
import sys
import traceback
import zipfile
from pathlib import Path

from . import kamchatka, model

CLIENT_VERSION = "0.1.6"
OUTPUT_VERSION = 2  # This example's saved-output layout, not a metamodel version.
DATASET_IDS = (110743, 111118)
QUERY = {"pks": list(DATASET_IDS)}
BASE_URL = "https://db-amdis.org/collisiondb/"
PATH = "collision_dataset@collisiondb:collisiondb-api"
PRESENTATION = {
    "title": "Oxygen collision reference data",
    "subtitle": "Electron-impact ionization of atomic oxygen. Two published reference datasets, retaining their native coordinates and fit metadata.",
    "coverage_note": "These are reference inputs for possible physical modelling. Their presence in a study does not establish applicability to a particular ionospheric observation.",
    "empty": "Fetch the two fixed CollisionDB datasets, then inspect their reaction, curves and publication references.",
    "footer": "CollisionDB / IAEA · native units: E in eV, cross section in cm2, rate coefficient in cm3.s-1. Tables are reported as fit-generated. Rate-coordinate interpretation remains to be checked against the cited source. Data: CC BY 4.0; retain the original publication citations.",
    "export_name": "collisiondb-study.json",
    "command": "python -m demo.collisiondb",
}


def finite(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Non-finite CollisionDB value")
    return number


def participants(items):
    result = []
    for count, species in items:
        item = {"count": finite(count), "designation": str(species), "species": str(species.formula)}
        if species.states:
            item["state"] = [str(state) for state in species.states]
        result.append(item)
    return result


def project_dataset(dataset):
    """Project the library object, preserving source tokens needed for uncertainty."""
    metadata = dataset.metadata
    qid = metadata["qid"]
    if qid not in {"D" + str(pk) for pk in DATASET_IDS}:
        raise ValueError("Unexpected dataset ID: " + qid)
    kind = {"cross section": "cross_section", "rate coefficient": "rate_coefficient"}.get(metadata["data_type"])
    if kind is None:
        raise ValueError("Unreviewed CollisionDB data type")
    columns = metadata["columns"]
    if len(columns) != 2 or not all(c.get("name") and c.get("units") for c in columns):
        raise ValueError("Expected two documented columns with units")
    lines = Path(dataset.filepath).read_text(encoding="utf-8").splitlines()[2:]
    if len(lines) != dataset.n or len(dataset.x) != dataset.n or len(dataset.y) != dataset.n:
        raise ValueError("CollisionDB table/array lengths differ")
    points = []
    for index, line in enumerate(lines):
        fields = line.split()
        if len(fields) != 2:
            raise ValueError("Expected a two-column table")
        # The library initializes absent uncertainty arrays to zero. Inspect the
        # original source token so absent, explicit zero and percentage stay distinct.
        values = fields[1].split(":")
        if len(values) not in (1, 2, 3):
            raise ValueError("Unreviewed uncertainty token")
        x, y = finite(dataset.x[index]), finite(dataset.y[index])
        if x != finite(fields[0]) or y != finite(values[0]):
            raise ValueError("Library arrays differ from the retained source table")
        point = {"X": x, "Y": y}
        if len(values) > 1:
            lower = finite(values[1])
            upper = finite(values[-1])
            if lower < 0 or upper < 0:
                raise ValueError("Negative absolute uncertainty")
            point["uncertainty"] = {"lower": lower, "upper": upper}
        points.append(point)
    if any(b["X"] <= a["X"] for a, b in zip(points, points[1:])):
        raise ValueError("Coordinate grid is not strictly increasing")
    if any(p["Y"] < 0 for p in points):
        raise ValueError("Negative collision quantity")
    provenance = model.provenance("collisiondb", "collisiondb-api", BASE_URL + "api/")
    if metadata.get("method"):
        provenance["method"] = {"name": metadata["method"]}
    citations = []
    for source_id, reference in metadata.get("refs", {}).items():
        citation = {"identity": {"source_id": source_id, "namespace": "collisiondb:reference"}}
        if reference.get("doi"):
            citation["doi"] = reference["doi"]
        citations.append(citation)
    if citations:
        provenance["citation"] = citations
    if metadata.get("time_added"):
        provenance["database"] = {"name": "CollisionDB", "added_at": model.stamp(model.utc(metadata["time_added"]))}
    reaction = dataset.reaction
    process = {"reaction": metadata["reaction"], "reactant": participants(reaction.reactants),
               "product": participants(reaction.products),
               "classification": [{"code": code, "description": meaning, "vocabulary": "IAEA plasma process codes"}
                                  for code, meaning in metadata["process_types"].items()]}
    if "threshold" in metadata:
        process["threshold"] = {"value": finite(metadata["threshold"]), "unit": "eV"}
    if metadata.get("frame"):
        process["energy_reference"] = metadata["frame"]
    record = {"identity": {"source_id": qid, "namespace": "collisiondb:dataset"},
              "provenance": provenance, "process": process}
    if metadata.get("comment"):
        record["description"] = metadata["comment"]
    if "unc_perc" in metadata:
        percent = finite(metadata["unc_perc"])
        if percent < 0:
            raise ValueError("Negative relative uncertainty")
        record["uncertainty"] = {"relative_percent": percent}
    curve = {"X": {"name": columns[0]["name"], "unit": columns[0]["units"]},
             "Y": {"name": columns[1]["name"], "unit": columns[1]["units"]}, "points": points}
    # An axis named E in eV is not sufficient evidence to relabel a rate curve as T.
    if "data_from_fit" in metadata:
        if not isinstance(metadata["data_from_fit"], bool):
            raise ValueError("data_from_fit must be a reported boolean")
        curve["data_from_fit"] = metadata["data_from_fit"]
    if "fit" in metadata:
        native_fit = metadata["fit"]
        fit = {}
        if native_fit.get("func"):
            fit["function"] = native_fit["func"]
        if "coeffs" in native_fit:
            fit["coefficient"] = [{"name": name, "value": finite(value)} for name, value in native_fit["coeffs"].items()]
        validity = {}
        for source, target in [("Elo", "lower_argument"), ("Ehi", "upper_argument")]:
            if source in native_fit:
                validity[target] = finite(native_fit[source])
        if validity:
            validity["unit"] = columns[0]["units"]
            fit["validity"] = validity
        if fit:
            curve["fit"] = fit
    record[kind] = curve
    return record


def archive_contents(path):
    """Validate the small native archive before extraction or cache replay."""
    if path.stat().st_size > 4_000_000:
        raise ValueError("CollisionDB archive exceeds this fixed example's 4 MB bound")
    allowed = {str(pk) + ".txt" for pk in DATASET_IDS} | {"manifest.json", "bibliography.json"}
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) - allowed:
            raise ValueError("Unexpected or duplicate archive members")
        if sum(item.file_size for item in archive.infolist()) > 4_000_000:
            raise ValueError("Expanded archive exceeds the 4 MB bound")
        contents = {name: archive.read(name) for name in names}
    manifest = json.loads(contents["manifest.json"])
    ids = set(manifest["datasets"])
    if ids - {"D" + str(pk) for pk in DATASET_IDS}:
        raise ValueError("Unexpected dataset in native manifest")
    if manifest["ndatasets"] != len(ids) or {str(int(qid[1:])) + ".txt" for qid in ids} != set(names) - {"manifest.json", "bibliography.json"}:
        raise ValueError("Manifest and dataset files differ")
    return contents


def fetch_worker(output, reuse=False):
    """Run the unmodified client's HTTP calls in a process with a parent deadline."""
    from pycollisiondb.pycollisiondb import PyCollision
    version = importlib.metadata.version("pycollisiondb")
    if version != CLIENT_VERSION:
        raise ValueError("Install demo/requirements.txt: expected pycollisiondb==" + CLIENT_VERSION)
    raw = Path(output) / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    receipt_path = raw / "client-receipt.json"
    if reuse and receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        if receipt["query"] != QUERY or receipt["client_version"] != version or receipt["base_url"] != BASE_URL:
            raise ValueError("Cached request/client differs from this fixed example")
        if receipt.get("archive_name"):
            # Use the retained archive itself, not an unchecked extracted directory.
            archive_name = receipt["archive_name"]
            if Path(archive_name).name != archive_name or not archive_name.endswith(".zip"):
                raise ValueError("Invalid cached archive name")
            archive = raw / archive_name
            if hashlib.sha256(archive.read_bytes()).hexdigest() != receipt["sha256"]:
                raise ValueError("Cached archive checksum differs")
            contents = archive_contents(archive)
            directory = raw / archive.stem
            directory.mkdir(exist_ok=True)
            for name, body in contents.items():
                (directory / name).write_bytes(body)
            client = PyCollision.get_datasets(archive_uuid=archive.stem, DATA_DIR=raw)
        else:
            client = None  # Cached successful no-data result, not a transport failure.
        receipt.update({"cached": True, "attempted_at": kamchatka.now()})
    else:
        # Retain the official client's query/archive/parser behaviour. Its extraction
        # hook is bounded for this two-ID example; the archive is unchanged.
        class FixedClient(PyCollision):
            def unzip_dataset_archive(self):
                archive_contents(self.archive_path)
                return super().unzip_dataset_archive()
        client = FixedClient.get_datasets(query=QUERY, DB_URL=BASE_URL, DATA_DIR=raw)
        if client is None:
            raise RuntimeError("CollisionDB client could not retrieve data")
        receipt = {"query": QUERY, "base_url": BASE_URL, "client_version": version,
                   "cached": False, "attempted_at": kamchatka.now(), "fetched_at": kamchatka.now()}
        if client.archive_path:
            receipt.update({"archive_name": Path(client.archive_path).name,
                            "sha256": hashlib.sha256(Path(client.archive_path).read_bytes()).hexdigest(),
                            "bytes": Path(client.archive_path).stat().st_size})
    if client and any(ds.metadata["qid"] != "D" + str(pk) for pk, ds in client.datasets.items()):
        raise ValueError("Dataset identity differs from its archive key")
    records = [project_dataset(ds) for _, ds in sorted(client.datasets.items())] if client else []
    if len(records) > len(DATASET_IDS):
        raise ValueError("Unexpected record count")
    # Request/archive/library details are retrieval evidence, not scientific time.
    result = {"records": records, "receipt": receipt,
              "metadata_versions": sorted({ds.metadata.get("metadata_version", "unspecified") for ds in client.datasets.values()}) if client else []}
    json.dumps(result, allow_nan=False)
    if not receipt["cached"]:
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    (raw / "worker-result.json").write_text(json.dumps(result, allow_nan=False), encoding="utf-8")


def fetch(output, reuse=False):
    command = [sys.executable, "-m", "demo.collisiondb", "--fetch-worker", str(Path(output).resolve())]
    if reuse:
        command.append("--reuse-cache")
    try:
        response = subprocess.run(command, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("CollisionDB client exceeded the 120-second retrieval deadline") from error
    if response.returncode:
        raise RuntimeError(response.stderr.strip() or response.stdout.strip() or "CollisionDB client failed")
    return json.loads((Path(output) / "raw" / "worker-result.json").read_text())


def collect(output, reuse=False, progress=print):
    """Collect the same fixed records for either study; do not write a study here."""
    progress("Retrieving the two fixed oxygen datasets through pycollisiondb")
    try:
        result = fetch(output, reuse)
        records = result["records"]
        returned = {record["identity"]["source_id"] for record in records}
        missing = sorted({"D" + str(pk) for pk in DATASET_IDS} - returned)
        status = "no_data" if not records else "partial" if missing else "ok"
        return records, {"status": status, "datasets": len(records), "missing_ids": missing,
                         "attempt": result["receipt"], "metadata_versions": result["metadata_versions"]}
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        return [], {"status": "failed", "error": str(error)}


def run(output, reuse=False, progress=print):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = {"output_version": OUTPUT_VERSION, "scenario_id": "collisiondb-oxygen",
              "scenario": PRESENTATION["title"], "presentation": PRESENTATION,
              "started_at": kamchatka.now(), "reuse_cache": reuse, "request": QUERY, "sources": {},
              "notes": ["Reference data have no Earth-observation time or position.",
                        "Dataset IDs are fixed; species and process searches were used only to review this example.",
                        "Native values and units are preserved; no fit is evaluated or rate calculated here.",
                        "Rate dataset D110743 labels its coordinate E in eV; its temperature/distribution meaning remains unverified.",
                        "DOI citations are supplied by each dataset. The client's separate bibliography-resolution route returned HTTP 404 during review.",
                        "Database insertion time, metadata schema version and archive generation time are distinct from physical observation time and dataset revision."]}
    study = {}
    records, source = collect(output, reuse, progress)
    if records:
        study[PATH] = records
    report["sources"]["collisiondb"] = source
    report["status"] = "failed" if source["status"] == "failed" else "partial" if source.get("missing_ids") else "complete"
    report.update({"finished_at": kamchatka.now(), "record_count": sum(len(items) for items in study.values())})
    document = {"study": study, "run": report}
    progress("Building reference figures from the assembled study; no additional source requests")
    kamchatka.save(document, output)
    progress("Finished: " + report["status"] + "; " + str(report["record_count"]) + " reference records")
    return document


def saved_document(output):
    root = Path(output)
    if not (root / "run.json").exists():
        return None
    report = json.loads((root / "run.json").read_text())
    if report.get("scenario_id") != "collisiondb-oxygen" or report.get("output_version") != OUTPUT_VERSION:
        return None
    from . import visuals
    return visuals.load({"study": json.loads((root / "study.json").read_text())["study"], "run": report}, root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--reuse-cache", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("build/collisiondb"))
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--fetch-worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.fetch_worker:
        try:
            fetch_worker(args.fetch_worker, args.reuse_cache)
        except Exception:
            traceback.print_exc()
            raise SystemExit(1)
    elif args.once:
        document = run(args.output, args.reuse_cache)
        print("Open " + str(args.output.resolve() / "index.html"))
        if document["run"]["status"] != "complete":
            raise SystemExit(1)
    else:
        template = (kamchatka.HERE / "viewer.html").read_text(encoding="utf-8")
        presentation = json.dumps(PRESENTATION).replace("<", "\\u003c").replace("&", "\\u0026")
        page = template.replace("/*PRESENTATION*/null", presentation).encode()
        kamchatka.serve(args.output, args.port, args.reuse_cache, run_study=run, load_saved=saved_document, viewer_html=page)


if __name__ == "__main__":
    main()
