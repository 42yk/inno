import ast
from pathlib import Path
from sys import stdlib_module_names


def test_models_dto_and_rules_use_only_standard_library_or_domain_imports():
    """Adding any unapproved external or upper-layer import would break pure-rule isolation."""
    package_root = Path(__file__).parents[2] / "review_analytics"
    checked_files = [package_root / "models.py", package_root / "dto.py", *sorted((package_root / "rules").glob("*.py"))]
    allowed_domain_prefixes = ("review_analytics.models", "review_analytics.dto", "review_analytics.rules")

    for path in checked_files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        imports.extend(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names)
        assert all(
            name.split(".", 1)[0] in stdlib_module_names or name.startswith(allowed_domain_prefixes)
            for name in imports
        ), path


def test_import_allowlist_rejects_unlisted_external_packages():
    """A blacklist would let unrelated SDKs through as long as their names were omitted."""
    allowed_domain_prefixes = ("review_analytics.models", "review_analytics.dto", "review_analytics.rules")

    assert "requests" not in stdlib_module_names
    assert "numpy" not in stdlib_module_names
    assert not "requests".startswith(allowed_domain_prefixes)
    assert not "numpy".startswith(allowed_domain_prefixes)


def test_cli_does_not_import_repository_client_or_output_implementations():
    """Composition wiring must not turn CLI parsing and presentation into an infrastructure layer."""
    cli_path = Path(__file__).parents[2] / "review_analytics" / "cli.py"
    tree = ast.parse(cli_path.read_text(encoding="utf-8"), filename=str(cli_path))
    imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    imports.extend(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    forbidden = (
        "review_analytics.repositories",
        "review_analytics.clients",
        "review_analytics.output",
        "sqlite3",
        "google",
        "matplotlib",
        "openpyxl",
    )

    assert not [name for name in imports if name.startswith(forbidden)]
