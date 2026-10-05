"""Confere as features existentes e registra sua preparação no MLflow."""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config
from detection.features import COLUNAS
from experimentos import rastreamento
from experimentos.preparacao import conferir


def main():
    cfg = config.carregar()
    config.fixar_semente(cfg["seed"])
    metricas, entradas = conferir(cfg)
    parametros = {
        "seed": cfg["seed"], "patch": json.dumps(cfg["candidatos"]["patch"]),
        "features": ",".join(COLUNAS), "lista": "candidates_V2",
        "registro": "conferencia de arquivos existentes; sem treinamento",
    }
    with rastreamento.iniciar(
        cfg, "Conferir features de treino e validacao", "preparacao", parametros, entradas
    ) as (cliente, run_id):
        for nome, valor in metricas.items():
            cliente.log_metric(run_id, nome, float(valor))
        recibo = {"run_id": run_id, "tipo": "preparacao", "metricas": metricas}
    destino = cfg["caminhos"]["mlflow_preparacao"]
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(".tmp")
    temporario.write_text(json.dumps(recibo, indent=2))
    temporario.replace(destino)
    print(json.dumps(recibo, indent=2))


if __name__ == "__main__":
    main()
