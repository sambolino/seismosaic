"""Fixed live Kamchatka requests, output assembly, and a loopback-only viewer."""
import argparse
import hashlib
import json
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import model

HERE = Path(__file__).parent
SEISMIC_START, SEISMIC_END = model.utc("2025-07-20T00:00:00Z"), model.utc("2025-08-13T00:00:00Z")
CONTEXT_START, CONTEXT_END = model.utc("2025-07-15T00:00:00Z"), model.utc("2025-08-06T00:00:00Z")
GEOMAG_START = model.utc("2025-07-01T00:00:00Z")
ANCHOR = {"latitude": 52.4948, "longitude": 160.2395, "time": "2025-07-29T23:24:52.483Z", "usgs_id": "us6000qw60"}
CATALOGUES = {
    "usgs": ("https://earthquake.usgs.gov/fdsnws/event/1/query", "usgs-fdsn"),
    "emsc": ("https://www.seismicportal.eu/fdsnws/event/1/query", "emsc-fdsn"),
    "geofon": ("https://geofon.gfz.de/fdsnws/event/1/query", "geofon-fdsn"),
}
REVIEWED_MAINSHOCKS = {
    "emsc": "quakeml:eu.emsc/event/20250729_0000311",
    "geofon": "smi:org.gfz-potsdam.de/geofon/gfz2025otqm",
}
GIRO_URL = "https://giro.uml.edu/didbase/scaled.php"
GOES_ROOT = "https://data.ngdc.noaa.gov/platforms/solar-space-observing-satellites/goes/goes18/l2/data/xrsf-l2-avg1m_science/"


def now():
    return model.stamp(datetime.now(model.UTC))


def request(url, params=None, method="GET", output=None, reuse=False):
    encoded = urllib.parse.urlencode(params or {}, doseq=True).encode()
    full_url = url + ("?" + encoded.decode() if encoded and method == "GET" else "")
    key = hashlib.sha256(method.encode() + b" " + full_url.encode() + b" " + (encoded if method == "POST" else b"")).hexdigest()
    cache = output / "raw" if output else None
    if cache:
        cache.mkdir(parents=True, exist_ok=True)
    info = {"url": full_url, "method": method, "parameters": params or {}, "attempted_at": now(), "cached": False}
    if cache and reuse and (cache / (key + ".json")).exists():
        saved = json.loads((cache / (key + ".json")).read_text())
        payload = (cache / (key + ".body")).read_bytes()
        if hashlib.sha256(payload).hexdigest() != saved["sha256"]:
            raise ValueError("Cached body checksum differs")
        info.update(saved)
        info.update({"cached": True, "attempted_at": now()})
        return payload, info
    req = urllib.request.Request(full_url, data=encoded if method == "POST" else None,
                                 headers={"User-Agent": "Seismosaic-fixed-scenario/0.1", "Accept": "*/*"}, method=method)
    with urllib.request.urlopen(req, timeout=30) as response:
        info.update({"http_status": response.status, "fetched_at": now(), "resolved_url": response.url})
        payload = response.read(20_000_001)
    if len(payload) > 20_000_000:
        raise ValueError("Response exceeds this demo's 20 MB per-request bound")
    # GIRO text and station JSON echo client IP; it has no scientific role.
    if url == GIRO_URL:
        payload = b"\n".join(line for line in payload.splitlines() if b"# Requested by" not in line)
        info["redacted"] = "Client-IP comment removed before caching/normalization"
    elif "ionoweb/locations" in url and payload:
        document = json.loads(payload)
        document.pop("RequesterIp", None)
        payload = json.dumps(document).encode()
        info["redacted"] = "RequesterIp removed before caching/normalization"
    info["sha256"] = hashlib.sha256(payload).hexdigest()
    info["bytes"] = len(payload)
    if cache:
        (cache / (key + ".body")).write_bytes(payload)
        (cache / (key + ".json")).write_text(json.dumps(info, indent=2))
    return payload, info


def event_window(record):
    origin, magnitude = model.preferred(record, "origin"), model.preferred(record, "magnitude")
    if not origin or not magnitude:
        raise ValueError("Cannot select entry without source-reported preferred origin/magnitude")
    when, position = model.utc(origin["time"]["instant"]), origin["position"]
    return (SEISMIC_START <= when < SEISMIC_END and magnitude.get("value", -1) >= 6 and
            model.distance(ANCHOR["latitude"], ANCHOR["longitude"], position["latitude"], position["longitude"]) <= 500)


def fetch_catalogue(source, fetch):
    uri, channel = CATALOGUES[source]
    params = {"format": "xml", "starttime": model.stamp(SEISMIC_START),
              "endtime": model.stamp(SEISMIC_END), "minmagnitude": 6,
              "latitude": ANCHOR["latitude"], "longitude": ANCHOR["longitude"], "includeallorigins": "true"}
    if source == "usgs":
        params.update({"maxradiuskm": 500, "includeallmagnitudes": "true", "limit": 1000})
    else:
        params["maxradius"] = math_radius()
        if source == "geofon":
            params["includeallmagnitudes"] = "true"
        else:
            params["limit"] = 1000
    body, info = fetch(uri, params)
    if info["http_status"] == 204:
        return [], [info], {"returned_entries": 0, "selected_entries": 0}
    records = model.quakeml(body, source, channel, uri)
    if len(records) >= 1000:
        raise ValueError("Catalogue query may be truncated; subdivide this fixed scenario before use")
    selected = [r for r in records if event_window(r)]
    return selected, [info], {"returned_entries": len(records), "selected_entries": len(selected),
                              "excluded_after_exact_window_check": len(records)-len(selected)}


def math_radius():
    import math
    return math.degrees(500 / 6371.0088)


def selection_edge(anchor):
    return {"type": "--selected_for_comparison_with-->", "target": anchor,
            "basis": "Selected by the fixed Kamchatka source/window/radius requests in run.request; no physical association is asserted.",
            "provenance": model.provenance("seismosaic-kamchatka-demo", "fixed-scenario", "demo/kamchatka.py")}


def run(output, reuse=False, progress=print):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    study, report = {}, {"started_at": now(), "reuse_cache": reuse, "scenario": "Kamchatka 2025 multi-source context",
                         "request": {"anchor": ANCHOR, "seismic": {"start": model.stamp(SEISMIC_START), "end": model.stamp(SEISMIC_END), "min_magnitude": 6, "radius_km": 500},
                                     "ionospheric": {"start": model.stamp(CONTEXT_START), "end": model.stamp(CONTEXT_END), "radius_km": 3000},
                                     "geomagnetic": {"start": model.stamp(GEOMAG_START), "end": model.stamp(CONTEXT_END)},
                                     "solar": {"start": model.stamp(CONTEXT_START), "end": model.stamp(CONTEXT_END), "satellite": "GOES-18"}},
                         "sources": {}, "notes": ["All windows are UTC and half-open; Aug 5 and Aug 12 are included as full calendar days.",
                                                   "Catalogue selection uses reported magnitude types, with no magnitude conversion.",
                                                   "Only the reviewed mainshock entries receive identity edges; neighbours remain separate catalogue reports.",
                                                   "GIRO no-data does not establish station outage or absence of a physical anomaly.",
                                                   "This study reports selected source data, not a correlation or causal finding."]}
    fetch = lambda url, params=None, method="GET": request(url, params, method, output, reuse)
    progress("Fetching the USGS anchor")
    uri, channel = CATALOGUES["usgs"]
    body, attempt = fetch(uri, {"format": "xml", "eventid": ANCHOR["usgs_id"], "includeallorigins": "true", "includeallmagnitudes": "true"})
    anchor_records = model.quakeml(body, "usgs", channel, uri)
    if len(anchor_records) != 1 or not event_window(anchor_records[0]):
        raise ValueError("USGS anchor response needs review")
    anchor_record = anchor_records[0]
    if model.preferred(anchor_record, "magnitude")["value"] < 8:
        raise ValueError("Anchor no longer satisfies the reviewed great-earthquake condition")
    anchor_record["identity"]["identifier"] = [{"source_id": ANCHOR["usgs_id"], "namespace": "usgs:event"}]
    anchor_path = "study.seismic_event@usgs:usgs-fdsn"
    anchor_locator = {"path": anchor_path, "identity": model.identity(anchor_record["identity"]["source_id"])}
    study["seismic_event@usgs:usgs-fdsn"] = [anchor_record]
    report["anchor"] = {"record": anchor_locator, "attempt": attempt}

    for source in CATALOGUES:
        progress("Fetching " + source + " catalogue neighbours")
        try:
            records, attempts, counts = fetch_catalogue(source, fetch)
            path = "seismic_event@" + source + ":" + CATALOGUES[source][1]
            existing = {r["identity"]["source_id"] for r in study.get(path, [])}
            for record in records:
                if record["identity"]["source_id"] in existing:
                    continue
                record["$edges"] = [selection_edge(anchor_locator)]
                if record["identity"]["source_id"] == REVIEWED_MAINSHOCKS.get(source):
                    origin = model.preferred(record, "origin")
                    pos = origin["position"]
                    if (abs((model.utc(origin["time"]["instant"])-model.utc(ANCHOR["time"])).total_seconds()) <= 120 and
                        model.distance(pos["latitude"], pos["longitude"], ANCHOR["latitude"], ANCHOR["longitude"]) <= 100 and
                        model.preferred(record, "magnitude")["value"] >= 8):
                        record["$edges"].append({"type": "--same_event_as--", "target": anchor_locator,
                            "basis": "Explicit reviewed mainshock ID in this fixed scenario, corroborated by catalogue time/location/magnitude; not a generic matching result or independence claim.",
                            "provenance": model.provenance("seismosaic-kamchatka-demo", "reviewed-fixture", "demo/kamchatka.py")})
                study.setdefault(path, []).append(record)
                existing.add(record["identity"]["source_id"])
            report["sources"][source] = {"status": "ok" if records else "no_data", "attempts": attempts, **counts}
        except (OSError, ValueError, KeyError) as error:
            report["sources"][source] = {"status": "failed", "error": str(error)}

    progress("Fetching GFZ Kp/ap intervals")
    gfz_report = {"status": "ok", "indices": {}}
    for index in ["Kp", "ap"]:
        try:
            uri = "https://kp.gfz.de/app/json/"
            body, attempt = fetch(uri, {"start": model.stamp(GEOMAG_START), "end": model.stamp(CONTEXT_END), "index": index, "status": "def"})
            record = model.gfz(body, index, GEOMAG_START, CONTEXT_END, uri)
            record["$edges"] = [selection_edge(anchor_locator)]
            study.setdefault("geomagnetic_series@gfz-kp:gfz-kp-json", []).append(record)
            gfz_report["indices"][index] = {"status": "ok" if record["points"] else "no_data", "points": len(record["points"]), "attempt": attempt}
        except (OSError, ValueError, KeyError) as error:
            gfz_report["status"] = "partial"
            gfz_report["indices"][index] = {"status": "failed", "error": str(error)}
    report["sources"]["gfz-kp"] = gfz_report

    progress("Discovering nearby GIRO sites")
    try:
        body, listing_attempt = fetch("https://lgdc.uml.edu/ionoweb/locations")
        sites = model.stations(body, ANCHOR["latitude"], ANCHOR["longitude"], 3000)
        giro_report = {"status": "ok", "station_list_attempt": listing_attempt, "stations": []}
        for i, site in enumerate(sites):
            progress("GIRO " + site["code"] + " (" + str(i+1) + "/" + str(len(sites)) + ")")
            detail = dict(site)
            try:
                params = [("location", site["code"]), ("date_start", "2025-07-15 00:00"), ("date_end", "2025-08-06 00:00"),
                          ("chosenchars[]", "0"), ("chosenchars[]", "17"), ("query_submit", "Search")]
                body, attempt = fetch(GIRO_URL, params, "POST")
                record = model.giro(body, site, CONTEXT_START, CONTEXT_END, GIRO_URL)
                detail.update({"status": "ok" if record else "no_data_reported", "attempt": attempt, "points": len(record["points"]) if record else 0})
                if record:
                    record["$edges"] = [selection_edge(anchor_locator)]
                    study["ionospheric_series@station-" + site["code"].lower() + ":giro-fastchar-form"] = [record]
            except (OSError, ValueError, KeyError) as error:
                detail.update({"status": "failed", "error": str(error)})
                giro_report["status"] = "partial"
            giro_report["stations"].append(detail)
        report["sources"]["giro"] = giro_report
    except (OSError, ValueError, KeyError) as error:
        report["sources"]["giro"] = {"status": "failed", "error": str(error)}

    progress("Fetching GOES-18 science-quality daily products")
    solar_report = {"status": "ok", "days": []}
    days = [CONTEXT_START + timedelta(days=i) for i in range((CONTEXT_END-CONTEXT_START).days)]

    def fetch_day(day):
        filename = "sci_xrsf-l2-avg1m_g18_d" + day.strftime("%Y%m%d") + "_v2-2-1.nc"
        uri = GOES_ROOT + day.strftime("%Y/%m/") + filename
        body, attempt = fetch(uri)
        return model.goes(body, uri, CONTEXT_START, CONTEXT_END), attempt

    # NetCDF/HDF5 libraries need not be thread-safe; normalize in this thread.
    for i, day in enumerate(days):
        progress("GOES " + day.strftime("%Y-%m-%d") + " (" + str(i+1) + "/" + str(len(days)) + ")")
        detail = {"date": day.strftime("%Y-%m-%d")}
        try:
            (record, metadata), attempt = fetch_day(day)
            record["$edges"] = [selection_edge(anchor_locator)]
            study.setdefault("solar_irradiance_series@noaa-ncei:ncei-exis", []).append(record)
            detail.update({"status": "ok", "points": len(record["points"]), "attempt": attempt, "metadata": metadata})
        except (OSError, ValueError, KeyError, ImportError) as error:
            detail.update({"status": "failed", "error": str(error)})
            solar_report["status"] = "partial"
        solar_report["days"].append(detail)
    report["sources"]["goes"] = solar_report
    report["finished_at"] = now()
    report["status"] = "complete" if all(s["status"] in ["ok", "no_data"] for s in report["sources"].values()) else "partial"
    report["record_count"] = sum(len(records) for records in study.values())
    document = {"study": study, "run": report}
    save(document, output)
    progress("Finished: " + report["status"] + "; " + str(report["record_count"]) + " records")
    return document


def save(document, output):
    compact = json.dumps(document, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    (output / "study.json").write_text(json.dumps({"study": document["study"]}, ensure_ascii=False, allow_nan=False, indent=2), encoding="utf-8")
    (output / "run.json").write_text(json.dumps(document["run"], ensure_ascii=False, allow_nan=False, indent=2), encoding="utf-8")
    embedded = compact.replace("<", "\\u003c").replace("&", "\\u0026")
    template = (HERE / "viewer.html").read_text(encoding="utf-8")
    (output / "index.html").write_text(template.replace("/*SNAPSHOT*/null", embedded), encoding="utf-8")


def serve(output, port, reuse=False):
    state = {"status": "idle", "messages": [], "document": None, "reuse_cache": reuse}
    lock = threading.Lock()
    snapshot = Path(output) / "index.html"
    if snapshot.exists():
        # Existing snapshot remains visible until a successful refresh replaces it.
        state["document"] = {"study": json.loads((Path(output)/"study.json").read_text())["study"],
                             "run": json.loads((Path(output)/"run.json").read_text())}

    def work():
        def progress(message):
            print(message, flush=True)
            with lock:
                state["messages"].append(message)
        try:
            document = run(output, reuse, progress)
            with lock:
                state.update({"status": "done", "document": document})
        except Exception as error:
            with lock:
                state.update({"status": "failed", "error": str(error)})

    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, body, mime="application/json"):
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/":
                self.respond(200, (HERE/"viewer.html").read_bytes(), "text/html; charset=utf-8")
            elif self.path == "/api/status":
                with lock:
                    body = {k: v for k, v in state.items() if k != "document"}
                self.respond(200, json.dumps(body).encode())
            elif self.path == "/api/study":
                with lock:
                    document = state["document"]
                self.respond(200 if document else 404, json.dumps(document, allow_nan=False).encode())
            else:
                self.respond(404, b'{"error":"Unknown route"}')

        def do_POST(self):
            if self.path != "/api/run":
                self.respond(404, b'{"error":"Unknown route"}')
                return
            # No source/query parameters accepted. Cross-origin pages cannot trigger requests.
            origin = self.headers.get("Origin")
            if origin and origin not in ["http://127.0.0.1:"+str(port), "http://localhost:"+str(port)]:
                self.respond(403, b'{"error":"Local origin required"}')
                return
            if self.headers.get("Content-Length", "0") != "0":
                self.respond(400, b'{"error":"This scenario accepts no request body"}')
                return
            with lock:
                if state["status"] == "running":
                    self.respond(409, b'{"error":"A run is already in progress"}')
                    return
                state.update({"status": "running", "messages": []})
                state.pop("error", None)
            threading.Thread(target=work, daemon=True).start()
            self.respond(202, b'{"status":"running"}')

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print("Open http://127.0.0.1:" + str(port) + " — fixed requests only; Ctrl-C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Fetch once and write a standalone HTML/JSON snapshot")
    parser.add_argument("--reuse-cache", action="store_true", help="Explicitly reuse cached bodies; run report marks them cached")
    parser.add_argument("--output", type=Path, default=Path("build/kamchatka"))
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if args.once:
        run(args.output, args.reuse_cache, lambda message: print(message, flush=True))
        print("Open " + str(args.output.resolve()/"index.html"))
    else:
        serve(args.output, args.port, args.reuse_cache)


if __name__ == "__main__":
    main()
