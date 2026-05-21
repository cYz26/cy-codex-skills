from __future__ import annotations


PROJECT_ORCHESTRATOR_SKILLS = [
    "project-orchestrator",
    "project-setup",
    "feature-intake",
    "change-plan",
    "execute-task",
    "verify-and-archive",
    "workflow-doctor",
    "checkpoint-compact",
    "context-tool-audit",
]

REQUIRED_SUPERPOWERS_PROJECT_SKILLS = [
    "brainstorming",
    "writing-plans",
    "test-driven-development",
    "verification-before-completion",
]

REQUIRED_SKILLS = {
    "superpowers": REQUIRED_SUPERPOWERS_PROJECT_SKILLS,
}

DEVELOPER_SKILLS = {"plugin-eval": ["evaluate-plugin"]}

REQUIRED_CLI_TOOLS = ["openspec", "gsd-sdk"]

REQUIRED_GSD_SKILLS = [
    "gsd-new-project",
    "gsd-discuss-phase",
    "gsd-plan-phase",
    "gsd-execute-phase",
    "gsd-verify-work",
]

REQUIRED_GSD_AGENTS = [
    "gsd-phase-researcher.toml",
    "gsd-planner.toml",
    "gsd-plan-checker.toml",
    "gsd-executor.toml",
]

REQUIRED_OPENSPEC_SKILLS = [
    "openspec-propose",
    "openspec-explore",
    "openspec-apply-change",
    "openspec-archive-change",
]
