#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
import re
import stat
import zipfile


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_SCRIPTS = REPO_ROOT / "dev" / "plugins" / "dev-flow" / "scripts"
RELEASE_SCRIPTS = REPO_ROOT / "plugins" / "dev-flow" / "scripts"
ARCHIVE_NAME = "devflow_runtime.pyz"
ENTRYPOINT_SCAN_ROOTS = (
    REPO_ROOT / "plugins" / "dev-flow" / "hooks.json",
    REPO_ROOT / "plugins" / "dev-flow" / "README.md",
    REPO_ROOT / "plugins" / "dev-flow" / "skills",
)


LAUNCHER = """from __future__ import annotations

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
"""


WRAPPER_TEMPLATE = """#!/usr/bin/env python3
from __future__ import annotations

from devflow_launcher import export_or_run

export_or_run({module_name!r}, globals(), __name__)
"""


def iter_source_scripts() -> list[Path]:
    return sorted(SOURCE_SCRIPTS.glob("*.py"))


def referenced_entrypoint_names() -> set[str]:
    names: set[str] = set()
    for root in ENTRYPOINT_SCAN_ROOTS:
        paths = [root] if root.is_file() else sorted(root.rglob("*.md"))
        for path in paths:
            names.update(re.findall(r"[A-Za-z0-9_]+\.py", path.read_text()))
    return names


def write_archive(sources: list[Path]) -> Path:
    RELEASE_SCRIPTS.mkdir(parents=True, exist_ok=True)
    archive = RELEASE_SCRIPTS / ARCHIVE_NAME
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as package:
        for source in sources:
            info = zipfile.ZipInfo(source.name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (source.stat().st_mode & 0o777) << 16
            package.writestr(info, source.read_text())
    return archive


def write_wrappers(sources: list[Path]) -> None:
    (RELEASE_SCRIPTS / "devflow_launcher.py").write_text(LAUNCHER)
    entrypoint_names = referenced_entrypoint_names()
    entrypoints = [
        source
        for source in sources
        if source.name in entrypoint_names or stat.S_IMODE(source.stat().st_mode) & stat.S_IXUSR
    ]
    keep = {source.name for source in entrypoints} | {"devflow_launcher.py"}
    for target in RELEASE_SCRIPTS.glob("*.py"):
        if target.name not in keep:
            target.unlink()
    for source in entrypoints:
        target = RELEASE_SCRIPTS / source.name
        target.write_text(WRAPPER_TEMPLATE.format(module_name=source.stem))
        os.chmod(target, stat.S_IMODE(source.stat().st_mode))


def main() -> int:
    sources = iter_source_scripts()
    write_archive(sources)
    write_wrappers(sources)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
