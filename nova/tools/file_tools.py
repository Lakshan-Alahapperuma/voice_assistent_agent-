import os
import shutil
import time
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional
from nova.tools.base import BaseTool
from nova.config import USER_HOME, BACKUP_DIR, ALLOWED_PATHS, FILE_CATEGORIES

def _is_path_allowed(target_path: Path) -> bool:
    """Verifies that the target path is inside allowed user directories or temp directories."""
    resolved = target_path.resolve()
    temp_dir = Path(tempfile.gettempdir()).resolve()

    # Allowed in temp dir (useful for tests and temporary operations)
    if resolved == temp_dir or temp_dir in resolved.parents:
        return True

    # Check if resolved is within user home
    if str(resolved).startswith(str(USER_HOME.resolve())):
        return True

    for allowed in ALLOWED_PATHS:
        try:
            if resolved == allowed.resolve() or allowed.resolve() in resolved.parents:
                return True
        except Exception:
            continue
    return False

def _backup_file(file_path: Path) -> Optional[Path]:
    """Creates a timestamped backup before modifying an existing file."""
    if not file_path.exists():
        return None
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_name = f"{timestamp}_{file_path.name}"
    backup_dest = BACKUP_DIR / backup_name
    shutil.copy2(file_path, backup_dest)
    return backup_dest

class SearchFilesTool(BaseTool):
    name = "search_files"
    description = "Searches for files matching a pattern or keyword in a folder (e.g. Documents, Downloads, Desktop)."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "File name, pattern, or keyword to search for (e.g. 'report', '*.pdf', 'notes')"
            },
            "directory": {
                "type": "string",
                "description": "Directory to search in. Defaults to user's Documents or Downloads. Can be 'Documents', 'Downloads', 'Desktop', or a full path."
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (default 10)"
            }
        },
        "required": ["query"]
    }

    def execute(self, query: str, directory: Optional[str] = None, max_results: int = 10) -> Dict[str, Any]:
        if not directory or directory.lower() == "documents":
            search_dir = USER_HOME / "Documents"
        elif directory.lower() == "downloads":
            search_dir = USER_HOME / "Downloads"
        elif directory.lower() == "desktop":
            search_dir = USER_HOME / "Desktop"
        else:
            search_dir = Path(directory).expanduser()

        if not _is_path_allowed(search_dir):
            return {"error": f"Access to directory '{search_dir}' is restricted."}

        if not search_dir.exists():
            return {"error": f"Directory '{search_dir}' does not exist."}

        matches = []
        pattern = query if "*" in query else f"*{query}*"
        for p in search_dir.rglob(pattern):
            if not p.name.startswith("."):
                matches.append({
                    "name": p.name,
                    "path": str(p),
                    "size_bytes": p.stat().st_size if p.is_file() else 0,
                    "is_dir": p.is_dir()
                })
                if len(matches) >= max_results:
                    break

        return {
            "directory": str(search_dir),
            "query": query,
            "count": len(matches),
            "files": matches
        }

class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Reads the content of a text or document file."
    parameters = {
        "type": "object",
        "properties": {
            "filepath": {
                "type": "string",
                "description": "The path to the file to read."
            },
            "max_lines": {
                "type": "integer",
                "description": "Maximum number of lines to read (default 200)."
            }
        },
        "required": ["filepath"]
    }

    def execute(self, filepath: str, max_lines: int = 200) -> Dict[str, Any]:
        path = Path(filepath).expanduser().resolve()
        if not _is_path_allowed(path):
            return {"error": f"Access to '{path}' is restricted."}

        if not path.exists():
            return {"error": f"File '{path}' does not exist."}

        if path.is_dir():
            return {"error": f"'{path}' is a directory, not a file."}

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = [f.readline() for _ in range(max_lines)]
                content = "".join(lines)
                truncated = bool(f.readline())
            return {
                "path": str(path),
                "content": content,
                "lines_read": len(lines),
                "truncated": truncated
            }
        except Exception as e:
            return {"error": f"Could not read file: {str(e)}"}

class WriteFileTool(BaseTool):
    name = "write_file"
    description = "Creates or updates a file. Automatically creates a backup of existing files before overwriting."
    requires_confirmation = True
    parameters = {
        "type": "object",
        "properties": {
            "filepath": {
                "type": "string",
                "description": "The destination path of the file."
            },
            "content": {
                "type": "string",
                "description": "The text content to write."
            },
            "append": {
                "type": "boolean",
                "description": "Whether to append to the file instead of overwriting (default: false)."
            }
        },
        "required": ["filepath", "content"]
    }

    def execute(self, filepath: str, content: str, append: bool = False) -> Dict[str, Any]:
        path = Path(filepath).expanduser().resolve()
        if not _is_path_allowed(path):
            return {"error": f"Access to '{path}' is restricted."}

        backup_path = None
        if path.exists() and not append:
            backup_path = _backup_file(path)

        path.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with open(path, mode, encoding="utf-8") as f:
            f.write(content)

        return {
            "status": "success",
            "path": str(path),
            "bytes_written": len(content.encode("utf-8")),
            "backup_created": str(backup_path) if backup_path else None
        }

class OrganizeFolderTool(BaseTool):
    name = "organize_folder"
    description = "Organizes files in a folder (such as Downloads) into subcategories (Documents, Images, Audio, Video, Archives, Code) based on file type. Can run a preview (dry_run) first."
    requires_confirmation = True
    parameters = {
        "type": "object",
        "properties": {
            "folder_path": {
                "type": "string",
                "description": "The folder to organize (e.g. 'Downloads', 'Documents', or full path)."
            },
            "dry_run": {
                "type": "boolean",
                "description": "If true, previews the planned file movements without moving files. Default is true."
            }
        },
        "required": ["folder_path"]
    }

    def execute(self, folder_path: str, dry_run: bool = True) -> Dict[str, Any]:
        if folder_path.lower() == "downloads":
            target_dir = USER_HOME / "Downloads"
        elif folder_path.lower() == "documents":
            target_dir = USER_HOME / "Documents"
        elif folder_path.lower() == "desktop":
            target_dir = USER_HOME / "Desktop"
        else:
            target_dir = Path(folder_path).expanduser().resolve()

        if not _is_path_allowed(target_dir):
            return {"error": f"Access to '{target_dir}' is restricted."}

        if not target_dir.exists() or not target_dir.is_dir():
            return {"error": f"'{target_dir}' is not a valid directory."}

        planned_moves = []
        for item in target_dir.iterdir():
            if item.is_dir() or item.name.startswith("."):
                continue

            ext = item.suffix.lower()
            category = "Other"
            for cat_name, extensions in FILE_CATEGORIES.items():
                if ext in extensions:
                    category = cat_name
                    break

            destination_dir = target_dir / category
            destination_file = destination_dir / item.name
            planned_moves.append({
                "source": str(item),
                "filename": item.name,
                "category": category,
                "destination": str(destination_file)
            })

        if dry_run:
            return {
                "status": "preview",
                "total_files": len(planned_moves),
                "target_folder": str(target_dir),
                "moves": planned_moves,
                "message": f"Preview: {len(planned_moves)} files will be organized into categories. Set dry_run=false to execute."
            }

        # Execute moves
        executed_moves = []
        for move in planned_moves:
            src = Path(move["source"])
            dst = Path(move["destination"])
            dst.parent.mkdir(exist_ok=True)

            # Avoid overwrite if file exists with same name
            if dst.exists():
                dst = dst.parent / f"{src.stem}_{int(time.time())}{src.suffix}"

            shutil.move(src, dst)
            executed_moves.append({"source": str(src), "destination": str(dst), "category": move["category"]})

        return {
            "status": "success",
            "total_organized": len(executed_moves),
            "target_folder": str(target_dir),
            "moves": executed_moves
        }

class ListDirectoryTool(BaseTool):
    name = "list_directory"
    description = "Lists files and subdirectories in a directory."
    parameters = {
        "type": "object",
        "properties": {
            "directory": {
                "type": "string",
                "description": "Path of directory to list (e.g. 'Downloads', 'Documents', 'Desktop', or path)."
            }
        },
        "required": []
    }

    def execute(self, directory: Optional[str] = None) -> Dict[str, Any]:
        if not directory or directory.lower() == "documents":
            target = USER_HOME / "Documents"
        elif directory.lower() == "downloads":
            target = USER_HOME / "Downloads"
        elif directory.lower() == "desktop":
            target = USER_HOME / "Desktop"
        else:
            target = Path(directory).expanduser().resolve()

        if not _is_path_allowed(target):
            return {"error": f"Access to '{target}' is restricted."}

        if not target.exists():
            return {"error": f"Path '{target}' does not exist."}

        items = []
        for p in target.iterdir():
            if not p.name.startswith("."):
                items.append({
                    "name": p.name,
                    "is_dir": p.is_dir(),
                    "size_bytes": p.stat().st_size if p.is_file() else None
                })

        return {
            "path": str(target),
            "count": len(items),
            "items": sorted(items, key=lambda x: (not x["is_dir"], x["name"].lower()))
        }
