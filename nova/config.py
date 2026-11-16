import os
from pathlib import Path
from dotenv import load_dotenv

# Load local environment variables from .env if present
load_dotenv()

# Base paths
USER_HOME = Path.home()
default_nova_home = Path(os.getenv("NOVA_HOME", USER_HOME / ".nova"))

try:
    default_nova_home.mkdir(parents=True, exist_ok=True)
    test_file = default_nova_home / ".write_test"
    test_file.touch()
    test_file.unlink(missing_ok=True)
    NOVA_HOME = default_nova_home
except (PermissionError, OSError):
    # Fallback to project directory if user home is restricted
    NOVA_HOME = Path.cwd() / ".nova"
    NOVA_HOME.mkdir(parents=True, exist_ok=True)

BACKUP_DIR = NOVA_HOME / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = NOVA_HOME / "memory.db"

# LLM Configuration
MODEL_NAME = os.getenv("NOVA_MODEL", "qwen2.5:3b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")

# Voice Configuration (macOS native say)
NOVA_VOICE = os.getenv("NOVA_VOICE", "Samantha")
NOVA_SPEECH_RATE = int(os.getenv("NOVA_SPEECH_RATE", "190"))

# Safety & Permissions
AUTO_CONFIRM_SAFE = os.getenv("NOVA_AUTO_CONFIRM_SAFE", "True").lower() in ("true", "1", "yes")

# Allowed root paths for file operations (prevents escaping into system files)
ALLOWED_PATHS = [
    USER_HOME / "Desktop",
    USER_HOME / "Documents",
    USER_HOME / "Downloads",
    Path.cwd(),
]
custom_allowed = os.getenv("NOVA_ALLOWED_PATHS")
if custom_allowed:
    ALLOWED_PATHS.extend([Path(p.strip()).expanduser() for p in custom_allowed.split(",") if p.strip()])

# Safe commands for shell execution
ALLOWED_COMMANDS = {
    "git status", "git diff", "git log -n 5",
    "pytest", "python3 -m unittest",
    "ls -la", "ls", "pwd", "date", "uptime", "sw_vers",
}

# Categorization mapping for folder organization
FILE_CATEGORIES = {
    "Documents": [".pdf", ".docx", ".doc", ".txt", ".rtf", ".odt", ".pptx", ".xlsx", ".csv", ".pages", ".key", ".numbers"],
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".heic", ".tiff"],
    "Audio": [".mp3", ".wav", ".aac", ".flac", ".m4a", ".ogg"],
    "Video": [".mp4", ".mov", ".avi", ".mkv", ".wmv"],
    "Archives": [".zip", ".tar", ".gz", ".tar.gz", ".rar", ".7z", ".dmg"],
    "Code": [".py", ".js", ".ts", ".html", ".css", ".json", ".yaml", ".yml", ".sh", ".c", ".cpp", ".swift", ".rs"],
}
