"""Configuration for STEdgeAI Developer Cloud CLI.

Endpoints sourced from ST official backend:
https://github.com/STMicroelectronics/stm32ai-modelzoo-services
"""

import os

# --- STEdgeAI Developer Cloud Base URL ---
BASE_URL = os.environ.get("BASE_URL_DEVCLOUD", "https://stedgeai-dc.st.com/")

# Ensure trailing slash
if not BASE_URL.endswith("/"):
    BASE_URL += "/"

# --- Service Endpoints (exact paths from ST source) ---
USER_SERVICE_URL    = f"{BASE_URL}api/user_service"
FILE_SERVICE_URL    = f"{BASE_URL}api/file"
BENCHMARK_URL       = f"{BASE_URL}api/benchmark"
VERSIONS_URL        = f"{BASE_URL}assets/versions.json"
CALLBACK_URL        = f"{BASE_URL}callback"

# STM32AI service URL is version-dependent: {BASE_URL}api/{version}/stm32ai/
# Built dynamically in cloud_api.py

# --- SSO / OAuth2 ---
SSO_URL    = os.environ.get("SSO_URL", "https://sso.st.com")
CLIENT_ID  = os.environ.get("CLIENTID", "oidc_prod_client_app_stm32ai")

# --- Routes derived from services ---
# File service sub-routes
MODELS_ROUTE              = f"{FILE_SERVICE_URL}/files/models"
VALIDATION_INPUTS_ROUTE   = f"{FILE_SERVICE_URL}/files/validation/inputs"
VALIDATION_OUTPUTS_ROUTE  = f"{FILE_SERVICE_URL}/files/validation/outputs"
GENERATED_FILES_ROUTE     = f"{FILE_SERVICE_URL}/files/generated"

# Benchmark sub-routes
BENCHMARK_BOARDS_ROUTE = f"{BENCHMARK_URL}/boards"

# User service sub-routes
LOGIN_CALLBACK_ROUTE = f"{USER_SERVICE_URL}/login/callback"
LOGIN_REFRESH_ROUTE  = f"{USER_SERVICE_URL}/login/refresh"
USER_AUTHENTICATE    = f"{USER_SERVICE_URL}/login/authenticate"

# --- Token Storage ---
TOKEN_FILE = os.path.expanduser("~/.stmai_token")

# --- Project Paths ---
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR  = os.path.join(PROJECT_DIR, "modeles")
RESULTS_DIR = os.path.join(PROJECT_DIR, "resultats")
RESULTS_CSV = os.path.join(RESULTS_DIR, "resultats.csv")

# --- Supported Model Extensions ---
MODEL_EXTENSIONS = {".tflite", ".h5", ".onnx", ".keras", ".pb"}

# --- Default STEdgeAI version (fetched from API at runtime if possible) ---
# The actual latest version is resolved dynamically via get_latest_version()
STEDGEAI_DEFAULT_VERSION = os.environ.get("STEDGEAI_VERSION", "10.0.0")

# --- SSL ---
# Set NO_SSL_VERIFY=1 to disable SSL verification (corporate proxy environments)
SSL_VERIFY = os.environ.get("NO_SSL_VERIFY", "") == ""

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
