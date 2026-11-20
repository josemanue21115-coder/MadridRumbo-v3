from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dockerfile_instala_y_arranca_api():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "FROM python:3.11-slim" in dockerfile
    assert "pip install -r requirements.txt" in dockerfile
    assert "uvicorn app:app" in dockerfile


def test_dockerfile_publica_y_resuelve_port():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "EXPOSE 8000" in dockerfile
    assert "${PORT:-8000}" in dockerfile
    assert "--host 0.0.0.0" in dockerfile


def test_dockerignore_excluye_secretos_y_artifactos():
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    excluidos = set(dockerignore)
    assert ".env" in excluidos
    assert "tests" in excluidos
    assert "docs" in excluidos
    assert "specs" in excluidos
    assert "chroma" in excluidos
