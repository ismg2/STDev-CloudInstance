"""STEdgeAI Developer Cloud REST client.

Implements the exact API calls matching ST's official SDK.
CLI parameter values sourced from ST Edge AI Core 4.0 documentation.

Sources:
  - STMicroelectronics/stm32ai-modelzoo-services (file/benchmark/stm32ai services)
  - Documentation/ST Edge AI Core 4.0/command_line_interface.html
  - Documentation/ST Edge AI Core 4.0/evaluation_metrics.html
"""

import functools
import json
import os
import time

import requests

from config import (
    BASE_URL,
    FILE_SERVICE_URL, BENCHMARK_URL, VERSIONS_URL,
    MODELS_ROUTE, BENCHMARK_BOARDS_ROUTE,
    STEDGEAI_DEFAULT_VERSION,
    SSL_VERIFY,
    OPTIMIZATION_DEFAULT, COMPRESSION_DEFAULT,
    EXTENSION_TO_TYPE,
)
from auth import get_bearer_token


class CloudAPIError(Exception):
    """Raised when an API call returns an unexpected response."""


# ---------------------------------------------------------------------------
# HTTP helpers  (matching helpers.py from ST SDK)
# ---------------------------------------------------------------------------

def _get_proxy():
    config = {}
    for key in ("http_proxy", "HTTP_PROXY", "https_proxy", "HTTPS_PROXY"):
        val = os.environ.get(key)
        if val:
            proto = "http" if "http_proxy" in key.lower() else "https"
            config[proto] = val
    return config or None


def _send_get(url: str, token: str, params: dict = None) -> requests.Response:
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    resp = requests.get(
        url, headers=headers, params=params,
        verify=SSL_VERIFY, proxies=_get_proxy(), timeout=60,
    )
    if resp.status_code == 404:
        raise CloudAPIError(f"Route introuvable: {url}")
    return resp


def _send_post(url: str, token: str, data=None, files=None, json_body=None) -> requests.Response:
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    resp = requests.post(
        url, headers=headers,
        data=data, files=files, json=json_body,
        verify=SSL_VERIFY, proxies=_get_proxy(), timeout=120,
    )
    return resp


# ---------------------------------------------------------------------------
# Version resolution
# ---------------------------------------------------------------------------

def get_latest_version(token: str = None) -> str:
    """Fetch supported versions list and return the latest.

    Falls back to STEDGEAI_DEFAULT_VERSION ("4.0.0") if unreachable.
    """
    try:
        resp = requests.get(VERSIONS_URL, verify=SSL_VERIFY, proxies=_get_proxy(), timeout=15)
        if resp.status_code == 200:
            versions = resp.json()
            for v in versions:
                if v.get("isLatest", False):
                    return v["version"]
            if versions:
                return versions[-1]["version"]
    except Exception:
        pass
    return STEDGEAI_DEFAULT_VERSION


# ---------------------------------------------------------------------------
# FileService  →  {BASE_URL}api/file/files/models
# ---------------------------------------------------------------------------

class FileService:

    def __init__(self, token: str):
        self.token = token

    def list_models(self) -> list:
        """GET /files/models → list of {name, ...}"""
        resp = _send_get(MODELS_ROUTE, self.token)
        if resp.status_code == 200:
            data = resp.json()
            return data if isinstance(data, list) else []
        return []

    def model_names(self) -> list:
        return [m["name"] for m in self.list_models()]

    def upload_model(self, model_path: str) -> bool:
        """POST /files/models (multipart) → {upload: true/false}"""
        if not os.path.exists(model_path):
            raise CloudAPIError(f"Fichier introuvable: {model_path}")
        with open(model_path, "rb") as f:
            resp = _send_post(MODELS_ROUTE, self.token, files={"file": f})
        if resp.status_code == 200:
            return resp.json().get("upload", False) is True
        raise CloudAPIError(f"Upload echoue (HTTP {resp.status_code}): {resp.text[:300]}")

    def ensure_uploaded(self, model_path: str) -> str:
        """Upload if not already on cloud. Returns the filename."""
        filename = os.path.basename(model_path)
        if filename not in self.model_names():
            size_kb = os.path.getsize(model_path) / 1024
            print(f"  Upload de '{filename}' ({size_kb:.1f} Ko)...", end=" ", flush=True)
            ok = self.upload_model(model_path)
            if not ok:
                raise CloudAPIError(f"Upload de '{filename}' echoue.")
            print("OK")
        else:
            print(f"  '{filename}' deja present sur le cloud.")
        return filename

    def delete_model(self, model_name: str) -> bool:
        headers = {"Accept": "application/json", "Authorization": f"Bearer {self.token}"}
        resp = requests.delete(
            f"{MODELS_ROUTE}/{model_name}",
            headers=headers, verify=SSL_VERIFY, proxies=_get_proxy(), timeout=30,
        )
        return resp.status_code == 200 and resp.json().get("deleted", False)


# ---------------------------------------------------------------------------
# Stm32AiService  →  {BASE_URL}api/{version}/stm32ai/
# ---------------------------------------------------------------------------

def _stm32ai_base(version: str) -> str:
    if version:
        return f"{BASE_URL}api/{version}/stm32ai/"
    return f"{BASE_URL}api/stm32ai/"


class Stm32AiService:

    def __init__(self, token: str, version: str):
        self.token    = token
        self.version  = version
        base = _stm32ai_base(version)
        self.analyze_url  = base + "analyze"
        self.validate_url = base + "validate"
        self.run_base     = base + "run/"

    def trigger_analyze(
        self,
        model_name: str,
        model_type: str = None,
        optimization: str = OPTIMIZATION_DEFAULT,
        compression: str = COMPRESSION_DEFAULT,
        verbosity: int = 1,
    ) -> str:
        """POST multipart form with args JSON → runtimeId.

        Args documented in ST Edge AI Core 4.0/command_line_interface.html:
          model        : filename as uploaded on cloud
          type         : keras | tflite | onnx  (-t/--type)
          optimization : balanced | ram | time | size  (-O)
          compression  : none | lossless | low | medium | high  (-c)
          verbosity    : 0-3  (-v)
        """
        args = {
            "model":        model_name,
            "optimization": optimization,
            "compression":  compression,
            "verbosity":    verbosity,
        }
        if model_type:
            args["type"] = model_type

        resp = _send_post(
            self.analyze_url, self.token,
            data={"args": json.dumps(args)},
        )
        if resp.status_code == 200:
            body = resp.json()
            if body and "runtimeId" in body:
                return body["runtimeId"]
            if body and body.get("status") == "ko":
                raise CloudAPIError(f"Erreur serveur: {body.get('error', 'inconnue')}")
        raise CloudAPIError(
            f"Analyze echoue HTTP {resp.status_code}: {resp.text[:300]}"
        )

    def _get_run(self, runtime_id: str) -> dict:
        resp = _send_get(f"{self.run_base}{runtime_id}", self.token)
        return resp.json() if resp.status_code == 200 else None

    def wait_for_run(self, runtime_id: str, timeout: int = 300, poll: float = 2.0) -> dict:
        """Poll until run completes. Returns the result dict."""
        start = time.time()
        while (time.time() - start) < timeout:
            result = self._get_run(runtime_id)
            if result:
                state    = result.get("state", "").lower()
                progress = result.get("progress", 0)
                print(f"    STM32AI: {state} ({progress}%)   ", end="\r", flush=True)
                if result.get("result") is not None:
                    print()
                    return result["result"]
                if state == "error":
                    print()
                    raise CloudAPIError(f"Analyse en erreur: {result}")
            time.sleep(poll)
        raise CloudAPIError(f"Timeout apres {timeout}s.")


# ---------------------------------------------------------------------------
# BenchmarkService  →  {BASE_URL}api/benchmark/
# ---------------------------------------------------------------------------

_MPU_KEYWORDS = ("MP2", "MP1", "MP257", "MP131", "LINUX", "MPU")


def _is_mpu(board_name: str) -> bool:
    return any(kw in board_name.upper() for kw in _MPU_KEYWORDS)


class BenchmarkService:

    def __init__(self, token: str, version: str):
        self.token   = token
        self.version = version

    def list_boards(self) -> dict:
        """GET /benchmark/boards → dict of board_name → board_info"""
        resp = _send_get(BENCHMARK_BOARDS_ROUTE, self.token)
        return resp.json() if resp.status_code == 200 else {}

    def trigger_benchmark(
        self,
        model_name: str,
        board_name: str,
        optimization: str = OPTIMIZATION_DEFAULT,
        compression: str = COMPRESSION_DEFAULT,
        model_type: str = None,
        is_mpu: bool = False,
    ) -> str:
        """POST /benchmark/benchmark/{board} → benchmarkId

        Payload mirrors ST SDK BenchmarkService.trigger_benchmark():
          model      : filename
          version    : STEdgeAI version
          optimization, compression: from CLI params doc
        """
        payload = {
            "model":        model_name,
            "version":      self.version,
            "optimization": optimization,
            "compression":  compression,
        }
        if model_type:
            payload["type"] = model_type

        route = f"{BENCHMARK_URL}/benchmark"
        if is_mpu:
            route += "/mpu"
        route += f"/{board_name.lower()}"

        resp = _send_post(route, self.token, json_body=payload)
        if resp.status_code == 200:
            body = resp.json()
            if "benchmarkId" in body:
                return body["benchmarkId"]
            raise CloudAPIError(f"benchmarkId absent: {body}")
        try:
            err = resp.json().get("errors") or resp.text
        except Exception:
            err = resp.text
        raise CloudAPIError(f"Benchmark echoue HTTP {resp.status_code}: {err[:300]}")

    def _get_run(self, benchmark_id: str) -> dict:
        resp = _send_get(f"{BENCHMARK_URL}/benchmark/{benchmark_id}", self.token)
        return resp.json() if resp.status_code == 200 else None

    def wait_for_run(self, benchmark_id: str, timeout: int = 900, poll: float = 5.0) -> dict:
        """Poll until benchmark is done. Returns full result dict."""
        start    = time.time()
        last_st  = ""
        while (time.time() - start) < timeout:
            result = self._get_run(benchmark_id)
            if result:
                state = result.get("state", "").lower()
                if state != last_st:
                    last_st = state
                elapsed = int(time.time() - start)
                print(f"    Benchmark: {state} ({elapsed}s)   ", end="\r", flush=True)
                if state == "done":
                    print()
                    return result
                if state == "error":
                    print()
                    raise CloudAPIError(f"Benchmark echoue: {result.get('message', 'inconnue')}")
            time.sleep(poll)
        raise CloudAPIError(f"Timeout benchmark apres {timeout}s.")


# ---------------------------------------------------------------------------
# Result parsers  (mirroring cloud.py + evaluation_metrics.html field names)
# ---------------------------------------------------------------------------

def _sum(values):
    if isinstance(values, list):
        return functools.reduce(lambda a, b: a + b, values, 0)
    return values or 0


def _extract_val_metrics(val_metrics: list) -> dict:
    """Extract accuracy and error metrics from val_metrics array.

    Field names from evaluation_metrics.html:
      acc       - accuracy (classification)
      rmse      - Root Mean Square Error
      mae       - Mean Absolute Error
      l2r       - L2 relative error
    """
    if not val_metrics:
        return {}
    # Take the first (or best) metric set
    m = val_metrics[0]
    return {
        "accuracy": round(m.get("acc", 0) * 100, 2) if m.get("acc") is not None else "N/A",
        "rmse":     m.get("rmse", "N/A"),
        "mae":      m.get("mae", "N/A"),
        "l2r":      m.get("l2r", "N/A"),
    }


def parse_analyze_result(data: dict) -> dict:
    """Extract memory/MACC/params from analyze result.

    Fields from command_line_interface.html:
      weights (ro)    → ROM/Flash in bytes
      activations (rw)→ RAM in bytes
      macc            → Multiply-Accumulate ops
      params #        → number of parameters
    """
    report = data.get("report") or {}
    graph  = data.get("graph")  or {}
    info   = data.get("info")

    if info:
        memory_footprint = info.get("memory_footprint", {})
        cinfo_graph      = info["graphs"][0] if info.get("graphs") else {}
        nodes            = cinfo_graph.get("nodes", [])
        macc             = sum(n.get("macc", 0) for n in nodes)
        params           = sum(n.get("params", 0) for n in nodes)
        val_metrics      = info.get("validation", {}).get("val_metrics", [])
    else:
        memory_footprint = graph.get("memory_footprint", {})
        macc             = graph.get("macc", 0)
        params           = graph.get("params", 0)
        val_metrics      = report.get("val_metrics", [])

    activations = memory_footprint.get("activations", 0)
    weights     = memory_footprint.get("weights", 0)
    io_list     = memory_footprint.get("io", [])

    rom_bytes = (
        weights
        + memory_footprint.get("kernel_flash", 0)
        + memory_footprint.get("toolchain_flash", 0)
    )
    ram_bytes = (
        activations
        + _sum(io_list)
        + memory_footprint.get("kernel_ram", 0)
        + memory_footprint.get("toolchain_ram", memory_footprint.get("extra_ram", 0))
    )

    result = {
        "ram_ko":  round(ram_bytes / 1024, 2) if ram_bytes else "N/A",
        "rom_ko":  round(rom_bytes / 1024, 2) if rom_bytes else "N/A",
        "macc":    macc or "N/A",
        "params":  params or "N/A",
    }
    result.update(_extract_val_metrics(val_metrics))
    return result


def parse_benchmark_result(result: dict) -> dict:
    """Extract inference time, memory, and accuracy from benchmark result.

    State progression (from benchmark_service.py + doc):
      waiting_for_build → in_queue → generating_sources → copying_sources
      → loading_sources → building → validation → done

    Result fields from cloud.py + evaluation_metrics.html:
      exec_time.duration_ms  → inference time in ms
      exec_time.cycles        → CPU cycles
      memory_footprint.*      → memory breakdown
      val_metrics[].acc       → accuracy
    """
    benchmark      = result.get("benchmark", {})
    info           = benchmark.get("info")
    graph          = benchmark.get("graph", {})
    memory_mapping = result.get("memoryMapping") or {}

    if info:
        cinfo_graph      = info["graphs"][0] if info.get("graphs") else {}
        exec_time        = cinfo_graph.get("exec_time", {}) if cinfo_graph else graph.get("exec_time", {})
        memory_footprint = memory_mapping.get("memoryFootprint", info.get("memory_footprint", {}))
        nodes            = cinfo_graph.get("nodes", [])
        macc             = sum(n.get("macc", 0) for n in nodes)
        params           = sum(n.get("params", 0) for n in nodes)
        val_metrics      = info.get("validation", {}).get("val_metrics", [])
    else:
        report           = benchmark.get("report", {})
        exec_time        = graph.get("exec_time", {})
        memory_footprint = memory_mapping.get("memoryFootprint", graph.get("memory_footprint", {}))
        macc             = report.get("rom_n_macc", 0)
        params           = report.get("params", 0)
        val_metrics      = report.get("val_metrics", [])

    duration_ms = exec_time.get("duration_ms", -1)
    activations = memory_footprint.get("activations", 0)
    weights     = memory_footprint.get("weights", 0)
    io_list     = memory_footprint.get("io", [])

    rom_bytes = (
        weights
        + memory_footprint.get("kernel_flash", 0)
        + memory_footprint.get("toolchain_flash", 0)
    )
    ram_bytes = (
        activations
        + _sum(io_list)
        + memory_footprint.get("kernel_ram", 0)
        + memory_footprint.get("toolchain_ram", memory_footprint.get("extra_ram", 0))
    )

    parsed = {
        "inference_time_ms": round(duration_ms, 3) if duration_ms >= 0 else "N/A",
        "ram_ko":    round(ram_bytes / 1024, 2) if ram_bytes else "N/A",
        "rom_ko":    round(rom_bytes / 1024, 2) if rom_bytes else "N/A",
        "macc":      macc or "N/A",
        "params":    params or "N/A",
        "cycles":    exec_time.get("cycles", "N/A"),
    }
    parsed.update(_extract_val_metrics(val_metrics))
    return parsed


def parse_mpu_benchmark_result(result: dict) -> dict:
    """Extract results from MPU benchmark format."""
    bench     = result.get("benchmark", {})
    exec_time = bench.get("exec_time", {})
    return {
        "inference_time_ms": round(exec_time.get("duration_ms", -1), 3),
        "ram_ko":   round(bench.get("ram_peak", 0) / 1024, 2) if bench.get("ram_peak") else "N/A",
        "rom_ko":   round(bench.get("model_size", 0) / 1024, 2) if bench.get("model_size") else "N/A",
        "macc":     "N/A",
        "params":   "N/A",
        "cycles":   "N/A",
        "accuracy": "N/A",
        "rmse":     "N/A",
        "mae":      "N/A",
        "l2r":      "N/A",
    }


# ---------------------------------------------------------------------------
# High-level CloudClient
# ---------------------------------------------------------------------------

class CloudClient:
    """Orchestrates upload → analyze → benchmark for one model."""

    def __init__(self):
        self.token    = get_bearer_token()
        self.version  = get_latest_version(self.token)
        print(f"  [Cloud] Connecte | STEdgeAI Core version: {self.version}")
        self.file_svc  = FileService(self.token)
        self.ai_svc    = Stm32AiService(self.token, self.version)
        self.bench_svc = BenchmarkService(self.token, self.version)

    def get_boards(self) -> list:
        """Return sorted list of available board names."""
        boards_dict = self.bench_svc.list_boards()
        if isinstance(boards_dict, dict):
            return sorted(boards_dict.keys())
        return []

    def _model_type(self, model_path: str) -> str:
        """Auto-detect framework type from file extension."""
        ext = os.path.splitext(model_path)[1].lower()
        return EXTENSION_TO_TYPE.get(ext)

    def run_analyze(
        self,
        model_path: str,
        optimization: str = OPTIMIZATION_DEFAULT,
        compression: str = COMPRESSION_DEFAULT,
    ) -> dict:
        """Upload model if needed, run analysis, return parsed metrics."""
        model_name  = self.file_svc.ensure_uploaded(model_path)
        model_type  = self._model_type(model_path)
        print(f"  Analyse de '{model_name}' (opt={optimization}, comp={compression})...")
        runtime_id = self.ai_svc.trigger_analyze(
            model_name, model_type=model_type,
            optimization=optimization, compression=compression,
        )
        raw = self.ai_svc.wait_for_run(runtime_id)
        return parse_analyze_result(raw)

    def run_benchmark(
        self,
        model_path: str,
        board_name: str,
        optimization: str = OPTIMIZATION_DEFAULT,
        compression: str = COMPRESSION_DEFAULT,
    ) -> dict:
        """Upload model if needed, run benchmark, return parsed metrics."""
        model_name = self.file_svc.ensure_uploaded(model_path)
        model_type = self._model_type(model_path)
        mpu        = _is_mpu(board_name)
        print(f"  Benchmark '{model_name}' sur {board_name}"
              f" (opt={optimization}, comp={compression})"
              f"{'  [MPU]' if mpu else ''}...")
        benchmark_id = self.bench_svc.trigger_benchmark(
            model_name, board_name,
            optimization=optimization, compression=compression,
            model_type=model_type, is_mpu=mpu,
        )
        raw = self.bench_svc.wait_for_run(benchmark_id)
        if mpu:
            return parse_mpu_benchmark_result(raw)
        return parse_benchmark_result(raw)
