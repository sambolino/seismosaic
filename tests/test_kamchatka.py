"""Offline checks for scientific distinctions that a live smoke run cannot ensure."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from demo import kamchatka, model

START = model.utc("2025-07-29T00:00:00Z")
END = model.utc("2025-07-30T00:00:00Z")


class ProjectionTests(unittest.TestCase):
    def test_quakeml_estimates_and_references(self):
        payload = b'''<q:quakeml xmlns:q="http://quakeml.org/xmlns/quakeml/1.2" xmlns="http://quakeml.org/xmlns/bed/1.2"><eventParameters publicID="ep"><event publicID="event">
        <preferredOriginID>o2</preferredOriginID><preferredMagnitudeID>m1</preferredMagnitudeID>
        <origin publicID="o1"><depth><value>35000</value></depth></origin>
        <origin publicID="o2"><time><value>2025-07-29T23:24:52.483Z</value></time><depth><value>20000</value></depth></origin>
        <magnitude publicID="m1"><mag><value>8.8</value></mag><type>mww</type><originID>o2</originID></magnitude>
        </event></eventParameters></q:quakeml>'''
        record = model.quakeml(payload, "catalogue", "route", "https://example.invalid")[0]
        self.assertEqual(record["origin"][0]["depth"], 35)
        self.assertEqual(model.preferred(record, "origin")["identity"]["source_id"], "o2")
        self.assertFalse(record["origin"][0]["preferred"])
        self.assertEqual(record["magnitude"][0]["origin_id"], "o2")
        self.assertNotIn("provenance", record["origin"][0])
        self.assertNotIn("$edges", record)
        with self.assertRaises(ValueError):
            model.quakeml(payload.replace(b"<originID>o2", b"<originID>absent"), "catalogue", "route", "uri")

    def test_gfz_end_label_and_missing_status(self):
        payload = json.dumps({"datetime": ["2025-07-29T21:00:00Z", "2025-07-30T00:00:00Z"], "ap": [12, 0]}).encode()
        record = model.gfz(payload, "ap", START, END, "uri")
        self.assertEqual(len(record["points"]), 1)
        self.assertEqual(record["points"][0]["ap"]["value"], 12)  # Keep the 2 nT scale.
        self.assertEqual(record["points"][0]["time"]["end"], "2025-07-30T00:00:00Z")
        self.assertNotIn("quality", record["points"][0])
        with self.assertRaises(ValueError):
            model.gfz(json.dumps({"datetime": ["2025-07-29T00:00:00Z"], "ap": []}).encode(), "ap", START, END, "uri")

    def test_station_coordinates_cross_the_dateline(self):
        payload = json.dumps({"Status": "SUCCESS", "LocationList_Brief": [{"U": "EA653", "N": "EARECKSON", "Lat": 52.7, "Lon": 185.9}]}).encode()
        selected = model.stations(payload, 52.4948, 160.2395, 3000)
        self.assertAlmostEqual(selected[0]["longitude"], -174.1)
        self.assertLess(selected[0]["distance_km"], 3000)

    def test_giro_quality_and_missing_quantity(self):
        body = '''# Tabulated Rapid Access Ionospheric Characteristics, Version 1.1
# Location: URSI-Code EA653
# Time                    CS   foF2 QD   hmF2 QD
2025-07-29T00:00:00Z 999 5.9 AB 250 CD
2025-07-29T00:07:30Z -1 --- __ 251 //
2025-07-29T00:15:00Z 100 0 // 252 //
'''.encode()
        site = {"code": "EA653", "name": "EARECKSON", "latitude": 52.7, "longitude": -174.1}
        record = model.giro(body, site, START, END, "uri")
        first, missing, zero = record["points"]
        self.assertEqual(first["quality"]["confidence_code"], "999")
        self.assertNotIn("confidence_score", first["quality"])
        self.assertNotIn("status", first["foF2"]["quality"])
        self.assertEqual(first["foF2"]["quality"]["scaling"], "manual")
        self.assertEqual(first["foF2"]["quality"]["qualifying_letter"], "A")
        self.assertNotIn("value", missing["foF2"])
        self.assertNotIn("confidence_score", missing["quality"])
        self.assertEqual(zero["foF2"]["value"], 0)
        self.assertNotIn("cadence", record)
        self.assertIsNone(model.giro(b"# STATUS: ERROR (No measurement data could be found for requested time)", site, START, END, "uri"))

    def test_goes_masked_flux_support_and_flags(self):
        try:
            from netCDF4 import Dataset
        except ImportError:
            self.skipTest("Install demo/requirements.txt to check historical GOES projection")
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp)/"tiny.nc"
            with Dataset(file, "w") as data:
                data.title = "L2 XRS 1 minute average"
                data.platform = "g18"
                data.id = "sci_xrsf-l2-avg1m_g18_d20250729_v2-2-1.nc"
                data.processing_level = "Level 2"
                data.createDimension("time", 1)
                time = data.createVariable("time", "f8", ("time",))
                time.units = "seconds since 2000-01-01 12:00:00 UTC"
                time.long_name = "Record start time. Neglects leap seconds since 2000-01-01."
                time[:] = [(START-model.utc("2000-01-01T12:00:00Z")).total_seconds()]
                for prefix in ["xrsa", "xrsb"]:
                    for suffix in ["_flux", "_flux_observed", "_flux_electrons"]:
                        var = data.createVariable(prefix+suffix, "f4", ("time",), fill_value=-9999)
                        var.units = "W/m2"
                        var[:] = [-9999 if prefix == "xrsa" else 0]
                    for suffix in ["_flag", "_flag_excluded"]:
                        var = data.createVariable(prefix+suffix, "i4", ("time",))
                        var[:] = [2]
                data.createVariable("electron_correction_flag", "i4", ("time",))[:] = [1]
            record, native = model.goes(file.read_bytes(), "uri", START, END)
        point = record["points"][0]
        self.assertEqual(point["time"]["start"], "2025-07-29T00:00:00Z")
        self.assertEqual(point["time"]["end"], "2025-07-29T00:01:00Z")
        self.assertNotIn("value", point["irradiance"]["xrs_a"])
        self.assertEqual(point["irradiance"]["xrs_b"]["value"], 0)
        self.assertEqual(json.loads(point["irradiance"]["xrs_a"]["quality"]["flags"])["xrsa_flag"], 2)

    def test_snapshot_escapes_source_text_and_preserves_numbers(self):
        doc = {"study": {"x": [{"value": 0, "name": "</script><script>evil()</script>"}]}, "run": {}}
        with tempfile.TemporaryDirectory() as tmp:
            kamchatka.save(doc, Path(tmp))
            content = (Path(tmp)/"index.html").read_text()
            self.assertNotIn("</script><script>evil", content)
            self.assertIn("\\u003c/script>", content)
            self.assertEqual(json.loads((Path(tmp)/"study.json").read_text())["study"]["x"][0]["value"], 0)

    def test_cached_report_never_mislabels_cache_as_live(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            class Response:
                status, url = 200, "https://example.invalid/data"
                def __enter__(self): return self
                def __exit__(self, *_): pass
                def read(self, _): return b'[{"value":0}]'
            with patch("urllib.request.urlopen", return_value=Response()):
                _, first = kamchatka.request(Response.url, output=root)
            with patch("urllib.request.urlopen", side_effect=AssertionError("Unexpected network call")):
                body, cached = kamchatka.request(Response.url, output=root, reuse=True)
            self.assertFalse(first["cached"])
            self.assertTrue(cached["cached"])
            self.assertEqual(first["fetched_at"], cached["fetched_at"])
            self.assertEqual(body, b'[{"value":0}]')

    def test_source_failures_leave_a_partial_study_without_fake_series(self):
        anchor = b'''<q:quakeml xmlns:q="http://quakeml.org/xmlns/quakeml/1.2" xmlns="http://quakeml.org/xmlns/bed/1.2"><eventParameters publicID="ep"><event publicID="anchor">
        <preferredOriginID>origin</preferredOriginID><preferredMagnitudeID>magnitude</preferredMagnitudeID>
        <origin publicID="origin"><time><value>2025-07-29T23:24:52.483Z</value></time><latitude><value>52.4948</value></latitude><longitude><value>160.2395</value></longitude></origin>
        <magnitude publicID="magnitude"><mag><value>8.8</value></mag><type>mww</type><originID>origin</originID></magnitude>
        </event></eventParameters></q:quakeml>'''
        def fetch(url, params=None, *args):
            if isinstance(params, dict) and params.get("eventid") == kamchatka.ANCHOR["usgs_id"]:
                return anchor, {"http_status": 200, "cached": False}
            raise OSError("Source unavailable in offline test")
        with tempfile.TemporaryDirectory() as tmp, patch("demo.kamchatka.request", side_effect=fetch):
            document = kamchatka.run(tmp, progress=lambda _: None)
        self.assertEqual(document["run"]["status"], "partial")
        self.assertEqual(document["run"]["record_count"], 1)
        self.assertEqual(document["run"]["sources"]["giro"]["status"], "failed")
        self.assertEqual(len(document["run"]["sources"]["goes"]["days"]), 22)
        self.assertEqual(list(document["study"]), ["seismic_event@usgs:usgs-fdsn"])


if __name__ == "__main__":
    unittest.main()
