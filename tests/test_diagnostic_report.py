import json
import os
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

import app.diagnostic_report as diagnostic_report


class TestDiagnosticReport(unittest.TestCase):
    def test_export_diagnostic_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = os.path.join(tmp, "resultats.csv")
            logs_path = os.path.join(tmp, "benchmarks.jsonl")
            out_dir = os.path.join(tmp, "diag")

            df = pd.DataFrame([
                {
                    "modele": "m.tflite",
                    "dossier": "demo",
                    "type_framework": "tflite",
                    "board": "STM32H747I-DISCO",
                    "optimization": "balanced",
                    "compression": "lossless",
                    "inference_time_ms": 1.0,
                    "ram_ko": 2.0,
                    "rom_ko": 3.0,
                    "macc": 10,
                    "params": 20,
                    "accuracy": 90,
                    "rmse": "N/A",
                    "mae": "N/A",
                    "l2r": "N/A",
                    "core_version": "4.0.0",
                    "target": "stm32",
                    "st_neural_art": "",
                    "memory_pool": "",
                    "split_weights": "False",
                    "allocate_activations": "False",
                    "allocate_states": "False",
                    "input_memory_alignment": "",
                    "output_memory_alignment": "",
                    "no_inputs_allocation": "False",
                    "no_outputs_allocation": "False",
                    "core_command": "POST /api/benchmark ...",
                    "run_id": "run-123",
                    "benchmark_id": "bench-123",
                    "date": "2026-01-01 00:00:00",
                    "status": "OK",
                }
            ])
            df.to_csv(csv_path, sep=";", index=False, encoding="utf-8")

            with open(logs_path, "w", encoding="utf-8") as f:
                f.write(json.dumps({"event": "benchmark_triggered", "run_id": "run-123"}) + "\n")
                f.write(json.dumps({"event": "benchmark_done", "run_id": "run-123"}) + "\n")
                f.write(json.dumps({"event": "other", "run_id": "run-456"}) + "\n")

            with patch("app.diagnostic_report.RESULTS_CSV", csv_path), patch("app.diagnostic_report.RUN_LOGS_JSONL", logs_path):
                report = diagnostic_report.export_diagnostic_report("run-123", out_dir)

            self.assertEqual(report["csv_rows_count"], 1)
            self.assertEqual(report["events_count"], 2)
            self.assertTrue(os.path.exists(report["rows_csv"]))
            self.assertTrue(os.path.exists(report["events_jsonl"]))
            self.assertTrue(os.path.exists(report["summary_json"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)

