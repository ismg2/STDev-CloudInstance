import os
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

import app.batch_benchmark as batch_benchmark
import app.results_manager as results_manager


class _FakeCloudClient:
    def __init__(self, version=None):
        self.version = version or "4.0.0"

    @staticmethod
    def available_versions():
        return ["4.0.0"]

    def run_benchmark(self, *args, **kwargs):
        return {
            "inference_time_ms": 7.1,
            "ram_ko": 12.5,
            "rom_ko": 40.0,
            "macc": 123,
            "params": 77,
            "accuracy": 91.1,
            "rmse": "N/A",
            "mae": "N/A",
            "l2r": "N/A",
            "_run_meta": {
                "core_version": self.version,
                "core_command": "POST /api/benchmark/benchmark/stm32h747i-disco payload={\"version\":\"4.0.0\"}",
                "run_id": "run-e2e",
                "benchmark_id": "bench-e2e",
                "target": "stm32",
                "st_neural_art": "",
                "memory_pool": "",
                "split_weights": False,
                "allocate_activations": False,
                "allocate_states": False,
                "input_memory_alignment": None,
                "output_memory_alignment": None,
                "no_inputs_allocation": False,
                "no_outputs_allocation": False,
            },
        }


class TestBatchEndToEndSimulated(unittest.TestCase):
    @patch("app.cloud_api.CloudClient", _FakeCloudClient)
    def test_batch_writes_core_command_to_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_csv = results_manager.RESULTS_CSV
            old_dir = results_manager.RESULTS_DIR
            old_db = results_manager.RESULTS_DB
            try:
                results_manager.RESULTS_DIR = tmp
                results_manager.RESULTS_CSV = os.path.join(tmp, "resultats.csv")
                results_manager.RESULTS_DB = os.path.join(tmp, "resultats.db")

                cfg = {
                    "models": [{
                        "name": "m.tflite",
                        "relative_dir": "demo",
                        "extension": ".tflite",
                        "path": "demo/m.tflite",
                    }],
                    "boards": ["STM32H747I-DISCO"],
                    "versions": ["4.0.0"],
                    "optimizations": ["balanced"],
                    "compressions": ["lossless"],
                    "simple_preferences": {
                        "compute_mode": "auto",
                        "split_weights": False,
                        "allocate_activations": False,
                    },
                    "board_modes": {
                        "STM32H747I-DISCO": "auto",
                    },
                }

                with patch("app.batch_benchmark.interactive_batch_benchmark", return_value=cfg):
                    batch_benchmark.run_batch_benchmark(core_version="4.0.0")

                df = results_manager.load_results()
                self.assertEqual(len(df), 1)
                self.assertEqual(df.iloc[0]["core_version"], "4.0.0")
                self.assertIn("POST /api/benchmark/benchmark/stm32h747i-disco", df.iloc[0]["core_command"])
                self.assertEqual(df.iloc[0]["benchmark_id"], "bench-e2e")
            finally:
                results_manager.RESULTS_CSV = old_csv
                results_manager.RESULTS_DIR = old_dir
                results_manager.RESULTS_DB = old_db


if __name__ == "__main__":
    unittest.main(verbosity=2)

