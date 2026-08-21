from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_required_repository_boundaries_exist() -> None:
    required = {
        "containers/transformation",
        "docs/adr",
        "docs/architecture",
        "docs/development",
        "docs/operations",
        "docs/security",
        "infrastructure/bicep/environments",
        "infrastructure/bicep/modules",
        "infrastructure/parameters",
        "orchestration/adf",
        "scripts",
        "sql/migrations",
        "tests/integration",
    }
    assert not [path for path in required if not (ROOT / path).is_dir()]


def test_safe_environment_template_and_ignore_contract() -> None:
    template = (ROOT / ".env.example").read_text(encoding="utf-8")
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "SDPA_ENVIRONMENT=development" in template
    assert ".env\n" in ignore.replace("\r\n", "\n")
    assert "!.env.example" in ignore
    assert ".venv/" in ignore
