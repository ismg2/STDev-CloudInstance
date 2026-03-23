"""Configuration for STEdgeAI Developer Cloud CLI.

Endpoints and parameters sourced from:
  - ST official backend: STMicroelectronics/stm32ai-modelzoo-services
  - ST Edge AI Core 4.0 documentation (Documentation/ST Edge AI Core 4.0/)
"""

import os

# ---------------------------------------------------------------------------
# URLs
# ---------------------------------------------------------------------------

BASE_URL = os.environ.get("BASE_URL_DEVCLOUD", "https://stedgeai-dc.st.com/")
if not BASE_URL.endswith("/"):
    BASE_URL += "/"

USER_SERVICE_URL  = f"{BASE_URL}api/user_service"
FILE_SERVICE_URL  = f"{BASE_URL}api/file"
BENCHMARK_URL     = f"{BASE_URL}api/benchmark"
VERSIONS_URL      = f"{BASE_URL}assets/versions.json"
CALLBACK_URL      = f"{BASE_URL}callback"

# File service sub-routes
MODELS_ROUTE             = f"{FILE_SERVICE_URL}/files/models"
VALIDATION_INPUTS_ROUTE  = f"{FILE_SERVICE_URL}/files/validation/inputs"
VALIDATION_OUTPUTS_ROUTE = f"{FILE_SERVICE_URL}/files/validation/outputs"
GENERATED_FILES_ROUTE    = f"{FILE_SERVICE_URL}/files/generated"

# Benchmark sub-routes
BENCHMARK_BOARDS_ROUTE = f"{BENCHMARK_URL}/boards"

# User / Login sub-routes
LOGIN_CALLBACK_ROUTE = f"{USER_SERVICE_URL}/login/callback"
LOGIN_REFRESH_ROUTE  = f"{USER_SERVICE_URL}/login/refresh"

# SSO / OAuth2
SSO_URL   = os.environ.get("SSO_URL", "https://sso.st.com")
CLIENT_ID = os.environ.get("CLIENTID", "oidc_prod_client_app_stm32ai")

# ---------------------------------------------------------------------------
# ST Edge AI Core 4.0 CLI Parameters
# Source: Documentation/ST Edge AI Core 4.0/command_line_interface.html
# ---------------------------------------------------------------------------

# -O / --optimization
OPTIMIZATION_OPTIONS = {
    "balanced": "Equilibre RAM et temps d'inference (defaut)",
    "ram":      "Minimise l'utilisation de la RAM",
    "time":     "Minimise la latence d'inference",
    "size":     "Minimise la taille du modele",
}
OPTIMIZATION_DEFAULT = "balanced"

# -c / --compression
COMPRESSION_OPTIONS = {
    "none":     "Aucune compression",
    "lossless": "Compression structurelle sans perte (defaut)",
    "low":      "Compression x4 des couches denses",
    "medium":   "Compression x8, plus agressive",
    "high":     "Compression extreme",
}
COMPRESSION_DEFAULT = "lossless"

# -t / --type  (framework du modele)
MODEL_TYPE_OPTIONS = {
    "keras":  "Modele Keras (.h5, .keras)",
    "tflite": "Modele TensorFlow Lite (.tflite)",
    "onnx":   "Modele ONNX (.onnx)",
}

# Mapping extension -> type automatique
EXTENSION_TO_TYPE = {
    ".h5":    "keras",
    ".keras": "keras",
    ".tflite":"tflite",
    ".onnx":  "onnx",
    ".pb":    "keras",
}

# --input-data-type / --output-data-type
DATA_TYPE_OPTIONS = ["float32", "int8", "uint8"]

# Advanced options from ST Edge AI Core 4.0 CLI
TARGET_OPTIONS = {
    "auto": "Selection automatique (defaut)",
    "stm32": "STM32 MCU generic target",
    "stm32n6": "STM32N6 (NPU)",
}

ST_NEURAL_ART_OPTIONS = {
    "none": "Desactive (defaut)",
    "default": "Profil Neural-ART par defaut",
}

# -v / --verbosity
VERBOSITY_OPTIONS = {
    0: "Silencieux",
    1: "Normal (defaut)",
    2: "Detaille",
    3: "Debug",
}

# ---------------------------------------------------------------------------
# Metrics retournees par l'API (depuis evaluation_metrics.html)
# ---------------------------------------------------------------------------
# Champs JSON dans les resultats de validation/benchmark:
#   acc       - Accuracy (classification)
#   rmse      - Root Mean Square Error
#   mae       - Mean Absolute Error
#   l2r       - L2 relative error
#   snr       - Signal to Noise Ratio
#   nse       - Nash-Sutcliffe efficiency
#   f1_score  - F1 score
#   variance  - Variance

# ---------------------------------------------------------------------------
# Chemins projet
# ---------------------------------------------------------------------------

TOKEN_FILE  = os.path.expanduser("~/.stmai_token")
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR  = os.path.join(PROJECT_DIR, "modeles")
RESULTS_DIR = os.path.join(PROJECT_DIR, "resultats")
RESULTS_CSV = os.path.join(RESULTS_DIR, "resultats.csv")
RESULTS_DB  = os.path.join(RESULTS_DIR, "resultats.db")
LOGS_DIR    = os.path.join(RESULTS_DIR, "logs")
RUN_LOGS_JSONL = os.path.join(LOGS_DIR, "benchmarks.jsonl")
EXPORT_CSV_ON_APPEND = os.environ.get("EXPORT_CSV_ON_APPEND", "0") == "1"

# ST Edge AI Core 4.0 (version courante)
STEDGEAI_DEFAULT_VERSION = os.environ.get("STEDGEAI_VERSION", "4.0.0")

# SSL
SSL_VERIFY = os.environ.get("NO_SSL_VERIFY", "") == ""

# Formats supportes
MODEL_EXTENSIONS = {".tflite", ".h5", ".onnx", ".keras", ".pb"}

# ---------------------------------------------------------------------------
# Colonnes CSV des resultats
# ---------------------------------------------------------------------------
CSV_COLUMNS = [
    "modele",
    "dossier",
    "type_framework",
    "board",
    "optimization",
    "compression",
    "inference_time_ms",
    "ram_ko",
    "rom_ko",
    "macc",
    "params",
    "accuracy",
    "rmse",
    "mae",
    "l2r",
    "core_version",
    "target",
    "st_neural_art",
    "memory_pool",
    "split_weights",
    "allocate_activations",
    "allocate_states",
    "input_memory_alignment",
    "output_memory_alignment",
    "no_inputs_allocation",
    "no_outputs_allocation",
    "core_command",
    "run_id",
    "benchmark_id",
    "date",
    "status",
]
