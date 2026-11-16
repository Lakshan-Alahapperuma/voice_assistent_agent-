import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from nova.tools.base import BaseTool
from nova.config import ALLOWED_COMMANDS, ALLOWED_PATHS

class RunCommandTool(BaseTool):
    name = "run_command"
    description = "Executes an approved development or inspection command (e.g. 'pytest', 'git status', 'python3 -m unittest') and returns the output."
    requires_confirmation = True
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The command string to execute (e.g. 'pytest', 'git status', 'ls -la')."
            },
            "working_directory": {
                "type": "string",
                "description": "Optional working directory in which to execute the command."
            }
        },
        "required": ["command"]
    }

    def execute(self, command: str, working_directory: Optional[str] = None) -> Dict[str, Any]:
        cmd_clean = command.strip()

        # Check allowlist
        is_allowed = False
        for allowed in ALLOWED_COMMANDS:
            if cmd_clean == allowed or cmd_clean.startswith(allowed + " "):
                is_allowed = True
                break

        if not is_allowed:
            return {
                "status": "error",
                "error": f"Command '{cmd_clean}' is not in Nova's allowlist for safe execution. Allowed commands include: {', '.join(sorted(ALLOWED_COMMANDS))}"
            }

        cwd = Path(working_directory).expanduser().resolve() if working_directory else Path.cwd()

        try:
            res = subprocess.run(
                cmd_clean,
                shell=True,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=30
            )
            return {
                "status": "success",
                "command": cmd_clean,
                "exit_code": res.returncode,
                "stdout": res.stdout,
                "stderr": res.stderr
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": "Command execution timed out after 30 seconds."}
        except Exception as e:
            return {"status": "error", "error": str(e)}
