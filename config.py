"""Configuration for STEdgeAI Developer Cloud CLI."""

import os

# --- STEdgeAI Developer Cloud Endpoints ---
BASE_URL = os.environ.get("BASE_URL_DEVCLOUD", "https://stedgeai-dc.st.com")

ENDPOINTS = {
    "user_service": f"{BASE_URL}/api/user_service",
    "file_service": f"{BASE_URL}/api/file",
    "benchmark": f"{BASE_URL}/api/benchmark",
    "stm32ai": f"{BASE_URL}/api/stm32ai",
    "generate_nbg": f"{BASE_URL}/api/generate_nbg",
    "versions": f"{BASE_URL}/assets/versions.json",
    "login_callback": f"{BASE_URL}/login/callback",
    "login_refresh": f"{BASE_URL}/login/refresh",
}

# --- SSO Configuration ---
SSO_URL = os.environ.get("SSO_URL", "https://sso.st.com")
SSO_CLIENT_ID = "oidc_prod_client_app_stm32ai"
SSO_CALLBACK_URL = f"{BASE_URL}/callback"

# --- Token Storage ---
TOKEN_FILE = os.path.expanduser("~/.stmai_token")

# --- Project Paths ---
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(PROJECT_DIR, "modeles")
RESULTS_DIR = os.path.join(PROJECT_DIR, "resultats")
RESULTS_CSV = os.path.join(RESULTS_DIR, "resultats.csv")

# --- Supported Model Extensions ---
MODEL_EXTENSIONS = {".tflite", ".h5", ".onnx", ".keras", ".pb", ".savedmodel"}

# --- Available STM32 Boards for Benchmarking ---
AVAILABLE_BOARDS = [
    "STM32H747I-DISCO",
    "STM32H7S78-DK",
    "STM32F469I-DISCO",
    "STM32F746G-DISCO",
    "STM32H573I-DK",
    "STM32L4R9I-DISCO",
    "STM32MP257F-EV1",
    "STM32N6570-DK",
    "B-U585I-IOT02A",
    "NUCLEO-F401RE",
    "NUCLEO-H743ZI2",
    "NUCLEO-U575ZI-Q",
]

# --- STEdgeAI Version ---
STEDGEAI_VERSION = os.environ.get("STEDGEAI_VERSION", "10.0.0")

# --- CSV Columns ---
CSV_COLUMNS = [
    "modele",
    "dossier",
    "board",
    "inference_time_ms",
    "ram_ko",
    "rom_ko",
    "macc",
    "precision",
    "date",
    "status",
]
