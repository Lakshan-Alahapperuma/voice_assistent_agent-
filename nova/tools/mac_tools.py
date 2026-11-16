import subprocess
import shutil
from typing import Dict, Any, Optional
from nova.tools.base import BaseTool

class OpenAppTool(BaseTool):
    name = "open_app"
    description = "Opens a macOS application (e.g. Safari, Notes, VS Code, Music, Terminal, Slack)."
    parameters = {
        "type": "object",
        "properties": {
            "app_name": {
                "type": "string",
                "description": "Name of the application to open (e.g. 'Safari', 'Notes', 'Visual Studio Code', 'Spotify', 'Finder')."
            }
        },
        "required": ["app_name"]
    }

    def execute(self, app_name: str) -> Dict[str, Any]:
        # Clean app name
        clean_name = app_name.strip()
        cmd = ["open", "-a", clean_name]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if res.returncode == 0:
                return {"status": "success", "message": f"Successfully opened {clean_name}."}
            else:
                return {"status": "error", "message": f"Could not open application '{clean_name}': {res.stderr.strip()}"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to open app: {str(e)}"}

class MacNotificationTool(BaseTool):
    name = "mac_notification"
    description = "Displays a native macOS banner notification."
    parameters = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "The title of the notification (e.g. 'Nova Assistant')."
            },
            "message": {
                "type": "string",
                "description": "The message body of the notification."
            }
        },
        "required": ["message"]
    }

    def execute(self, message: str, title: str = "Nova") -> Dict[str, Any]:
        clean_msg = message.replace('"', '\\"')
        clean_title = title.replace('"', '\\"')
        script = f'display notification "{clean_msg}" with title "{clean_title}"'
        try:
            subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
            return {"status": "success", "message": "Notification posted."}
        except Exception as e:
            return {"status": "error", "message": f"Failed to show notification: {str(e)}"}

class SetVolumeTool(BaseTool):
    name = "set_volume"
    description = "Sets the macOS output volume level between 0 and 100."
    parameters = {
        "type": "object",
        "properties": {
            "level": {
                "type": "integer",
                "description": "Volume percentage from 0 (mute) to 100 (max)."
            }
        },
        "required": ["level"]
    }

    def execute(self, level: int) -> Dict[str, Any]:
        level = max(0, min(100, int(level)))
        script = f"set volume output volume {level}"
        try:
            subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
            return {"status": "success", "level": level, "message": f"Volume set to {level}%."}
        except Exception as e:
            return {"status": "error", "message": f"Failed to set volume: {str(e)}"}

class GetSystemStatusTool(BaseTool):
    name = "get_system_status"
    description = "Retrieves macOS system status including disk space, battery level, uptime, and macOS version."
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }

    def execute(self) -> Dict[str, Any]:
        status = {}

        # Disk space
        total, used, free = shutil.disk_usage("/")
        status["disk"] = {
            "total_gb": round(total / (2**30), 1),
            "free_gb": round(free / (2**30), 1),
            "used_percent": round((used / total) * 100, 1)
        }

        # Battery info
        try:
            batt = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True, check=False)
            if batt.returncode == 0:
                lines = batt.stdout.strip().split("\n")
                if len(lines) > 1:
                    status["battery"] = lines[1].strip()
        except Exception:
            status["battery"] = "Unknown"

        # macOS Version
        try:
            sw = subprocess.run(["sw_vers", "-productVersion"], capture_output=True, text=True, check=False)
            status["macos_version"] = sw.stdout.strip()
        except Exception:
            status["macos_version"] = "macOS"

        # Uptime
        try:
            up = subprocess.run(["uptime"], capture_output=True, text=True, check=False)
            status["uptime"] = up.stdout.strip()
        except Exception:
            pass

        return status

class RunAppleScriptTool(BaseTool):
    name = "run_applescript"
    description = "Executes an AppleScript script on macOS for application automation."
    requires_confirmation = True
    parameters = {
        "type": "object",
        "properties": {
            "script": {
                "type": "string",
                "description": "The AppleScript code to run."
            }
        },
        "required": ["script"]
    }

    def execute(self, script: str) -> Dict[str, Any]:
        try:
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=False)
            if res.returncode == 0:
                return {"status": "success", "output": res.stdout.strip()}
            else:
                return {"status": "error", "error": res.stderr.strip()}
        except Exception as e:
            return {"status": "error", "message": f"AppleScript execution error: {str(e)}"}
