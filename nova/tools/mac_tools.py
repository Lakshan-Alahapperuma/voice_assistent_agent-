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

class OpenUrlTool(BaseTool):
    name = "open_url"
    description = "Opens a specific website URL in the browser (e.g. 'https://youtube.com', 'https://github.com')."
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to open (e.g. 'https://youtube.com', 'https://google.com')."
            },
            "browser": {
                "type": "string",
                "description": "Optional browser name (e.g. 'Safari', 'Google Chrome'). Defaults to default browser."
            }
        },
        "required": ["url"]
    }

    def execute(self, url: str, browser: Optional[str] = None) -> Dict[str, Any]:
        target_url = url.strip()
        if not target_url.startswith(("http://", "https://")):
            target_url = f"https://{target_url}"

        cmd = ["open"]
        if browser:
            cmd.extend(["-a", browser])
        cmd.append(target_url)

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if res.returncode == 0:
                return {"status": "success", "message": f"Opened {target_url}."}
            return {"status": "error", "message": res.stderr.strip()}
        except Exception as e:
            return {"status": "error", "message": str(e)}

class SearchWebTool(BaseTool):
    name = "search_web"
    description = "Searches Google or YouTube and opens the results directly in the user's browser."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query (e.g. 'Python tutorials', 'latest tech news')."
            },
            "engine": {
                "type": "string",
                "description": "Search destination: 'google' or 'youtube'. Defaults to 'google'."
            }
        },
        "required": ["query"]
    }

    def execute(self, query: str, engine: str = "google") -> Dict[str, Any]:
        import urllib.parse
        encoded = urllib.parse.quote_plus(query.strip())

        if engine.lower() == "youtube":
            target_url = f"https://www.youtube.com/results?search_query={encoded}"
        else:
            target_url = f"https://www.google.com/search?q={encoded}"

        try:
            subprocess.run(["open", target_url], check=False)
            return {"status": "success", "message": f"Searching {engine} for '{query}'."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

class PlayMusicTool(BaseTool):
    name = "play_music"
    description = "Searches and plays music, songs, or videos on YouTube, Spotify, or Apple Music."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Song name, artist, playlist, or genre (e.g. 'lofi hip hop', 'jazz music', 'Coldplay')."
            },
            "platform": {
                "type": "string",
                "description": "Music platform to use: 'youtube', 'spotify', or 'apple_music'. Defaults to 'youtube'."
            }
        },
        "required": ["query"]
    }

    def execute(self, query: str, platform: str = "youtube") -> Dict[str, Any]:
        import urllib.parse
        clean_query = query.strip()
        encoded = urllib.parse.quote_plus(clean_query)
        plat = platform.lower().strip()

        if plat == "spotify":
            # Open Spotify search or URI
            try:
                subprocess.run(["open", f"spotify:search:{encoded}"], check=False)
                # Tell Spotify to play if running
                script = 'tell application "Spotify" to play'
                subprocess.run(["osascript", "-e", script], check=False, capture_output=True)
                return {"status": "success", "message": f"Playing '{clean_query}' on Spotify."}
            except Exception:
                # Fallback to web player
                subprocess.run(["open", f"https://open.spotify.com/search/{encoded}"], check=False)
                return {"status": "success", "message": f"Opened Spotify for '{clean_query}'."}

        elif plat in ("apple_music", "music"):
            # Control macOS Music.app
            script = f'''
            tell application "Music"
                activate
                set sound volume to 75
                play
            end tell
            '''
            try:
                subprocess.run(["osascript", "-e", script], check=False, capture_output=True)
                return {"status": "success", "message": f"Opened Apple Music."}
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            # Default to YouTube
            target_url = f"https://www.youtube.com/results?search_query={encoded}"
            try:
                # Open YouTube search in Safari or default browser
                subprocess.run(["open", target_url], check=False)
                return {
                    "status": "success",
                    "platform": "YouTube",
                    "query": clean_query,
                    "message": f"Opened YouTube and searched for '{clean_query}'."
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

class MediaControlTool(BaseTool):
    name = "media_control"
    description = "Controls playback for currently playing media (play, pause, next track, previous track)."
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "Action to perform: 'play', 'pause', 'toggle', 'next', 'previous'."
            }
        },
        "required": ["action"]
    }

    def execute(self, action: str) -> Dict[str, Any]:
        act = action.lower().strip()

        # Try Spotify first, then Music.app
        script = f'''
        if application "Spotify" is running then
            tell application "Spotify"
                if "{act}" is in {{"play", "pause", "toggle"}} then
                    playpause
                else if "{act}" is "next" then
                    next track
                else if "{act}" is "previous" then
                    previous track
                end if
            end tell
        else if application "Music" is running then
            tell application "Music"
                if "{act}" is in {{"play", "pause", "toggle"}} then
                    playpause
                else if "{act}" is "next" then
                    next track
                else if "{act}" is "previous" then
                    previous track
                end if
            end tell
        end if
        '''
        try:
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=False)
            return {"status": "success", "message": f"Media control '{act}' executed."}
        except Exception as e:
            return {"status": "error", "message": str(e)}
