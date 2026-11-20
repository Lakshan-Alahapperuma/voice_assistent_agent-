import os
import plistlib
import subprocess
from pathlib import Path
from typing import Dict, Any

PLIST_NAME = "com.nova.assistant.plist"
LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
PLIST_PATH = LAUNCH_AGENTS_DIR / PLIST_NAME

def get_service_paths() -> Dict[str, Path]:
    project_root = Path(__file__).resolve().parent.parent.parent
    venv_python = project_root / ".venv" / "bin" / "python3"
    main_py = project_root / "main.py"
    log_dir = Path.home() / ".nova"
    log_dir.mkdir(parents=True, exist_ok=True)
    return {
        "python": venv_python,
        "main": main_py,
        "stdout": log_dir / "service_stdout.log",
        "stderr": log_dir / "service_stderr.log",
    }

def is_service_installed() -> bool:
    return PLIST_PATH.exists()

def is_service_running() -> bool:
    try:
        res = subprocess.run(["launchctl", "list", "com.nova.assistant"], capture_output=True, text=True, check=False)
        return res.returncode == 0
    except Exception:
        return False

def install_launch_agent() -> Dict[str, Any]:
    paths = get_service_paths()
    LAUNCH_AGENTS_DIR.mkdir(parents=True, exist_ok=True)

    plist_data = {
        "Label": "com.nova.assistant",
        "ProgramArguments": [
            str(paths["python"]),
            str(paths["main"]),
            "--menubar"
        ],
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(paths["stdout"]),
        "StandardErrorPath": str(paths["stderr"]),
        "WorkingDirectory": str(paths["main"].parent),
        "EnvironmentVariables": {
            "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
        }
    }

    with open(PLIST_PATH, "wb") as f:
        plistlib.dump(plist_data, f)

    # Load into launchd
    try:
        subprocess.run(["launchctl", "unload", str(PLIST_PATH)], capture_output=True, check=False)
        subprocess.run(["launchctl", "load", str(PLIST_PATH)], capture_output=True, check=True)
        return {"status": "success", "message": "Nova background service installed and started."}
    except Exception as e:
        return {"status": "error", "message": f"Service installed but failed to load: {str(e)}"}

def uninstall_launch_agent() -> Dict[str, Any]:
    if not PLIST_PATH.exists():
        return {"status": "success", "message": "Service is not installed."}

    try:
        subprocess.run(["launchctl", "unload", str(PLIST_PATH)], capture_output=True, check=False)
    except Exception:
        pass

    try:
        PLIST_PATH.unlink(missing_ok=True)
        return {"status": "success", "message": "Nova background service uninstalled."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
