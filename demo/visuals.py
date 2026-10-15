"""Offline figures from a saved study; never contact a provider or calculate a model."""
import argparse
import base64
import hashlib
import json
import math
import textwrap
from datetime import datetime, timedelta
from pathlib import Path

from . import model

VISUAL_VERSION = 3
CLOSEUP_HOURS = 24
PANELS = [("earthquake", "Catalogue reports", "Reported magnitude\n(native scales)", "seismic"),
          ("foF2", "Ionospheric foF2", "MHz", "ionospheric"),
          ("hmF2", "Ionospheric hmF2", "km", "ionospheric"),
          ("Kp", "Planetary Kp", "Kp (dimensionless)", "geomagnetic"),
          ("ap", "Planetary ap", "ap (2 nT scale)", "geomagnetic"),
          ("XRS", "GOES XRS interval means", "Irradiance / W m−2\n(logarithmic)", "solar")]
COLOURS = ["#126b67", "#416fa3", "#9061a0", "#b87332", "#546c87", "#a05458"]


def numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def date(value):
    if not value:
        return None
    try:
        return model.utc(value)
    except (AttributeError, TypeError, ValueError):
        return None


def digest(document):
    native = {key: document[key] for key in ["study", "run"]}
    return hashlib.sha256(json.dumps(native, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def records(document):
    for key, items in document["study"].items():
        if isinstance(items, list):
            for index, record in enumerate(items):
                if isinstance(record, dict):
                    locator = {"path": "study." + key, "index": index}
                    if record.get("identity"):
                        locator["identity"] = record["identity"]
                    yield key, record, locator


def label(key, record):
    qualified = key.partition("@")[2] or key
    station = record.get("provenance", {}).get("acquisition", {}).get("station", {})
    station_id = station.get("identity", {}).get("source_id")
    return station_id + " / " + qualified.partition(":")[2] if station_id else qualified


def timeline_data(document):
    """Fixed display projections; source records and arrays remain untouched."""
    groups = {name: [] for name, *_ in PANELS}
    for key, record, locator in records(document):
        kind = key.partition("@")[0]
        if kind == "seismic_event":
            origin, magnitude = model.preferred(record, "origin"), model.preferred(record, "magnitude")
            when = date((origin or {}).get("time", {}).get("instant"))
            value = (magnitude or {}).get("value")
            groups["earthquake"].append({"label": label(key, record) + " / " + str((magnitude or {}).get("scale", "unspecified scale")),
                "locator": locator, "points": [(when, None, value)] if when and numeric(value) else [],
                "missing": int(not when or not numeric(value)), "nonpositive": 0,
                "excluded": [(when, None, "missing")] if not when or not numeric(value) else []})
            continue
        quantities = [("foF2", "foF2"), ("hmF2", "hmF2")] if kind == "ionospheric_series" else \
                     [("Kp", "Kp"), ("ap", "ap")] if kind == "geomagnetic_series" else \
                     [("XRS", "xrs_a"), ("XRS", "xrs_b")] if kind == "solar_irradiance_series" else []
        for panel, quantity in quantities:
            points, excluded, missing, nonpositive = [], [], 0, 0
            native_points = record.get("points", [])
            present = any(quantity in (point.get("irradiance", {}) if panel == "XRS" else point) for point in native_points)
            if not present:
                continue
            for point in native_points:
                values = point.get("irradiance", {}).get(quantity, {}) if panel == "XRS" else point.get(quantity, {})
                time = point.get("time", {})
                begin = date(time.get("instant") or time.get("start") or time.get("label"))
                end = date(time.get("end")) if time.get("start") else None
                value = values.get("value")
                if not begin or not numeric(value):
                    missing += 1
                    excluded.append((begin, end, "missing"))
                elif panel == "XRS" and value <= 0:
                    nonpositive += 1  # Retained in study; cannot be placed on a log ordinate.
                    excluded.append((begin, end, "nonpositive"))
                else:
                    points.append((begin, end, value))
            if present:
                groups[panel].append({"label": label(key, record) + (" / " + quantity if panel == "XRS" else ""),
                    "locator": locator, "points": points, "missing": missing, "nonpositive": nonpositive, "excluded": excluded})
    return groups


def closeup_window(document):
    anchor = anchor_time(document)
    return (anchor - timedelta(hours=CLOSEUP_HOURS), anchor + timedelta(hours=CLOSEUP_HOURS)) if anchor else None


def in_window(begin, end, window):
    if begin is None:
        return False
    start, stop = window
    return begin < stop and end > start if end and end > begin else start <= begin < stop


def timeline_window(groups, window):
    """Select intersecting native support, without trimming intervals or changing values."""
    selected = {}
    for panel, items in groups.items():
        selected[panel] = []
        for item in items:
            points = [point for point in item["points"] if in_window(point[0], point[1], window)]
            excluded = [point for point in item["excluded"] if in_window(point[0], point[1], window)]
            selected[panel].append(dict(item, points=points, excluded=excluded,
                missing=sum(reason == "missing" for _, _, reason in excluded),
                nonpositive=sum(reason == "nonpositive" for _, _, reason in excluded)))
    return selected


def extent(record):
    times = []
    for time in [record.get("time", {}), *[point.get("time", {}) for point in record.get("points", [])]]:
        times.extend(parsed for key in ["instant", "start", "end", "label"] if (parsed := date(time.get(key))))
    if record.get("origin"):
        origin = model.preferred(record, "origin")
        when = date((origin or {}).get("time", {}).get("instant"))
        if when:
            times.append(when)
    return [model.stamp(min(times)), model.stamp(max(times))] if times else None


def family_source(key):
    kind = key.partition("@")[0]
    if kind == "seismic_event":
        return key.partition("@")[2].partition(":")[0], "seismic"
    return {"ionospheric_series": ("giro", "ionospheric"), "geomagnetic_series": ("gfz-kp", "geomagnetic"),
            "solar_irradiance_series": ("goes", "solar"), "collision_dataset": ("collisiondb", "collisiondb")}.get(kind, (None, None))


def coverage_rows(document):
    rows, grouped, represented = [], {}, set()
    sources, request = document["run"].get("sources", {}), document["run"].get("request", {})
    for key, record, locator in records(document):
        source, family = family_source(key)
        represented.add(source)
        row = grouped.setdefault(key, {"label": key, "source": source, "status": sources.get(source, {}).get("status", "not_reported"),
            "requested": request.get(family, request if family == "collisiondb" and "pks" in request else None), "records": 0, "samples": 0, "quality_samples": 0, "extents": [], "locators": []})
        row["records"] += 1
        row["locators"].append(locator)
        points = record.get("points", [])
        if "collision_dataset" == key.partition("@")[0]:
            points = record.get("cross_section", record.get("rate_coefficient", {})).get("points", [])
        row["samples"] += len(points)
        row["quality_samples"] += sum(bool(point.get("quality") or any(isinstance(v, dict) and v.get("quality") for v in point.values())
            or any(v.get("quality") for v in point.get("irradiance", {}).values())) for point in points)
        span = extent(record)
        if span:
            row["extents"].extend(span)
    for row in grouped.values():
        spans = [date(value) for value in row.pop("extents")]
        row["returned"] = [model.stamp(min(spans)), model.stamp(max(spans))] if spans else None
        rows.append(row)
    for source, result in sources.items():
        if source not in represented:
            family = {"usgs": "seismic", "emsc": "seismic", "geofon": "seismic", "giro": "ionospheric",
                      "gfz-kp": "geomagnetic", "goes": "solar", "collisiondb": "collisiondb"}.get(source)
            rows.append({"label": source, "source": source, "status": result.get("status", "not_reported"),
                         "requested": request.get(family, request if family == "collisiondb" and "pks" in request else None), "returned": None, "records": 0, "samples": 0, "quality_samples": 0, "locators": [], "error": result.get("error")})
    for station in sources.get("giro", {}).get("stations", []):
        if station.get("status") != "ok":
            rows.append({"label": "GIRO " + station.get("code", "unknown site"), "source": "giro", "status": station.get("status", "not_reported"),
                         "requested": request.get("ionospheric"), "returned": None, "records": 0, "samples": 0, "quality_samples": 0, "locators": [], "error": station.get("error")})
    return rows


def anchor_time(document):
    target = document["run"].get("anchor", {}).get("record", {})
    key = target.get("path", "").removeprefix("study.")
    identity = target.get("identity", {}).get("source_id")
    for record in document["study"].get(key, []):
        if record.get("identity", {}).get("source_id") == identity:
            return date((model.preferred(record, "origin") or {}).get("time", {}).get("instant"))
    return None


def coordinates(position):
    lat, lon = position.get("latitude"), position.get("longitude")
    if numeric(lat) and numeric(lon) and -90 <= lat <= 90 and -180 <= lon <= 180:
        return {"latitude": lat, "longitude": lon}
    return None


def project(position, centre):
    """Spherical azimuthal equidistant coordinates; the same radius as model.distance."""
    lat, lat0 = math.radians(position["latitude"]), math.radians(centre["latitude"])
    delta = math.radians((position["longitude"] - centre["longitude"] + 180) % 360 - 180)
    cosine = math.sin(lat0) * math.sin(lat) + math.cos(lat0) * math.cos(lat) * math.cos(delta)
    angle = math.acos(max(-1, min(1, cosine)))
    if angle < 1e-12:
        return 0., 0.
    if math.pi - angle < 1e-8:
        raise ValueError("Antipodal position has no unique bearing on this regional map")
    scale = 6371.0088 * angle / math.sin(angle)
    return scale * math.cos(lat) * math.sin(delta), scale * (math.cos(lat0) * math.sin(lat) - math.sin(lat0) * math.cos(lat) * math.cos(delta))


def geographic_data(document):
    """Display positions and retrieval outcomes, never manufacture observation records."""
    entries, missing = [], {"catalogue_positions": 0, "station_positions": 0}
    anchor = document["run"].get("anchor", {}).get("record", {})
    actual = None
    station_records = {}
    for key, record, locator in records(document):
        if key.partition("@")[0] == "seismic_event":
            origin = model.preferred(record, "origin") or {}
            position = coordinates(origin.get("position", {}))
            if not position:
                missing["catalogue_positions"] += 1
                continue
            is_anchor = locator["path"] == anchor.get("path") and record.get("identity", {}).get("source_id") == anchor.get("identity", {}).get("source_id")
            if is_anchor:
                actual = position
            entries.append({"kind": "catalogue", "label": label(key, record) + " · " + str(record.get("identity", {}).get("source_id", "unidentified report")),
                "source": key.partition("@")[2], "position": position, "locator": locator,
                "status": "preferred origin", "anchor": is_anchor})
        elif key.partition("@")[0] == "ionospheric_series":
            site = record.get("provenance", {}).get("acquisition", {}).get("station", {})
            code = site.get("identity", {}).get("source_id")
            if code:
                station_records.setdefault(code, []).append((site, locator))
    represented = set()
    for index, site in enumerate(document["run"].get("sources", {}).get("giro", {}).get("stations", [])):
        code = site.get("code", "unknown site")
        represented.add(code)
        matches = station_records.get(code, [])
        position = coordinates(site) or next((pos for native, _ in matches if (pos := coordinates(native.get("position", {})))), None)
        if not position:
            missing["station_positions"] += 1
            continue
        entries.append({"kind": "station", "label": "GIRO " + code, "source": "giro", "position": position,
            "status": site.get("status", "not_reported"), "locators": [locator for _, locator in matches],
            "run_locator": {"station_index": index}, "error": site.get("error")})
    for code, matches in station_records.items():
        if code in represented:
            continue
        position = next((pos for native, _ in matches if (pos := coordinates(native.get("position", {})))), None)
        if position:
            entries.append({"kind": "station", "label": "GIRO " + code, "source": "giro", "position": position,
                "status": "record_present_outcome_unreported", "locators": [locator for _, locator in matches]})
        else:
            missing["station_positions"] += 1
    request = document["run"].get("request", {})
    requested_centre = coordinates(request.get("anchor", {}))
    centre = requested_centre or actual
    rings = []
    if requested_centre:
        for family in ["seismic", "ionospheric"]:
            radius = request.get(family, {}).get("radius_km")
            if numeric(radius) and 0 < radius < math.pi * 6371.0088:
                rings.append({"family": family, "radius_km": radius})
    return {"centre": centre, "centre_basis": "request" if requested_centre else "returned anchor", "rings": rings,
            "entries": entries, "missing": missing, "giro_status": document["run"].get("sources", {}).get("giro", {}).get("status", "not_reported")}


def draw_geography(document, output, plt):
    data = geographic_data(document)
    if not data["centre"]:
        return None
    centre = data["centre"]
    located, antipodes = [], 0
    for index, entry in enumerate(data["entries"]):
        try:
            x, y = project(entry["position"], centre)
        except ValueError:
            antipodes += 1
            continue
        located.append((index, entry, x, y))
    extent_km = max([1000, *[ring["radius_km"] for ring in data["rings"]], *[max(abs(x), abs(y)) for _, _, x, y in located]]) * 1.12
    seismic_radius = next((ring["radius_km"] for ring in data["rings"] if ring["family"] == "seismic"), None)
    detail_extent = max([seismic_radius or 500, *[max(abs(x), abs(y)) for _, entry, x, y in located if entry["kind"] == "catalogue"]]) * 1.12
    fig, axes = plt.subplots(1, 2, figsize=(13, 7.7))
    fig.subplots_adjust(left=.08, right=.97, top=.89, bottom=.31, wspace=.24)
    palette, hotspots = {}, []
    for ax, limit, title in zip(axes, [extent_km, detail_extent], ["Regional coverage", "Catalogue detail"]):
        ax.set_xlim(-limit, limit)
        ax.set_ylim(-limit, limit)
        ax.set_aspect("equal", adjustable="box")
        ax.set_title(title, loc="left", fontsize=11)
        ax.set_xlabel("East / km", fontsize=9)
        ax.set_ylabel("North / km", fontsize=9)
        ax.tick_params(labelsize=8)
        ax.grid(color="#edf0f3", linewidth=.5)
        # A geographic graticule provides orientation without a basemap request.
        for latitude in range(-80, 81, 10):
            xy = [project({"latitude": latitude, "longitude": centre["longitude"] + offset}, centre) for offset in range(-85, 86)]
            ax.plot(*zip(*xy), color="#bfcbd4", linewidth=.5, zorder=0)
            x, y = project({"latitude": latitude, "longitude": centre["longitude"]}, centre)
            if abs(y) < limit:
                ax.text(0, y, str(abs(latitude)) + "°" + ("N" if latitude >= 0 else "S"), fontsize=7, color="#657387")
        for offset in range(-80, 81, 10):
            longitude = (centre["longitude"] + offset + 180) % 360 - 180
            xy = [project({"latitude": latitude, "longitude": longitude}, centre) for latitude in range(-80, 81)]
            ax.plot(*zip(*xy), color="#bfcbd4", linewidth=.5, zorder=0)
            x, y = project({"latitude": centre["latitude"], "longitude": longitude}, centre)
            if abs(x) < limit and abs(y) < limit:
                ax.text(x, y, f"{abs(longitude):.1f}°" + ("E" if longitude >= 0 else "W"), fontsize=7, color="#657387")
        for ring in data["rings"]:
            radius = ring["radius_km"]
            if radius <= limit:
                ax.add_patch(plt.Circle((0, 0), radius, fill=False, linestyle="--", linewidth=1,
                    edgecolor="#b87332" if ring["family"] == "seismic" else "#798ca2", label=ring["family"] + f" request · {radius:g} km"))
        ax.plot(0, 0, marker="+", color="#333333", markersize=10, linestyle="none", label=data["centre_basis"] + " centre", zorder=4)
        for index, entry, x, y in located:
            if abs(x) > limit or abs(y) > limit:
                continue
            if entry["kind"] == "catalogue":
                colour = palette.setdefault(entry["source"], COLOURS[len(palette) % len(COLOURS)])
                marker, size, description, face = "o", 34, entry["source"], "none"
                if entry.get("anchor"):
                    marker, size, description, face = "*", 145, "Returned USGS anchor", colour
            else:
                status = entry["status"]
                marker, colour = {"ok": ("^", "#126b67"), "no_data_reported": ("s", "#798ca2"), "failed": ("X", "#a05458")}.get(status, ("D", "#9061a0"))
                size, description, face = 55, "GIRO · " + status.replace("_", " "), colour if status in ["ok", "failed"] else "none"
            ax.scatter([x], [y], marker=marker, s=size, facecolors=face, edgecolors=colour, linewidths=1.1, label=description, zorder=5)
            if entry["kind"] == "station":
                ax.annotate(entry["label"].removeprefix("GIRO "), (x, y), xytext=(5, 5), textcoords="offset points", fontsize=8)
            hotspots.append((ax, index, x, y))
        handles, labels = ax.get_legend_handles_labels()
        unique = dict(zip(labels, handles))
        ax.legend(unique.values(), unique.keys(), loc="upper left", bbox_to_anchor=(0, -.13), fontsize=7, ncol=2, frameon=False)
    fig.suptitle("Kamchatka study · geographic selection and returned records", fontsize=13, x=.08, ha="left")
    fig.text(.08, .018, "Spherical azimuthal equidistant projection · radius 6371.0088 km · no basemap or network tiles\nUSGS / EMSC / GEOFON · GIRO: doi:10.5047/eps.2011.03.001 (CC BY-NC-SA 4.0); station IDs beside markers\nRequest rings show selection, not physical influence. GIRO retrieval outcomes do not establish historical operation or a physical null.", fontsize=8, color="#657387")
    try:
        fig.canvas.draw()
        width, height = fig.get_size_inches() * fig.dpi
        hit_targets = []
        for ax, index, x, y in hotspots:
            px, py = ax.transData.transform((x, y))
            hit_targets.append({"entry": index, "x": float(px / width), "y": float(1 - py / height)})
        files = figure_files(fig, output, "geography")
    finally:
        plt.close(fig)
    return {"title": "Geographic context", "files": files, "locators": [], "spatial_entries": data["entries"], "hotspots": hit_targets,
        "caption": "Preferred-origin positions are shown per catalogue report, without merging agencies, plotting all alternative origins, magnitude conversion or marker jitter. Overlapping reports remain distinct; click a marker to choose among nearby records, or use the spatial list. Rings are centred on the recorded request anchor; the star is the returned USGS preferred origin. Radial distances follow the demo's spherical distance convention; the map is not an ellipsoidal survey. Missing positions omitted: " + str(data["missing"]) + "; antipodal positions omitted: " + str(antipodes) + ". GIRO source status: " + data["giro_status"] + ". Global Kp/ap, solar measurements and CollisionDB references have no station position on this map."}


def figure_files(figure, output, name):
    result = {}
    for format_ in ["svg", "png"]:
        path = output / (name + "." + format_)
        figure.savefig(path, format=format_, dpi=160, facecolor="white")
        result[format_] = {"filename": path.name, "base64": base64.b64encode(path.read_bytes()).decode("ascii")}
    return result


def draw_timeline(document, groups, output, plt, mdates, LineCollection, *, window=None, vertical_ranges=None):
    unlocated = sum(begin is None for items in groups.values() for item in items for begin, _, _ in item["excluded"])
    if window:
        groups = timeline_window(groups, window)
    request = document["run"].get("request", {})
    active = [panel for panel in PANELS if groups[panel[0]] or panel[3] in request]
    times = [time for series in groups.values() for item in series for begin, end, _ in item["points"] for time in [begin, end] if time]
    for panel in active:
        selection = request.get(panel[3], {})
        times.extend(parsed for name in ["start", "end"] if (parsed := date(selection.get(name))))
    if not active or (not times and not window):
        return None
    if window:
        limits = window
    elif min(times) == max(times):
        limits = (min(times) - timedelta(hours=1), max(times) + timedelta(hours=1))
    else:
        limits = (min(times), max(times))
    fig, axes = plt.subplots(len(active), 1, figsize=(15.8, 2.3 * len(active) + 1.2), sharex=True, squeeze=False)
    fig.subplots_adjust(left=.09, right=.70, top=.95, bottom=.09, hspace=.35)
    figure_title = "Mainshock close-up · ±24 hours" if window else "Temporal context"
    fig.suptitle(figure_title, x=.09, ha="left", fontsize=12)
    anchor = anchor_time(document)
    locators, omissions, ranges = [], [], {}
    for ax, (name, title, unit, family) in zip(axes[:, 0], active):
        selection = request.get(family, {})
        begin, end = date(selection.get("start")), date(selection.get("end"))
        if begin and end:
            ax.axvspan(begin, end, color="#edf4f4", zorder=0)
        palette, plotted = {}, 0
        for item in groups[name]:
            colour = palette.setdefault(item["label"], COLOURS[len(palette) % len(COLOURS)])
            spans, instants = [], []
            for begin, end, value in item["points"]:
                if end and end > begin:
                    spans.append([(mdates.date2num(begin), value), (mdates.date2num(end), value)])
                else:
                    instants.append((begin, value))
            if spans:
                collection = LineCollection(spans, colors=colour, linewidths=1, label=item["label"], rasterized=True)
                ax.add_collection(collection)
                ax.autoscale_view(scalex=False)
            if instants:
                ax.scatter([point[0] for point in instants], [point[1] for point in instants], s=14 if name == "earthquake" else 4,
                           color=colour, label=item["label"], rasterized=True)
            plotted += len(item["points"])
            if item["points"] or item["missing"] or item["nonpositive"]:
                locators.append(item["locator"])
        if name == "XRS" and (plotted or (vertical_ranges and name in vertical_ranges)):
            ax.set_yscale("log")
        if name == "Kp":
            ax.set_ylim(0, 9)
        if vertical_ranges and name in vertical_ranges:
            ax.set_ylim(*vertical_ranges[name])
        ranges[name] = [float(value) for value in ax.get_ylim()]
        if not plotted:
            ax.text(.5, .5, "No plottable returned values", ha="center", va="center", transform=ax.transAxes, color="#657387")
            ax.set_yticks([])
        if anchor:
            ax.axvline(anchor, color="#b87332", linestyle="--", linewidth=.9)
        handles, labels = ax.get_legend_handles_labels()
        unique = dict(zip(labels, handles))
        if unique:
            ax.legend(unique.values(), unique.keys(), fontsize=8, loc="upper left", bbox_to_anchor=(1.025, 1),
                      borderaxespad=0, ncol=1, frameon=False)
        missing = sum(item["missing"] for item in groups[name])
        nonpositive = sum(item["nonpositive"] for item in groups[name])
        ax.set_title(title + " · " + str(plotted) + (" catalogue reports" if name == "earthquake" else " values"), loc="left", fontsize=10)
        ax.set_ylabel(unit, fontsize=9)
        ax.grid(axis="y", color="#dbe2e8", linewidth=.5)
        ax.set_xlim(*limits)
        ax.tick_params(labelsize=8)
        if missing or nonpositive:
            omissions.append({"panel": name, "missing_or_invalid_time": missing, "nonpositive_on_log_axis": nonpositive})
    axes[-1, 0].xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=7, tz=model.UTC))
    axes[-1, 0].xaxis.set_major_formatter(mdates.DateFormatter("%d %b\n%H:%M", tz=model.UTC))
    axes[-1, 0].set_xlabel("UTC · orange dashed line: source-preferred USGS anchor origin" if anchor else "UTC", fontsize=9)
    fig.text(.09, .014, "USGS / EMSC / GEOFON · GFZ: doi:10.5880/Kp.0001 (CC BY 4.0)\nGIRO: station IDs in legends; doi:10.5047/eps.2011.03.001 (CC BY-NC-SA 4.0) · NOAA/NCEI GOES-18 XRS\nTemporal context only. Tinted regions are requested windows; gaps are not filled." +
             (" Close-up: ±24 h; vertical ranges match the overview." if window else ""), fontsize=8, color="#657387")
    try:
        files = figure_files(fig, output, "mainshock-closeup" if window else "timeline")
    finally:
        plt.close(fig)
    unique_locators = list({(item["path"], item["index"]): item for item in locators}.values())
    return {"title": figure_title, "files": files, "locators": unique_locators, "omissions": omissions,
            "vertical_ranges": ranges, "time_window": [model.stamp(value) for value in limits],
            "caption": "Each catalogue report uses its preferred origin time and preferred magnitude; those preferences may belong to different origins. Native scales are shown in legends and alternative estimates remain in the record. No event deduplication or causal finding is asserted. Instant/label-only samples use markers; explicit support intervals use horizontal segments. Finite values with usable timestamps are shown except nonpositive XRS values, which cannot appear on a logarithmic ordinate. Quality flags are retained without a display filter. Dense marks are rasterized inside SVG; axis text stays vector." +
                ((" Close-up window [" + model.stamp(limits[0]) + ", " + model.stamp(limits[1]) + ") is centred on the returned preferred anchor time, with the overview's vertical ranges. Counts include native intervals intersecting the window; edges of those intervals are visually clipped, without shortening their stored support. Omission counts refer to this window. Across the full input, " + str(unlocated) + " quantity/report entries lack usable timestamps and cannot be assigned to this window. No baseline subtraction, resampling or response-lag correction is performed.") if window else "")}


def curve_data(record):
    kind = "cross_section" if "cross_section" in record else "rate_coefficient"
    curve = record.get(kind, {})
    if not curve.get("X", {}).get("unit") or not curve.get("Y", {}).get("unit"):
        raise ValueError("Reference curve needs the X/Y layout; rebuild the study with the axis patch first")
    points = [point for point in curve.get("points", []) if numeric(point.get("X")) and numeric(point.get("Y"))]
    bands = []
    percent = record.get("uncertainty", {}).get("relative_percent")
    for point in points:
        error = point.get("uncertainty", {})
        lower, upper = error.get("lower"), error.get("upper")
        if not error and numeric(percent):
            lower = upper = abs(point["Y"]) * percent / 100
        bands.append((lower, upper) if numeric(lower) and numeric(upper) else None)
    return kind, curve, points, bands


def draw_reference(key, record, locator, output, number, plt):
    kind, curve, points, bands = curve_data(record)
    fig, ax = plt.subplots(figsize=(7, 4.6))
    fig.subplots_adjust(left=.15, right=.96, top=.85, bottom=.28)
    if points:
        x, y = [point["X"] for point in points], [point["Y"] for point in points]
        ax.plot(x, y, color="#126b67", linewidth=1, marker=".", markersize=4, label="Reported table")
        for point, band in zip(points, bands):
            if band:
                ax.vlines(point["X"], point["Y"] - band[0], point["Y"] + band[1], color="#126b67", alpha=.3, linewidth=.7)
        if all(value > 0 for value in x):
            ax.set_xscale("log")
        validity = curve.get("fit", {}).get("validity", {})
        lo, hi = validity.get("lower_argument"), validity.get("upper_argument")
        if numeric(lo) and numeric(hi) and lo < hi and validity.get("unit") == curve["X"]["unit"]:
            ax.axvspan(lo, hi, color="#edf4f4", zorder=0, label="Reported fit domain")
        ax.legend(fontsize=8)
    else:
        ax.text(.5, .5, "No finite tabulated points", ha="center", transform=ax.transAxes)
    ax.set_xlabel(curve["X"].get("name", "X") + " / " + curve["X"]["unit"])
    ax.set_ylabel(curve["Y"].get("name", "Y") + " / " + curve["Y"]["unit"])
    qid = record.get("identity", {}).get("source_id", "Unidentified dataset")
    ax.set_title(qid + " · " + kind.replace("_", " "), loc="left", fontsize=11)
    ax.grid(color="#dbe2e8", linewidth=.5)
    citations = [item["doi"] for item in record.get("provenance", {}).get("citation", []) if item.get("doi")]
    production = "Fit-generated table" if curve.get("data_from_fit") is True else "Source table" if curve.get("data_from_fit") is False else "Table production unspecified"
    if curve.get("fit", {}).get("function"):
        production += " · fit: " + curve["fit"]["function"]
    if record.get("provenance", {}).get("method", {}).get("name"):
        production += " · method: " + record["provenance"]["method"]["name"]
    notes = [record.get("process", {}).get("reaction", ""), production,
             "Reported uncertainties; no confidence level assumed. CollisionDB: CC BY 4.0.", *citations]
    fig.text(.15, .04, "\n".join(textwrap.fill(line, 86) for line in notes if line), fontsize=7, color="#657387")
    try:
        files = figure_files(fig, output, "reference-" + str(number).zfill(3))
    finally:
        plt.close(fig)
    return {"title": qid + " · " + kind.replace("_", " "), "files": files, "locators": [locator],
            "caption": "Native X/Y labels and units are retained. Connecting lines join supplied table points for display; no fit is evaluated and no extrapolation or rate calculation is performed. Error marks use explicit point uncertainties first, otherwise the reported dataset percentage. The rate coordinate E/eV is not relabelled as temperature. Fit shading represents source-stated validity, not sample coverage.",
            "citations": citations, "points": len(points), "missing_values": len(curve.get("points", [])) - len(points)}


def build(document, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.collections import LineCollection
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    groups = timeline_data(document)
    figures = []
    timeline = draw_timeline(document, groups, output, plt, mdates, LineCollection)
    if timeline:
        figures.append(timeline)
        window = closeup_window(document)
        if window:
            closeup = draw_timeline(document, groups, output, plt, mdates, LineCollection,
                                    window=window, vertical_ranges=timeline["vertical_ranges"])
            if closeup:
                figures.append(closeup)
    try:
        geography = draw_geography(document, output, plt)
        if geography:
            figures.append(geography)
    except (ValueError, KeyError, TypeError) as error:
        figures.append({"title": "Geographic context", "error": str(error), "locators": []})
    for key, record, locator in records(document):
        if key.partition("@")[0] == "collision_dataset":
            try:
                figures.append(draw_reference(key, record, locator, output, len(figures) + 1, plt))
            except (ValueError, KeyError, TypeError) as error:
                figures.append({"title": record.get("identity", {}).get("source_id", "Reference curve"), "error": str(error), "locators": [locator]})
    return {"version": VISUAL_VERSION, "status": "partial" if any(figure.get("error") for figure in figures) else "ok", "input_sha256": digest(document),
            "generated_at": model.stamp(datetime.now(model.UTC)), "figures": figures, "coverage": coverage_rows(document),
            "notes": ["Figures are built entirely from this study and run report; no provider is contacted.",
                      "Returned extent includes gaps and missing-valued samples; it is not a statement of continuous observing coverage.",
                      "Quality counts describe metadata availability, not a universal acceptance or confidence score.",
                      "Sample/record counts do not count independent evidence or unique physical earthquakes."]}


def load(document, output):
    path = Path(output) / "visuals.json"
    if path.exists():
        try:
            result = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return document
        if result.get("version") == VISUAL_VERSION and result.get("input_sha256") == digest(document):
            document["visuals"] = result
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("build/kamchatka"), help="Directory of the existing study.json and run.json")
    args = parser.parse_args()
    document = {"study": json.loads((args.output / "study.json").read_text())["study"],
                "run": json.loads((args.output / "run.json").read_text())}
    from .kamchatka import save
    save(document, args.output, write_science=False)
    if document["visuals"]["status"] != "ok":
        raise SystemExit(document["visuals"].get("error") or "Some figures could not be built; inspect index.html or visuals.json")
    print("Figures and viewer written under " + str(args.output.resolve()) + "; no source requests made")


if __name__ == "__main__":
    main()
