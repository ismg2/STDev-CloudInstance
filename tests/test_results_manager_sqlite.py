import os
import tempfile
import unittest

import pandas as pd

import results_manager


class TestResultsManagerSQLite(unittest.TestCase):
    def test_migrate_csv_to_sqlite_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_csv = results_manager.RESULTS_CSV
            old_dir = results_manager.RESULTS_DIR
            old_db = results_manager.RESULTS_DB
            try:
                results_manager.RESULTS_DIR = tmp
                results_manager.RESULTS_CSV = os.path.join(tmp, "resultats.csv")
                results_manager.RESULTS_DB = os.path.join(tmp, "resultats.db")

                df = pd.DataFrame([
                    {
                        "modele": "m.tflite",
                        "dossier": "demo",
                        "type_framework": "tflite",
                        "board": "STM32H747I-DISCO",
                        "optimization": "balanced",
                        "compression": "lossless",
                        "inference_time_ms": "1.0",
                        "ram_ko": "2.0",
                        "rom_ko": "3.0",
                        "macc": "10",
                        "params": "20",
                        "accuracy": "90",
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
                        "core_command": "POST /api/benchmark payload={}",
                        "run_id": "run-a",
                        "benchmark_id": "bench-a",
                        "date": "2026-03-20 10:00:00",
                        "status": "OK",
                    }
                ])
                df.to_csv(results_manager.RESULTS_CSV, sep=";", index=False, encoding="utf-8")

                first = results_manager.migrate_csv_to_sqlite()
                second = results_manager.migrate_csv_to_sqlite()
                self.assertGreaterEqual(first, 1)
                self.assertEqual(second, 0)

                loaded = results_manager.load_results()
                self.assertEqual(len(loaded), 1)
                self.assertEqual(loaded.iloc[0]["benchmark_id"], "bench-a")
            finally:
                results_manager.RESULTS_CSV = old_csv
                results_manager.RESULTS_DIR = old_dir
                results_manager.RESULTS_DB = old_db


if __name__ == "__main__":
    unittest.main(verbosity=2)
