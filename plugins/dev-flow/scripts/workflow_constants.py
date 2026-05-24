from __future__ import annotations

from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
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
