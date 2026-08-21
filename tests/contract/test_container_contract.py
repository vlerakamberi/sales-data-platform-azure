from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_container_is_local_non_root_and_excludes_sensitive_context() -> None:
    dockerfile = (ROOT / "containers/transformation/Dockerfile").read_text(encoding="utf-8")
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")

    assert "FROM python:3.13-slim" in dockerfile
    assert "USER runtime" in dockerfile
    assert (
        'ENTRYPOINT ["python", "-m", "sales_data_platform_azure.transformation.cli"]' in dockerfile
    )
    for excluded in (".git", ".venv", ".env", "infrastructure", "tests"):
        assert excluded in dockerignore
