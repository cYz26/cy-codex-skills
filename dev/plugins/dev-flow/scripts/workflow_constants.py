from __future__ import annotations

import os
from pathlib import Path


def resolve_plugin_root(fallback_file: str = __file__) -> Path:
    configured = os.environ.get("DEVFLOW_PLUGIN_ROOT") or os.environ.get("PLUGIN_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(fallback_file).resolve().parents[1]


PLUGIN_ROOT = resolve_plugin_root()
TEMPLATE_ROOT = PLUGIN_ROOT / "assets" / "templates"

CODE_EXTENSIONS = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".html",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".mjs",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".scss",
    ".swift",
    ".ts",
    ".tsx",
    ".vue",
}

SOURCE_DIRS = ("src", "app", "lib", "packages", "apps", "server", "client")
TEST_DIRS = ("test", "tests", "__tests__", "spec", "specs")
BUILD_FILES = (
    "package.json",
    "pyproject.toml",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "Makefile",
    "vite.config.js",
    "next.config.js",
    "tsconfig.json",
)
