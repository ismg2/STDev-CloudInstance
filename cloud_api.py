"""STEdgeAI Developer Cloud API client.

Handles model upload, analysis, benchmarking, and result retrieval
via the REST API at https://stedgeai-dc.st.com.
"""

import os
import time

import requests

from config import ENDPOINTS, STEDGEAI_VERSION, BASE_URL
from auth import get_auth_headers, _get_ssl_verify


class CloudAPIError(Exception):
    """Raised when an API call fails."""


class CloudClient:
    """Client for STEdgeAI Developer Cloud REST API."""

    def __init__(self):
        self.headers = get_auth_headers()
        self.verify = _get_ssl_verify()
        self.version = STEDGEAI_VERSION

    def _request(self, method, url, **kwargs):
        """Make an authenticated HTTP request with error handling."""
        kwargs.setdefault("headers", self.headers)
        kwargs.setdefault("verify", self.verify)
        kwargs.setdefault("timeout", 120)
        try:
            resp = requests.request(method, url, **kwargs)
        except requests.RequestException as e:
            raise CloudAPIError(f"Erreur reseau: {e}")
        if resp.status_code == 401:
            raise CloudAPIError("Token expire ou invalide. Relancez le script pour vous reconnecter.")
        if resp.status_code >= 400:
            raise CloudAPIError(f"Erreur API (HTTP {resp.status_code}): {resp.text[:500]}")
        return resp

    def get_available_boards(self):
        """Fetch the list of available boards from the cloud.

        Falls back to config.AVAILABLE_BOARDS if the API call fails.
        """
        try:
            resp = self._request("GET", f"{ENDPOINTS['benchmark']}/boards")
            return resp.json()
        except CloudAPIError:
            from config import AVAILABLE_BOARDS
            return AVAILABLE_BOARDS

    def get_versions(self):
        """Fetch available STEdgeAI versions."""
        try:
            resp = self._request("GET", ENDPOINTS["versions"])
            return resp.json()
        except CloudAPIError:
            return {"stedgeai": [self.version]}

    def upload_model(self, model_path):
        """Upload a model file to the cloud.

        Args:
            model_path: Path to the model file.

        Returns:
            str: The uploaded file ID/name on the cloud.
        """
        if not os.path.exists(model_path):
            raise CloudAPIError(f"Fichier introuvable: {model_path}")

        filename = os.path.basename(model_path)
        file_size = os.path.getsize(model_path) / 1024  # KB
        print(f"  Upload de {filename} ({file_size:.1f} Ko)...")

        headers = {k: v for k, v in self.headers.items() if k != "Content-Type"}
        with open(model_path, "rb") as f:
            files = {"file": (filename, f)}
            resp = self._request(
                "POST",
                ENDPOINTS["file_service"],
                headers=headers,
                files=files,
            )

        result = resp.json()
        file_id = result.get("id") or result.get("filename") or filename
        print(f"  Upload reussi: {file_id}")
        return file_id

    def analyze_model(self, model_name, optimization="balanced"):
        """Analyze a model to get memory footprint and complexity.

        Args:
            model_name: Name/ID of the uploaded model.
            optimization: Optimization level (balanced, time, size).

        Returns:
            dict: Analysis results with RAM, ROM, MACC info.
        """
        stm32ai_url = f"{ENDPOINTS['stm32ai']}/{self.version}/stm32ai" if self.version else ENDPOINTS["stm32ai"]

        payload = {
            "model": model_name,
            "optimization": optimization,
        }

        print(f"  Analyse du modele {model_name}...")
        resp = self._request("POST", f"{stm32ai_url}/analyze", json=payload)
        result = resp.json()

        # Poll for completion
        run_id = result.get("id") or result.get("run_id")
        if run_id:
            result = self._wait_for_run(stm32ai_url, run_id)

        return self._parse_analysis(result)

    def benchmark_model(self, model_name, board_name, optimization="balanced"):
        """Benchmark a model on a specific STM32 board.

        Args:
            model_name: Name/ID of the uploaded model.
            board_name: Target board name.
            optimization: Optimization level.

        Returns:
            dict: Benchmark results with inference time, memory, etc.
        """
        payload = {
            "model": model_name,
            "board": board_name,
            "optimization": optimization,
            "version": self.version,
        }

        print(f"  Benchmark de {model_name} sur {board_name}...")
        resp = self._request("POST", ENDPOINTS["benchmark"], json=payload)
        result = resp.json()

        # Poll for completion
        run_id = result.get("id") or result.get("run_id") or result.get("bid")
        if run_id:
            result = self._wait_for_benchmark(run_id)

        return self._parse_benchmark(result, board_name)

    def _wait_for_run(self, base_url, run_id, max_wait=300):
        """Poll for a run to complete.

        Args:
            base_url: Base URL for the service.
            run_id: The run ID to poll.
            max_wait: Maximum wait time in seconds.

        Returns:
            dict: Final run result.
        """
        start = time.time()
        poll_interval = 3
        while time.time() - start < max_wait:
            resp = self._request("GET", f"{base_url}/run/{run_id}")
            data = resp.json()
            status = data.get("status", "").lower()
            if status in ("done", "completed", "success"):
                return data
            if status in ("error", "failed"):
                raise CloudAPIError(f"Run echoue: {data.get('message', 'erreur inconnue')}")
            print(f"    En cours... ({status})", end="\r")
            time.sleep(poll_interval)
            poll_interval = min(poll_interval * 1.5, 15)
        raise CloudAPIError(f"Timeout apres {max_wait}s d'attente.")

    def _wait_for_benchmark(self, run_id, max_wait=600):
        """Poll for benchmark completion (can be longer than analysis)."""
        start = time.time()
        poll_interval = 5
        while time.time() - start < max_wait:
            resp = self._request("GET", f"{ENDPOINTS['benchmark']}/{run_id}")
            data = resp.json()
            status = data.get("status", "").lower()
            if status in ("done", "completed", "success"):
                return data
            if status in ("error", "failed"):
                raise CloudAPIError(f"Benchmark echoue: {data.get('message', 'erreur inconnue')}")
            elapsed = int(time.time() - start)
            print(f"    Benchmark en cours... {elapsed}s ({status})  ", end="\r")
            time.sleep(poll_interval)
            poll_interval = min(poll_interval * 1.5, 20)
        raise CloudAPIError(f"Timeout benchmark apres {max_wait}s.")

    def _parse_analysis(self, data):
        """Extract relevant metrics from analysis results."""
        # The API may nest results differently, try common patterns
        results = data.get("results", data.get("report", data))

        return {
            "ram_ko": self._extract_value(results, ["ram", "ram_size", "ram_total"], default="N/A"),
            "rom_ko": self._extract_value(results, ["rom", "flash", "rom_size", "flash_total"], default="N/A"),
            "macc": self._extract_value(results, ["macc", "maccs", "total_macc"], default="N/A"),
        }

    def _parse_benchmark(self, data, board_name):
        """Extract relevant metrics from benchmark results."""
        results = data.get("results", data.get("report", data))

        return {
            "board": board_name,
            "inference_time_ms": self._extract_value(
                results, ["inference_time", "duration_ms", "exec_time", "inference_time_ms"], default="N/A"
            ),
            "ram_ko": self._extract_value(results, ["ram", "ram_size", "internal_ram_consumption"], default="N/A"),
            "rom_ko": self._extract_value(results, ["rom", "flash", "rom_size", "internal_flash_consumption"], default="N/A"),
            "macc": self._extract_value(results, ["macc", "maccs"], default="N/A"),
        }

    @staticmethod
    def _extract_value(data, keys, default="N/A"):
        """Try multiple keys to extract a value from nested data."""
        if not isinstance(data, dict):
            return default
        for key in keys:
            if key in data:
                val = data[key]
                if isinstance(val, dict):
                    # Try to get a total or value sub-key
                    for sub in ["total", "value", "size"]:
                        if sub in val:
                            return val[sub]
                    return default
                return val
        # Try nested
        for v in data.values():
            if isinstance(v, dict):
                result = CloudClient._extract_value(v, keys, default=None)
                if result is not None:
                    return result
        return default
