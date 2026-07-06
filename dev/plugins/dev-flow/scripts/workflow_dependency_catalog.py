from __future__ import annotations


PROJECT_ORCHESTRATOR_SKILLS = [
    "ai-native-tech-plan",
    "capability-research",
    "claude-code-delegate",
    "project-orchestrator",
    "project-setup",
    "feature-intake",
    "change-plan",
    "execute-task",
    "verify-and-archive",
    "workflow-doctor",
    "checkpoint-compact",
    "context-health-check",
    "context-tool-audit",
    "codex-updater",
    "plugin-project-migration",
]

REQUIRED_SUPERPOWERS_PROJECT_SKILLS = [
    "brainstorming",
    "writing-plans",
    "test-driven-development",
    "verification-before-completion",
]

REQUIRED_SKILLS = {
    "superpowers": [
        "using-superpowers",
        *REQUIRED_SUPERPOWERS_PROJECT_SKILLS,
    ],
}

DEVELOPER_SKILLS = {"plugin-eval": ["evaluate-plugin"]}

STRICT_RECOMMENDED_SUPERPOWERS_SKILLS = [
    "using-git-worktrees",
    "executing-plans",
    "subagent-driven-development",
    "requesting-code-review",
    "finishing-a-development-branch",
]

REQUIRED_CLI_TOOLS = ["openspec"]

REQUIRED_GSD_SKILLS = [
    "gsd-new-project",
    "gsd-discuss-phase",
    "gsd-plan-phase",
    "gsd-execute-phase",
    "gsd-progress",
    "gsd-verify-work",
]

REQUIRED_GSD_AGENTS = [
    "gsd-phase-researcher.toml",
    "gsd-planner.toml",
    "gsd-plan-checker.toml",
    "gsd-executor.toml",
]

OPENSPEC_WORKFLOW_SKILLS = [
    "openspec-propose",
    "openspec-explore",
    "openspec-apply-change",
    "openspec-sync-specs",
    "openspec-archive-change",
]

LEGACY_OPENSPEC_SKILLS = OPENSPEC_WORKFLOW_SKILLS
