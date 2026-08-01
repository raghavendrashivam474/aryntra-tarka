import os
from pathlib import Path
from typing import Any, Dict
from runtime.plugins.base import PluginBase


class FilesystemPlugin(PluginBase):

    @property
    def name(self) -> str:
        return "filesystem"

    @property
    def description(self) -> str:
        return "Read files and list directories safely."

    @property
    def version(self) -> str:
        return "1.0.0"

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        action = input_data.get("action")
        path   = input_data.get("path", ".")

        if action == "list":
            return self._list_directory(path)
        elif action == "read":
            return self._read_file(path)
        else:
            return {"error": f"Unknown action: {action}"}

    def _list_directory(self, path: str) -> Dict:
        try:
            entries = os.listdir(path)
            return {"path": path, "entries": entries}
        except Exception as e:
            return {"error": str(e)}

    def _read_file(self, path: str) -> Dict:
        try:
            content = Path(path).read_text(encoding="utf-8")
            return {"path": path, "content": content}
        except Exception as e:
            return {"error": str(e)}
