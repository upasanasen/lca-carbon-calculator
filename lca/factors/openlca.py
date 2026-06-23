from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


DEFAULT_APP = Path("/Applications/openLCA.app")
DEFAULT_WORKSPACE = Path.home() / "openLCA-data-1.4"
DEFAULT_IPC_SCRIPT = DEFAULT_APP / "Contents" / "Eclipse" / "bin" / "ipc-server.sh"


@dataclass
class OpenLCAStatus:
    app_path: str
    app_found: bool
    workspace_path: str
    workspace_found: bool
    ipc_script_path: str
    ipc_script_found: bool
    database_names: List[str]


def discover_openlca() -> OpenLCAStatus:
    ignored = {".metadata", "html", "libraries", "log"}
    database_names: List[str] = []
    if DEFAULT_WORKSPACE.exists():
        for child in DEFAULT_WORKSPACE.iterdir():
            if child.is_dir() and child.name not in ignored and not child.name.startswith("."):
                database_names.append(child.name)
    return OpenLCAStatus(
        app_path=str(DEFAULT_APP),
        app_found=DEFAULT_APP.exists(),
        workspace_path=str(DEFAULT_WORKSPACE),
        workspace_found=DEFAULT_WORKSPACE.exists(),
        ipc_script_path=str(DEFAULT_IPC_SCRIPT),
        ipc_script_found=DEFAULT_IPC_SCRIPT.exists(),
        database_names=sorted(database_names),
    )


def ipc_command(database_name: str) -> List[str]:
    return [str(DEFAULT_IPC_SCRIPT), database_name]


class OpenLCAIPCClient:
    """Small JSON-RPC client for a running openLCA IPC server.

    The server is started outside this class with openLCA's bundled
    ipc-server.sh script. Database-specific model mapping still belongs in a
    real adapter once a database is available.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8080, timeout: int = 10) -> None:
        self.url = f"http://{host}:{port}"
        self.timeout = timeout
        self._request_id = 0

    def call(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or {},
        }
        response = requests.post(self.url, data=json.dumps(payload), timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise RuntimeError(data["error"])
        return data.get("result")

    def is_available(self) -> bool:
        try:
            self.call("data/get/descriptors", {"@type": "Flow"})
            return True
        except Exception:
            return False

    def descriptors(self, model_type: str) -> Any:
        return self.call("data/get/descriptors", {"@type": model_type})


def start_ipc_server(database_name: str) -> subprocess.Popen:
    command = ipc_command(database_name)
    return subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
