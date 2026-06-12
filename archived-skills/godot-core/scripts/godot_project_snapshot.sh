#!/usr/bin/env bash

set -euo pipefail

target_dir="${1:-.}"

if [[ ! -d "$target_dir" ]]; then
  echo "ERROR: directory does not exist: $target_dir" >&2
  exit 1
fi

target_dir="$(cd "$target_dir" && pwd)"
project_file="$target_dir/project.godot"

if [[ ! -f "$project_file" ]]; then
  echo "ERROR: project.godot not found in: $target_dir" >&2
  exit 2
fi

search_file() {
  local pattern="$1"
  local file="$2"

  if command -v rg >/dev/null 2>&1; then
    rg -n "$pattern" "$file" || true
  else
    grep -nE "$pattern" "$file" || true
  fi
}

extract_section() {
  local file="$1"
  local section="$2"

  awk -v section="$section" '
    $0 == "[" section "]" {in_section=1; next}
    in_section && /^\[.*\]$/ {exit}
    in_section && NF {print}
  ' "$file"
}

count_files() {
  local glob="$1"
  find "$target_dir" -type f -name "$glob" 2>/dev/null | wc -l | tr -d ' '
}

has_make_target() {
  local target="$1"
  local makefile="$2"

  if command -v rg >/dev/null 2>&1; then
    rg -q "^${target}:" "$makefile"
  else
    grep -qE "^${target}:" "$makefile"
  fi
}

echo "== Project =="
echo "root: $target_dir"
echo

echo "== Core Settings =="
search_file '^(config/name|config/features|run/main_scene|application/config/version)=' "$project_file"
echo

echo "== Autoloads =="
autoload_lines="$(extract_section "$project_file" "autoload")"
if [[ -n "${autoload_lines}" ]]; then
  echo "$autoload_lines"
else
  echo "(none)"
fi
echo

echo "== Input Actions (first 40 lines) =="
input_lines="$(extract_section "$project_file" "input" | sed -n '1,40p')"
if [[ -n "${input_lines}" ]]; then
  echo "$input_lines"
else
  echo "(none)"
fi
echo

echo "== File Counts =="
echo "*.tscn: $(count_files '*.tscn')"
echo "*.gd:   $(count_files '*.gd')"
echo "*.cs:   $(count_files '*.cs')"
echo "*.tres: $(count_files '*.tres')"
echo

echo "== Addons =="
if [[ -d "$target_dir/addons" ]]; then
  find "$target_dir/addons" -mindepth 1 -maxdepth 2 -type d | sed "s|$target_dir/||" | sort
else
  echo "(none)"
fi
echo

echo "== C# Project Files =="
csproj_list="$(find "$target_dir" -maxdepth 2 -type f \( -name '*.sln' -o -name '*.csproj' \) 2>/dev/null | sed "s|$target_dir/||")"
if [[ -n "${csproj_list}" ]]; then
  echo "$csproj_list"
else
  echo "(none)"
fi
echo

echo "== Export Presets =="
if [[ -f "$target_dir/export_presets.cfg" ]]; then
  search_file '^\[preset\.[0-9]+\]|^name=' "$target_dir/export_presets.cfg"
else
  echo "(export_presets.cfg not found)"
fi
echo

echo "== Quality Gates =="
if [[ -f "$target_dir/Makefile" ]]; then
  for target in fmt lint test smoke export-web web-smoke; do
    if has_make_target "$target" "$target_dir/Makefile"; then
      echo "${target}: yes"
    else
      echo "${target}: no"
    fi
  done
else
  echo "Makefile: missing"
fi
if [[ -f "$target_dir/.pre-commit-config.yaml" ]]; then
  echo "pre-commit: yes"
else
  echo "pre-commit: no"
fi
echo

echo "== Constraints and Tests =="
if [[ -f "$target_dir/docs/constraints.md" ]]; then
  echo "docs/constraints.md: yes"
else
  echo "docs/constraints.md: no"
fi
if [[ -d "$target_dir/tests" ]]; then
  echo "tests/: yes"
else
  echo "tests/: no"
fi
if [[ -f "$target_dir/tools/smoke_test_runner.gd" ]]; then
  echo "tools/smoke_test_runner.gd: yes"
else
  echo "tools/smoke_test_runner.gd: no"
fi
echo

echo "== Top-Level Directories (depth <= 2) =="
find "$target_dir" -maxdepth 2 -type d ! -path '*/.*' | sed "s|$target_dir/||; s|^$target_dir$|.|" | sort
