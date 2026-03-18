"""STEdgeAI Developer Cloud REST client.

Implements the exact API calls matching ST's official SDK:
  STMicroelectronics/stm32ai-modelzoo-services

Services used:
  - FileService:      upload, list, delete models
  - Stm32AiService:  analyze (memory footprint, MACC)
  - BenchmarkService: benchmark on real STM32/MPU hardware
"""

import functools
import json
import os
import time

import requests

from config import (
    BASE_URL, USER_SERVICE_URL,
    FILE_SERVICE_URL, BENCHMARK_URL, VERSIONS_URL,
    MODELS_ROUTE, BENCHMARK_BOARDS_ROUTE,
    STEDGEAI_DEFAULT_VERSION,
    SSL_VERIFY,
)
from auth import get_bearer_token


class CloudAPIError(Exception):
    """Raised when an API call returns an unexpected response."""


# ---------------------------------------------------------------------------
# HTTP helpers
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
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    resp = requests.get(
        url, headers=headers, params=params,
        verify=SSL_VERIFY, proxies=_get_proxy(), timeout=60,
    )
    if resp.status_code == 404:
        raise CloudAPIError(f"Route introuvable: {url}")
    return resp


def _send_post(url: str, token: str, data=None, files=None, json_body=None) -> requests.Response:
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
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
    """Fetch supported versions from cloud and return the latest one."""
    try:
        resp = requests.get(VERSIONS_URL, verify=SSL_VERIFY, proxies=_get_proxy(), timeout=15)
        if resp.status_code == 200:
            versions = resp.json()  # list of {version, isLatest, platform}
            for v in versions:
                if v.get("isLatest", False):
                    return v["version"]
            if versions:
                return versions[-1]["version"]
    except Exception:
        pass
    return STEDGEAI_DEFAULT_VERSION


# ---------------------------------------------------------------------------
# File Service
# ---------------------------------------------------------------------------

class FileService:
    """Wraps {BASE_URL}api/file/files/models endpoints."""

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
            result = resp.json()
            return result.get("upload", False) is True
        raise CloudAPIError(f"Upload echoue (HTTP {resp.status_code}): {resp.text[:300]}")

    def ensure_uploaded(self, model_path: str) -> str:
        """Upload model if not already present. Returns the filename."""
        filename = os.path.basename(model_path)
        existing = self.model_names()
        if filename not in existing:
            size_kb = os.path.getsize(model_path) / 1024
            print(f"  Upload de '{filename}' ({size_kb:.1f} Ko)...", end=" ", flush=True)
            ok = self.upload_model(model_path)
            if not ok:
                raise CloudAPIError(f"L'upload de {filename} a echoue.")
            print("OK")
        else:
            print(f"  '{filename}' deja present sur le cloud.")
        return filename

    def delete_model(self, model_name: str) -> bool:
        """DELETE /files/models/{name}"""
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.token}",
        }
        resp = requests.delete(
            f"{MODELS_ROUTE}/{model_name}",
            headers=headers, verify=SSL_VERIFY, proxies=_get_proxy(), timeout=30,
        )
        if resp.status_code == 200:
            return resp.json().get("deleted", False)
        return False


# ---------------------------------------------------------------------------
# STM32AI Service  (analyze / validate)
# ---------------------------------------------------------------------------

def _stm32ai_base(version: str) -> str:
    """Build the versioned STM32AI service base URL."""
    if version:
        return f"{BASE_URL}api/{version}/stm32ai/"
    return f"{BASE_URL}api/stm32ai/"


class Stm32AiService:
    """Wraps the versioned STM32AI analyze/validate service."""

    def __init__(self, token: str, version: str):
        self.token   = token
        self.version = version
        base = _stm32ai_base(version)
        self.analyze_url  = base + "analyze"
        self.validate_url = base + "validate"
        self.run_base     = base + "run/"

    def _trigger(self, route: str, model_name: str, extra_args: dict = None) -> str:
        """POST multipart form with args JSON string → runtimeId."""
        args = {"model": model_name}
        if extra_args:
            args.update(extra_args)

        resp = _send_post(
            route, self.token,
            data={"args": json.dumps(args)},
        )
        if resp.status_code == 200:
            if resp.headers.get("Content-Type", "") == "application/zip":
                return None  # generate endpoint returned zip directly
            body = resp.json()
            if body is None:
                raise CloudAPIError("Reponse vide du serveur.")
            if "runtimeId" in body:
                return body["runtimeId"]
            if body.get("status") == "ko":
                raise CloudAPIError(f"Erreur serveur: {body.get('error', 'inconnue')}")
        raise CloudAPIError(
            f"Erreur HTTP {resp.status_code} sur {route}: {resp.text[:300]}"
        )

    def trigger_analyze(self, model_name: str, optimization: str = "balanced") -> str:
        return self._trigger(self.analyze_url, model_name, {"optimization": optimization})

    def _get_run(self, runtime_id: str) -> dict:
        resp = _send_get(f"{self.run_base}{runtime_id}", self.token)
        if resp.status_code == 200:
            return resp.json()
        return None

    def wait_for_run(self, runtime_id: str, timeout: int = 300, poll_delay: float = 2.0) -> dict:
        """Poll until run is done. Returns the result dict."""
        start = time.time()
        while (time.time() - start) < timeout:
            result = self._get_run(runtime_id)
            if result:
                state = result.get("state", "").lower()
                progress = result.get("progress", 0)
                print(f"    STM32AI: {state} ({progress}%)   ", end="\r", flush=True)
                if result.get("result") is not None:
                    print()  # newline after \r
                    return result["result"]
                if state == "error":
                    print()
                    raise CloudAPIError(f"Run en erreur: {result}")
            time.sleep(poll_delay)
        raise CloudAPIError(f"Timeout apres {timeout}s.")


# ---------------------------------------------------------------------------
# Benchmark Service
# ---------------------------------------------------------------------------

class BenchmarkService:
    """Wraps {BASE_URL}api/benchmark endpoints."""

    def __init__(self, token: str, version: str):
        self.token   = token
        self.version = version

    def list_boards(self) -> dict:
        """GET /benchmark/boards → dict of board_name → board_info"""
        resp = _send_get(BENCHMARK_BOARDS_ROUTE, self.token)
        if resp.status_code == 200:
            return resp.json()
        return {}

    def trigger_benchmark(self, model_name: str, board_name: str, is_mpu: bool = False) -> str:
        """POST /benchmark/benchmark/{board} → benchmarkId"""
        payload = {
            "model": model_name,
            "version": self.version,
        }
        route = f"{BENCHMARK_URL}/benchmark"
        if is_mpu:
            route += "/mpu"
        route += f"/{board_name.lower()}"

        resp = _send_post(route, self.token, json_body=payload)
        if resp.status_code == 200:
            body = resp.json()
            if "benchmarkId" in body:
                return body["benchmarkId"]
            raise CloudAPIError(f"benchmarkId absent de la reponse: {body}")
        try:
            err = resp.json().get("errors") or resp.text
        except Exception:
            err = resp.text
        raise CloudAPIError(f"Benchmark echoue HTTP {resp.status_code}: {err[:300]}")

    def _get_run(self, benchmark_id: str) -> dict:
        resp = _send_get(f"{BENCHMARK_URL}/benchmark/{benchmark_id}", self.token)
        if resp.status_code == 200:
            return resp.json()
        return None

    def wait_for_run(self, benchmark_id: str, timeout: int = 900, poll_delay: float = 5.0) -> dict:
        """Poll until benchmark is done. Returns the full result dict."""
        start   = time.time()
        last_st = ""
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
                    raise CloudAPIError(
                        f"Benchmark echoue: {result.get('message', 'inconnue')}"
                    )
            time.sleep(poll_delay)
        raise CloudAPIError(f"Timeout benchmark apres {timeout}s.")


# ---------------------------------------------------------------------------
# Result parsers  (mirroring cloud.py logic exactly)
# ---------------------------------------------------------------------------

def _sum(values):
    if isinstance(values, list):
        return functools.reduce(lambda a, b: a + b, values, 0)
    return values or 0


def parse_analyze_result(data: dict) -> dict:
    """Extract memory/MACC from analyze result dict (mirrors cloud.py)."""
    report = data.get("report") or {}
    graph  = data.get("graph")  or {}
    info   = data.get("info")

    if info:
        memory_footprint = info.get("memory_footprint", {})
        cinfo_graph = info["graphs"][0] if info.get("graphs") else {}
        nodes = cinfo_graph.get("nodes", [])
        macc  = sum(n.get("macc", 0) for n in nodes)
    else:
        memory_footprint = graph.get("memory_footprint", {})
        macc = graph.get("macc", 0)

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

    return {
        "ram_ko":  round(ram_bytes / 1024, 2) if ram_bytes else "N/A",
        "rom_ko":  round(rom_bytes / 1024, 2) if rom_bytes else "N/A",
        "macc":    macc or "N/A",
    }


def parse_benchmark_result(result: dict) -> dict:
    """Extract inference time and memory from benchmark result dict (mirrors cloud.py)."""
    benchmark = result.get("benchmark", {})
    info      = benchmark.get("info")
    graph     = benchmark.get("graph", {})
    memory_mapping = result.get("memoryMapping") or {}

    if info:
        # New format with 'info' field
        cinfo_graph = info["graphs"][0] if info.get("graphs") else {}
        exec_time   = cinfo_graph.get("exec_time", {}) if cinfo_graph else graph.get("exec_time", {})
        memory_footprint = memory_mapping.get(
            "memoryFootprint",
            info.get("memory_footprint", {})
        )
        nodes = cinfo_graph.get("nodes", [])
        macc  = sum(n.get("macc", 0) for n in nodes)
    else:
        # Legacy format using 'report'
        report       = benchmark.get("report", {})
        exec_time    = graph.get("exec_time", {})
        memory_footprint = memory_mapping.get(
            "memoryFootprint",
            graph.get("memory_footprint", {})
        )
        macc = report.get("rom_n_macc", 0)

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

    return {
        "inference_time_ms": round(duration_ms, 3) if duration_ms >= 0 else "N/A",
        "ram_ko":  round(ram_bytes / 1024, 2) if ram_bytes else "N/A",
        "rom_ko":  round(rom_bytes / 1024, 2) if rom_bytes else "N/A",
        "macc":    macc or "N/A",
        "cycles":  exec_time.get("cycles", "N/A"),
    }


def parse_mpu_benchmark_result(result: dict) -> dict:
    """Extract results from MPU benchmark format (mirrors cloud.py)."""
    bench = result.get("benchmark", {})
    exec_time = bench.get("exec_time", {})
    return {
        "inference_time_ms": round(exec_time.get("duration_ms", -1), 3),
        "ram_ko":  round(bench.get("ram_peak", 0) / 1024, 2) if bench.get("ram_peak") else "N/A",
        "rom_ko":  round(bench.get("model_size", 0) / 1024, 2) if bench.get("model_size") else "N/A",
        "macc":    "N/A",
        "cycles":  "N/A",
    }


# ---------------------------------------------------------------------------
# High-level CloudClient
# ---------------------------------------------------------------------------

# Board names that use the MPU endpoint
_MPU_KEYWORDS = ("MP2", "MP1", "MP257", "MP131", "LINUX", "MPU")


def _is_mpu(board_name: str) -> bool:
    return any(kw in board_name.upper() for kw in _MPU_KEYWORDS)


class CloudClient:
    """High-level client that orchestrates upload → analyze → benchmark."""

    def __init__(self):
        self.token   = get_bearer_token()
        self.version = get_latest_version(self.token)
        print(f"  [Cloud] Connecte | STEdgeAI version: {self.version}")
        self.file_svc  = FileService(self.token)
        self.ai_svc    = Stm32AiService(self.token, self.version)
        self.bench_svc = BenchmarkService(self.token, self.version)

    def get_boards(self) -> list:
        """Return list of available board names from the cloud."""
        boards_dict = self.bench_svc.list_boards()
        if isinstance(boards_dict, dict):
            return list(boards_dict.keys())
        return []

    def run_analyze(self, model_path: str) -> dict:
        """Upload model if needed, run analysis, return parsed metrics."""
        model_name = self.file_svc.ensure_uploaded(model_path)
        print(f"  Analyse de '{model_name}'...")
        runtime_id = self.ai_svc.trigger_analyze(model_name)
        raw = self.ai_svc.wait_for_run(runtime_id)
        return parse_analyze_result(raw)

    def run_benchmark(self, model_path: str, board_name: str) -> dict:
        """Upload model if needed, run benchmark, return parsed metrics."""
        model_name = self.file_svc.ensure_uploaded(model_path)
        mpu = _is_mpu(board_name)
        print(f"  Benchmark de '{model_name}' sur {board_name}{'  (MPU)' if mpu else ''}...")
        benchmark_id = self.bench_svc.trigger_benchmark(model_name, board_name, is_mpu=mpu)
        raw = self.bench_svc.wait_for_run(benchmark_id)
        if mpu:
            return parse_mpu_benchmark_result(raw)
        return parse_benchmark_result(raw)
