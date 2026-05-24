from __future__ import annotations


def print_text_report(report: dict) -> None:
    print(f"Context pressure: {report['contextPressure']}")
    print(f"Codex home: {report['codexHome']}")
    print_repo(report)
    print_project_signals(report)
    print_section("Findings", report["findings"] or [{"message": "No global context pressure detected."}])
    print_section("Recommendations", report["recommendations"] or [{"title": "No recommendations.", "reason": ""}])
    print_actions(report["actions"] or [{"id": "none", "title": "No actions available"}])


def print_repo(report: dict) -> None:
    if report.get("repo"):
        print(f"Repo: {report['repo']}")


def print_project_signals(report: dict) -> None:
    if report["projectSignals"]:
        print("Project signals: " + ", ".join(report["projectSignals"]))


def print_section(title: str, items: list[dict]) -> None:
    print(f"\n{title}:")
    for item in items:
        suffix = f" {item['reason']}" if item.get("reason") else ""
        label = item.get("title") or item.get("message")
        print(f"- {label}.{suffix}")


def print_actions(actions: list[dict]) -> None:
    print("\nActions:")
    for action in actions:
        print(f"- {action['id']}: {action['title']}")
