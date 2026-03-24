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
import uuid
from datetime import datetime

import requests

from app.config import (
    BASE_URL,
    FILE_SERVICE_URL, BENCHMARK_URL, VERSIONS_URL,
    MODELS_ROUTE, BENCHMARK_BOARDS_ROUTE,
    STEDGEAI_DEFAULT_VERSION,
    SSL_VERIFY,
    OPTIMIZATION_DEFAULT, COMPRESSION_DEFAULT,
    EXTENSION_TO_TYPE,
    RUN_LOGS_JSONL,
)
from app.auth import get_bearer_token


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


def get_available_versions() -> list:
    """Fetch all available STEdgeAI versions from the cloud."""
    try:
        resp = requests.get(VERSIONS_URL, verify=SSL_VERIFY, proxies=_get_proxy(), timeout=15)
        if resp.status_code == 200:
            versions = resp.json()
            if isinstance(versions, list):
                out = []
                for item in versions:
                    if isinstance(item, dict) and item.get("version"):
                        out.append(item["version"])
                if out:
                    return out
    except Exception:
        pass
    return [STEDGEAI_DEFAULT_VERSION]


def _append_jsonl(path: str, event: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def _extract_error_message(payload: dict, fallback: str = "inconnue") -> str:
    if not isinstance(payload, dict):
        return fallback
    for key in ("message", "error", "errors", "detail", "cause", "traceId"):
        value = payload.get(key)
        if value:
            if isinstance(value, (dict, list)):
                try:
                    return json.dumps(value, ensure_ascii=False)[:300]
                except Exception:
                    return str(value)[:300]
            return str(value)[:300]
    return fallback


def actionable_error_hint(message: str) -> str:
    """Return a concrete next-step hint from an error message."""
    text = (message or "").lower()
    if "memory footprint" in text or "empreinte" in text:
        return (
            "Essaye compute_mode=cpu (ou auto), garde memory_pool vide (memoire interne), "
            "desactive split_weights/allocate_activations, puis reduis le modele si besoin."
        )
    if "invalidmodelerror" in text or "invalid model" in text or "modele invalide" in text:
        return (
            "Verifie le format (.tflite/.onnx/.h5/.keras), charge le modele localement, "
            "et controle les operateurs supportes par ST Edge AI Core."
        )
    if "split-weights" in text or "allocate-activations" in text or "memory-pool" in text:
        return (
            "Pour stm32n6/NPU: laisser memory_pool vide et desactiver split_weights/"
            "allocate_activations/allocate_states."
        )
    if "timeout" in text or "timed out" in text:
        return "Queue chargee ou execution lente: reessaye plus tard, augmente le timeout, ou change de board."
    return "Relance en mode auto ou cpu, garde les options memoire par defaut, puis consulte benchmarks.jsonl pour le detail backend."


# ---------------------------------------------------------------------------
# FileService  ->  {BASE_URL}api/file/files/models
# ---------------------------------------------------------------------------

class FileService:

    def __init__(self, token: str):
        self.token = token

    def list_models(self) -> list:
        """GET /files/models -> list of {name, ...}"""
        resp = _send_get(MODELS_ROUTE, self.token)
        if resp.status_code == 200:
            data = resp.json()
            return data if isinstance(data, list) else []
        return []

    def model_names(self) -> list:
        return [m["name"] for m in self.list_models()]

    def upload_model(self, model_path: str) -> bool:
        """POST /files/models (multipart) -> {upload: true/false}"""
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
# Stm32AiService  ->  {BASE_URL}api/{version}/stm32ai/
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
        """POST multipart form with args JSON -> runtimeId.

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
# BenchmarkService  ->  {BASE_URL}api/benchmark/
# ---------------------------------------------------------------------------

_MPU_KEYWORDS = ("MP2", "MP1", "MP257", "MP131", "LINUX", "MPU")
_NPU_KEYWORDS = ("N6", "N6570", "NEURAL-ART", "NEURAL_ART", "NPU")
_ISPU_KEYWORDS = ("ISPU",)


def _is_mpu(board_name: str) -> bool:
    return any(kw in board_name.upper() for kw in _MPU_KEYWORDS)


def _is_npu_board(board_name: str) -> bool:
    upper = board_name.upper()
    return any(kw in upper for kw in _NPU_KEYWORDS)


def _is_ispu_board(board_name: str) -> bool:
    upper = board_name.upper()
    return any(kw in upper for kw in _ISPU_KEYWORDS)


def validate_benchmark_options(
    board_name: str,
    target: str = "",
    st_neural_art: str = "",
    memory_pool: str = "",
    split_weights: bool = False,
    allocate_activations: bool = False,
    allocate_states: bool = False,
) -> None:
    """Validate known incompatible combinations before calling cloud benchmark API."""
    is_mpu = _is_mpu(board_name)
    is_npu = _is_npu_board(board_name)
    is_ispu = _is_ispu_board(board_name)

    if target:
        t = target.lower()
        if t == "stm32n6" and not is_npu:
            raise CloudAPIError(
                f"Combinaison invalide: target={target} mais le board '{board_name}' ne semble pas NPU stm32n6."
            )

    if st_neural_art and not is_npu:
        raise CloudAPIError(
            f"Option --st-neural-art incompatible avec board '{board_name}' (supporte uniquement stm32n6 + NPU)."
        )

    # Advanced memory placement options are for embedded targets, not MPU benchmark route.
    if is_mpu and (memory_pool or split_weights or allocate_activations or allocate_states):
        raise CloudAPIError(
            "Options avancees memoire/poids non supportees pour boards MPU (route /benchmark/mpu)."
        )

    # Documented unsupported combinations for explicit NPU mode (stm32n6 + NPU).
    npu_mode = bool((target or "").lower() == "stm32n6" or st_neural_art)
    if is_npu and npu_mode:
        if memory_pool:
            raise CloudAPIError("Option --memory-pool non supportee pour stm32n6 avec NPU.")
        if split_weights:
            raise CloudAPIError("Option --split-weights non supportee pour stm32n6 avec NPU.")
        if allocate_activations:
            raise CloudAPIError("Option --allocate-activations non supportee pour stm32n6 avec NPU.")
        if allocate_states:
            raise CloudAPIError("Option --allocate-states non supportee pour stm32n6 avec NPU.")

    # ISPU does not support memory-pool according to CLI doc.
    if is_ispu and memory_pool:
        raise CloudAPIError("Option --memory-pool non supportee pour ISPU.")


class BenchmarkService:

    def __init__(self, token: str, version: str):
        self.token   = token
        self.version = version
        self.last_trigger = {}

    def list_boards(self) -> dict:
        """GET /benchmark/boards -> dict of board_name -> board_info"""
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
        extra_options: dict = None,
        run_id: str = "",
    ) -> str:
        """POST /benchmark/benchmark/{board} -> benchmarkId

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
        if extra_options:
            for key, value in extra_options.items():
                if value is None:
                    continue
                if isinstance(value, str) and not value.strip():
                    continue
                payload[key] = value

        route = f"{BENCHMARK_URL}/benchmark"
        if is_mpu:
            route += "/mpu"
        route += f"/{board_name.lower()}"

        resp = _send_post(route, self.token, json_body=payload)
        if resp.status_code == 200:
            body = resp.json()
            if "benchmarkId" in body:
                benchmark_id = body["benchmarkId"]
                self.last_trigger = {
                    "route": route,
                    "payload": payload,
                    "benchmark_id": benchmark_id,
                }
                _append_jsonl(RUN_LOGS_JSONL, {
                    "ts": datetime.utcnow().isoformat() + "Z",
                    "event": "benchmark_triggered",
                    "run_id": run_id,
                    "benchmark_id": benchmark_id,
                    "route": route,
                    "payload": payload,
                })
                return benchmark_id
            raise CloudAPIError(f"benchmarkId absent: {body}")
        try:
            err = resp.json().get("errors") or resp.text
        except Exception:
            err = resp.text
        _append_jsonl(RUN_LOGS_JSONL, {
            "ts": datetime.utcnow().isoformat() + "Z",
            "event": "benchmark_trigger_error",
            "run_id": run_id,
            "route": route,
            "status_code": resp.status_code,
            "error": str(err)[:300],
            "payload": payload,
        })
        raise CloudAPIError(f"Benchmark echoue HTTP {resp.status_code}: {err[:300]}")

    def _get_run(self, benchmark_id: str) -> dict:
        resp = _send_get(f"{BENCHMARK_URL}/benchmark/{benchmark_id}", self.token)
        return resp.json() if resp.status_code == 200 else None

    def wait_for_run(self, benchmark_id: str, timeout: int = 900, poll: float = 5.0, run_id: str = "") -> dict:
        """Poll until benchmark is done. Returns full result dict."""
        start    = time.time()
        last_st  = ""
        while (time.time() - start) < timeout:
            result = self._get_run(benchmark_id)
            if result:
                state = result.get("state", "").lower()
                if state != last_st:
                    last_st = state
                    _append_jsonl(RUN_LOGS_JSONL, {
                        "ts": datetime.utcnow().isoformat() + "Z",
                        "event": "benchmark_state",
                        "run_id": run_id,
                        "benchmark_id": benchmark_id,
                        "state": state,
                    })
                elapsed = int(time.time() - start)
                print(f"    Benchmark: {state} ({elapsed}s)   ", end="\r", flush=True)
                if state == "done":
                    print()
                    _append_jsonl(RUN_LOGS_JSONL, {
                        "ts": datetime.utcnow().isoformat() + "Z",
                        "event": "benchmark_done",
                        "run_id": run_id,
                        "benchmark_id": benchmark_id,
                    })
                    return result
                if state == "error":
                    print()
                    msg = _extract_error_message(result, "inconnue")
                    hint = actionable_error_hint(msg)
                    _append_jsonl(RUN_LOGS_JSONL, {
                        "ts": datetime.utcnow().isoformat() + "Z",
                        "event": "benchmark_error",
                        "run_id": run_id,
                        "benchmark_id": benchmark_id,
                        "message": msg,
                        "action_hint": hint,
                        "result": result,
                    })
                    raise CloudAPIError(f"Benchmark echoue: {msg} | Action: {hint}")
            time.sleep(poll)
        _append_jsonl(RUN_LOGS_JSONL, {
            "ts": datetime.utcnow().isoformat() + "Z",
            "event": "benchmark_timeout",
            "run_id": run_id,
            "benchmark_id": benchmark_id,
            "timeout_s": timeout,
        })
        hint = actionable_error_hint("timeout benchmark")
        raise CloudAPIError(f"Timeout benchmark apres {timeout}s. | Action: {hint}")


# ---------------------------------------------------------------------------
# Result parsers  (mirroring cloud.py + evaluation_metrics.html field names)
# ---------------------------------------------------------------------------

def _sum(values):
    if isinstance(values, list):
        total = 0.0
        for value in values:
            num = to_float(value)
            if num is not None:
                total += num
        return total
    num = to_float(values)
    return num if num is not None else 0.0


def to_float(value):
    """Convert int/float/str to float, return None when not numeric."""
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None
    return None


def _safe_round(value, ndigits: int):
    """Round only numeric values converted through to_float."""
    num = to_float(value)
    if num is None:
        return None
    return round(num, ndigits)


def _safe_int(value):
    num = to_float(value)
    if num is None:
        return None
    return int(num)


FLASH_THRESHOLDS_KB = [512, 1024, 2048]
RAM_THRESHOLDS_KB = [128, 256, 512]


def _normalize_shape(shape):
    if isinstance(shape, (list, tuple)):
        return "x".join(str(x) for x in shape)
    if shape is None:
        return "N/A"
    return str(shape)


def _extract_tensor_desc(data: dict):
    """Best-effort extraction of first input/output tensor descriptors."""
    candidates = []
    if isinstance(data, dict):
        info = data.get("info")
        if isinstance(info, dict):
            candidates.append(info)
            graphs = info.get("graphs")
            if isinstance(graphs, list) and graphs:
                candidates.append(graphs[0])
        graph = data.get("graph")
        if isinstance(graph, dict):
            candidates.append(graph)

    in_keys = ("inputs", "input_tensors", "in_desc", "input_desc", "input")
    out_keys = ("outputs", "output_tensors", "out_desc", "output_desc", "output")

    def _first_tensor(container, keys):
        for key in keys:
            val = container.get(key)
            if isinstance(val, list) and val:
                return val[0] if isinstance(val[0], dict) else {"shape": val[0]}
            if isinstance(val, dict):
                return val
        return {}

    input_tensor = {}
    output_tensor = {}
    for c in candidates:
        if not input_tensor:
            input_tensor = _first_tensor(c, in_keys)
        if not output_tensor:
            output_tensor = _first_tensor(c, out_keys)

    input_shape = _normalize_shape(
        input_tensor.get("shape")
        or input_tensor.get("dims")
        or input_tensor.get("dim")
        or input_tensor.get("size")
    )
    output_shape = _normalize_shape(
        output_tensor.get("shape")
        or output_tensor.get("dims")
        or output_tensor.get("dim")
        or output_tensor.get("size")
    )
    input_dtype = str(
        input_tensor.get("dtype")
        or input_tensor.get("type")
        or input_tensor.get("data_type")
        or "N/A"
    )
    output_dtype = str(
        output_tensor.get("dtype")
        or output_tensor.get("type")
        or output_tensor.get("data_type")
        or "N/A"
    )
    return {
        "input_shape": input_shape,
        "output_shape": output_shape,
        "input_dtype": input_dtype,
        "output_dtype": output_dtype,
    }


def build_memory_visibility_report(analysis: dict) -> dict:
    """Evaluate model memory against common STM32 internal memory thresholds."""
    weights_ko = to_float(analysis.get("weights_ko")) if isinstance(analysis, dict) else None
    activations_ko = to_float(analysis.get("activations_ko")) if isinstance(analysis, dict) else None

    rows = []
    for flash_kb, ram_kb in zip(FLASH_THRESHOLDS_KB, RAM_THRESHOLDS_KB):
        flash_ok = weights_ko is not None and weights_ko <= flash_kb
        ram_ok = activations_ko is not None and activations_ko <= ram_kb
        rows.append(
            {
                "tier": f"Flash {flash_kb}KB / RAM {ram_kb}KB",
                "flash_kb": flash_kb,
                "ram_kb": ram_kb,
                "flash_ok": flash_ok,
                "ram_ok": ram_ok,
                "overall_ok": flash_ok and ram_ok,
            }
        )

    return {
        "weights_ko": weights_ko,
        "activations_ko": activations_ko,
        "rows": rows,
    }


def recommend_memory_pooling(analysis: dict, flash_limit_kb: int = 512, ram_limit_kb: int = 128) -> dict:
    """Recommend split_weights / allocate_activations from memory pressure."""
    weights_ko = to_float(analysis.get("weights_ko")) if isinstance(analysis, dict) else None
    activations_ko = to_float(analysis.get("activations_ko")) if isinstance(analysis, dict) else None

    flash_too_small = weights_ko is not None and weights_ko > flash_limit_kb
    ram_too_small = activations_ko is not None and activations_ko > ram_limit_kb

    split_weights = bool(flash_too_small)
    allocate_activations = bool(ram_too_small)

    if not flash_too_small and not ram_too_small:
        reason = "Le modele tient en memoire interne cible (flash+ram)."
    elif flash_too_small and not ram_too_small:
        reason = "Flash interne insuffisante pour les poids: split_weights recommande."
    elif not flash_too_small and ram_too_small:
        reason = "RAM interne insuffisante pour les activations: allocate_activations recommande."
    else:
        reason = "Flash et RAM internes insuffisantes: activer split_weights et allocate_activations."

    return {
        "split_weights": split_weights,
        "allocate_activations": allocate_activations,
        "flash_too_small": flash_too_small,
        "ram_too_small": ram_too_small,
        "flash_limit_kb": flash_limit_kb,
        "ram_limit_kb": ram_limit_kb,
        "reason": reason,
    }


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
    acc = to_float(m.get("acc"))
    rmse = _safe_round(m.get("rmse"), 6)
    mae = _safe_round(m.get("mae"), 6)
    l2r = _safe_round(m.get("l2r"), 6)
    return {
        "accuracy": round(acc * 100, 2) if acc is not None else "N/A",
        "rmse":     rmse if rmse is not None else "N/A",
        "mae":      mae if mae is not None else "N/A",
        "l2r":      l2r if l2r is not None else "N/A",
    }


def parse_analyze_result(data: dict) -> dict:
    """Extract memory/MACC/params from analyze result.

    Fields from command_line_interface.html:
            weights (ro)    -> ROM/Flash in bytes
            activations (rw)-> RAM in bytes
            macc            -> Multiply-Accumulate ops
            params #        -> number of parameters
    """
    report = data.get("report") or {}
    graph  = data.get("graph")  or {}
    info   = data.get("info")

    if info:
        memory_footprint = info.get("memory_footprint", {})
        cinfo_graph      = info["graphs"][0] if info.get("graphs") else {}
        nodes            = cinfo_graph.get("nodes", [])
        macc             = sum(to_float(n.get("macc")) or 0.0 for n in nodes)
        params           = sum(to_float(n.get("params")) or 0.0 for n in nodes)
        val_metrics      = info.get("validation", {}).get("val_metrics", [])
    else:
        memory_footprint = graph.get("memory_footprint", {})
        macc             = to_float(graph.get("macc")) or 0.0
        params           = to_float(graph.get("params")) or 0.0
        val_metrics      = report.get("val_metrics", [])

    activations = to_float(memory_footprint.get("activations")) or 0.0
    weights     = to_float(memory_footprint.get("weights")) or 0.0
    io_list     = memory_footprint.get("io", [])
    io_bytes = _sum(io_list)
    kernel_flash = to_float(memory_footprint.get("kernel_flash")) or 0.0
    toolchain_flash = to_float(memory_footprint.get("toolchain_flash")) or 0.0
    kernel_ram = to_float(memory_footprint.get("kernel_ram")) or 0.0
    toolchain_ram = to_float(memory_footprint.get("toolchain_ram"))
    extra_ram = to_float(memory_footprint.get("extra_ram")) or 0.0

    rom_bytes = (
        weights
        + kernel_flash
        + toolchain_flash
    )
    ram_bytes = (
        activations
        + io_bytes
        + kernel_ram
        + (toolchain_ram if toolchain_ram is not None else extra_ram)
    )

    result = {
        "ram_ko":  _safe_round(ram_bytes / 1024, 2) if ram_bytes > 0 else "N/A",
        "rom_ko":  _safe_round(rom_bytes / 1024, 2) if rom_bytes > 0 else "N/A",
        "weights_ko": _safe_round(weights / 1024, 2) if weights > 0 else "N/A",
        "activations_ko": _safe_round(activations / 1024, 2) if activations > 0 else "N/A",
        "io_ko": _safe_round(io_bytes / 1024, 2) if io_bytes > 0 else "N/A",
        "macc":    _safe_int(macc) if macc > 0 else "N/A",
        "params":  _safe_int(params) if params > 0 else "N/A",
    }
    result.update(_extract_tensor_desc(data))
    result.update(_extract_val_metrics(val_metrics))
    return result


def parse_benchmark_result(result: dict) -> dict:
    """Extract inference time, memory, and accuracy from benchmark result.

    State progression (from benchmark_service.py + doc):
            waiting_for_build -> in_queue -> generating_sources -> copying_sources
            -> loading_sources -> building -> validation -> done

    Result fields from cloud.py + evaluation_metrics.html:
            exec_time.duration_ms  -> inference time in ms
            exec_time.cycles       -> CPU cycles
            memory_footprint.*     -> memory breakdown
            val_metrics[].acc      -> accuracy
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
        macc             = sum(to_float(n.get("macc")) or 0.0 for n in nodes)
        params           = sum(to_float(n.get("params")) or 0.0 for n in nodes)
        val_metrics      = info.get("validation", {}).get("val_metrics", [])
    else:
        report           = benchmark.get("report", {})
        exec_time        = graph.get("exec_time", {})
        memory_footprint = memory_mapping.get("memoryFootprint", graph.get("memory_footprint", {}))
        macc             = to_float(report.get("rom_n_macc")) or 0.0
        params           = to_float(report.get("params")) or 0.0
        val_metrics      = report.get("val_metrics", [])

    duration_ms = to_float(exec_time.get("duration_ms"))
    activations = to_float(memory_footprint.get("activations")) or 0.0
    weights     = to_float(memory_footprint.get("weights")) or 0.0
    io_list     = memory_footprint.get("io", [])
    kernel_flash = to_float(memory_footprint.get("kernel_flash")) or 0.0
    toolchain_flash = to_float(memory_footprint.get("toolchain_flash")) or 0.0
    kernel_ram = to_float(memory_footprint.get("kernel_ram")) or 0.0
    toolchain_ram = to_float(memory_footprint.get("toolchain_ram"))
    extra_ram = to_float(memory_footprint.get("extra_ram")) or 0.0
    cycles = to_float(exec_time.get("cycles"))

    rom_bytes = (
        weights
        + kernel_flash
        + toolchain_flash
    )
    ram_bytes = (
        activations
        + _sum(io_list)
        + kernel_ram
        + (toolchain_ram if toolchain_ram is not None else extra_ram)
    )

    parsed = {
        "inference_time_ms": _safe_round(duration_ms, 3) if duration_ms is not None and duration_ms >= 0 else "N/A",
        "ram_ko":    _safe_round(ram_bytes / 1024, 2) if ram_bytes > 0 else "N/A",
        "rom_ko":    _safe_round(rom_bytes / 1024, 2) if rom_bytes > 0 else "N/A",
        "macc":      _safe_int(macc) if macc > 0 else "N/A",
        "params":    _safe_int(params) if params > 0 else "N/A",
        "cycles":    _safe_int(cycles) if cycles is not None and cycles >= 0 else "N/A",
    }
    parsed.update(_extract_val_metrics(val_metrics))
    return parsed


def parse_mpu_benchmark_result(result: dict) -> dict:
    """Extract results from MPU benchmark format."""
    bench     = result.get("benchmark", {})
    exec_time = bench.get("exec_time", {})
    duration_ms = to_float(exec_time.get("duration_ms"))
    ram_peak = to_float(bench.get("ram_peak"))
    model_size = to_float(bench.get("model_size"))
    return {
        "inference_time_ms": _safe_round(duration_ms, 3) if duration_ms is not None and duration_ms >= 0 else "N/A",
        "ram_ko":   _safe_round(ram_peak / 1024, 2) if ram_peak is not None and ram_peak > 0 else "N/A",
        "rom_ko":   _safe_round(model_size / 1024, 2) if model_size is not None and model_size > 0 else "N/A",
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
    """Orchestrates upload -> analyze -> benchmark for one model."""

    def __init__(self, version: str = None):
        self.token    = get_bearer_token()
        self.version  = version or get_latest_version(self.token)
        print(f"  [Cloud] Connecte | STEdgeAI Core version: {self.version}")
        self.file_svc  = FileService(self.token)
        self.ai_svc    = Stm32AiService(self.token, self.version)
        self.bench_svc = BenchmarkService(self.token, self.version)

    @staticmethod
    def available_versions() -> list:
        return get_available_versions()

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
        target: str = "",
        st_neural_art: str = "",
        memory_pool: str = "",
        split_weights: bool = False,
        allocate_activations: bool = False,
        allocate_states: bool = False,
        input_memory_alignment: int = None,
        output_memory_alignment: int = None,
        no_inputs_allocation: bool = False,
        no_outputs_allocation: bool = False,
    ) -> dict:
        """Upload model if needed, run benchmark, return parsed metrics."""
        validate_benchmark_options(
            board_name=board_name,
            target=target,
            st_neural_art=st_neural_art,
            memory_pool=memory_pool,
            split_weights=split_weights,
            allocate_activations=allocate_activations,
            allocate_states=allocate_states,
        )

        model_name = self.file_svc.ensure_uploaded(model_path)
        model_type = self._model_type(model_path)
        mpu        = _is_mpu(board_name)
        run_id     = str(uuid.uuid4())
        extra_options = {
            "target": target,
            "st_neural_art": st_neural_art,
            "memory_pool": memory_pool,
            "split_weights": True if split_weights else None,
            "allocate_activations": True if allocate_activations else None,
            "allocate_states": True if allocate_states else None,
            "input_memory_alignment": input_memory_alignment,
            "output_memory_alignment": output_memory_alignment,
            "no_inputs_allocation": True if no_inputs_allocation else None,
            "no_outputs_allocation": True if no_outputs_allocation else None,
        }
        print(f"  Benchmark '{model_name}' sur {board_name}"
              f" (opt={optimization}, comp={compression})"
              f"{'  [MPU]' if mpu else ''}...")
        benchmark_id = ""
        try:
            benchmark_id = self.bench_svc.trigger_benchmark(
                model_name, board_name,
                optimization=optimization, compression=compression,
                model_type=model_type, is_mpu=mpu,
                extra_options=extra_options,
                run_id=run_id,
            )
            raw = self.bench_svc.wait_for_run(benchmark_id, run_id=run_id)
            route = self.bench_svc.last_trigger.get("route", "")
            payload = self.bench_svc.last_trigger.get("payload", {})
            core_command = f"POST {route} payload={json.dumps(payload, sort_keys=True, ensure_ascii=False)}"
            if mpu:
                metrics = parse_mpu_benchmark_result(raw)
            else:
                metrics = parse_benchmark_result(raw)

            metrics["_run_meta"] = {
                "run_id": run_id,
                "benchmark_id": benchmark_id,
                "core_version": self.version,
                "core_command": core_command,
                "target": target,
                "st_neural_art": st_neural_art,
                "memory_pool": memory_pool,
                "split_weights": bool(split_weights),
                "allocate_activations": bool(allocate_activations),
                "allocate_states": bool(allocate_states),
                "input_memory_alignment": input_memory_alignment,
                "output_memory_alignment": output_memory_alignment,
                "no_inputs_allocation": bool(no_inputs_allocation),
                "no_outputs_allocation": bool(no_outputs_allocation),
            }
            _append_jsonl(RUN_LOGS_JSONL, {
                "ts": datetime.utcnow().isoformat() + "Z",
                "event": "benchmark_metrics",
                "run_id": run_id,
                "benchmark_id": benchmark_id,
                "core_version": self.version,
                "core_command": core_command,
                "metrics": {k: v for k, v in metrics.items() if k != "_run_meta"},
            })
            return metrics
        except Exception as exc:
            route = self.bench_svc.last_trigger.get("route", "")
            payload = self.bench_svc.last_trigger.get("payload", {})
            core_command = ""
            if route:
                core_command = f"POST {route} payload={json.dumps(payload, sort_keys=True, ensure_ascii=False)}"
            hint = actionable_error_hint(str(exc))
            _append_jsonl(RUN_LOGS_JSONL, {
                "ts": datetime.utcnow().isoformat() + "Z",
                "event": "benchmark_run_error",
                "run_id": run_id,
                "benchmark_id": benchmark_id,
                "core_version": self.version,
                "core_command": core_command,
                "error": str(exc),
                "action_hint": hint,
            })
            msg = f"{exc} | Action: {hint}"
            if core_command:
                msg += f" | Commande: {core_command}"
            raise CloudAPIError(msg) from exc
