import os
import tempfile
import unittest

import pandas as pd

import app.results_manager as results_manager


class TestResultsManagerExtended(unittest.TestCase):
    def test_append_result_with_core_command_and_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_csv = results_manager.RESULTS_CSV
            old_dir = results_manager.RESULTS_DIR
            old_db = results_manager.RESULTS_DB
            try:
                results_manager.RESULTS_DIR = tmp
                results_manager.RESULTS_CSV = os.path.join(tmp, "resultats.csv")
                results_manager.RESULTS_DB = os.path.join(tmp, "resultats.db")

                results_manager.ensure_storage_ready()
                results_manager.append_result(
                    model_name="m.tflite",
                    model_dir="demo",
                    type_framework="tflite",
                    board="STM32H747I-DISCO",
                    optimization="balanced",
                    compression="lossless",
                    inference_time_ms=1.2,
                    ram_ko=2.3,
                    rom_ko=4.5,
                    macc=100,
                    params=50,
                    core_version="4.0.0",
                    core_command="POST /api/benchmark payload={...}",
                    run_id="run-1",
                    benchmark_id="bench-1",
                )

                df = results_manager.load_results()
                self.assertEqual(df.iloc[0]["core_version"], "4.0.0")
                self.assertEqual(df.iloc[0]["run_id"], "run-1")
                self.assertIn("POST /api/benchmark", df.iloc[0]["core_command"])

                ok = results_manager.tag_benchmark("bench-1", tag_name="reference")
                self.assertTrue(ok)

                active = results_manager.get_active_reference(model_name="m.tflite", board="STM32H747I-DISCO")
                self.assertEqual(active.get("benchmark_id"), "bench-1")

                history = results_manager.get_version_history("m.tflite", "STM32H747I-DISCO")
                self.assertEqual(len(history), 1)
            finally:
                results_manager.RESULTS_CSV = old_csv
                results_manager.RESULTS_DIR = old_dir
                results_manager.RESULTS_DB = old_db


if __name__ == "__main__":
    unittest.main(verbosity=2)

