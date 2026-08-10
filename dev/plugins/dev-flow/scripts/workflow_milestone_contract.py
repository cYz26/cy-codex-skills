from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import re
from typing import Any


CONTRACT_SCHEMA_VERSION = "1.0"
EXPECTED_REQUESTED_EFFECTS = (
    "git.commit",
    "git.push",
    "git.tag.push",
    "github.release",
    "devflow.source.fast_forward",
    "codex.cache.refresh",
    "devflow.project.refresh",
)
EFFECT_ALIASES = {
    "release.publish": "github.release",
    "devflow.source.fast_forward_named": "devflow.source.fast_forward",
    "plugin.cache.refresh_named": "codex.cache.refresh",
    "devflow.project.refresh_named": "devflow.project.refresh",
}
SUPPORTED_EFFECTS = frozenset(
    {"release.promote_local", *EXPECTED_REQUESTED_EFFECTS, *EFFECT_ALIASES}
)
REQUIRED_EXCLUSIONS = (
    "archive",
    "force-push",
    "game-dev-plugins",
    "merge",
    "pr",
    "rebase",
    "unnamed-consumer",
    "unnamed-plugin",
    "unrelated-release",
)
EXPECTED_FAILURE_POLICY: dict[str, object] = {
    "preserveCommit": True,
    "preserveTag": True,
    "maxDiagnoses": 1,
    "maxRemediations": 1,
    "allowAlternatePublication": False,
}
EXPECTED_REENTRY_POLICY: dict[str, object] = {
    "sameIdentityOnly": True,
    "resume": "first_incomplete_step",
    "duplicateEffects": False,
}

_ROOT_KEYS = frozenset(
    {
        "schemaVersion",
        "contractId",
        "goalId",
        "goal",
        "change",
        "milestone",
        "plugin",
        "repository",
        "commit",
        "publication",
        "requestedEffects",
        "writeSet",
        "refreshTargets",
        "failurePolicy",
        "reentryPolicy",
        "exclusions",
    }
)
_PLUGIN_KEYS = frozenset({"id", "marketplace", "versionRule", "version"})
_REPOSITORY_KEYS = frozenset({"remote", "remoteUrl", "ref", "expectedBase"})
_COMMIT_KEYS = frozenset({"message"})
_PUBLICATION_KEYS = frozenset(
    {"tag", "channel", "mechanism", "workflow", "assets", "assetExpectation"}
)
_REF_COMPONENT = re.compile(r"[A-Za-z0-9._/-]+")
_IDENTIFIER = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?")
_SEMVER = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?")


def validate_milestone_contract(
    contract: Mapping[str, Any],
    *,
    project_target_available: bool,
) -> dict[str, Any]:
    """Purely validate one contract and caller-observed project-target evidence.

    The caller owns the read-only filesystem observation. Passing that boolean
    keeps this seam deterministic and lets the standing resolver and milestone
    executor share exactly the same document and evidence classification.
    """

    if not isinstance(contract, Mapping):
        return _invalid_contract(
            "STANDING_CONTRACT_IDENTITY_INVALID",
            "contract.document",
        )

    requested_effects = contract.get("requestedEffects")
    if requested_effects != list(EXPECTED_REQUESTED_EFFECTS):
        return _invalid_contract(
            "REQUESTED_EFFECTS_INVALID",
            "contract.requestedEffects",
        )

    invalidations: list[str] = []
    _require_exact_keys(contract, _ROOT_KEYS, "contract", invalidations)
    if contract.get("schemaVersion") != CONTRACT_SCHEMA_VERSION:
        invalidations.append("contract.schemaVersion")

    for field in ("contractId", "goalId", "goal", "change", "milestone"):
        if not _non_empty_string(contract.get(field)):
            invalidations.append(f"contract.{field}")

    plugin = _mapping_field(contract, "plugin", "contract.plugin", invalidations)
    if plugin is not None:
        _require_exact_keys(plugin, _PLUGIN_KEYS, "contract.plugin", invalidations)
        for field in _PLUGIN_KEYS:
            if not _non_empty_string(plugin.get(field)):
                invalidations.append(f"contract.plugin.{field}")
        for field in ("id", "marketplace", "versionRule"):
            if _non_empty_string(plugin.get(field)) and not _IDENTIFIER.fullmatch(
                str(plugin[field])
            ):
                invalidations.append(f"contract.plugin.{field}")
        if _non_empty_string(plugin.get("version")) and not _SEMVER.fullmatch(
            str(plugin["version"])
        ):
            invalidations.append("contract.plugin.version")

    repository = _mapping_field(
        contract,
        "repository",
        "contract.repository",
        invalidations,
    )
    if repository is not None:
        _require_exact_keys(
            repository,
            _REPOSITORY_KEYS,
            "contract.repository",
            invalidations,
        )
        remote = repository.get("remote")
        if not _non_empty_string(remote) or not _IDENTIFIER.fullmatch(str(remote or "")):
            invalidations.append("contract.repository.remote")
        if not _valid_remote_url(repository.get("remoteUrl")):
            invalidations.append("contract.repository.remoteUrl")
        if not _valid_head_ref(repository.get("ref")):
            invalidations.append("contract.repository.ref")
        if not _sha1_string(repository.get("expectedBase")):
            invalidations.append("contract.repository.expectedBase")

    commit = _mapping_field(contract, "commit", "contract.commit", invalidations)
    if commit is not None:
        _require_exact_keys(commit, _COMMIT_KEYS, "contract.commit", invalidations)
        if not _non_empty_string(commit.get("message")):
            invalidations.append("contract.commit.message")

    publication = _mapping_field(
        contract,
        "publication",
        "contract.publication",
        invalidations,
    )
    if publication is not None:
        _require_exact_keys(
            publication,
            _PUBLICATION_KEYS,
            "contract.publication",
            invalidations,
        )
        if not _valid_ref_name(publication.get("tag")):
            invalidations.append("contract.publication.tag")
        if not _non_empty_string(publication.get("channel")):
            invalidations.append("contract.publication.channel")
        if publication.get("mechanism") != "github_actions":
            invalidations.append("contract.publication.mechanism")
        workflow = publication.get("workflow")
        if not _safe_relative_path(workflow) or not str(workflow).startswith(
            ".github/workflows/"
        ) or Path(str(workflow)).suffix not in {".yml", ".yaml"}:
            invalidations.append("contract.publication.workflow")
        if not _valid_asset_names(publication.get("assets")):
            invalidations.append("contract.publication.assets")
        asset_expectation = publication.get("assetExpectation")
        if not _safe_relative_path(asset_expectation):
            invalidations.append("contract.publication.assetExpectation")
        write_set = contract.get("writeSet")
        if _safe_relative_path(asset_expectation) and (
            not isinstance(write_set, list) or asset_expectation not in write_set
        ):
            invalidations.append("contract.publication.assetExpectation:writeSet")

    if not _valid_write_set(contract.get("writeSet")):
        invalidations.append("contract.writeSet")

    refresh = _mapping_field(
        contract,
        "refreshTargets",
        "contract.refreshTargets",
        invalidations,
    )
    if refresh is not None:
        _require_exact_keys(
            refresh,
            frozenset({"cache", "project"}),
            "contract.refreshTargets",
            invalidations,
        )
        cache = refresh.get("cache")
        expected_cache = None
        if plugin is not None:
            expected_cache = f"{plugin.get('id')}@{plugin.get('marketplace')}"
        if not _non_empty_string(cache) or cache != expected_cache:
            invalidations.append("contract.refreshTargets.cache")
        if not _absolute_project_path(refresh.get("project")):
            invalidations.append("contract.refreshTargets.project")

    _validate_exact_policy(
        contract.get("failurePolicy"),
        EXPECTED_FAILURE_POLICY,
        "contract.failurePolicy",
        invalidations,
    )
    _validate_exact_policy(
        contract.get("reentryPolicy"),
        EXPECTED_REENTRY_POLICY,
        "contract.reentryPolicy",
        invalidations,
    )
    exclusions = contract.get("exclusions")
    if exclusions != list(REQUIRED_EXCLUSIONS):
        invalidations.append("contract.exclusions")
        if isinstance(exclusions, list):
            invalidations.extend(
                f"contract.exclusions:{item}"
                for item in REQUIRED_EXCLUSIONS
                if item not in exclusions
            )

    invalidations = list(dict.fromkeys(invalidations))
    if invalidations:
        return _invalid_contract(
            "STANDING_CONTRACT_IDENTITY_INVALID",
            *invalidations,
        )
    if project_target_available is not True:
        return _invalid_contract(
            "STANDING_CONTRACT_TARGET_UNAVAILABLE",
            "contract.refreshTargets.project:unavailable",
        )

    assert repository is not None
    assert publication is not None
    assert refresh is not None
    remote_ref = f"{repository['remote']}:{repository['ref']}"
    tag = str(publication["tag"])
    project = str(refresh["project"])
    cache = str(refresh["cache"])
    effect_targets = {
        "release.promote_local": f"plugins/{plugin['id']}",
        "git.commit": remote_ref,
        "git.push": remote_ref,
        "git.tag.push": tag,
        "github.release": tag,
        "devflow.source.fast_forward": project,
        "codex.cache.refresh": cache,
        "devflow.project.refresh": project,
    }
    effect_targets.update(
        {
            alias: effect_targets[canonical]
            for alias, canonical in EFFECT_ALIASES.items()
        }
    )
    return {
        "schemaVersion": 1,
        "ok": True,
        "reasonCodes": [],
        "invalidations": [],
        "requestedEffects": list(requested_effects),
        "effectTargets": effect_targets,
        "assetExpectation": str(publication["assetExpectation"]),
    }


def _invalid_contract(reason: str, *invalidations: str) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "ok": False,
        "reasonCodes": [reason],
        "invalidations": list(dict.fromkeys(invalidations)),
        "requestedEffects": [],
        "effectTargets": {},
        "assetExpectation": None,
    }


def _mapping_field(
    value: Mapping[str, Any],
    field: str,
    label: str,
    invalidations: list[str],
) -> Mapping[str, Any] | None:
    nested = value.get(field)
    if not isinstance(nested, Mapping):
        invalidations.append(label)
        return None
    return nested


def _require_exact_keys(
    value: Mapping[str, Any],
    expected: frozenset[str],
    label: str,
    invalidations: list[str],
) -> None:
    if set(value) != expected:
        invalidations.append(f"{label}.keys")


def _validate_exact_policy(
    value: object,
    expected: Mapping[str, object],
    label: str,
    invalidations: list[str],
) -> None:
    if not isinstance(value, Mapping):
        invalidations.append(label)
        return
    _require_exact_keys(value, frozenset(expected), label, invalidations)
    for field, expected_value in expected.items():
        actual = value.get(field)
        if type(actual) is not type(expected_value) or actual != expected_value:
            invalidations.append(f"{label}.{field}")


def _non_empty_string(value: object) -> bool:
    return bool(
        isinstance(value, str)
        and value
        and value == value.strip()
        and not any(character in value for character in ("\x00", "\r", "\n"))
    )


def _sha1_string(value: object) -> bool:
    return bool(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value))


def _valid_remote_url(value: object) -> bool:
    if not _non_empty_string(value):
        return False
    text = str(value)
    if any(character.isspace() for character in text):
        return False
    if Path(text).is_absolute():
        return _absolute_project_path(text)
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9+.-]*://[^\s]+", text):
        return True
    return bool(re.fullmatch(r"[^\s/@:]+@[^\s/:]+:[^\s]+", text))


def _valid_head_ref(value: object) -> bool:
    if not _non_empty_string(value) or not str(value).startswith("refs/heads/"):
        return False
    return _valid_ref_name(str(value)[len("refs/heads/") :])


def _valid_ref_name(value: object) -> bool:
    if not _non_empty_string(value):
        return False
    text = str(value)
    if not _REF_COMPONENT.fullmatch(text):
        return False
    if any(token in text for token in ("..", "//", "@{")):
        return False
    if text.startswith(("/", ".")) or text.endswith(("/", ".")):
        return False
    return all(
        part and not part.startswith(".") and not part.endswith(".lock")
        for part in text.split("/")
    )


def _safe_relative_path(value: object) -> bool:
    if not _non_empty_string(value):
        return False
    text = str(value)
    if "\\" in text:
        return False
    path = Path(text)
    return bool(
        not path.is_absolute()
        and path != Path(".")
        and ".." not in path.parts
        and path.as_posix() == text
    )


def _absolute_project_path(value: object) -> bool:
    if not _non_empty_string(value):
        return False
    text = str(value)
    path = Path(text)
    return bool(
        path.is_absolute()
        and ".." not in path.parts
        and path.as_posix() == text
    )


def _valid_write_set(value: object) -> bool:
    return bool(
        isinstance(value, list)
        and value
        and all(isinstance(item, str) for item in value)
        and len(set(value)) == len(value)
        and all(_safe_relative_path(item) for item in value)
    )


def _valid_asset_names(value: object) -> bool:
    return bool(
        isinstance(value, list)
        and value
        and all(isinstance(item, str) for item in value)
        and len(set(value)) == len(value)
        and all(
            _non_empty_string(item)
            and Path(str(item)).name == item
            and item not in {".", ".."}
            for item in value
        )
    )
