import unittest

from app.cloud_api import (
    parse_analyze_result,
    parse_benchmark_result,
    parse_mpu_benchmark_result,
    build_memory_visibility_report,
    recommend_memory_pooling,
    to_float,
    _safe_round,
)


class TestNumericParsing(unittest.TestCase):
    def test_to_float_accepts_int_float_str(self):
        self.assertEqual(to_float(10), 10.0)
        self.assertEqual(to_float(10.5), 10.5)
        self.assertEqual(to_float("12.34"), 12.34)
        self.assertEqual(to_float("  7  "), 7.0)

    def test_to_float_rejects_invalid_values(self):
        self.assertIsNone(to_float(None))
        self.assertIsNone(to_float(""))
        self.assertIsNone(to_float("abc"))
        self.assertIsNone(to_float({"x": 1}))

    def test_safe_round_never_raises_on_strings(self):
        self.assertEqual(_safe_round("12.3456", 2), 12.35)
        self.assertIsNone(_safe_round("not-a-number", 2))


class TestCloudApiParsers(unittest.TestCase):
    def test_parse_benchmark_result_handles_numeric_strings(self):
        payload = {
            "benchmark": {
                "graph": {
                    "exec_time": {
                        "duration_ms": "12.3456",
                        "cycles": "123456",
                    }
                },
                "report": {
                    "rom_n_macc": "98765",
                    "params": "4321",
                    "val_metrics": [
                        {
                            "acc": "0.91234",
                            "rmse": "0.100123",
                            "mae": "0.080987",
                            "l2r": "0.050456",
                        }
                    ],
                },
            },
            "memoryMapping": {
                "memoryFootprint": {
                    "activations": "2048",
                    "weights": "4096",
                    "io": ["512", 256, "not-a-number"],
                    "kernel_ram": "128",
                    "extra_ram": "64",
                    "kernel_flash": "1024",
                    "toolchain_flash": "2048",
                }
            },
        }

        parsed = parse_benchmark_result(payload)

        self.assertEqual(parsed["inference_time_ms"], 12.346)
        self.assertEqual(parsed["cycles"], 123456)
        self.assertEqual(parsed["macc"], 98765)
        self.assertEqual(parsed["params"], 4321)
        self.assertEqual(parsed["accuracy"], 91.23)
        self.assertEqual(parsed["rmse"], 0.100123)
        self.assertEqual(parsed["mae"], 0.080987)
        self.assertEqual(parsed["l2r"], 0.050456)
        self.assertEqual(parsed["ram_ko"], 2.94)
        self.assertEqual(parsed["rom_ko"], 7.0)

    def test_parse_benchmark_result_tolerates_non_numeric_strings(self):
        payload = {
            "benchmark": {
                "graph": {"exec_time": {"duration_ms": "oops", "cycles": "not-int"}},
                "report": {"rom_n_macc": "nan", "params": "bad", "val_metrics": [{"acc": "bad"}]},
            },
            "memoryMapping": {
                "memoryFootprint": {
                    "activations": "x",
                    "weights": "y",
                    "io": ["z"],
                }
            },
        }
        parsed = parse_benchmark_result(payload)
        self.assertEqual(parsed["inference_time_ms"], "N/A")
        self.assertEqual(parsed["cycles"], "N/A")
        self.assertEqual(parsed["macc"], "N/A")
        self.assertEqual(parsed["params"], "N/A")

    def test_parse_analyze_result_handles_numeric_strings(self):
        payload = {
            "graph": {
                "memory_footprint": {
                    "activations": "1024",
                    "weights": "2048",
                    "io": ["256", "128"],
                    "kernel_ram": "64",
                    "toolchain_ram": "32",
                    "kernel_flash": "512",
                    "toolchain_flash": "256",
                },
                "macc": "10000",
                "params": "2500",
                "inputs": [{"shape": [1, 32, 32, 3], "dtype": "float32"}],
                "outputs": [{"shape": [1, 10], "dtype": "float32"}],
            },
            "report": {
                "val_metrics": [
                    {
                        "acc": "0.8",
                        "rmse": "0.3",
                        "mae": "0.2",
                        "l2r": "0.1",
                    }
                ]
            },
        }

        parsed = parse_analyze_result(payload)

        self.assertEqual(parsed["ram_ko"], 1.47)
        self.assertEqual(parsed["rom_ko"], 2.75)
        self.assertEqual(parsed["weights_ko"], 2.0)
        self.assertEqual(parsed["activations_ko"], 1.0)
        self.assertEqual(parsed["io_ko"], 0.38)
        self.assertEqual(parsed["macc"], 10000)
        self.assertEqual(parsed["params"], 2500)
        self.assertEqual(parsed["input_shape"], "1x32x32x3")
        self.assertEqual(parsed["output_shape"], "1x10")
        self.assertEqual(parsed["input_dtype"], "float32")
        self.assertEqual(parsed["output_dtype"], "float32")
        self.assertEqual(parsed["accuracy"], 80.0)
        self.assertEqual(parsed["rmse"], 0.3)
        self.assertEqual(parsed["mae"], 0.2)
        self.assertEqual(parsed["l2r"], 0.1)

    def test_memory_visibility_and_recommendation_rules(self):
        analysis = {
            "weights_ko": 700,
            "activations_ko": 96,
        }
        visibility = build_memory_visibility_report(analysis)
        self.assertEqual(len(visibility["rows"]), 3)
        self.assertFalse(visibility["rows"][0]["flash_ok"])
        self.assertTrue(visibility["rows"][0]["ram_ok"])

        recommendation = recommend_memory_pooling(analysis)
        self.assertTrue(recommendation["split_weights"])
        self.assertFalse(recommendation["allocate_activations"])

        both_too_small = recommend_memory_pooling({"weights_ko": 900, "activations_ko": 190})
        self.assertTrue(both_too_small["split_weights"])
        self.assertTrue(both_too_small["allocate_activations"])

    def test_parse_mpu_benchmark_result_handles_numeric_strings(self):
        payload = {
            "benchmark": {
                "exec_time": {"duration_ms": "4.56789"},
                "ram_peak": "3072",
                "model_size": "10240",
            }
        }

        parsed = parse_mpu_benchmark_result(payload)

        self.assertEqual(parsed["inference_time_ms"], 4.568)
        self.assertEqual(parsed["ram_ko"], 3.0)
        self.assertEqual(parsed["rom_ko"], 10.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

