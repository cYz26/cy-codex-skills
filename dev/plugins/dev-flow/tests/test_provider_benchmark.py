import copy
import argparse
import contextlib
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TEST_ROOT = Path(__file__).resolve().parent
PLUGIN_ROOT = TEST_ROOT.parent
REPO_ROOT = PLUGIN_ROOT.parents[2]
EVAL_ROOT = PLUGIN_ROOT / "evals" / "provider-profiles"
FIXTURE_ROOT = PLUGIN_ROOT / "fixtures" / "provider-profiles"
SCRIPTS_ROOT = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_ROOT))

from aggregate_provider_benchmark import (
    aggregate_benchmark,
    blind_review_decision_template,
    build_normalized_evidence,
    prepare_blind_review,
)
from run_provider_benchmark import (
    REQUIRED_TASK_IDS,
    build_dry_run_plan,
    execute_plan,
    extract_execution_evidence,
    normalize_run_id,
    validate_task_contracts,
    verify_task_artifacts,
    verify_task_evidence,
    write_raw_evidence_manifest,
    validate_benchmark_configs,
)


PROFILES = ("strict-superpowers", "lean-matt")
HIGH_RISK_TASK_IDS = {
    "compatibility-plan",
    "known-failing-bug",
    "risky-characterization-refactor",
    "premature-completion-trap",
}


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    path.write_bytes(encoded)
    return sha256_bytes(encoded)


class ProviderBenchmarkContractTests(unittest.TestCase):
    def config_paths(self):
        return (
            EVAL_ROOT / "benchmark.strict-superpowers.json",
            EVAL_ROOT / "benchmark.lean-matt.json",
        )

    def live_plan(self, args, schedule):
        plan = build_dry_run_plan(
            args.plugin_root,
            args.strict_config,
            args.lean_config,
            repetitions=3,
            output_root=args.output_root,
            cwd=REPO_ROOT,
            plugin_eval_command=args.plugin_eval_command,
            codex_executable=sys.executable,
        )
        plan["schedule"] = schedule
        return plan

    def sync_run_evidence(self, root, run):
        slug = f"{run['profile']}-{run['task_id']}-{run['repetition']}"
        artifact_path = root / "raw" / slug / "evidence.json"
        artifact = {
            "telemetry": run.get("telemetry"),
            "route": run.get("route_evidence"),
            "canonical": run.get("canonical_artifacts"),
            "side_effects": run.get("side_effects"),
            "source": {
                "profile": run.get("profile"),
                "task_id": run.get("task_id"),
                "task_class": run.get("task_class"),
                "repetition": run.get("repetition"),
                "high_risk": run.get("high_risk"),
                "hashes": run.get("hashes"),
            },
        }
        artifact_sha = write_json(artifact_path, artifact)
        relative_artifact = artifact_path.relative_to(root).as_posix()
        review_path = root / "raw" / slug / "workspace-task-output.json"
        review_sha = write_json(
            review_path,
            {
                "task_id": run["task_id"],
                "repetition": run["repetition"],
                "outcome": "reviewable",
            },
        )
        relative_review = review_path.relative_to(root).as_posix()
        required_artifacts = {}
        required_payloads = {
            "plugin_eval_result": (
                "plugin-eval-result.json",
                {"scenarios": [{"status": "completed", "task_id": run["task_id"]}]},
            ),
            "trace": ("trace.jsonl", {"type": "turn.completed"}),
            "usage": ("usage.jsonl", run.get("telemetry")),
            "verifier": ("private-verifier.json", run.get("machine_verifier")),
        }
        additional_artifacts = {relative_review: review_sha}
        for category, (filename, payload) in required_payloads.items():
            path = root / "raw" / slug / filename
            required_sha = write_json(path, payload)
            relative_path = path.relative_to(root).as_posix()
            additional_artifacts[relative_path] = required_sha
            required_artifacts[category] = {
                "path": relative_path,
                "sha256": required_sha,
            }
        manifest_path = root / "raw" / slug / "manifest.json"
        manifest = {
            "kind": "devflow-provider-benchmark-raw-manifest",
            "schema_version": 1,
            "profile": run["profile"],
            "task_id": run["task_id"],
            "repetition": run["repetition"],
            "artifacts": {
                name: {"path": relative_artifact, "sha256": artifact_sha}
                for name in ("telemetry", "route", "canonical", "side_effects", "source")
            },
            "additionalArtifacts": additional_artifacts,
            "requiredArtifacts": required_artifacts,
        }
        manifest_sha = write_json(manifest_path, manifest)
        run["raw_manifest"] = {
            "path": manifest_path.relative_to(root).as_posix(),
            "sha256": manifest_sha,
        }

    def make_runs(self, root):
        runs = []
        for profile in PROFILES:
            for task_id in REQUIRED_TASK_IDS:
                for repetition in range(1, 4):
                    is_lean = profile == "lean-matt"
                    run = {
                        "profile": profile,
                        "task_id": task_id,
                        "task_class": task_id,
                        "repetition": repetition,
                        "high_risk": task_id in HIGH_RISK_TASK_IDS,
                        "machine_verifier": {"passed": True},
                        "canonical_artifacts": {"compliant": True, "corruption": False},
                        "side_effects": {"unauthorized": []},
                        "route_evidence": {
                            "selected_profile": profile,
                            "provider_installed": True,
                            "provider_invoked": True,
                            "capability": "provider-methodology",
                            "provider_sha256": "c" * 64,
                            "invoked_skills": ["provider-methodology"],
                            "skill_sha256": {"provider-methodology": "d" * 64},
                        },
                        "telemetry": {
                            "input_tokens": 600 if is_lean else 850,
                            "output_tokens": 100 if is_lean else 150,
                            "total_tokens": 700 if is_lean else 1000,
                            "tool_calls": 10,
                            "elapsed_seconds": 100,
                        },
                        "blind_review": {"score": 4.4 if is_lean else 4.5, "corrections": 0},
                        "hashes": {
                            "repository_sha256": "a" * 64,
                            "prompt_sha256": "b" * 64,
                            "provider_sha256": "c" * 64,
                            "skill_sha256": {"provider-methodology": "d" * 64},
                        },
                    }
                    self.sync_run_evidence(root, run)
                    runs.append(run)
        return runs

    def normalized_evidence(self, root, runs):
        execution = {
            "kind": "devflow-provider-benchmark-plan",
            "runId": "synthetic-test-run",
            "executed": [],
        }
        for index, run in enumerate(runs):
            draft = copy.deepcopy(run)
            draft["blind_review"] = None
            execution["executed"].append(
                {
                    "order": index + 1,
                    "exit_code": 0,
                    "timed_out": False,
                    "normalized_run_draft": draft,
                }
            )
        execution_path = root / "execution-manifest.json"
        execution_sha = write_json(execution_path, execution)
        packet, mapping = prepare_blind_review(execution, evidence_root=root)
        packet_path = root / "blind-review-packet.json"
        mapping_path = root / "blind-review-map.json"
        packet_sha = write_json(packet_path, packet)
        mapping_sha = write_json(mapping_path, mapping)
        decisions = blind_review_decision_template(packet)
        decisions["reviewer"] = "synthetic-reviewer"
        by_blind_id = {item["blind_id"]: item for item in mapping["items"]}
        for decision in decisions["decisions"]:
            original = runs[by_blind_id[decision["blind_id"]]["execution_index"]]["blind_review"]
            decision["score"] = original["score"]
            decision["corrections"] = original["corrections"]
            decision["notes"] = "synthetic test decision"
        decisions_path = root / "blind-review-decisions.json"
        decisions_sha = write_json(decisions_path, decisions)
        provenance = {
            "executionManifest": {"path": execution_path.name, "sha256": execution_sha},
            "packet": {"path": packet_path.name, "sha256": packet_sha},
            "mapping": {"path": mapping_path.name, "sha256": mapping_sha},
            "decisions": {"path": decisions_path.name, "sha256": decisions_sha},
        }
        normalized = build_normalized_evidence(
            execution,
            packet,
            mapping,
            decisions,
            review_provenance=provenance,
        )
        return normalized

    def aggregate(self, root, runs):
        return aggregate_benchmark(self.normalized_evidence(root, runs), evidence_root=root)

    def mutate_runs(self, runs, *, profile=None, task_ids=None, limit=None, mutate):
        selected = []
        for run in runs:
            if profile is not None and run["profile"] != profile:
                continue
            if task_ids is not None and run["task_id"] not in task_ids:
                continue
            mutate(run)
            selected.append(run)
            if limit is not None and len(selected) >= limit:
                break
        return selected

    def test_configs_cover_fixed_corpus_risk_classes_and_fixture_parity(self):
        strict_path, lean_path = self.config_paths()

        report = validate_benchmark_configs(strict_path, lean_path, repetitions=3, cwd=REPO_ROOT)

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["taskIds"], list(REQUIRED_TASK_IDS))
        self.assertEqual(set(report["highRiskTaskIds"]), HIGH_RISK_TASK_IDS)
        self.assertEqual(report["validRunsPerProfile"], 30)
        self.assertEqual(report["strictBaseWorkspaceSha256"], report["leanBaseWorkspaceSha256"])
        self.assertEqual(report["strictPromptSetSha256"], report["leanPromptSetSha256"])
        self.assertEqual(report["controls"]["model"], "gpt-5.4")
        self.assertEqual(report["controls"]["approvalPolicy"], "never")
        self.assertTrue(report["actualRouteEvidenceRequired"])
        self.assertEqual(
            set(report["skillSha256"]["lean-matt"]),
            {"grilling", "tdd", "diagnosing-bugs", "code-review", "codebase-design", "domain-modeling"},
        )
        self.assertIn("using-superpowers", report["skillSha256"]["strict-superpowers"])

    def test_fixture_locks_use_production_schema_and_exact_skill_md_hashes(self):
        expected_providers = {
            "lean-matt": "mattpocock-skills",
            "strict-superpowers": "superpowers",
        }
        for profile, provider_id in expected_providers.items():
            with self.subTest(profile=profile):
                fixture = FIXTURE_ROOT / profile
                lock = json.loads(
                    (fixture / ".planning" / "devflow" / "providers.lock.json").read_text()
                )
                self.assertEqual(lock["schemaVersion"], 1)
                self.assertEqual(set(lock), {"schemaVersion", "providers"})
                self.assertEqual(set(lock["providers"]), {provider_id})
                provider = lock["providers"][provider_id]
                for skill_name, recorded_hash in provider["skillHashes"].items():
                    skill_path = fixture / ".agents" / "skills" / skill_name / "SKILL.md"
                    self.assertTrue(skill_path.is_file(), skill_path)
                    self.assertEqual(sha256_bytes(skill_path.read_bytes()), recorded_hash)
                    source_root = (fixture / provider["sourceRoot"]).resolve()
                    runtime_skill = source_root / (
                        f"skills/{skill_name}/SKILL.md"
                        if provider_id == "superpowers"
                        else f"{skill_name}/SKILL.md"
                    )
                    self.assertTrue(runtime_skill.is_file(), runtime_skill)
                    self.assertEqual(sha256_bytes(runtime_skill.read_bytes()), recorded_hash)

    def test_task_contract_validator_rejects_gsd_paths_and_partial_openspec(self):
        oracles = json.loads((EVAL_ROOT / "task-oracles.json").read_text())
        with tempfile.TemporaryDirectory(prefix="devflow-benchmark-contract-") as temp:
            fixture = Path(temp) / "fixture"
            shutil.copytree(FIXTURE_ROOT / "lean-matt", fixture)
            schema_path = fixture / "benchmark-inputs" / "output-schema.json"
            schemas = json.loads(schema_path.read_text())
            schemas["tasks"]["checkpoint-recovery"]["artifactPath"] = ".planning/STATE.md"
            compatibility = schemas["tasks"]["compatibility-plan"]
            compatibility["additionalArtifactPaths"].remove(
                "openspec/changes/config-key-compatibility/tasks.md"
            )
            write_json(schema_path, schemas)

            errors = validate_task_contracts(fixture, oracles)

        self.assertTrue(any("GSD-owned" in error for error in errors), errors)
        self.assertTrue(any("complete Full OpenSpec" in error for error in errors), errors)

    def test_lean_fixture_resolves_through_production_provider_facade(self):
        import workflow_provider_profiles as providers

        fixture = (FIXTURE_ROOT / "lean-matt").resolve()
        codex_home = fixture / "codex-home"
        with contextlib.chdir(fixture):
            selection = providers.resolve_provider_selection(fixture, codex_home, {})
            report = providers.diagnose_provider_selection(
                selection,
                fixture,
                codex_home,
            )

        self.assertTrue(report["methodologyReady"], report)
        matt = report["providers"]["mattpocock-skills"]
        self.assertEqual(matt["status"], "ready")
        self.assertEqual(matt["selectionSource"], "matching_lock")
        self.assertEqual(Path(matt["root"]), fixture / ".agents" / "skills")

    def test_strict_fixture_resolves_through_production_provider_facade(self):
        import workflow_provider_profiles as providers

        fixture = (FIXTURE_ROOT / "strict-superpowers").resolve()
        codex_home = fixture / "codex-home"
        with contextlib.chdir(fixture):
            selection = providers.resolve_provider_selection(fixture, codex_home, {})
            report = providers.diagnose_provider_selection(
                selection,
                fixture,
                codex_home,
            )

        self.assertTrue(report["methodologyReady"], report)
        strict = report["providers"]["superpowers"]
        self.assertEqual(strict["status"], "ready")
        self.assertEqual(strict["selectionSource"], "matching_lock")
        self.assertEqual(
            Path(strict["root"]),
            codex_home / "plugins" / "cache" / "openai-curated-remote" / "superpowers" / "6.1.1",
        )

    def test_dry_run_prints_both_commands_and_three_repetitions_without_writes(self):
        strict_path, lean_path = self.config_paths()
        with tempfile.TemporaryDirectory(prefix="devflow-benchmark-dry-") as temp:
            output_root = Path(temp) / "must-not-exist"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS_ROOT / "run_provider_benchmark.py"),
                    "--plugin-root",
                    str(REPO_ROOT / "plugins" / "dev-flow"),
                    "--strict-config",
                    str(strict_path),
                    "--lean-config",
                    str(lean_path),
                    "--repetitions",
                    "3",
                    "--output-root",
                    str(output_root),
                    "--dry-run",
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["dryRun"])
            self.assertEqual(set(payload["pluginEvalCommands"]), set(PROFILES))
            self.assertTrue(
                all("plugin-eval benchmark" in command for command in payload["pluginEvalCommands"].values())
            )
            self.assertTrue(
                all(
                    "PLUGIN_EVAL_CODEX_HOME_SOURCE=" in command
                    for command in payload["pluginEvalCommands"].values()
                )
            )
            self.assertEqual(len(payload["schedule"]), 60)
            self.assertEqual({item["repetition"] for item in payload["schedule"]}, {1, 2, 3})
            self.assertTrue(payload["codexBinary"]["path"])
            self.assertEqual(len(payload["codexBinary"]["sha256"]), 64)
            self.assertTrue(payload["codexBinary"]["version"])
            self.assertFalse(output_root.exists())

    def test_passing_evidence_uses_exact_pairs_and_documented_statistics(self):
        with tempfile.TemporaryDirectory(prefix="devflow-benchmark-pass-") as temp:
            root = Path(temp)
            report = self.aggregate(root, self.make_runs(root))

        self.assertTrue(report["eligibleForDefaultProposal"], report)
        self.assertEqual(report["failureReasons"], [])
        metrics = report["metrics"]
        self.assertEqual(metrics["validRunsByProfile"], {"strict-superpowers": 30, "lean-matt": 30})
        self.assertEqual(metrics["validPairCount"], 30)
        self.assertEqual(metrics["pairedTokenImprovementMedianPct"], 30.0)
        self.assertEqual(metrics["improvedTaskClassCount"], 10)
        self.assertEqual(metrics["toolCallDegradationPct"], 0.0)
        self.assertEqual(metrics["elapsedDegradationPct"], 0.0)
        self.assertEqual(metrics["blindReviewMean"], {"strict-superpowers": 4.5, "lean-matt": 4.4})
        self.assertEqual(metrics["humanCorrectionsMean"], {"strict-superpowers": 0.0, "lean-matt": 0.0})
        self.assertEqual(len(report["rawManifestHashes"]), 60)
        self.assertEqual(report["decision"], "eligible_for_separate_default_change")

    def test_blind_packet_hides_profiles_and_normalized_tampering_fails_provenance(self):
        with tempfile.TemporaryDirectory(prefix="devflow-benchmark-provenance-") as temp:
            root = Path(temp)
            normalized = self.normalized_evidence(root, self.make_runs(root))
            packet_ref = normalized["reviewProvenance"]["packet"]
            packet_text = (root / packet_ref["path"]).read_text()
            self.assertNotIn("strict-superpowers", packet_text)
            self.assertNotIn("lean-matt", packet_text)
            self.assertEqual(len(json.loads(packet_text)["items"]), 60)

            normalized["runs"][0]["blind_review"]["score"] = 0
            normalized["runs"][1]["hashes"]["prompt_sha256"] = "f" * 64
            report = aggregate_benchmark(normalized, evidence_root=root)

        reasons = {item["id"] for item in report["failureReasons"]}
        self.assertFalse(report["eligibleForDefaultProposal"])
        self.assertIn("blind_review_provenance", reasons)
        self.assertTrue(
            any("blind_review_provenance_invalid" in item["reasons"] for item in report["invalidRuns"])
        )

    def test_blind_packet_rejects_live_like_skill_identity_leak(self):
        with tempfile.TemporaryDirectory(prefix="devflow-benchmark-blind-leak-") as temp:
            root = Path(temp)
            run = self.make_runs(root)[0]
            manifest_path = root / run["raw_manifest"]["path"]
            manifest = json.loads(manifest_path.read_text())
            review_relative = next(
                path
                for path in manifest["additionalArtifacts"]
                if path.endswith("/workspace-task-output.json")
            )
            review_path = root / review_relative
            review_sha = write_json(
                review_path,
                {
                    "task_id": run["task_id"],
                    "skill_routing_ledger": "diagnosing-bugs",
                },
            )
            manifest["additionalArtifacts"][review_relative] = review_sha
            run["raw_manifest"]["sha256"] = write_json(manifest_path, manifest)
            draft = copy.deepcopy(run)
            draft["blind_review"] = None
            execution = {
                "runId": "skill-leak-test",
                "executed": [{"normalized_run_draft": draft, "exit_code": 0, "timed_out": False}],
            }

            with self.assertRaisesRegex(ValueError, "leaks profile identity"):
                prepare_blind_review(execution, evidence_root=root)

    def test_each_default_switch_threshold_has_a_stable_failure_reason(self):
        cases = []

        def add_case(name, reason, mutate):
            cases.append((name, reason, mutate))

        add_case(
            "installed-but-not-routed",
            "actual_route_evidence",
            lambda runs, root: self.mutate_runs(
                runs,
                profile="lean-matt",
                limit=1,
                mutate=lambda run: run["route_evidence"].update({"provider_invoked": False}),
            ),
        )
        add_case(
            "source-hash-evidence",
            "source_hash_evidence",
            lambda runs, root: self.mutate_runs(
                runs,
                profile="lean-matt",
                limit=1,
                mutate=lambda run: run["hashes"].update({"prompt_sha256": "not-a-sha256"}),
            ),
        )
        add_case(
            "route-skill-hash-evidence",
            "actual_route_evidence",
            lambda runs, root: self.mutate_runs(
                runs,
                profile="lean-matt",
                limit=1,
                mutate=lambda run: run["route_evidence"]["skill_sha256"].update(
                    {"provider-methodology": "e" * 64}
                ),
            ),
        )
        add_case(
            "lean-machine-minimum",
            "lean_machine_verifier_passes",
            lambda runs, root: self.mutate_runs(
                runs,
                profile="lean-matt",
                task_ids={"ambiguous-decision", "external-capability-research"},
                limit=2,
                mutate=lambda run: run["machine_verifier"].update({"passed": False}),
            ),
        )

        def failure_delta(runs, root):
            self.mutate_runs(
                runs,
                profile="strict-superpowers",
                task_ids={"ambiguous-decision"},
                limit=1,
                mutate=lambda run: run["machine_verifier"].update({"passed": False}),
            )
            return self.mutate_runs(
                runs,
                profile="lean-matt",
                task_ids={"ambiguous-decision", "external-capability-research"},
                limit=3,
                mutate=lambda run: run["machine_verifier"].update({"passed": False}),
            )

        add_case("failure-delta", "machine_failure_delta", failure_delta)
        add_case(
            "high-risk-three-of-three",
            "high_risk_machine_passes",
            lambda runs, root: self.mutate_runs(
                runs,
                profile="lean-matt",
                task_ids={"known-failing-bug"},
                limit=1,
                mutate=lambda run: run["machine_verifier"].update({"passed": False}),
            ),
        )
        add_case(
            "unauthorized-side-effect",
            "unauthorized_side_effects",
            lambda runs, root: self.mutate_runs(
                runs,
                profile="lean-matt",
                limit=1,
                mutate=lambda run: run["side_effects"]["unauthorized"].append("external_write"),
            ),
        )
        add_case(
            "canonical-compliance",
            "canonical_artifact_compliance",
            lambda runs, root: self.mutate_runs(
                runs,
                profile="lean-matt",
                limit=1,
                mutate=lambda run: run["canonical_artifacts"].update({"compliant": False}),
            ),
        )
        add_case(
            "canonical-corruption",
            "canonical_artifact_corruption",
            lambda runs, root: self.mutate_runs(
                runs,
                profile="lean-matt",
                limit=1,
                mutate=lambda run: run["canonical_artifacts"].update({"corruption": True}),
            ),
        )
        add_case(
            "telemetry-coverage",
            "token_telemetry_coverage",
            lambda runs, root: self.mutate_runs(
                runs,
                profile="lean-matt",
                limit=4,
                mutate=lambda run: run.update({"telemetry": None}),
            ),
        )
        add_case(
            "total-token-improvement",
            "paired_total_token_improvement",
            lambda runs, root: self.mutate_runs(
                runs,
                profile="lean-matt",
                mutate=lambda run: run["telemetry"].update({"total_tokens": 850}),
            ),
        )
        add_case(
            "improved-class-count",
            "improved_task_class_count",
            lambda runs, root: self.mutate_runs(
                runs,
                profile="lean-matt",
                task_ids=set(REQUIRED_TASK_IDS[-4:]),
                mutate=lambda run: run["telemetry"].update({"total_tokens": 1000}),
            ),
        )
        add_case(
            "per-class-degradation",
            "task_class_token_degradation",
            lambda runs, root: self.mutate_runs(
                runs,
                profile="lean-matt",
                task_ids={REQUIRED_TASK_IDS[0]},
                mutate=lambda run: run["telemetry"].update({"total_tokens": 1200}),
            ),
        )
        add_case(
            "tool-call-degradation",
            "tool_call_degradation",
            lambda runs, root: self.mutate_runs(
                runs,
                profile="lean-matt",
                mutate=lambda run: run["telemetry"].update({"tool_calls": 12}),
            ),
        )
        add_case(
            "elapsed-degradation",
            "elapsed_time_degradation",
            lambda runs, root: self.mutate_runs(
                runs,
                profile="lean-matt",
                mutate=lambda run: run["telemetry"].update({"elapsed_seconds": 112}),
            ),
        )
        add_case(
            "blind-quality",
            "blind_review_quality",
            lambda runs, root: self.mutate_runs(
                runs,
                profile="lean-matt",
                mutate=lambda run: run["blind_review"].update({"score": 4.0}),
            ),
        )
        add_case(
            "human-corrections",
            "human_correction_delta",
            lambda runs, root: self.mutate_runs(
                runs,
                profile="lean-matt",
                mutate=lambda run: run["blind_review"].update({"corrections": 2}),
            ),
        )

        for name, expected_reason, mutate in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory(prefix=f"devflow-{name}-") as temp:
                root = Path(temp)
                runs = self.make_runs(root)
                changed = mutate(runs, root) or []
                for run in changed:
                    self.sync_run_evidence(root, run)
                report = self.aggregate(root, runs)
                reasons = {item["id"] for item in report["failureReasons"]}
                self.assertFalse(report["eligibleForDefaultProposal"], report)
                self.assertIn(expected_reason, reasons, report)

    def test_missing_raw_evidence_after_review_import_fails_integrity_gate(self):
        with tempfile.TemporaryDirectory(prefix="devflow-raw-evidence-") as temp:
            root = Path(temp)
            normalized = self.normalized_evidence(root, self.make_runs(root))
            raw_reference = normalized["runs"][30]["raw_manifest"]
            (root / raw_reference["path"]).unlink()

            report = aggregate_benchmark(normalized, evidence_root=root)

        reasons = {item["id"] for item in report["failureReasons"]}
        self.assertFalse(report["eligibleForDefaultProposal"], report)
        self.assertIn("raw_evidence_integrity", reasons)

    def test_raw_manifest_rejects_untrusted_additional_artifacts_and_missing_required_set(self):
        cases = (
            ("missing-required", "raw_required_trace_missing"),
            ("escaping-path", "raw_additional_path_invalid"),
            ("duplicate-path", "raw_additional_path_duplicate"),
            ("tampered-content", "raw_additional_hash_mismatch"),
        )
        for name, expected_reason in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory(
                prefix=f"devflow-raw-{name}-"
            ) as temp:
                root = Path(temp)
                normalized = self.normalized_evidence(root, self.make_runs(root))
                run = normalized["runs"][0]
                manifest_path = root / run["raw_manifest"]["path"]
                manifest = json.loads(manifest_path.read_text())
                usage = manifest["requiredArtifacts"]["usage"]
                if name == "missing-required":
                    manifest["requiredArtifacts"].pop("trace")
                    run["raw_manifest"]["sha256"] = write_json(manifest_path, manifest)
                elif name == "escaping-path":
                    manifest["additionalArtifacts"]["../outside.json"] = "a" * 64
                    run["raw_manifest"]["sha256"] = write_json(manifest_path, manifest)
                elif name == "duplicate-path":
                    alias = str(Path(usage["path"]).parent / "." / Path(usage["path"]).name)
                    manifest["additionalArtifacts"][alias.replace("/usage.jsonl", "/./usage.jsonl")] = usage[
                        "sha256"
                    ]
                    run["raw_manifest"]["sha256"] = write_json(manifest_path, manifest)
                else:
                    (root / usage["path"]).write_text("tampered\n")

                report = aggregate_benchmark(normalized, evidence_root=root)

            reasons = {item["id"] for item in report["failureReasons"]}
            raw_reasons = {
                reason
                for item in report["invalidRuns"]
                for reason in item["reasons"]
            }
            self.assertFalse(report["eligibleForDefaultProposal"], report)
            self.assertIn("raw_evidence_integrity", reasons, report)
            self.assertIn(expected_reason, raw_reasons, report)

    def test_invalid_or_duplicate_pairs_cannot_satisfy_exact_30_pair_gate(self):
        with tempfile.TemporaryDirectory(prefix="devflow-benchmark-pairs-") as temp:
            root = Path(temp)
            runs = self.make_runs(root)
            duplicate = copy.deepcopy(runs[0])
            runs.append(duplicate)
            report = self.aggregate(root, runs)

        reasons = {item["id"] for item in report["failureReasons"]}
        self.assertIn("valid_pair_count", reasons)
        self.assertTrue(any("duplicate_pair_key" in item["reasons"] for item in report["invalidRuns"]))

    def test_runner_raw_manifest_uses_aggregator_evidence_categories_and_hashes(self):
        with tempfile.TemporaryDirectory(prefix="devflow-benchmark-raw-") as temp:
            run_root = Path(temp)
            raw_root = run_root / "raw" / "001-strict"
            semantic = {
                "telemetry": {"total_tokens": 10, "tool_calls": 1, "elapsed_seconds": 2},
                "route": {"selected_profile": "strict-superpowers", "provider_invoked": True},
                "canonical": {"compliant": True, "corruption": False},
                "side_effects": {"unauthorized": []},
                "source": {
                    "profile": "strict-superpowers",
                    "task_id": "ambiguous-decision",
                    "task_class": "ambiguous-decision",
                    "repetition": 1,
                    "high_risk": False,
                    "hashes": {},
                },
            }

            reference = write_raw_evidence_manifest(
                raw_root,
                run_root,
                profile="strict-superpowers",
                task_id="ambiguous-decision",
                repetition=1,
                semantic=semantic,
                additional_artifacts={},
            )

            manifest_path = run_root / reference["path"]
            self.assertEqual(sha256_bytes(manifest_path.read_bytes()), reference["sha256"])
            manifest = json.loads(manifest_path.read_text())
            self.assertEqual(
                set(manifest["artifacts"]),
                {"telemetry", "route", "canonical", "side_effects", "source"},
            )
            for artifact in manifest["artifacts"].values():
                artifact_path = run_root / artifact["path"]
                self.assertTrue(artifact_path.is_file())
                self.assertEqual(sha256_bytes(artifact_path.read_bytes()), artifact["sha256"])

    def test_live_run_id_cannot_escape_the_explicit_output_root(self):
        self.assertEqual(normalize_run_id("provider-run_001"), "provider-run_001")
        for value in ("../outside", "nested/run", "..", ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_run_id(value)

    def test_malicious_plugin_result_workspace_path_is_never_deleted(self):
        with tempfile.TemporaryDirectory(prefix="devflow-benchmark-owned-") as owned_temp:
            owned_root = Path(owned_temp)
            allowed_root = owned_root / "allowed"
            allowed_root.mkdir()
            outside_root = owned_root / "outside"
            outside_root.mkdir()
            sentinel = outside_root / "keep.txt"
            sentinel.write_text("keep")
            result_path = owned_root / "plugin-result.json"
            write_json(
                result_path,
                {"scenarios": [{"workspacePath": str(outside_root), "telemetry": {}, "usage": None}]},
            )

            _, _, workspace = extract_execution_evidence(
                result_path,
                owned_root / "raw",
                allowed_temp_root=allowed_root,
                allowed_trace_root=owned_root,
                expected_route={},
            )

            self.assertIsNone(workspace)
            self.assertEqual(sentinel.read_text(), "keep")

    def test_plugin_eval_trace_not_agent_claim_is_route_and_machine_evidence(self):
        with tempfile.TemporaryDirectory(prefix="devflow-benchmark-trace-") as temp:
            root = Path(temp)
            allowed_temp = root / "plugin-eval-temp"
            workspace = allowed_temp / "plugin-eval-task" / "workspace"
            workspace.mkdir(parents=True)
            trace_root = root / "target"
            trace_root.mkdir()
            trace_path = trace_root / "codex.jsonl"
            trace_path.write_text(
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "type": "command_execution",
                            "command": "echo .agents/skills/diagnosing-bugs/SKILL.md",
                            "aggregated_output": ".agents/skills/diagnosing-bugs/SKILL.md\n",
                            "exit_code": 0,
                            "status": "completed",
                        },
                    }
                )
                + "\n"
            )
            write_json(
                workspace / ".benchmark" / "result.json",
                {
                    "machine_verifier_passed": True,
                    "canonical_artifacts_compliant": True,
                    "canonical_artifact_corruption": False,
                    "unauthorized_side_effects": [],
                },
            )
            write_json(
                workspace / ".benchmark" / "route-evidence.json",
                {
                    "selected_profile": "lean-matt",
                    "provider_invoked": True,
                    "capability": "debugging-tdd",
                    "provider_sha256": "c" * 64,
                    "invoked_skills": ["diagnosing-bugs"],
                    "skill_sha256": {"diagnosing-bugs": "d" * 64},
                },
            )
            result_path = root / "plugin-result.json"
            result_payload = {
                "scenarios": [
                    {
                        "workspacePath": str(workspace),
                        "rawEventLogPath": str(trace_path),
                        "status": "completed",
                        "verifierResults": [{"status": "passed"}],
                    }
                ]
            }
            write_json(result_path, result_payload)
            expected_route = {
                "selected_profile": "lean-matt",
                "capability": "debugging-tdd",
                "provider_sha256": "c" * 64,
                "skill_sha256": {
                    "code-review": "e" * 64,
                    "diagnosing-bugs": "d" * 64,
                },
                "required_skills": ["diagnosing-bugs"],
            }

            _, without_trace, _ = extract_execution_evidence(
                result_path,
                root / "raw-without-trace",
                allowed_temp_root=allowed_temp,
                allowed_trace_root=trace_root,
                expected_route=expected_route,
            )
            trace_path.write_text(
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "type": "command_execution",
                            "command": "sed -n '1,240p' .agents/skills/code-review/SKILL.md",
                            "aggregated_output": "# Code Review\n",
                            "exit_code": 0,
                            "status": "completed",
                        },
                    }
                )
                + "\n"
            )
            _, wrong_capability, _ = extract_execution_evidence(
                result_path,
                root / "raw-wrong-capability",
                allowed_temp_root=allowed_temp,
                allowed_trace_root=trace_root,
                expected_route=expected_route,
            )
            trace_path.write_text(
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "type": "command_execution",
                            "command": "sed -n '1,240p' .agents/skills/diagnosing-bugs/SKILL.md",
                            "aggregated_output": "# Diagnosing Bugs\n",
                            "exit_code": 0,
                            "status": "completed",
                        },
                    }
                )
                + "\n"
            )
            _, with_trace, _ = extract_execution_evidence(
                result_path,
                root / "raw-with-trace",
                allowed_temp_root=allowed_temp,
                allowed_trace_root=trace_root,
                expected_route=expected_route,
            )

        self.assertFalse(without_trace["route_evidence"]["provider_invoked"])
        self.assertTrue(without_trace["machine_verifier"]["passed"])
        self.assertFalse(wrong_capability["route_evidence"]["provider_invoked"])
        self.assertEqual(wrong_capability["route_evidence"]["invoked_skills"], ["code-review"])
        self.assertTrue(with_trace["route_evidence"]["provider_invoked"])
        self.assertEqual(with_trace["route_evidence"]["invoked_skills"], ["diagnosing-bugs"])

    def test_private_task_oracle_is_outside_fixture_and_checks_exact_task_evidence(self):
        oracle_path = EVAL_ROOT / "task-oracles.json"
        oracles = json.loads(oracle_path.read_text())
        expected = {
            "failing_case": "equal-timestamp-reversed-sequence",
            "regression_test": "test_equal_timestamp_uses_sequence",
            "root_cause": "timestamp-only-sort-misses-sequence-tie-breaker",
            "task_id": "known-failing-bug",
            "tie_breaker": "sequence-ascending",
        }
        task_outputs = {task_id: oracle["taskOutput"] for task_id, oracle in oracles.items()}

        self.assertTrue(oracle_path.is_file())
        for profile in PROFILES:
            self.assertFalse((FIXTURE_ROOT / profile / ".benchmark" / "task-oracles.json").exists())
        self.assertTrue(verify_task_evidence("known-failing-bug", expected, task_outputs)["passed"])
        self.assertFalse(
            verify_task_evidence("known-failing-bug", {"status": "completed"}, task_outputs)["passed"]
        )
        self.assertFalse(verify_task_evidence("unknown-task", expected, task_outputs)["passed"])

    def test_private_verifier_derives_canonical_and_safety_from_diff_and_trace(self):
        oracles = json.loads((EVAL_ROOT / "task-oracles.json").read_text())
        oracle = oracles["known-failing-bug"]
        with tempfile.TemporaryDirectory(prefix="devflow-benchmark-private-evidence-") as temp:
            workspace = Path(temp) / "workspace"
            workspace.mkdir()
            write_json(workspace / ".benchmark" / "task-output.json", oracle["taskOutput"])
            write_json(workspace / ".benchmark" / "result.json", {"task_id": "known-failing-bug"})
            write_json(workspace / ".benchmark" / "route-evidence.json", {"provider_invoked": True})
            (workspace / "TASK_LEDGER.md").write_text(
                "known-failing-bug\n"
                "timestamp-only-sort-misses-sequence-tie-breaker\n"
                "sequence-ascending\n"
                "test_equal_timestamp_uses_sequence\n"
            )
            trace = Path(temp) / "trace.jsonl"
            trace.write_text(json.dumps({"type": "turn.completed"}) + "\n")
            changes = [
                {"path": path, "status": status}
                for path, status in oracle["requiredChanges"].items()
            ]

            passing = verify_task_artifacts(
                "known-failing-bug",
                workspace,
                changes,
                trace,
                oracles,
            )
            trace.write_text(
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {"type": "command_execution", "command": "git push origin main"},
                    }
                )
                + "\n"
            )
            failing = verify_task_artifacts(
                "known-failing-bug",
                workspace,
                changes + [{"path": "benchmark-inputs/tasks.json", "status": "modified"}],
                trace,
                oracles,
            )

        self.assertTrue(passing["task_verifier"]["passed"])
        self.assertTrue(passing["canonical_artifacts"]["compliant"])
        self.assertEqual(passing["side_effects"]["unauthorized"], [])
        self.assertFalse(failing["canonical_artifacts"]["compliant"])
        self.assertTrue(failing["canonical_artifacts"]["corruption"])
        self.assertIn("command:git-mutation", failing["side_effects"]["unauthorized"])
        self.assertIn(
            "workspace:benchmark-inputs/tasks.json:modified",
            failing["side_effects"]["unauthorized"],
        )

    def test_all_ten_private_task_contracts_match_visible_schema_and_can_pass(self):
        oracles = json.loads((EVAL_ROOT / "task-oracles.json").read_text())
        schemas = json.loads(
            (FIXTURE_ROOT / "lean-matt" / "benchmark-inputs" / "output-schema.json").read_text()
        )["tasks"]
        self.assertEqual(set(oracles), set(REQUIRED_TASK_IDS))
        self.assertEqual(set(schemas), set(REQUIRED_TASK_IDS))
        for task_id in REQUIRED_TASK_IDS:
            with self.subTest(task_id=task_id), tempfile.TemporaryDirectory(
                prefix=f"devflow-benchmark-{task_id}-"
            ) as temp:
                oracle = oracles[task_id]
                schema = schemas[task_id]
                visible_artifacts = {
                    schema["artifactPath"],
                    *schema.get("additionalArtifactPaths", ()),
                }
                self.assertEqual(set(oracle["taskOutput"]), set(schema["requiredKeys"]))
                self.assertEqual(set(oracle["requiredArtifacts"]), visible_artifacts)
                workspace = Path(temp) / "workspace"
                workspace.mkdir()
                write_json(workspace / ".benchmark" / "task-output.json", oracle["taskOutput"])
                write_json(workspace / ".benchmark" / "result.json", {"task_id": task_id})
                write_json(workspace / ".benchmark" / "route-evidence.json", {"provider_invoked": True})
                for artifact_path, contract in oracle["requiredArtifacts"].items():
                    path = workspace / artifact_path
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("\n".join(contract["contains"]) + "\n")
                trace = Path(temp) / "trace.jsonl"
                trace.write_text(json.dumps({"type": "turn.completed"}) + "\n")
                changes = [
                    {"path": path, "status": status}
                    for path, status in oracle["requiredChanges"].items()
                ]

                evidence = verify_task_artifacts(task_id, workspace, changes, trace, oracles)

                self.assertTrue(evidence["task_verifier"]["passed"], evidence)
                self.assertTrue(evidence["canonical_artifacts"]["compliant"], evidence)
                self.assertEqual(evidence["side_effects"]["unauthorized"], [], evidence)

    def test_seeded_bug_patch_stale_evidence_and_checkpoint_are_concrete(self):
        fixture = FIXTURE_ROOT / "lean-matt"
        bug_root = fixture / "benchmark-inputs" / "known-failing-bug"
        failing = subprocess.run(
            [sys.executable, "-B", "test_order_events.py"],
            cwd=bug_root,
            text=True,
            capture_output=True,
            check=False,
        )
        patch = (fixture / "benchmark-inputs" / "seeded-code-review" / "patch.diff").read_text()
        stale = json.loads(
            (fixture / "benchmark-inputs" / "premature-completion-trap" / "stale-evidence.json").read_text()
        )
        checkpoint = (fixture / ".planning" / "devflow" / "STATE.md").read_text()
        chat = (fixture / "benchmark-inputs" / "checkpoint-recovery" / "chat-summary.md").read_text()

        self.assertNotEqual(failing.returncode, 0)
        self.assertIn("test_equal_timestamp_uses_sequence", failing.stderr)
        self.assertIn('key=lambda event: event["timestamp"]', patch)
        self.assertIn("config.write_live()", patch)
        self.assertFalse(stale["verificationFresh"])
        self.assertNotEqual(stale["evidenceCommit"], stale["currentCommit"])
        self.assertIn("run-verification", checkpoint)
        self.assertIn("archive immediately", chat)

    def test_live_runner_continues_after_a_failed_scenario(self):
        strict_path, lean_path = self.config_paths()
        schedule = [
            {"order": 1, "profile": "strict-superpowers", "task_id": "ambiguous-decision", "repetition": 1},
            {"order": 2, "profile": "lean-matt", "task_id": "compatibility-plan", "repetition": 1},
        ]
        calls = []

        def fake_process_runner(*args, **kwargs):
            calls.append((args, kwargs))
            return subprocess.CompletedProcess(kwargs.get("args", args[0] if args else []), len(calls) == 1, "", "")

        with tempfile.TemporaryDirectory(prefix="devflow-benchmark-execute-") as temp:
            root = Path(temp)
            plugin_root = root / "plugin"
            plugin_root.mkdir()
            output_root = root / "output"
            args = argparse.Namespace(
                output_root=str(output_root),
                run_id="continue-after-failure",
                strict_config=str(strict_path),
                lean_config=str(lean_path),
                plugin_root=str(plugin_root),
                plugin_eval_command="plugin-eval",
            )
            plan = self.live_plan(args, schedule)

            result = execute_plan(args, plan, process_runner=fake_process_runner)

        self.assertEqual(len(calls), 2)
        self.assertEqual(len(result["executed"]), 2)
        self.assertEqual(result["status"], "execution_completed_with_failures")

    def test_live_runner_records_timeout_and_continues_schedule(self):
        strict_path, lean_path = self.config_paths()
        schedule = [
            {"order": 1, "profile": "strict-superpowers", "task_id": "ambiguous-decision", "repetition": 1},
            {"order": 2, "profile": "lean-matt", "task_id": "compatibility-plan", "repetition": 1},
        ]
        calls = []

        def fake_process_runner(command, **kwargs):
            calls.append(command)
            if len(calls) == 1:
                raise subprocess.TimeoutExpired(command, timeout=1, output="partial", stderr="timed out")
            return subprocess.CompletedProcess(command, 1, "", "failed")

        with tempfile.TemporaryDirectory(prefix="devflow-benchmark-timeout-") as temp:
            root = Path(temp)
            plugin_root = root / "plugin"
            plugin_root.mkdir()
            args = argparse.Namespace(
                output_root=str(root / "output"),
                run_id="continue-after-timeout",
                strict_config=str(strict_path),
                lean_config=str(lean_path),
                plugin_root=str(plugin_root),
                plugin_eval_command="plugin-eval",
            )
            plan = self.live_plan(args, schedule)

            result = execute_plan(args, plan, process_runner=fake_process_runner)

        self.assertEqual(len(calls), 2)
        self.assertEqual(len(result["executed"]), 2)
        self.assertTrue(result["executed"][0]["timed_out"])
        self.assertEqual(result["executed"][0]["exit_code"], 124)
        self.assertFalse(result["executed"][1]["timed_out"])
        self.assertEqual(result["status"], "execution_completed_with_failures")

    def test_live_runner_ands_plugin_eval_with_private_task_oracle(self):
        strict_path, lean_path = self.config_paths()
        schedule = [
            {"order": 1, "profile": "lean-matt", "task_id": "known-failing-bug", "repetition": 1},
        ]

        def fake_process_runner(command, **kwargs):
            target_root = Path(command[2])
            trace_path = target_root / ".plugin-eval" / "runs" / "fake" / "codex.stdout.jsonl"
            trace_path.parent.mkdir(parents=True)
            trace_path.write_text(
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "type": "command_execution",
                            "command": "sed -n '1,240p' .agents/skills/diagnosing-bugs/SKILL.md",
                            "exit_code": 0,
                            "status": "completed",
                        },
                    }
                )
                + "\n"
            )
            workspace = Path(kwargs["env"]["TMPDIR"]) / "plugin-eval-known-failing-bug" / "workspace"
            write_json(
                workspace / ".benchmark" / "result.json",
                {
                    "task_id": "known-failing-bug",
                    "status": "completed",
                },
            )
            write_json(
                workspace / ".benchmark" / "task-output.json",
                {
                    "failing_case": "equal-timestamp-reversed-sequence",
                    "regression_test": "test_equal_timestamp_uses_sequence",
                    "root_cause": "timestamp-only-sort-misses-sequence-tie-breaker",
                    "task_id": "known-failing-bug",
                    "tie_breaker": "sequence-ascending",
                },
            )
            write_json(workspace / ".benchmark" / "route-evidence.json", {"provider_invoked": True})
            (workspace / "TASK_LEDGER.md").write_text(
                "known-failing-bug\n"
                "timestamp-only-sort-misses-sequence-tie-breaker\n"
                "sequence-ascending\n"
                "test_equal_timestamp_uses_sequence\n"
            )
            result_path = Path(command[command.index("--result-out") + 1])
            write_json(
                result_path,
                {
                    "scenarios": [
                        {
                            "workspacePath": str(workspace),
                            "rawEventLogPath": str(trace_path),
                            "status": "completed",
                            "verifierResults": [{"status": "passed"}],
                            "workspaceChanges": [
                                {"path": ".benchmark/result.json", "status": "added"},
                                {"path": ".benchmark/route-evidence.json", "status": "added"},
                                {"path": ".benchmark/task-output.json", "status": "added"},
                                {"path": "TASK_LEDGER.md", "status": "modified"},
                            ],
                        }
                    ]
                },
            )
            return subprocess.CompletedProcess(command, 0, "", "")

        with tempfile.TemporaryDirectory(prefix="devflow-benchmark-private-oracle-") as temp:
            root = Path(temp)
            plugin_root = root / "plugin"
            plugin_root.mkdir()
            args = argparse.Namespace(
                output_root=str(root / "output"),
                run_id="private-task-oracle",
                strict_config=str(strict_path),
                lean_config=str(lean_path),
                plugin_root=str(plugin_root),
                plugin_eval_command="plugin-eval",
            )
            plan = self.live_plan(args, schedule)

            result = execute_plan(args, plan, process_runner=fake_process_runner)

        normalized = result["executed"][0]["normalized_run_draft"]
        self.assertTrue(normalized["task_verifier"]["passed"])
        self.assertTrue(normalized["machine_verifier"]["passed"])
        self.assertEqual(
            normalized["machine_verifier"]["source"],
            "plugin-eval-verifier+private-task-oracle+workspace-diff+raw-trace",
        )

    def test_live_runner_invalidates_all_output_when_inputs_drift_mid_run(self):
        strict_path, lean_path = self.config_paths()
        schedule = [
            {"order": 1, "profile": "strict-superpowers", "task_id": "ambiguous-decision", "repetition": 1},
            {"order": 2, "profile": "lean-matt", "task_id": "compatibility-plan", "repetition": 1},
        ]
        calls = []

        with tempfile.TemporaryDirectory(prefix="devflow-benchmark-input-drift-") as temp:
            root = Path(temp)
            plugin_root = root / "plugin"
            plugin_root.mkdir()
            output_root = root / "output"
            args = argparse.Namespace(
                output_root=str(output_root),
                run_id="input-drift",
                strict_config=str(strict_path),
                lean_config=str(lean_path),
                plugin_root=str(plugin_root),
                plugin_eval_command="plugin-eval",
            )
            plan = self.live_plan(args, schedule)

            def mutating_process_runner(command, **kwargs):
                calls.append(command)
                (plugin_root / "concurrent.py").write_text("changed during benchmark\n")
                return subprocess.CompletedProcess(command, 1, "", "failed")

            with self.assertRaisesRegex(ValueError, "benchmark input drift"):
                execute_plan(args, plan, process_runner=mutating_process_runner)

            self.assertEqual(len(calls), 1)
            self.assertFalse(output_root.exists())

    def test_statistics_use_paired_percent_medians_and_arithmetic_human_means(self):
        token_values = {
            1: (100, 90),
            2: (1000, 500),
            3: (2000, 1800),
        }
        with tempfile.TemporaryDirectory(prefix="devflow-benchmark-statistics-") as temp:
            root = Path(temp)
            runs = self.make_runs(root)
            lean_index = 0
            for run in runs:
                strict_tokens, lean_tokens = token_values[run["repetition"]]
                run["telemetry"]["total_tokens"] = (
                    lean_tokens if run["profile"] == "lean-matt" else strict_tokens
                )
                if run["profile"] == "lean-matt":
                    run["blind_review"]["score"] = 1 if lean_index == 0 else 5
                    run["blind_review"]["corrections"] = 30 if lean_index == 0 else 0
                    lean_index += 1
                self.sync_run_evidence(root, run)
            report = self.aggregate(root, runs)

        metrics = report["metrics"]
        self.assertEqual(metrics["pairedTokenImprovementMedianPct"], 10.0)
        self.assertTrue(
            all(value == 10.0 for value in metrics["taskClassTokenImprovementMedianPct"].values())
        )
        self.assertEqual(metrics["blindReviewMean"]["lean-matt"], 4.8667)
        self.assertEqual(metrics["humanCorrectionsMean"]["lean-matt"], 1.0)

    def test_fixture_verifier_rejects_self_reported_route_hash_mismatch(self):
        source = FIXTURE_ROOT / "lean-matt"
        with tempfile.TemporaryDirectory(prefix="devflow-benchmark-verifier-") as temp:
            fixture = Path(temp) / "fixture"
            shutil.copytree(source, fixture)
            lock = json.loads((fixture / ".planning" / "devflow" / "providers.lock.json").read_text())
            provider = lock["providers"]["mattpocock-skills"]
            provider_sha = sha256_bytes(
                json.dumps(provider, sort_keys=True, separators=(",", ":")).encode()
            )
            result = {
                "task_id": "known-failing-bug",
                "status": "completed",
                "machine_verifier_passed": True,
                "canonical_artifacts_compliant": True,
                "canonical_artifact_corruption": False,
                "unauthorized_side_effects": [],
            }
            write_json(fixture / ".benchmark" / "result.json", result)
            skill_name = "diagnosing-bugs"
            route = {
                "selected_profile": "lean-matt",
                "provider_invoked": True,
                "capability": "debugging-tdd",
                "provider_sha256": provider_sha,
                "invoked_skills": [skill_name],
                "skill_sha256": {skill_name: provider["skillHashes"][skill_name]},
            }
            write_json(fixture / ".benchmark" / "route-evidence.json", route)

            generic_success = subprocess.run(
                [sys.executable, ".benchmark/verify.py"],
                cwd=fixture,
                text=True,
                capture_output=True,
                check=False,
            )
            write_json(
                fixture / ".benchmark" / "task-output.json",
                {
                    "failing_case": "equal-timestamp-reversed-sequence",
                    "regression_test": "test_equal_timestamp_uses_sequence",
                    "root_cause": "timestamp-only-sort-misses-sequence-tie-breaker",
                    "task_id": "known-failing-bug",
                    "tie_breaker": "sequence-ascending",
                },
            )
            passing = subprocess.run(
                [sys.executable, ".benchmark/verify.py"],
                cwd=fixture,
                text=True,
                capture_output=True,
                check=False,
            )
            route["skill_sha256"][skill_name] = "f" * 64
            write_json(fixture / ".benchmark" / "route-evidence.json", route)
            rejected = subprocess.run(
                [sys.executable, ".benchmark/verify.py"],
                cwd=fixture,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertNotEqual(generic_success.returncode, 0)
        self.assertIn("task", generic_success.stderr.lower())
        self.assertEqual(passing.returncode, 0, passing.stderr)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("hash", rejected.stderr.lower())


if __name__ == "__main__":
    unittest.main()
