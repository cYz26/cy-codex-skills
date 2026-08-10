from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[4]
RUNTIME_PACKAGER = REPO_ROOT / "dev" / "scripts" / "package_devflow_release_runtime.py"
RUNTIME_VERIFIER = (
    REPO_ROOT
    / "dev"
    / "plugins"
    / "dev-flow"
    / "scripts"
    / "verify_release_runtime.py"
)
BUNDLE_BUILDER = REPO_ROOT / "dev" / "scripts" / "package_devflow_release_bundle.py"
PUBLICATION_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "publish-dev-flow.yml"

VERSION = "0.4.0"
TAG = "dev-flow-v0.4.0"
EXPECTED_ASSETS = (
    "dev-flow-0.4.0.zip",
    "dev-flow-0.4.0.release-manifest.json",
    "dev-flow-0.4.0.sha256",
    "devflow_runtime.pyz",
    "devflow_runtime.MANIFEST.json",
    "devflow_runtime.sha256",
    "dev-flow-v0.4.0.md",
)
HASHED_ASSETS = tuple(name for name in EXPECTED_ASSETS if name != "dev-flow-0.4.0.sha256")
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
COMPACT_RELEASE_JSON = (
    ".codex-plugin/project-migration.json",
    "schemas/milestone-candidate-manifest-v1.schema.json",
    "schemas/milestone-effect-receipt-v1.schema.json",
    "schemas/milestone-external-effects-contract-v1.schema.json",
    "schemas/milestone-review-receipt-v1.schema.json",
    "schemas/milestone-terminal-receipt-v1.schema.json",
    "schemas/milestone-validation-receipt-v1.schema.json",
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def parse_sha256_file(path: Path) -> dict[str, str]:
    records: dict[str, str] = {}
    for line in path.read_text().splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([^/][^\n]*)", line)
        if match is None:
            raise AssertionError(f"invalid SHA-256 record: {line!r}")
        digest, name = match.groups()
        if name in records:
            raise AssertionError(f"duplicate SHA-256 record: {name}")
        records[name] = digest
    return records


def load_bundle_builder_module():
    spec = importlib.util.spec_from_file_location(
        "devflow_release_bundle_builder_under_test",
        BUNDLE_BUILDER,
    )
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load release bundle builder: {BUNDLE_BUILDER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RuntimeFixture:
    """A disposable repository for exercising checked-in public CLIs."""

    def __init__(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory(prefix="devflow-runtime-release-")
        self.root = Path(self.temporary_directory.name)
        (self.root / "dev" / "scripts").mkdir(parents=True)
        (self.root / "plugins").mkdir(parents=True)
        shutil.copy2(
            RUNTIME_PACKAGER,
            self.root / "dev" / "scripts" / RUNTIME_PACKAGER.name,
        )
        shutil.copytree(
            REPO_ROOT / "dev" / "plugins" / "dev-flow",
            self.root / "dev" / "plugins" / "dev-flow",
        )
        shutil.copytree(
            REPO_ROOT / "plugins" / "dev-flow",
            self.root / "plugins" / "dev-flow",
        )

    @property
    def packager(self) -> Path:
        return self.root / "dev" / "scripts" / RUNTIME_PACKAGER.name

    @property
    def release_scripts(self) -> Path:
        return self.root / "plugins" / "dev-flow" / "scripts"

    @property
    def source_scripts(self) -> Path:
        return self.root / "dev" / "plugins" / "dev-flow" / "scripts"

    def close(self) -> None:
        self.temporary_directory.cleanup()

    def run_packager(self, executable: Path | str = sys.executable) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(executable), str(self.packager)],
            cwd=self.root,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            text=True,
            capture_output=True,
            check=False,
        )

    def manifest(self) -> dict[str, object]:
        return json.loads((self.release_scripts / "devflow_runtime.MANIFEST.json").read_text())

    def runtime_outputs(self) -> dict[str, bytes]:
        names = (
            "devflow_runtime.pyz",
            "devflow_runtime.MANIFEST.json",
            "devflow_runtime.sha256",
            "devflow_runtime.SOURCE_COMMIT",
        )
        return {name: (self.release_scripts / name).read_bytes() for name in names}

    def alternate_python(self) -> Path:
        target = self.root / "toolchains" / "python-from-another-path"
        target.parent.mkdir(parents=True)
        target.symlink_to(Path(sys.executable).resolve())
        return target

    def initialize_git(self) -> None:
        commands = (
            ("init",),
            ("config", "user.name", "DevFlow Release Test"),
            ("config", "user.email", "devflow-release-test@example.invalid"),
            ("add", "dev/plugins/dev-flow", "plugins/dev-flow"),
            ("commit", "-m", "fixture baseline"),
        )
        for command in commands:
            result = subprocess.run(
                ["git", "-C", str(self.root), *command],
                text=True,
                capture_output=True,
                check=False,
            )
            if result.returncode != 0:
                raise AssertionError(result.stderr or result.stdout)

    def advance_git_head_without_source_changes(self) -> None:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(self.root),
                "commit",
                "--allow-empty",
                "-m",
                "unrelated containing commit",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise AssertionError(result.stderr or result.stdout)


class RuntimeReleaseReproducibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = RuntimeFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def build_runtime(self, executable: Path | str = sys.executable) -> dict[str, object]:
        result = self.fixture.run_packager(executable)
        self.assertEqual(result.returncode, 0, result.stderr)
        return self.fixture.manifest()

    def test_runtime_manifest_uses_logical_build_identity_and_source_tree_digest(self):
        first_manifest = self.build_runtime()
        first_outputs = self.fixture.runtime_outputs()
        second_manifest = self.build_runtime(self.fixture.alternate_python())
        second_outputs = self.fixture.runtime_outputs()

        self.assertEqual(
            first_manifest.get("buildCommand"),
            ["python3", "dev/scripts/package_devflow_release_runtime.py"],
        )
        self.assertEqual(first_manifest.get("schemaVersion"), 3)
        self.assertRegex(str(first_manifest.get("sourceTreeSha256", "")), r"^[0-9a-f]{64}$")
        self.assertEqual(
            first_manifest.get("sourceCommit"),
            f"sha256:{first_manifest['sourceTreeSha256']}",
        )
        self.assertEqual(
            first_manifest.get("sourceIdentity"),
            {
                "algorithm": "sha256",
                "kind": "source-tree",
                "sha256": first_manifest["sourceTreeSha256"],
            },
        )
        self.assertEqual(first_manifest.get("sourceCommit"), second_manifest.get("sourceCommit"))
        self.assertEqual(first_manifest, second_manifest)
        self.assertEqual(first_outputs, second_outputs)

        previous_tree_digest = first_manifest["sourceTreeSha256"]
        source = self.fixture.source_scripts / "workflow_lib.py"
        source.write_bytes(source.read_bytes() + b"\n# release provenance tamper fixture\n")
        tampered_manifest = self.build_runtime()
        self.assertNotEqual(tampered_manifest["sourceTreeSha256"], previous_tree_digest)

    def test_runtime_manifest_uses_compact_canonical_json(self):
        manifest = self.build_runtime()
        manifest_path = self.fixture.release_scripts / "devflow_runtime.MANIFEST.json"

        self.assertEqual(
            manifest_path.read_bytes(),
            (
                json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n"
            ).encode(),
        )

    def test_runtime_archive_uses_canonical_stored_member_metadata(self):
        self.build_runtime()
        archive_path = self.fixture.release_scripts / "devflow_runtime.pyz"

        with zipfile.ZipFile(archive_path) as archive:
            infos = archive.infolist()

        self.assertGreater(len(infos), 10)
        self.assertEqual([item.filename for item in infos], sorted(item.filename for item in infos))
        self.assertEqual({item.date_time for item in infos}, {FIXED_ZIP_TIME})
        self.assertEqual({item.compress_type for item in infos}, {zipfile.ZIP_STORED})
        self.assertEqual({item.create_system for item in infos}, {3})
        self.assertEqual({item.create_version for item in infos}, {20})
        self.assertEqual({item.extract_version for item in infos}, {20})
        self.assertEqual({item.flag_bits for item in infos}, {0})
        self.assertEqual({item.volume for item in infos}, {0})
        self.assertEqual({item.reserved for item in infos}, {0})
        self.assertEqual({item.internal_attr for item in infos}, {0})
        self.assertEqual({item.extra for item in infos}, {b""})
        self.assertEqual({item.comment for item in infos}, {b""})
        self.assertEqual(
            {(item.external_attr >> 16) & 0xFFFF for item in infos},
            {stat.S_IFREG | 0o644},
        )

    def test_runtime_archive_bytes_do_not_inherit_source_permission_drift(self):
        self.build_runtime()
        archive = self.fixture.release_scripts / "devflow_runtime.pyz"
        before = archive.read_bytes()
        source = self.fixture.source_scripts / "workflow_lib.py"
        original_mode = stat.S_IMODE(source.stat().st_mode)
        os.chmod(source, 0o755 if original_mode != 0o755 else 0o600)

        self.build_runtime()

        self.assertEqual(archive.read_bytes(), before)

    def test_runtime_audit_bytes_do_not_depend_on_containing_git_commit(self):
        self.fixture.initialize_git()
        self.build_runtime()
        before = self.fixture.runtime_outputs()
        self.fixture.advance_git_head_without_source_changes()

        self.build_runtime()

        self.assertEqual(self.fixture.runtime_outputs(), before)

    def test_runtime_verifier_accepts_a_legacy_schema_one_manifest(self):
        manifest = self.build_runtime()
        legacy_manifest = {
            "schemaVersion": 1,
            "sourceCommit": manifest["sourceCommit"],
            "buildCommand": [
                "/legacy/workstation/bin/python3.12",
                "dev/scripts/package_devflow_release_runtime.py",
            ],
            "archive": manifest["archive"],
            "sources": manifest["sources"],
        }
        (self.fixture.release_scripts / "devflow_runtime.MANIFEST.json").write_text(
            json.dumps(legacy_manifest, indent=2, sort_keys=True) + "\n"
        )
        # The synthetic fixture does not exercise project-refresh parity. Removing
        # this marker selects the verifier's documented synthetic-fixture path.
        (
            self.fixture.root
            / "dev"
            / "plugins"
            / "dev-flow"
            / ".codex-plugin"
            / "project-migration.json"
        ).unlink()

        result = subprocess.run(
            [
                sys.executable,
                str(RUNTIME_VERIFIER),
                "--plugin-root",
                str(self.fixture.root / "plugins" / "dev-flow"),
                "--repo-root",
                str(self.fixture.root),
                "--json",
            ],
            cwd=self.fixture.root,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(report["status"], "verified")


class ReleaseBundlePublicSeamTests(unittest.TestCase):
    def test_deterministic_bundle_builder_public_cli_exists(self):
        self.assertTrue(
            BUNDLE_BUILDER.is_file(),
            "expected RED until dev/scripts/package_devflow_release_bundle.py exists",
        )


@unittest.skipUnless(BUNDLE_BUILDER.is_file(), "deterministic release bundle CLI is intentionally RED")
class ReleaseBundleCleanupIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.builder = load_bundle_builder_module()

    def test_cleanup_preserves_unregistered_member_and_staging_directory(self):
        with tempfile.TemporaryDirectory(prefix="devflow-release-cleanup-") as temporary:
            staging = Path(temporary) / "invocation-owned-staging"
            staging.mkdir()
            staging_identity = self.builder.directory_identity(staging)
            unknown = staging / "not-registered-by-this-invocation.txt"
            unknown.write_bytes(b"unknown member must survive\n")

            with self.assertRaises(self.builder.BundleError):
                self.builder.remove_invocation_owned_directory(staging, staging_identity)

            self.assertTrue(staging.is_dir())
            self.assertEqual(unknown.read_bytes(), b"unknown member must survive\n")

    def test_cleanup_removes_only_registered_identity_and_then_exact_empty_directory(self):
        with tempfile.TemporaryDirectory(prefix="devflow-release-cleanup-") as temporary:
            staging = Path(temporary) / "invocation-owned-staging"
            staging.mkdir()
            staging_identity = self.builder.directory_identity(staging)
            owned = staging / "registered-asset.zip"
            owned.write_bytes(b"exact invocation-owned asset\n")
            owned_members = {
                owned.name: self.builder.regular_member_identity(owned),
            }

            self.builder.remove_invocation_owned_directory(
                staging,
                staging_identity,
                owned_members,
            )

            self.assertFalse(os.path.lexists(staging))

    def test_cleanup_preserves_registered_member_after_external_hard_link_drift(self):
        with tempfile.TemporaryDirectory(prefix="devflow-release-cleanup-link-drift-") as temporary:
            root = Path(temporary)
            staging = root / "invocation-owned-staging"
            staging.mkdir()
            staging_identity = self.builder.directory_identity(staging)
            owned = staging / "registered-asset.zip"
            owned.write_bytes(b"exact invocation-owned asset\n")
            registered_identity = self.builder.regular_member_identity(owned)
            owned_members = {
                owned.name: registered_identity,
            }
            external_link = root / "external-hard-link.zip"
            os.link(owned, external_link)
            linked_member_identity = self.builder.regular_member_identity(owned)
            linked_identity = (linked_member_identity.device, linked_member_identity.inode)

            self.assertEqual(
                registered_identity._fields,
                (
                    "device",
                    "inode",
                    "mode",
                    "link_count",
                    "size",
                    "mtime_ns",
                    "ctime_ns",
                    "sha256",
                ),
            )
            self.assertEqual(
                linked_member_identity.link_count,
                registered_identity.link_count + 1,
            )
            self.assertEqual(linked_member_identity.ctime_ns, owned.lstat().st_ctime_ns)

            with self.assertRaises(self.builder.BundleError):
                self.builder.remove_invocation_owned_directory(
                    staging,
                    staging_identity,
                    owned_members,
                )

            self.assertTrue(staging.is_dir())
            self.assertTrue(owned.is_file())
            self.assertTrue(external_link.is_file())
            self.assertEqual((owned.stat().st_dev, owned.stat().st_ino), linked_identity)
            self.assertEqual(
                (external_link.stat().st_dev, external_link.stat().st_ino),
                linked_identity,
            )
            self.assertEqual(owned.read_bytes(), b"exact invocation-owned asset\n")
            self.assertEqual(external_link.read_bytes(), owned.read_bytes())

    def test_partial_build_failure_cleans_exact_registered_members_and_staging(self):
        with tempfile.TemporaryDirectory(prefix="devflow-release-cleanup-") as temporary:
            root = Path(temporary)
            output = root / "release-assets"

            with mock.patch.object(
                self.builder.shutil,
                "copyfile",
                side_effect=OSError("injected runtime copy failure"),
            ):
                with self.assertRaises((self.builder.BundleError, OSError)):
                    self.builder.build_bundle_for_caller_output(REPO_ROOT, output)

            self.assertFalse(output.exists())
            self.assertEqual(list(root.glob(".release-assets.tmp-*")), [])

    def test_cleanup_preserves_registered_member_identity_type_and_symlink_drift(self):
        for drift_kind in ("identity", "directory-type", "symlink-type"):
            with self.subTest(drift_kind=drift_kind):
                with tempfile.TemporaryDirectory(
                    prefix="devflow-release-cleanup-drift-"
                ) as temporary:
                    root = Path(temporary)
                    staging = root / "invocation-owned-staging"
                    staging.mkdir()
                    staging_identity = self.builder.directory_identity(staging)
                    stable = staging / "stable-owned-asset.json"
                    drifted = staging / "drifted-owned-asset.zip"
                    stable.write_bytes(b"stable invocation-owned asset\n")
                    drifted.write_bytes(b"original invocation-owned asset\n")
                    owned_members = {
                        stable.name: self.builder.regular_member_identity(stable),
                        drifted.name: self.builder.regular_member_identity(drifted),
                    }

                    if drift_kind == "identity":
                        replacement = staging / "replacement.tmp"
                        replacement.write_bytes(b"replacement with a different inode\n")
                        os.replace(replacement, drifted)
                    elif drift_kind == "directory-type":
                        drifted.unlink()
                        drifted.mkdir()
                    else:
                        external = root / "external-sentinel.txt"
                        external.write_bytes(b"external sentinel must survive\n")
                        drifted.unlink()
                        drifted.symlink_to(external)

                    with self.assertRaises(self.builder.BundleError):
                        self.builder.remove_invocation_owned_directory(
                            staging,
                            staging_identity,
                            owned_members,
                        )

                    self.assertTrue(staging.is_dir())
                    self.assertFalse(os.path.lexists(stable))
                    self.assertTrue(os.path.lexists(drifted))
                    if drift_kind == "identity":
                        self.assertEqual(
                            drifted.read_bytes(),
                            b"replacement with a different inode\n",
                        )
                    elif drift_kind == "directory-type":
                        self.assertTrue(drifted.is_dir())
                        self.assertFalse(drifted.is_symlink())
                    else:
                        self.assertTrue(drifted.is_symlink())
                        self.assertEqual(
                            external.read_bytes(),
                            b"external sentinel must survive\n",
                        )

    def test_promotion_rejects_registered_regular_file_identity_drift(self):
        with tempfile.TemporaryDirectory(
            prefix="devflow-release-promotion-drift-"
        ) as temporary:
            root = Path(temporary)
            staging = root / "staging"
            output = root / "output"
            staging.mkdir()
            output.mkdir()
            source = staging / "declared-asset.zip"
            source.write_bytes(b"original registered bytes\n")
            staging_members = {
                source.name: self.builder.regular_member_identity(source),
            }
            replacement = staging / "replacement.tmp"
            replacement.write_bytes(b"replacement unknown bytes\n")
            os.replace(replacement, source)

            with self.assertRaises(self.builder.BundleError):
                self.builder.promote_staged_assets(
                    staging,
                    output,
                    [source.name],
                    staging_members=staging_members,
                    output_members={},
                )

            self.assertEqual(source.read_bytes(), b"replacement unknown bytes\n")
            self.assertEqual(list(output.iterdir()), [])

    def test_promotion_rechecks_identity_after_hard_link_creation(self):
        with tempfile.TemporaryDirectory(
            prefix="devflow-release-promotion-link-drift-"
        ) as temporary:
            root = Path(temporary)
            staging = root / "staging"
            output = root / "output"
            staging.mkdir()
            output.mkdir()
            source = staging / "declared-asset.zip"
            source.write_bytes(b"original registered bytes\n")
            staging_members = {
                source.name: self.builder.regular_member_identity(source),
            }
            output_members: dict[str, object] = {}
            real_link = os.link

            def replace_then_link(
                source_path: Path | str,
                target_path: Path | str,
                *,
                follow_symlinks: bool = True,
            ) -> None:
                source_file = Path(source_path)
                replacement = source_file.parent / "replacement.tmp"
                replacement.write_bytes(b"replacement unknown bytes\n")
                os.replace(replacement, source_file)
                real_link(
                    source_file,
                    target_path,
                    follow_symlinks=follow_symlinks,
                )

            with mock.patch.object(
                self.builder.os,
                "link",
                side_effect=replace_then_link,
            ):
                with self.assertRaises(self.builder.BundleError):
                    self.builder.promote_staged_assets(
                        staging,
                        output,
                        [source.name],
                        staging_members=staging_members,
                        output_members=output_members,
                    )

            self.assertEqual(source.read_bytes(), b"replacement unknown bytes\n")
            self.assertEqual(
                (output / source.name).read_bytes(),
                b"replacement unknown bytes\n",
            )
            self.assertEqual(output_members, {source.name: staging_members[source.name]})

    def test_wrapper_preserves_drift_injected_immediately_before_failure_cleanup(self):
        for drift_kind in ("unknown", "identity", "directory-type", "symlink-type"):
            with self.subTest(drift_kind=drift_kind):
                with tempfile.TemporaryDirectory(
                    prefix="devflow-release-wrapper-drift-"
                ) as temporary:
                    root = Path(temporary)
                    output = root / "release-assets"
                    preserved_name: str | None = None
                    external = root / "external-sentinel.txt"

                    def inject_drift_and_fail(
                        source: Path | str,
                        target: Path | str,
                        *,
                        follow_symlinks: bool = True,
                    ) -> None:
                        del target, follow_symlinks
                        source_path = Path(source)
                        nonlocal preserved_name
                        if drift_kind == "unknown":
                            preserved = source_path.parent / "unknown-member.txt"
                            preserved.write_bytes(b"unknown member must survive\n")
                        elif drift_kind == "identity":
                            preserved = source_path
                            replacement = source_path.parent / "replacement.tmp"
                            replacement.write_bytes(b"replacement unknown bytes\n")
                            os.replace(replacement, source_path)
                        elif drift_kind == "directory-type":
                            preserved = source_path
                            source_path.unlink()
                            source_path.mkdir()
                        else:
                            preserved = source_path
                            external.write_bytes(b"external sentinel must survive\n")
                            source_path.unlink()
                            source_path.symlink_to(external)
                        preserved_name = preserved.name
                        raise OSError("injected promotion failure after ownership check")

                    with mock.patch.object(
                        self.builder.os,
                        "link",
                        side_effect=inject_drift_and_fail,
                    ):
                        with self.assertRaises((self.builder.BundleError, OSError)):
                            self.builder.build_bundle_for_caller_output(REPO_ROOT, output)

                    self.assertFalse(output.exists())
                    staging_directories = list(root.glob(".release-assets.tmp-*"))
                    self.assertEqual(len(staging_directories), 1)
                    staging = staging_directories[0]
                    self.assertEqual(
                        [member.name for member in staging.iterdir()],
                        [preserved_name],
                    )
                    preserved = staging / str(preserved_name)
                    self.assertTrue(os.path.lexists(preserved))
                    if drift_kind == "unknown":
                        self.assertEqual(
                            preserved.read_bytes(),
                            b"unknown member must survive\n",
                        )
                    elif drift_kind == "identity":
                        self.assertEqual(
                            preserved.read_bytes(),
                            b"replacement unknown bytes\n",
                        )
                    elif drift_kind == "directory-type":
                        self.assertTrue(preserved.is_dir())
                        self.assertFalse(preserved.is_symlink())
                    else:
                        self.assertTrue(preserved.is_symlink())
                        self.assertEqual(
                            external.read_bytes(),
                            b"external sentinel must survive\n",
                        )

    def test_partial_promotion_cleans_owned_targets_but_preserves_caller_directory(self):
        with tempfile.TemporaryDirectory(
            prefix="devflow-release-caller-cleanup-"
        ) as temporary:
            root = Path(temporary)
            output = root / "caller-owned-output"
            output.mkdir()
            output_identity = self.builder.directory_identity(output)
            real_link = os.link
            link_count = 0

            def fail_second_link(
                source: Path | str,
                target: Path | str,
                *,
                follow_symlinks: bool = True,
            ) -> None:
                nonlocal link_count
                link_count += 1
                if link_count == 2:
                    raise OSError("injected second promotion failure")
                real_link(source, target, follow_symlinks=follow_symlinks)

            with mock.patch.object(
                self.builder.os,
                "link",
                side_effect=fail_second_link,
            ):
                with self.assertRaises((self.builder.BundleError, OSError)):
                    self.builder.build_bundle_for_caller_output(REPO_ROOT, output)

            self.assertEqual(self.builder.directory_identity(output), output_identity)
            self.assertEqual(list(output.iterdir()), [])
            self.assertEqual(list(root.glob(".caller-owned-output.tmp-*")), [])


@unittest.skipUnless(BUNDLE_BUILDER.is_file(), "deterministic release bundle CLI is intentionally RED")
class ReleaseBundleContractTests(unittest.TestCase):
    maxDiff = None

    def run_builder(
        self,
        output_directory: Path,
        *,
        executable: Path | str = sys.executable,
        extra_arguments: tuple[str, ...] = (),
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                str(executable),
                str(BUNDLE_BUILDER),
                "--repo",
                str(REPO_ROOT),
                "--output-dir",
                str(output_directory),
                "--json",
                *extra_arguments,
            ],
            cwd=REPO_ROOT,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            text=True,
            capture_output=True,
            check=False,
        )

    def build(self, output_directory: Path, executable: Path | str = sys.executable) -> dict[str, object]:
        result = self.run_builder(output_directory, executable=executable)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_machine_only_release_contracts_use_compact_canonical_json(self):
        for plugin_root in (
            REPO_ROOT / "dev" / "plugins" / "dev-flow",
            REPO_ROOT / "plugins" / "dev-flow",
        ):
            for relative in COMPACT_RELEASE_JSON:
                with self.subTest(plugin_root=plugin_root, relative=relative):
                    path = plugin_root / relative
                    document = json.loads(path.read_text())
                    expected = (
                        json.dumps(document, separators=(",", ":"), ensure_ascii=False)
                        + "\n"
                    ).encode()
                    self.assertEqual(path.read_bytes(), expected)

    def test_bundle_emits_only_seven_declared_assets_with_exact_hash_records(self):
        with tempfile.TemporaryDirectory(prefix="devflow-release-assets-") as temporary:
            output = Path(temporary)
            report = self.build(output)

            actual_names = sorted(path.name for path in output.iterdir() if path.is_file())
            self.assertEqual(actual_names, sorted(EXPECTED_ASSETS))
            self.assertEqual(report.get("status"), "built")
            self.assertEqual(report.get("plugin"), "dev-flow")
            self.assertEqual(report.get("version"), VERSION)
            self.assertEqual(report.get("tag"), TAG)

            reported_assets = {item["name"]: item for item in report.get("assets", [])}
            self.assertEqual(set(reported_assets), set(EXPECTED_ASSETS))
            for name, record in reported_assets.items():
                payload = (output / name).read_bytes()
                self.assertEqual(record["bytes"], len(payload), name)
                self.assertEqual(record["sha256"], sha256_bytes(payload), name)

            checksums = parse_sha256_file(output / "dev-flow-0.4.0.sha256")
            self.assertEqual(set(checksums), set(HASHED_ASSETS))
            for name, digest in checksums.items():
                self.assertEqual(digest, sha256_bytes((output / name).read_bytes()), name)

            manifest = json.loads((output / "dev-flow-0.4.0.release-manifest.json").read_text())
            self.assertNotIn("commit", manifest)
            self.assertRegex(str(manifest.get("treeSha256", "")), r"^[0-9a-f]{64}$")
            expected_manifest = Path(str(report.get("expectedManifest", "")))
            if not expected_manifest.is_absolute():
                expected_manifest = REPO_ROOT / expected_manifest
            self.assertTrue(expected_manifest.is_file(), report)
            self.assertTrue(expected_manifest.resolve().is_relative_to(REPO_ROOT.resolve()))
            self.assertEqual(expected_manifest.read_bytes(), (output / expected_manifest.name).read_bytes())

    def test_bundle_rebuild_is_byte_identical_across_python_executable_paths(self):
        with tempfile.TemporaryDirectory(prefix="devflow-release-rebuild-") as temporary:
            root = Path(temporary)
            first = root / "first"
            second = root / "second"
            alternate_python = root / "toolchains" / "alternate-python"
            alternate_python.parent.mkdir(parents=True)
            alternate_python.symlink_to(Path(sys.executable).resolve())

            self.build(first)
            self.build(second, alternate_python)

            self.assertEqual(
                {name: (first / name).read_bytes() for name in EXPECTED_ASSETS},
                {name: (second / name).read_bytes() for name in EXPECTED_ASSETS},
            )

    def test_builder_rejects_preexisting_nonempty_output_without_modifying_it(self):
        with tempfile.TemporaryDirectory(prefix="devflow-release-caller-output-") as temporary:
            output = Path(temporary) / "caller-owned"
            output.mkdir()
            sentinel = output / "keep.txt"
            sentinel.write_bytes(b"caller-owned sentinel\n")

            result = self.run_builder(output)

            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(output.is_dir())
            self.assertEqual(
                {path.name: path.read_bytes() for path in output.iterdir()},
                {"keep.txt": b"caller-owned sentinel\n"},
            )

    def test_plugin_zip_uses_canonical_stored_member_metadata(self):
        with tempfile.TemporaryDirectory(prefix="devflow-release-zip-") as temporary:
            output = Path(temporary)
            self.build(output)

            with zipfile.ZipFile(output / "dev-flow-0.4.0.zip") as archive:
                infos = archive.infolist()

            names = [item.filename for item in infos]
            self.assertEqual(names, sorted(names))
            self.assertTrue(names)
            self.assertTrue(all(name.startswith("dev-flow/") for name in names))
            self.assertTrue(all(".." not in Path(name).parts for name in names))
            self.assertEqual({item.date_time for item in infos}, {FIXED_ZIP_TIME})
            self.assertEqual({item.compress_type for item in infos}, {zipfile.ZIP_STORED})
            self.assertEqual({item.create_system for item in infos}, {3})
            self.assertEqual({item.create_version for item in infos}, {20})
            self.assertEqual({item.extract_version for item in infos}, {20})
            self.assertEqual({item.flag_bits for item in infos}, {0})
            self.assertEqual({item.volume for item in infos}, {0})
            self.assertEqual({item.reserved for item in infos}, {0})
            self.assertEqual({item.internal_attr for item in infos}, {0})
            self.assertEqual({item.extra for item in infos}, {b""})
            self.assertEqual({item.comment for item in infos}, {b""})
            modes = {(item.external_attr >> 16) & 0xFFFF for item in infos}
            self.assertTrue(modes.issubset({stat.S_IFREG | 0o644, stat.S_IFREG | 0o755}), modes)
            self.assertNotIn("dev-flow/dev-flow-0.4.0.release-manifest.json", names)
            self.assertNotIn("dev-flow/dev-flow-0.4.0.sha256", names)

    def test_builder_rejects_manual_version_tag_asset_or_repository_widening(self):
        forbidden_overrides = (
            ("--version", "0.4.1"),
            ("--tag", "dev-flow-v0.4.1"),
            ("--asset", "*.zip"),
            ("--repository", "another-owner/another-repository"),
        )
        with tempfile.TemporaryDirectory(prefix="devflow-release-widening-") as temporary:
            root = Path(temporary)
            for index, arguments in enumerate(forbidden_overrides):
                output = root / str(index)
                with self.subTest(arguments=arguments):
                    result = self.run_builder(output, extra_arguments=arguments)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(output.exists() and any(output.iterdir()))


class PublicationWorkflowPublicSeamTests(unittest.TestCase):
    def test_tag_bound_publication_workflow_exists(self):
        self.assertTrue(
            PUBLICATION_WORKFLOW.is_file(),
            "expected RED until .github/workflows/publish-dev-flow.yml exists",
        )


@unittest.skipUnless(PUBLICATION_WORKFLOW.is_file(), "tag-bound publication workflow is intentionally RED")
class PublicationWorkflowContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = PUBLICATION_WORKFLOW.read_text()
        self.lowered = self.text.lower()

    def test_workflow_is_exact_tag_only_and_least_privilege(self):
        self.assertRegex(self.text, r"(?m)^\s*tags:\s*$")
        self.assertRegex(self.text, rf"(?m)^\s*-\s*['\"]?{re.escape(TAG)}['\"]?\s*$")
        self.assertNotIn("workflow_dispatch", self.lowered)
        self.assertNotIn("repository_dispatch", self.lowered)
        self.assertNotIn("pull_request", self.lowered)
        self.assertNotIn("${{ inputs.", self.lowered)
        self.assertRegex(
            self.text,
            rf"(?m)^\s*ref:\s*(?:\$\{{\{{\s*github\.ref\s*\}}\}}|['\"]?refs/tags/{re.escape(TAG)}['\"]?)\s*$",
        )

        permissions = re.search(
            r"(?m)^permissions:\s*\n(?P<body>(?:^[ ]{2}[^\n]+\n?)+)",
            self.text,
        )
        self.assertIsNotNone(permissions)
        permission_lines = {
            line.strip()
            for line in permissions.group("body").splitlines()
            if line.strip()
        }
        self.assertEqual(permission_lines, {"contents: write"})

    def test_workflow_pins_every_action_and_uses_runner_github_cli(self):
        uses = re.findall(r"(?m)^\s*-?\s*uses:\s*([^@\s]+)@([^\s#]+)", self.text)
        self.assertTrue(uses)
        self.assertTrue(any(name == "actions/checkout" for name, _ in uses), uses)
        for name, revision in uses:
            with self.subTest(action=name):
                self.assertRegex(revision, r"^[0-9a-f]{40}$")
        self.assertRegex(self.text, rf"(?m)\bgh\s+release\s+create\s+['\"]?{re.escape(TAG)}\b")
        for checked_in_command in (
            "dev/scripts/package_devflow_release_runtime.py",
            "dev/scripts/package_devflow_release_bundle.py",
            "dev/plugins/dev-flow/scripts/verify_release_runtime.py",
        ):
            self.assertIn(checked_in_command, self.text)
        for external_bootstrap in ("pip install", "npm install", "npx ", "brew ", "curl ", "wget "):
            self.assertNotIn(external_bootstrap, self.lowered)

    def test_workflow_names_every_asset_and_has_no_overwrite_or_widening_path(self):
        for name in EXPECTED_ASSETS:
            with self.subTest(asset=name):
                self.assertIn(name, self.text)

        prohibited = (
            "--clobber",
            "--force",
            "git tag -f",
            "gh release delete",
            "gh release edit",
            "release-assets/*",
            "release-assets/**",
        )
        for token in prohibited:
            with self.subTest(token=token):
                self.assertNotIn(token, self.lowered)


if __name__ == "__main__":
    unittest.main(verbosity=2)
