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
    "dev-flow-refresh",
]

STRICT_SUPERPOWERS_BASE_PROJECT_SKILLS = [
    "using-superpowers",
    "brainstorming",
    "writing-plans",
    "test-driven-development",
    "systematic-debugging",
    "requesting-code-review",
    "verification-before-completion",
]

STRICT_SUPERPOWERS_CONDITIONAL_PROJECT_SKILLS = [
    "receiving-code-review",
    "using-git-worktrees",
    "executing-plans",
    "subagent-driven-development",
    "finishing-a-development-branch",
]

STRICT_SUPERPOWERS_PROJECT_SKILLS = [
    *STRICT_SUPERPOWERS_BASE_PROJECT_SKILLS,
    *STRICT_SUPERPOWERS_CONDITIONAL_PROJECT_SKILLS,
]

REQUIRED_SKILLS = {"superpowers": STRICT_SUPERPOWERS_BASE_PROJECT_SKILLS}

DEVELOPER_SKILLS = {"plugin-eval": ["evaluate-plugin"]}

STRICT_RECOMMENDED_SUPERPOWERS_SKILLS = STRICT_SUPERPOWERS_CONDITIONAL_PROJECT_SKILLS

REQUIRED_CLI_TOOLS = ["openspec"]

GSD_ROADMAP_SKILLS = [
    "gsd-new-project",
    "gsd-discuss-phase",
    "gsd-plan-phase",
    "gsd-execute-phase",
    "gsd-progress",
    "gsd-verify-work",
]

GSD_ROADMAP_AGENTS = [
    "gsd-phase-researcher.toml",
    "gsd-planner.toml",
    "gsd-plan-checker.toml",
    "gsd-executor.toml",
]

OPENSPEC_WORKFLOW_SKILLS = [
    "openspec-propose",
    "openspec-explore",
    "openspec-apply-change",
    "openspec-update-change",
    "openspec-sync-specs",
    "openspec-archive-change",
]

LEGACY_OPENSPEC_SKILLS = OPENSPEC_WORKFLOW_SKILLS
