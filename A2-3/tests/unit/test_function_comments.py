from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_FILES = (
    PROJECT_ROOT / "main.py",
    *sorted((PROJECT_ROOT / "review_analytics").rglob("*.py")),
)


def test_every_production_function_has_an_immediately_preceding_role_comment():
    """A new or edited function must not hide its purpose from source readers."""
    missing: list[str] = []

    for path in PRODUCTION_FILES:
        source_lines = path.read_text(encoding="utf-8").splitlines()
        tree = ast.parse("\n".join(source_lines), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            first_line = min(
                [node.lineno, *(decorator.lineno for decorator in node.decorator_list)]
            )
            preceding_line = source_lines[first_line - 2].strip() if first_line > 1 else ""
            if not preceding_line.startswith("#") or not preceding_line.removeprefix("#").strip():
                relative_path = path.relative_to(PROJECT_ROOT)
                missing.append(f"{relative_path}:{node.lineno}:{node.name}")

    assert not missing, "함수 역할 주석 누락:\n" + "\n".join(sorted(missing))
