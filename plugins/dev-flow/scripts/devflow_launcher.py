from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path
import zipimport


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = PLUGIN_ROOT / "scripts" / "devflow_runtime.pyz"


def install_runtime() -> zipimport.zipimporter:
    os.environ.setdefault("DEVFLOW_PLUGIN_ROOT", str(PLUGIN_ROOT))
    archive = str(ARCHIVE)
    if sys.path[:1] != [archive]:
        sys.path = [item for item in sys.path if item != archive]
        sys.path.insert(0, archive)
    return zipimport.zipimporter(archive)


def load_exports(module_name: str, target_globals: dict[str, object]) -> None:
    importer = install_runtime()
    namespace = {
        "__name__": f"_devflow_runtime_{module_name}",
        "__file__": f"{ARCHIVE}/{module_name}.py",
        "__package__": "",
        "__loader__": importer,
    }
    exec(importer.get_code(module_name), namespace)
    blocked = {"__name__", "__file__", "__package__", "__loader__", "__spec__"}
    target_globals.update({key: value for key, value in namespace.items() if key not in blocked})


def export_or_run(module_name: str, target_globals: dict[str, object], module_name_value: str) -> None:
    if module_name_value == "__main__":
        install_runtime()
        runpy.run_module(module_name, run_name="__main__")
        return
    load_exports(module_name, target_globals)
