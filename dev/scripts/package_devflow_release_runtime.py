#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
import hashlib
import json
import re
import stat
import subprocess
import zipfile


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_SCRIPTS = REPO_ROOT / "dev" / "plugins" / "dev-flow" / "scripts"
RELEASE_SCRIPTS = REPO_ROOT / "plugins" / "dev-flow" / "scripts"
ARCHIVE_NAME = "devflow_runtime.pyz"
MANIFEST_NAME = "devflow_runtime.MANIFEST.json"
SHA256_NAME = "devflow_runtime.sha256"
SOURCE_COMMIT_NAME = "devflow_runtime.SOURCE_COMMIT"
BUILD_COMMAND = ["python3", "dev/scripts/package_devflow_release_runtime.py"]
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
            package.writestr(info, source.read_bytes())
    return archive


def write_audit_artifacts(sources: list[Path], archive: Path) -> None:
    archive_sha = file_sha256(archive)
    source_commit = git_source_commit()
    manifest = {
        "schemaVersion": 1,
        "sourceCommit": source_commit,
        "buildCommand": BUILD_COMMAND,
        "archive": {
            "path": release_relative_path(archive),
            "sha256": archive_sha,
            "bytes": archive.stat().st_size,
        },
        "sources": [source_record(source) for source in sources],
    }
    (RELEASE_SCRIPTS / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (RELEASE_SCRIPTS / SHA256_NAME).write_text(f"{archive_sha}  {release_relative_path(archive)}\n")
    (RELEASE_SCRIPTS / SOURCE_COMMIT_NAME).write_text(f"{source_commit}\n")


def source_record(source: Path) -> dict[str, object]:
    return {
        "path": repo_relative_path(source),
        "sha256": file_sha256(source),
        "bytes": source.stat().st_size,
    }


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_source_commit() -> str:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return "unknown"


def repo_relative_path(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def release_relative_path(path: Path) -> str:
    return path.resolve().relative_to(RELEASE_SCRIPTS.parent.resolve()).as_posix()


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
    archive = write_archive(sources)
    write_audit_artifacts(sources, archive)
    write_wrappers(sources)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
