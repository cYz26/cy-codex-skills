#!/usr/bin/env python3
import hashlib
import json
import sys
from pathlib import Path


TYPE_CHECKS = {
    "array": list,
    "object": dict,
    "string": str,
}


def load_json(path):
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"invalid benchmark evidence {path}: {exc}")
    if not isinstance(payload, dict):
        raise SystemExit(f"benchmark evidence must be an object: {path}")
    return payload


root = Path.cwd()
result = load_json(root / ".benchmark" / "result.json")
task_output = load_json(root / ".benchmark" / "task-output.json")
route = load_json(root / ".benchmark" / "route-evidence.json")
config = load_json(root / ".dev-flow.json")
provider_lock = load_json(root / ".planning" / "devflow" / "providers.lock.json")
task_inputs = load_json(root / "benchmark-inputs" / "tasks.json").get("tasks", {})
output_schemas = load_json(root / "benchmark-inputs" / "output-schema.json").get("tasks", {})
errors = []
task_id = result.get("task_id")
if task_id not in task_inputs or task_id not in output_schemas:
    errors.append("result.task_id has no seeded task input and visible output schema")
if result.get("status") != "completed":
    errors.append("result.status must be completed")
schema = output_schemas.get(task_id, {})
required_keys = set(schema.get("requiredKeys", ()))
if set(task_output) != required_keys:
    errors.append("task-output keys do not exactly match the visible task schema")
if task_output.get("task_id") != task_id:
    errors.append("task-output.task_id does not match result.task_id")
for key, type_name in schema.get("types", {}).items():
    expected_type = TYPE_CHECKS.get(type_name)
    if expected_type is None or not isinstance(task_output.get(key), expected_type):
        errors.append(f"task-output.{key} does not match visible type {type_name}")
artifact_path = schema.get("artifactPath")
artifact_paths = [artifact_path, *schema.get("additionalArtifactPaths", ())]
for path in artifact_paths:
    if not isinstance(path, str) or Path(path).is_absolute() or ".." in Path(path).parts:
        errors.append("visible task schema has an unsafe canonical artifact path")
    elif not (root / path).is_file():
        errors.append(f"required canonical task artifact is missing: {path}")

selected_profile = config.get("workflow", {}).get("methodology_profile")
provider_id = {
    "lean-matt": "mattpocock-skills",
    "strict-superpowers": "superpowers",
}.get(selected_profile)
provider_record = provider_lock.get("providers", {}).get(provider_id, {})
provider_digest = hashlib.sha256(
    json.dumps(provider_record, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()
if route.get("selected_profile") != selected_profile:
    errors.append("route.selected_profile does not match project selection")
if route.get("provider_invoked") is not True:
    errors.append("selected provider was installed but not actually routed")
for key in ("capability", "provider_sha256", "invoked_skills", "skill_sha256"):
    if not route.get(key):
        errors.append(f"route.{key} is missing")
if isinstance(route.get("invoked_skills"), list) and isinstance(route.get("skill_sha256"), dict):
    if set(route["invoked_skills"]) != set(route["skill_sha256"]):
        errors.append("route skill hashes do not match exactly the invoked skills")
    expected_skill_hashes = {}
    for name in route["invoked_skills"]:
        skill_path = root / ".agents" / "skills" / name / "SKILL.md"
        expected_skill_hashes[name] = (
            hashlib.sha256(skill_path.read_bytes()).hexdigest() if skill_path.is_file() else None
        )
    if None in expected_skill_hashes.values() or route["skill_sha256"] != expected_skill_hashes:
        errors.append("route skill hash does not match the pinned fixture skill")
if route.get("provider_sha256") != provider_digest:
    errors.append("route provider hash does not match the pinned provider lock")

plugin_scripts = root / "plugins" / "dev-flow" / "scripts"
if plugin_scripts.is_dir():
    sys.path.insert(0, str(plugin_scripts))
    try:
        import workflow_provider_profiles as providers

        codex_home = root / "codex-home"
        selection = providers.resolve_provider_selection(root, codex_home, {})
        diagnosis = providers.diagnose_provider_selection(selection, root, codex_home)
        if not diagnosis.get("methodologyReady"):
            errors.append("production provider facade cannot resolve the pinned methodology provider")
    except (ImportError, OSError, ValueError) as exc:
        errors.append(f"production provider facade failed: {exc}")
if errors:
    print("\n".join(errors), file=sys.stderr)
    raise SystemExit(1)
print("provider benchmark structure and provider facade verified")
