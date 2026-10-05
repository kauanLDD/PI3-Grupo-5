"""Abre o painel local do MLflow usando os caminhos do projeto."""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config
from experimentos.rastreamento import uri_local


def main():
    cfg = config.carregar()
    subprocess.run([
        sys.executable, "-m", "mlflow", "server",
        "--backend-store-uri", uri_local(cfg),
        "--default-artifact-root", cfg["caminhos"]["mlflow_artefatos"].resolve().as_uri(),
        "--host", cfg["rastreamento"]["host"], "--port", str(cfg["rastreamento"]["porta"]),
        "--no-serve-artifacts",
    ], check=True)


if __name__ == "__main__":
    main()
