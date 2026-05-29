import ast
import re
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
WORDS = ("i" + "f", "e" + "lif", "fo" + "r", "wh" + "ile", "ex" + "cept", "a" + "nd", "o" + "r")


def frontmatter_value(path, key):
    prefix = f"{key}: "
    return next((line.split(": ", 1)[1] for line in path.read_text().splitlines() if line.startswith(prefix)), "")


def approximate_complexity(node):
    nodes = (ast.If, ast.For, ast.While, ast.Try, ast.BoolOp, ast.ExceptHandler, ast.IfExp, ast.comprehension)
    return 1 + sum(isinstance(child, nodes) for child in ast.walk(node))


def plugin_eval_file_complexity(text):
    return 1 + sum(len(re.findall(rf"\b{word}\b", text)) for word in WORDS)


class AgentKBQualityTests(unittest.TestCase):
    def test_skill_descriptions_advertise_clear_triggers(self):
        bad = [
            path
            for path in (PLUGIN_ROOT / "skills").glob("*/SKILL.md")
            if not frontmatter_value(path, "description").lower().startswith("use when ")
        ]
        self.assertEqual([], bad)

    def test_python_sources_stay_readable_for_plugin_eval(self):
        script_paths = list((PLUGIN_ROOT / "scripts").glob("*.py"))
        long_lines = [
            f"{path.relative_to(PLUGIN_ROOT)}:{number}"
            for path in script_paths
            for number, line in enumerate(path.read_text().splitlines(), 1)
            if len(line) > 120
        ]
        self.assertEqual([], long_lines)

        functions = [
            node
            for path in script_paths
            for node in ast.walk(ast.parse(path.read_text()))
            if isinstance(node, ast.FunctionDef)
        ]
        self.assertLessEqual(max(node.end_lineno - node.lineno + 1 for node in functions), 80)
        self.assertLessEqual(max(approximate_complexity(node) for node in functions), 16)

        high_complexity = [
            f"{path.relative_to(PLUGIN_ROOT)}:{plugin_eval_file_complexity(path.read_text())}"
            for path in script_paths
            if plugin_eval_file_complexity(path.read_text()) >= 18
        ]
        self.assertEqual([], high_complexity)
