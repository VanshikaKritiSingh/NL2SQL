# config.py - NL2SQL Backend Configuration

CORS_ORIGINS = [
    "http://localhost:5173",  # Vite dev server
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://localhost:3080",  # DSH GUI
    "http://127.0.0.1:3080",
]

APP_TITLE = "NL2SQL Pipeline API"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = "FastAPI backend bridge for NL2SQL Pipeline GUI (Modules 1 & 14)"
