import unittest
from unittest.mock import patch

import app.cloud_api as cloud_api


class _FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body
        self.text = str(body)

    def json(self):
        return self._body


class TestCloudApiExtended(unittest.TestCase):
    @patch("app.cloud_api.requests.get")
    def test_get_available_versions(self, mock_get):
        mock_get.return_value = _FakeResponse(200, [
            {"version": "3.2.0"},
            {"version": "4.0.0", "isLatest": True},
        ])

        versions = cloud_api.get_available_versions()
        self.assertEqual(versions, ["3.2.0", "4.0.0"])

    def test_extract_error_message(self):
        msg = cloud_api._extract_error_message({"errors": {"detail": "x"}})
        self.assertIn("detail", msg)

    def test_actionable_error_hint_memory_footprint(self):
        hint = cloud_api.actionable_error_hint("Error while calculating memory footprint")
        self.assertIn("memory_pool", hint)

    def test_actionable_error_hint_invalid_model(self):
        hint = cloud_api.actionable_error_hint("InvalidModelError: unsupported ops")
        self.assertIn("format", hint)

    @patch("app.cloud_api._append_jsonl")
    @patch("app.cloud_api._send_post")
    def test_trigger_benchmark_with_advanced_options(self, mock_post, _mock_log):
        mock_post.return_value = _FakeResponse(200, {"benchmarkId": "bench-1"})

        svc = cloud_api.BenchmarkService("token", "4.0.0")
        benchmark_id = svc.trigger_benchmark(
            "model.tflite",
            "STM32H747I-DISCO",
            optimization="time",
            compression="lossless",
            extra_options={
                "target": "stm32",
                "split_weights": True,
                "input_memory_alignment": 16,
            },
            run_id="run-1",
        )

        self.assertEqual(benchmark_id, "bench-1")
        self.assertEqual(svc.last_trigger["benchmark_id"], "bench-1")
        self.assertEqual(svc.last_trigger["payload"]["target"], "stm32")
        self.assertTrue(svc.last_trigger["payload"]["split_weights"])
        self.assertEqual(svc.last_trigger["payload"]["input_memory_alignment"], 16)


class _FakeFileService:
    def ensure_uploaded(self, _):
        return "model.tflite"


class _FakeBenchService:
    def __init__(self):
        self.last_trigger = {}

    def trigger_benchmark(self, model_name, board_name, **kwargs):
        self.last_trigger = {
            "route": "/api/benchmark/benchmark/stm32h747i-disco",
            "payload": {
                "model": model_name,
                "board": board_name,
                "optimization": kwargs.get("optimization"),
                "compression": kwargs.get("compression"),
                "target": kwargs.get("extra_options", {}).get("target"),
            },
            "benchmark_id": "bench-42",
        }
        return "bench-42"

    def wait_for_run(self, benchmark_id, run_id=""):
        return {
            "benchmark": {
                "graph": {
                    "exec_time": {"duration_ms": 12.3, "cycles": 1000}
                },
                "report": {
                    "rom_n_macc": 1200,
                    "params": 300,
                    "val_metrics": [{"acc": 0.8}],
                },
            },
            "memoryMapping": {
                "memoryFootprint": {
                    "activations": 1024,
                    "weights": 2048,
                    "io": [256],
                    "kernel_ram": 128,
                    "extra_ram": 64,
                    "kernel_flash": 512,
                    "toolchain_flash": 256,
                }
            },
        }


class TestCloudClientRunMeta(unittest.TestCase):
    @patch("app.cloud_api._append_jsonl")
    def test_run_benchmark_includes_core_command_meta(self, _mock_log):
        client = cloud_api.CloudClient.__new__(cloud_api.CloudClient)
        client.__dict__["version"] = "4.0.0"
        client.__dict__["file_svc"] = _FakeFileService()
        client.__dict__["bench_svc"] = _FakeBenchService()
        client.__dict__["_model_type"] = lambda model_path: "tflite"

        metrics = client.run_benchmark(
            "fake.tflite",
            "STM32H747I-DISCO",
            optimization="time",
            compression="lossless",
            target="stm32",
        )

        self.assertIn("_run_meta", metrics)
        self.assertEqual(metrics["_run_meta"]["core_version"], "4.0.0")
        self.assertIn("POST /api/benchmark/benchmark/stm32h747i-disco", metrics["_run_meta"]["core_command"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

