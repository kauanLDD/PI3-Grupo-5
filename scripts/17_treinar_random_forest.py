"""Treina o Random Forest no treino e salva escores de validação, sem acessar o teste."""

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from time import perf_counter

import joblib
import pandas as pd
import sklearn

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config
from detection.features import COLUNAS
from experimentos import floresta, rastreamento
from experimentos.preparacao import conferir


def main():
    cfg = config.carregar()
    config.fixar_semente(cfg["seed"])
    metricas, entradas = conferir(cfg)
    treino = pd.read_csv(cfg["caminhos"]["caracteristicas_treino"])
    validacao = pd.read_csv(cfg["caminhos"]["caracteristicas_validacao"])
    # Recusamos vazamento antes de gastar tempo no ajuste do modelo.
    for coluna in ("paciente", "seriesuid", "candidate_id"):
        if set(treino[coluna]) & set(validacao[coluna]):
            raise ValueError(f"{coluna} compartilhado entre treino e validacao")
    parametros = dict(cfg["random_forest"])
    registro = {**parametros, "seed": cfg["seed"], "features": ",".join(COLUNAS),
                "lista": "candidates_V2", "sklearn": sklearn.__version__}
    destino = cfg["caminhos"]["random_forest"]
    destino.parent.mkdir(parents=True, exist_ok=True)
    with rastreamento.iniciar(cfg, "Random Forest V2 inicial", "treinamento", registro,
                             entradas) as (cliente, run_id):
        print(f"MLflow: {run_id}", flush=True)
        print(f"Treinando com {len(treino)} candidatos de {treino.paciente.nunique()} pacientes",
              flush=True)
        inicio = perf_counter()
        modelo = floresta.treinar(treino, parametros, cfg["seed"])
        metricas["treino_segundos"] = perf_counter() - inicio
        previsoes = floresta.prever_validacao(modelo, validacao, treino)
        print(f"Treino concluido; {len(previsoes)} probabilidades de validacao", flush=True)
        with TemporaryDirectory(dir=destino.parent) as temporario:
            pasta = Path(temporario)
            joblib.dump({"modelo": modelo, "features": list(COLUNAS), "run_id": run_id,
                         "sklearn": sklearn.__version__, "parametros": registro},
                        pasta / "modelo.joblib", compress=3)
            previsoes.to_csv(pasta / "probabilidades_validacao.csv", index=False)
            recibo = {"run_id": run_id, "parametros": registro, "metricas": metricas,
                      "teste_utilizado": False, "avaliacao_froc": "pendente"}
            (pasta / "execucao.json").write_text(json.dumps(recibo, indent=2))
            # A cópia persistida precisa reproduzir exatamente os escores em memória.
            restaurado = joblib.load(pasta / "modelo.joblib")
            pd.testing.assert_frame_equal(
                previsoes, floresta.prever_validacao(restaurado["modelo"], validacao, treino)
            )
            for nome, valor in metricas.items():
                cliente.log_metric(run_id, nome, float(valor))
            cliente.log_artifacts(run_id, str(pasta), artifact_path="treinamento")
            destino.mkdir(parents=True, exist_ok=True)
            for arquivo in pasta.iterdir():
                arquivo.replace(destino / arquivo.name)
    print(json.dumps(recibo, indent=2))


if __name__ == "__main__":
    main()
