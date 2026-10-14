"""Offline scientific-display checks; commands are provided for local execution."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from demo import kamchatka, model, visuals


def reference():
    return {"identity": {"source_id": "D111118", "namespace": "collisiondb:dataset"},
            "provenance": {"database": {"added_at": "2023-02-09T16:09:28Z"},
                           "citation": [{"doi": "https://doi.org/10.1063/1.555809"}]},
            "process": {"reaction": "e- + O → O+ + 2e-"}, "uncertainty": {"relative_percent": 10},
            "cross_section": {"X": {"name": "E", "unit": "eV"}, "Y": {"name": "sigma", "unit": "cm2"},
                "data_from_fit": True, "fit": {"validity": {"lower_argument": 1, "upper_argument": 20, "unit": "eV"}},
                "points": [{"X": 1, "Y": 0}, {"X": 2, "Y": 10, "uncertainty": {"lower": 0, "upper": 0}},
                           {"X": 3, "Y": 20, "uncertainty": {"lower": 2, "upper": 4}}, {"X": 4, "Y": 100}]}}


def fixture():
    earthquake = {"identity": {"source_id": "event"},
                  "origin": [{"identity": {"source_id": "o"}, "preferred": True, "time": {"instant": "2025-07-29T23:24:52Z"},
                              "magnitude": [{"preferred": True, "value": 8.8, "scale": "mww"}]}]}
    return {"study": {
        "seismic_event@usgs:usgs-fdsn": [earthquake],
        "seismic_event@emsc:emsc-fdsn": [copy.deepcopy(earthquake)],
        "ionospheric_series@station-aa:giro-fastchar-form": [{"points": [
            {"time": {"instant": "2025-07-29T22:00:00Z"}, "foF2": {"value": 0, "quality": {"flags": "QD=//"}}},
            {"time": {"instant": "2025-07-29T22:15:00Z"}, "foF2": {"quality": {"flags": "QD=__"}}}]}],
        "geomagnetic_series@gfz-kp:gfz-kp-json": [{"points": [
            {"time": {"start": "2025-07-29T21:00:00Z", "end": "2025-07-30T00:00:00Z"}, "Kp": {"value": 0}},
            {"time": {"start": "2025-07-30T03:00:00Z", "end": "2025-07-30T06:00:00Z"}, "Kp": {"value": 4}}]}],
        "solar_irradiance_series@noaa-ncei:ncei-exis": [{"points": [
            {"time": {"start": "2025-07-29T23:24:00Z", "end": "2025-07-29T23:25:00Z"}, "irradiance": {"xrs_a": {"value": 0}}},
            {"time": {"start": "2025-07-29T23:25:00Z", "end": "2025-07-29T23:26:00Z"}, "irradiance": {"xrs_a": {"value": 1e-7, "quality": {"flags": "{\"xrsa_flag\":2}"}}}}]}],
        "collision_dataset@collisiondb:collisiondb-api": [reference()]},
        "run": {"output_version": kamchatka.OUTPUT_VERSION, "finished_at": "2026-10-14T00:00:00Z", "status": "partial",
            "request": {"seismic": {"start": "2025-07-29T00:00:00Z", "end": "2025-07-31T00:00:00Z"}, "collisiondb": {"pks": [111118]}},
            "sources": {"giro": {"status": "ok", "stations": [{"code": "BB", "status": "no_data_reported"}]},
                        "collisiondb": {"status": "partial"}},
            "anchor": {"record": {"path": "study.seismic_event@usgs:usgs-fdsn", "identity": {"source_id": "event"}}}}}


class VisualTests(unittest.TestCase):
    def test_support_zero_missing_and_log_exclusions(self):
        document = fixture()
        before = copy.deepcopy(document)
        groups = visuals.timeline_data(document)
        self.assertEqual(len(groups["earthquake"]), 2)  # Two reports, without automatic event merging.
        self.assertEqual(groups["foF2"][0]["points"][0][2], 0)
        self.assertEqual(groups["foF2"][0]["missing"], 1)
        self.assertIsNone(groups["foF2"][0]["points"][0][1])
        self.assertEqual((groups["Kp"][0]["points"][0][1] - groups["Kp"][0]["points"][0][0]).total_seconds(), 10800)
        self.assertEqual(len(groups["Kp"][0]["points"]), 2)  # The gap stays a gap.
        self.assertEqual(groups["XRS"][0]["nonpositive"], 1)
        self.assertEqual(len(groups["XRS"][0]["points"]), 1)  # Nonzero native flag does not remove a value.
        self.assertEqual(visuals.anchor_time(document), model.utc("2025-07-29T23:24:52Z"))
        self.assertEqual(document, before)

    def test_native_axes_uncertainty_precedence_and_extent(self):
        record = reference()
        before = copy.deepcopy(record)
        kind, curve, points, bands = visuals.curve_data(record)
        self.assertEqual(curve["Y"]["unit"], "cm2")
        self.assertEqual([point["Y"] for point in points], [0, 10, 20, 100])
        self.assertEqual(bands, [(0, 0), (0, 0), (2, 4), (10, 10)])
        self.assertIsNone(visuals.extent(record))  # Database insertion is not observation time.
        self.assertEqual(record, before)

    def test_coverage_includes_no_data_site_and_input_ids(self):
        rows = visuals.coverage_rows(fixture())
        site = next(row for row in rows if row["label"] == "GIRO BB")
        self.assertEqual(site["status"], "no_data_reported")
        self.assertEqual(site["records"], 0)
        row = next(row for row in rows if row["source"] == "collisiondb")
        self.assertEqual(row["requested"], {"pks": [111118]})
        self.assertIsNone(row["returned"])
        self.assertEqual(row["samples"], 4)

    def test_exports_offline_rebuild_and_sidecar_fingerprint(self):
        try:
            import matplotlib  # noqa: F401
        except ImportError:
            self.skipTest("Install demo/requirements.txt for figure export checks")
        document = fixture()
        before = copy.deepcopy(document)
        with tempfile.TemporaryDirectory() as tmp, patch("urllib.request.urlopen", side_effect=AssertionError("Unexpected network")), patch("demo.kamchatka.request", side_effect=AssertionError("Unexpected retrieval")):
            root = Path(tmp)
            (root / "study.json").write_text(json.dumps({"study": document["study"]}, separators=(",", ":")))
            (root / "run.json").write_text(json.dumps(document["run"], separators=(",", ":")))
            native_study, native_run = (root / "study.json").read_bytes(), (root / "run.json").read_bytes()
            kamchatka.save(document, root, write_science=False)
            result = document["visuals"]
            self.assertEqual(result["status"], "ok")
            self.assertEqual(len(result["figures"]), 2)
            for figure in result["figures"]:
                self.assertTrue((root / "figures" / figure["files"]["png"]["filename"]).read_bytes().startswith(b"\x89PNG"))
                self.assertIn(b"<svg", (root / "figures" / figure["files"]["svg"]["filename"]).read_bytes())
            self.assertEqual((root / "study.json").read_bytes(), native_study)
            self.assertEqual((root / "run.json").read_bytes(), native_run)
            self.assertEqual({key: document[key] for key in ["study", "run"]}, before)
            self.assertIn("visuals", visuals.load(copy.deepcopy(before), root))
            before["run"]["status"] = "changed"
            self.assertNotIn("visuals", visuals.load(before, root))


if __name__ == "__main__":
    unittest.main()
