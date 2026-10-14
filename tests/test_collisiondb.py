"""Offline checks for reference meaning, client uncertainty and native replay."""
import hashlib
import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from demo import collisiondb, kamchatka


class Species:
    def __init__(self, formula, states=()):
        self.formula, self.states = formula, list(states)

    def __str__(self):
        return " ".join([self.formula, *self.states])


def dataset(root, rows=("1 0", "2 4"), **updates):
    metadata = {"qid": "D111118", "reaction": "e- + O → O+ + 2e-",
                "data_type": "cross section", "process_types": {"EIN": "Ionization"},
                "columns": [{"name": "E", "units": "eV"}, {"name": "sigma", "units": "cm2"}],
                "refs": {"B54": {"doi": "https://doi.org/10.1063/1.555809"}}, "method": "semi-empirical"}
    metadata.update(updates)
    filepath = root / (metadata["qid"][1:] + ".txt")
    filepath.write_text(json.dumps(metadata) + "\n----\n" + "\n".join(rows) + "\n")
    reaction = SimpleNamespace(reactants=[(1, Species("e-")), (1, Species("O"))],
                               products=[(1, Species("O+")), (2, Species("e-"))])
    return SimpleNamespace(metadata=metadata, filepath=filepath, reaction=reaction, n=len(rows),
                           x=[float(row.split()[0]) for row in rows],
                           y=[float(row.split()[1].split(":")[0]) for row in rows],
                           unc_lo=[0] * len(rows), unc_hi=[0] * len(rows))


class ReferenceTests(unittest.TestCase):
    def test_native_values_scope_and_participants(self):
        with tempfile.TemporaryDirectory() as tmp:
            ds = dataset(Path(tmp), unc_perc=10, data_from_fit=True,
                         fit={"func": "BELI", "coeffs": {"pcf(1)": 13.6}, "Elo": 13.6, "Ehi": 20000},
                         time_added="2023-02-09 18:09:28.478408+02:00", metadata_version="M1.0")
            record = collisiondb.project_dataset(ds)
        curve = record["cross_section"]
        self.assertEqual(curve["points"][0], {"X": 1, "Y": 0})
        self.assertEqual(curve["Y"]["unit"], "cm2")
        self.assertEqual(record["uncertainty"], {"relative_percent": 10})
        self.assertEqual(curve["fit"]["validity"]["lower_argument"], 13.6)
        self.assertNotIn("threshold", record["process"])
        self.assertTrue(curve["data_from_fit"])
        self.assertEqual(record["process"]["product"][1]["count"], 2)
        self.assertEqual(record["provenance"]["database"]["added_at"], "2023-02-09T16:09:28.478408Z")
        self.assertEqual(record["provenance"]["citation"][0]["identity"]["namespace"], "collisiondb:reference")
        for field in ["time", "position", "$edges"]:
            self.assertNotIn(field, record)
        self.assertNotIn("creation", record["provenance"])
        self.assertNotIn("updated_at", record["provenance"])
        self.assertNotIn("version", record["provenance"]["producer"])

    def test_missing_zero_symmetric_and_asymmetric_uncertainty(self):
        with tempfile.TemporaryDirectory() as tmp:
            ds = dataset(Path(tmp), rows=("1 0", "2 4:0", "3 4:1", "4 4:1:2"))
            points = collisiondb.project_dataset(ds)["cross_section"]["points"]
        self.assertNotIn("uncertainty", points[0])
        self.assertEqual(points[1]["uncertainty"], {"lower": 0, "upper": 0})
        self.assertEqual(points[2]["uncertainty"], {"lower": 1, "upper": 1})
        self.assertEqual(points[3]["uncertainty"], {"lower": 1, "upper": 2})

    def test_rate_axis_is_not_invented_temperature(self):
        with tempfile.TemporaryDirectory() as tmp:
            ds = dataset(Path(tmp), qid="D110743", data_type="rate coefficient",
                         columns=[{"name": "E", "units": "eV"}, {"name": "rate", "units": "cm3.s-1"}],
                         data_from_fit=False, unc_perc=0)
            ds.reaction.reactants[1] = (1, Species("O", ["3P"]))
            record = collisiondb.project_dataset(ds)
        self.assertEqual(record["rate_coefficient"]["X"], {"name": "E", "unit": "eV"})
        self.assertFalse(record["rate_coefficient"]["data_from_fit"])
        self.assertEqual(record["uncertainty"]["relative_percent"], 0)
        self.assertEqual(record["process"]["reactant"][1]["state"], ["3P"])
        self.assertNotIn("cross_section", record)
        self.assertNotIn("temperature", json.dumps(record))

    def test_arrays_and_invalid_values_need_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ds = dataset(root)
            ds.y[1] = 5
            with self.assertRaisesRegex(ValueError, "differ"):
                collisiondb.project_dataset(ds)
            ds = dataset(root)
            ds.x.pop()
            with self.assertRaisesRegex(ValueError, "lengths"):
                collisiondb.project_dataset(ds)
            for rows in [("1 nan",), ("1 -1",), ("2 1", "1 2"), ("1 1:-2",)]:
                with self.subTest(rows=rows), self.assertRaises(ValueError):
                    collisiondb.project_dataset(dataset(root, rows=rows))
            ds = dataset(root, qid="D999")
            with self.assertRaisesRegex(ValueError, "Unexpected dataset"):
                collisiondb.project_dataset(ds)

    def test_no_data_partial_and_failure_stay_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = collisiondb.project_dataset(dataset(Path(tmp)))
            cases = [(list(), "no_data", "partial"), ([record], "partial", "partial")]
            for records, source_status, run_status in cases:
                payload = {"records": records, "receipt": {"cached": False}, "metadata_versions": ["M1.0"]}
                with patch("demo.collisiondb.fetch", return_value=payload):
                    document = collisiondb.run(tmp, progress=lambda _: None)
                self.assertEqual(document["run"]["sources"]["collisiondb"]["status"], source_status)
                self.assertEqual(document["run"]["status"], run_status)
                self.assertEqual(document["run"]["record_count"], len(records))
            with patch("demo.collisiondb.fetch", side_effect=RuntimeError("Unavailable")):
                document = collisiondb.run(tmp, progress=lambda _: None)
            self.assertEqual(document["run"]["status"], "failed")
            self.assertEqual(document["study"], {})
            self.assertEqual(document["run"]["sources"]["collisiondb"]["error"], "Unavailable")

    def test_client_deadline_is_a_failure(self):
        with patch("demo.collisiondb.subprocess.run", side_effect=subprocess.TimeoutExpired("worker", 120)):
            with self.assertRaisesRegex(RuntimeError, "120-second"):
                collisiondb.fetch(Path("unused"))

    def test_native_archive_replay_without_network_and_checksum_guard(self):
        try:
            import pycollisiondb  # noqa: F401
        except ImportError:
            self.skipTest("Install demo/requirements.txt to test the actual client's archive replay")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            raw = output / "raw"
            raw.mkdir()
            first = dataset(raw)
            second = dataset(raw, qid="D110743", data_type="rate coefficient",
                             columns=[{"name": "E", "units": "eV"}, {"name": "rate", "units": "cm3.s-1"}])
            archive = raw / "test-native.zip"
            manifest = {"ndatasets": 2, "datasets": {ds.metadata["qid"]: {"reaction": ds.metadata["reaction"]} for ds in [first, second]}}
            with zipfile.ZipFile(archive, "w") as zipfile_:
                for ds in [first, second]:
                    zipfile_.write(ds.filepath, ds.filepath.name)
                zipfile_.writestr("manifest.json", json.dumps(manifest))
                zipfile_.writestr("bibliography.json", "{}")
            receipt = {"query": collisiondb.QUERY, "client_version": collisiondb.CLIENT_VERSION,
                       "base_url": collisiondb.BASE_URL, "archive_name": archive.name,
                       "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                       "fetched_at": "2026-10-14T00:00:00Z", "cached": False}
            (raw / "client-receipt.json").write_text(json.dumps(receipt))
            with patch("requests.get", side_effect=AssertionError("Unexpected network")), patch("requests.post", side_effect=AssertionError("Unexpected network")):
                collisiondb.fetch_worker(output, reuse=True)
            result = json.loads((raw / "worker-result.json").read_text())
            self.assertEqual(len(result["records"]), 2)
            self.assertTrue(result["receipt"]["cached"])
            self.assertEqual(result["receipt"]["fetched_at"], receipt["fetched_at"])
            self.assertNotIn("uncertainty", result["records"][1]["cross_section"]["points"][0])
            with patch("pycollisiondb.pycollisiondb.PyCollision.get_datasets", return_value=SimpleNamespace(datasets={111118: second})):
                with self.assertRaisesRegex(ValueError, "identity differs"):
                    collisiondb.fetch_worker(output, reuse=True)
            archive.write_bytes(archive.read_bytes() + b"tampered")
            with self.assertRaisesRegex(ValueError, "checksum"):
                collisiondb.fetch_worker(output, reuse=True)

    def test_archive_members_and_saved_scenario_are_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "unexpected.zip"
            with zipfile.ZipFile(archive, "w") as zipfile_:
                zipfile_.writestr("../outside.txt", "bad")
            with self.assertRaisesRegex(ValueError, "Unexpected"):
                collisiondb.archive_contents(archive)
            (root / "run.json").write_text(json.dumps({"output_version": collisiondb.OUTPUT_VERSION}))
            self.assertIsNone(collisiondb.saved_document(root))
            document = {"study": {}, "run": {"scenario_id": "collisiondb-oxygen", "output_version": collisiondb.OUTPUT_VERSION}}
            kamchatka.save(document, root)
            self.assertEqual(collisiondb.saved_document(root), document)


if __name__ == "__main__":
    unittest.main()
