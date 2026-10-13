"""Small provider projections. Never parse the ordered ontology as YAML."""
import json
import math
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

UTC = timezone.utc
NS = {"b": "http://quakeml.org/xmlns/bed/1.2"}


def utc(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp has no timezone: " + value)
    return parsed.astimezone(UTC)


def stamp(value):
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def number(value):
    if value is None:
        return None
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Non-finite scientific value")
    return result


def distance(lat1, lon1, lat2, lon2):
    a, b, c, d = map(math.radians, (lat1, lon1, lat2, lon2))
    h = math.sin((c-a)/2)**2 + math.cos(a)*math.cos(c)*math.sin((d-b)/2)**2
    return 6371.0088 * 2 * math.asin(min(1, math.sqrt(h)))


def provenance(producer, channel, uri, reference=None):
    out = {"producer": {"name": producer}, "channel": {"name": channel, "uri": uri}}
    if reference:
        out["reference"] = reference
    return out


def text(element, path):
    return element.findtext(path, namespaces=NS)


def identity(public_id):
    return {"source_id": public_id, "namespace": "quakeml:publicID"}


def estimate_provenance(element):
    agency, author = text(element, "b:creationInfo/b:agencyID"), text(element, "b:creationInfo/b:author")
    parts = [label + "=" + value for label, value in [("agencyID", agency), ("author", author)] if value]
    if parts:
        return {"producer": {"name": "; ".join(parts)}}
    return None


def quakeml(payload, producer, channel, uri):
    root = ET.fromstring(payload)
    if root.tag != "{http://quakeml.org/xmlns/quakeml/1.2}quakeml":
        raise ValueError("Expected QuakeML 1.2 wrapper")
    records = []
    for event in root.findall("b:eventParameters/b:event", NS):
        record = {"identity": identity(event.attrib["publicID"]),
                  "provenance": provenance(producer, channel, uri), "origin": [], "magnitude": []}
        for tag in ["origin", "magnitude"]:
            preferred = text(event, "b:preferred" + tag.title() + "ID")
            for node in event.findall("b:" + tag, NS):
                item = {"identity": identity(node.attrib["publicID"])}
                if preferred:
                    item["preferred"] = preferred == node.attrib["publicID"]
                prov = estimate_provenance(node)
                if prov:
                    item["provenance"] = prov
                quality = {}
                for native, target in [("evaluationMode", "evaluation_mode"), ("evaluationStatus", "status")]:
                    value = text(node, "b:" + native)
                    if value:
                        quality[target] = value
                if quality:
                    item["quality"] = quality
                if tag == "origin":
                    value = text(node, "b:time/b:value")
                    if value:
                        item["time"] = {"instant": stamp(utc(value))}
                    position = {}
                    for field in ["latitude", "longitude"]:
                        value = text(node, "b:" + field + "/b:value")
                        if value is not None:
                            position[field] = number(value)
                    if position:
                        item["position"] = position
                    depth = text(node, "b:depth/b:value")
                    if depth is not None:
                        item["depth"] = number(depth) / 1000  # BED metres -> ontology km
                else:
                    for source, target in [("b:mag/b:value", "value"), ("b:mag/b:uncertainty", "uncertainty")]:
                        value = text(node, source)
                        if value is not None:
                            item[target] = number(value)
                    for source, target in [("b:type", "scale"), ("b:originID", "origin_id")]:
                        value = text(node, source)
                        if value:
                            item[target] = value
                record[tag].append(item)
            if preferred and not any(x["identity"]["source_id"] == preferred for x in record[tag]):
                raise ValueError("Unresolved preferred " + tag + " reference")
        origins = {x["identity"]["source_id"] for x in record["origin"]}
        for magnitude in record["magnitude"]:
            if "origin_id" in magnitude and magnitude["origin_id"] not in origins:
                raise ValueError("Unresolved magnitude originID")
        records.append(record)
    return records


def preferred(record, kind):
    return next((x for x in record[kind] if x.get("preferred")), None)


def gfz(payload, index, start, end, uri):
    data = json.loads(payload)
    labels, values = data["datetime"], data[index]
    statuses = data.get("status")
    if len(labels) != len(values) or (statuses is not None and len(statuses) != len(labels)):
        raise ValueError("GFZ parallel-array lengths differ")
    points = []
    for i, label in enumerate(labels):
        begin = utc(label)
        if not start <= begin < end:
            continue  # Select complete bins; never trim their support.
        point = {"time": {"start": stamp(begin), "end": stamp(begin + timedelta(hours=3))}}
        if statuses is not None:
            point["quality"] = {"status": statuses[i]}
        value = number(values[i])
        if value is not None:
            upper = 9 if index == "Kp" else 400
            if not 0 <= value <= upper:
                raise ValueError("GFZ value outside documented scale; possible missing token")
            point[index] = {"value": value}
        points.append(point)
    record = {"provenance": provenance("gfz-kp", "gfz-kp-json", uri, "https://doi.org/10.5880/Kp.0001"),
              "cadence": 10800, "points": points}
    if points:
        record["time"] = {"start": min(x["time"]["start"] for x in points),
                          "end": max(x["time"]["end"] for x in points)}
    return record


def stations(payload, latitude, longitude, radius):
    data = json.loads(payload)
    if data.get("Status") != "SUCCESS":
        raise ValueError("GIRO station-list status was not SUCCESS")
    selected = []
    for raw in data["LocationList_Brief"]:
        lat, lon = number(raw["Lat"]), (number(raw["Lon"]) + 180) % 360 - 180
        separation = distance(latitude, longitude, lat, lon)
        if separation <= radius:
            selected.append({"code": raw["U"], "name": raw["N"], "latitude": lat,
                             "longitude": lon, "distance_km": round(separation, 1)})
    return sorted(selected, key=lambda x: x["code"])


def giro(payload, station, start, end, uri):
    content = payload.decode("utf-8")
    if "No measurement data could be found for requested time" in content:
        return None
    if "Tabulated Rapid Access Ionospheric Characteristics, Version 1.1" not in content:
        raise ValueError("Unreviewed GIRO representation")
    if not re.search(r"URSI-Code\s+" + re.escape(station["code"]) + r"\b", content):
        raise ValueError("GIRO returned a different station")
    if "# Time                    CS   foF2 QD   hmF2 QD" not in content:
        raise ValueError("Unreviewed GIRO column layout")
    points = []
    for line in content.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 6:
            raise ValueError("Unreviewed GIRO row layout")
        timestamp, confidence, fof2, qd_f, hmf2, qd_h = parts
        instant = utc(timestamp)
        if not start <= instant < end:
            continue
        point = {"time": {"instant": stamp(instant)}, "quality": {"confidence_code": confidence}}
        if confidence not in ["999", "-1"]:
            score = number(confidence)
            if not 0 <= score <= 100:
                raise ValueError("Unknown GIRO confidence code")
            point["quality"]["confidence_score"] = score
        for quantity, raw, qd in [("foF2", fof2, qd_f), ("hmF2", hmf2, qd_h)]:
            quality = {"flags": "QD=" + qd}
            if confidence == "999":
                quality["scaling"] = "manual"  # This route's header says manual, not verified-clean.
            elif qd == "//":
                quality["scaling"] = "automatic"
            if len(qd) == 2:
                for name, token in zip(["qualifying_letter", "descriptive_letter"], qd):
                    if token.isalpha():
                        quality[name] = token
            value = {"quality": quality}
            if raw not in ["---", "----", "-----"]:
                value["value"] = number(raw)
            point[quantity] = value
        points.append(point)
    if not points:
        return None
    producer = "station-" + station["code"].lower()
    prov = provenance(producer, "giro-fastchar-form", uri,
                      "GIRO: doi:10.5047/eps.2011.03.001; acknowledge " + station["code"] +
                      " data provider; CC BY-NC-SA 4.0; https://giro.uml.edu/didbase/RulesOfTheRoad.html")
    site = {"identity": {"source_id": station["code"], "namespace": "ursi:station"},
            "name": station["name"], "position": {"latitude": station["latitude"], "longitude": station["longitude"]}}
    instrument = {"name": "Ionosonde"}
    model = re.search(r"# Instrument: Ionosonde, Model: \[([^\]]+)\]", content)
    if model:
        instrument["name"] += " " + model[1]
    prov["acquisition"] = {"station": site, "instrument": instrument}
    return {"provenance": prov, "points": points}


def goes(payload, uri, start, end):
    # netCDF4 is the only non-stdlib runtime dependency; automatic archive access.
    import numpy as np
    from netCDF4 import Dataset, num2date
    with Dataset("in-memory.nc", memory=payload) as dataset:
        if getattr(dataset, "platform", None) != "g18" or getattr(dataset, "title", None) != "L2 XRS 1 minute average":
            raise ValueError("Unexpected GOES satellite or product")
        time = dataset["time"]
        if "Record start time" not in getattr(time, "long_name", ""):
            raise ValueError("GOES time support must be reviewed")
        if getattr(time, "units", "") != "seconds since 2000-01-01 12:00:00 UTC":
            raise ValueError("Unreviewed GOES time units")
        raw_times = time[:]
        if np.ma.getmaskarray(raw_times).any():
            raise ValueError("Masked GOES time coordinate")
        times = num2date(raw_times, time.units, calendar=getattr(time, "calendar", "standard"),
                        only_use_cftime_datetimes=False, only_use_python_datetimes=True)
        names = [prefix + suffix for prefix in ["xrsa", "xrsb"] for suffix in
                 ["_flux", "_flux_observed", "_flux_electrons", "_flag", "_flag_excluded"]] + ["electron_correction_flag"]
        arrays = {name: dataset[name][:] for name in names}
        for name, values in arrays.items():
            if values.shape != raw_times.shape:
                raise ValueError("GOES variable shape mismatch: " + name)
            if "_flux" in name and getattr(dataset[name], "units", "") != "W/m2":
                raise ValueError("Unreviewed GOES irradiance units")
        definitions = {name: {key: str(getattr(dataset[name], key)) for key in
                       ["flag_meanings", "flag_values"] if hasattr(dataset[name], key)}
                       for name in names if "flag" in name}
        points = []
        for i, decoded in enumerate(times):
            begin = decoded.replace(tzinfo=UTC)
            if not start <= begin < end:
                continue
            irradiance = {}
            for prefix, band, low, high in [("xrsa", "xrs_a", .05, .4), ("xrsb", "xrs_b", .1, .8)]:
                quantity = {"statistic": "mean", "wavelength_band": {"lower": low, "upper": high}}
                for suffix, target in [("_flux", "value"), ("_flux_observed", "observed_value"), ("_flux_electrons", "electron_correction")]:
                    value = arrays[prefix+suffix][i]
                    if not np.ma.is_masked(value):
                        quantity[target] = number(value)
                flags = {}
                for name in [prefix+"_flag", prefix+"_flag_excluded", "electron_correction_flag"]:
                    value = arrays[name][i]
                    if not np.ma.is_masked(value):
                        flags[name] = int(value)
                if flags:
                    quantity["quality"] = {"flags": json.dumps(flags, separators=(",", ":"))}
                irradiance[band] = quantity
            points.append({"time": {"start": stamp(begin), "end": stamp(begin+timedelta(seconds=60)), "duration": 60},
                           "irradiance": irradiance})
        prov = provenance("noaa-ncei", "ncei-exis", uri, "NOAA/NCEI GOES-R EXIS science-quality XRS; retain product citation.")
        prov["acquisition"] = {"platform": {"name": "GOES-18"}, "instrument": {"name": "XRS"}}
        prov["product"] = {"name": dataset.id, "version": re.search(r"_v(.+)\.nc$", dataset.id)[1],
                           "edition": "science_quality", "processing_level": dataset.processing_level}
        record = {"provenance": prov, "cadence": 60, "points": points}
        if points:
            record["time"] = {"start": points[0]["time"]["start"], "end": points[-1]["time"]["end"]}
        return record, {"native_time_units": time.units, "native_time_description": time.long_name,
                        "flag_definitions": definitions, "institution": getattr(dataset, "institution", None)}
