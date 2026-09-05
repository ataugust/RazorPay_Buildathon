import os
from pathlib import Path

from dotenv import load_dotenv

# Absolute path resolution anchored to the backend directory
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BACKEND_DIR / ".env")
DATA_DIR = BACKEND_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_DB_FILE = DATA_DIR / "asc.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DB_FILE.as_posix()}"

def get_database_url() -> str:
    env_url = os.getenv("DATABASE_URL")
    if not env_url:
        return DEFAULT_DATABASE_URL
    
    # Handle relative sqlite URLs by anchoring them to BACKEND_DIR
    if env_url.startswith("sqlite:///") and not os.path.isabs(env_url.replace("sqlite:///", "")):
        rel_path = env_url.replace("sqlite:///", "")
        if rel_path.startswith("./"):
            rel_path = rel_path[2:]
        abs_file = (BACKEND_DIR / rel_path).resolve()
        abs_file.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{abs_file.as_posix()}"

    return env_url

DATABASE_URL = get_database_url()
