from nova.tools.base import BaseTool, ToolRegistry
from nova.tools.file_tools import (
    SearchFilesTool,
    ReadFileTool,
    WriteFileTool,
    OrganizeFolderTool,
    ListDirectoryTool
)
from nova.tools.mac_tools import (
    OpenAppTool,
    MacNotificationTool,
    SetVolumeTool,
    GetSystemStatusTool,
    RunAppleScriptTool
)
from nova.tools.email_tools import DraftEmailTool, SendEmailTool
from nova.tools.shell_tools import RunCommandTool

def create_default_registry() -> ToolRegistry:
    """Instantiates and registers all built-in Nova tools."""
    registry = ToolRegistry()

    # File tools
    registry.register(SearchFilesTool())
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(OrganizeFolderTool())
    registry.register(ListDirectoryTool())

    # Mac system tools
    registry.register(OpenAppTool())
    registry.register(MacNotificationTool())
    registry.register(SetVolumeTool())
    registry.register(GetSystemStatusTool())
    registry.register(RunAppleScriptTool())

    # Email tools
    registry.register(DraftEmailTool())
    registry.register(SendEmailTool())

    # Shell tools
    registry.register(RunCommandTool())

    return registry

__all__ = [
    "BaseTool",
    "ToolRegistry",
    "create_default_registry",
    "SearchFilesTool",
    "ReadFileTool",
    "WriteFileTool",
    "OrganizeFolderTool",
    "ListDirectoryTool",
    "OpenAppTool",
    "MacNotificationTool",
    "SetVolumeTool",
    "GetSystemStatusTool",
    "RunAppleScriptTool",
    "DraftEmailTool",
    "SendEmailTool",
    "RunCommandTool"
]
