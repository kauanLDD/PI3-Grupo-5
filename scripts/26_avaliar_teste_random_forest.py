"""Avalia uma única vez no teste o Random Forest centro congelado, sem treinar nem ajustar. Decisão 0009."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import joblib
import numpy as np
import pandas as pd
import sklearn

import config
from detection.procedencia_recortes import assinatura
from experimentos import avaliacao_oficial, rastreamento

# Identidades registradas na decisão 0009 antes de abrir o teste pela segunda vez.
MODELO_SHA256 = "58ba90fde1c7f6bbd7073ce8e6b6e6a9c6232591bddc03f7c758e57f27ff9b57"
# Os mesmos arquivos que o checkpoint da CNN gravou e que o script 20 conferiu no teste.
DIVISAO_SHA256 = "45b22b5e1d5468417243b8f8de5dd94d864a35e28f34e4759a8bef238a10d300"
CANDIDATOS_SHA256 = "8c168d9113f97a3cfd609d18703c50a62067f8f61fe4833be1650a02baa43c82"
AVALIACAO_CNN = config.RAIZ / "modelos/cnn_lr_3e-4_teste_final"


def treino_centro():
    # O script 25 é a fonte das features; carregá-lo garante o mesmo cálculo do treino.
    arquivo = Path(__file__).resolve().parent / "25_treinar_random_forest_centro.py"
    spec = importlib.util.spec_from_file_location("treinar_random_forest_centro", arquivo)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def conferir_congelado(caminhos, modelo):
    for nome, caminho, esperado in (("modelo", modelo, MODELO_SHA256),
                                    ("divisao", caminhos["divisao"], DIVISAO_SHA256),
                                    ("candidatos", caminhos["luna16_candidatos"], CANDIDATOS_SHA256)):
        if rastreamento.sha256(caminho) != esperado:
            raise ValueError(f"{nome} difere da identidade congelada na decisao 0009")


def conferir_origem(pasta, volumes, exames):
    for uid in exames:
        with np.load(Path(pasta) / f"{uid}.npz", allow_pickle=False) as dados:
            if "procedencia" not in dados:
                raise ValueError(f"recortes sem procedencia: {uid}")
            if json.loads(str(dados["procedencia"])) != assinatura(Path(volumes) / f"{uid}.mha", (34, 34, 34)):
                raise ValueError(f"recortes desatualizados: {uid}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, help="YAML com os caminhos desta máquina; padrão configuracao/config.yaml")
    args = parser.parse_args()
    cfg = config.carregar(args.config)
    config.fixar_semente(cfg["seed"])
    caminhos = cfg["caminhos"]
    origem = caminhos["random_forest_centro"]
    destino = caminhos["random_forest_centro_teste"]
    if destino.exists():
        raise ValueError(f"o teste do Random Forest ja foi executado; preserve {destino}")
    conferir_congelado(caminhos, origem / "modelo.joblib")
    pacote = joblib.load(origem / "modelo.joblib")
    parametros = pacote["parametros"]
    if parametros["sklearn"] != sklearn.__version__:
        raise ValueError(f"modelo salvo com scikit-learn {parametros['sklearn']}, ambiente tem {sklearn.__version__}")
    lados = [int(lado) for lado in parametros["lados"].split(",")]
    if lados != cfg["random_forest_centro"]["lados"]:
        raise ValueError("lados do modelo congelado diferem do config.yaml")
    protocolo_cnn = json.loads((AVALIACAO_CNN / "avaliacao.json").read_text(encoding="utf-8"))
    avaliacao = cfg["avaliacao"]
    if (protocolo_cnn["bootstrap"], protocolo_cnn["confianca"]) != (
            avaliacao["bootstrap_reamostras"], avaliacao["intervalo_confianca"]):
        raise ValueError("bootstrap ou confianca diferem da avaliacao da CNN no teste")

    divisao = pd.read_csv(caminhos["divisao"])
    uids = sorted(divisao.loc[divisao.particao.eq("teste"), "seriesuid"])
    exames_cnn = (AVALIACAO_CNN / "seriesuids.csv").read_text(encoding="utf-8").split()
    if uids != exames_cnn:
        raise ValueError("exames de teste diferem dos avaliados na CNN")
    candidatos = pd.read_csv(caminhos["luna16_candidatos"])
    pasta = caminhos["processado"] / "patches"
    conferir_origem(pasta, caminhos["volumes"], uids)

    entradas = {"modelo": origem / "modelo.joblib", "divisao": caminhos["divisao"],
                "candidatos": caminhos["luna16_candidatos"], "anotacoes": caminhos["luna16_anotacoes"],
                "excluidas": caminhos["luna16_anotacoes_excluidas"],
                "configuracao_execucao": args.config or config.CAMINHO}
    entradas.update({f"patches/{u}": pasta / f"{u}.npz" for u in uids})
    for nome in avaliacao_oficial.FONTES:
        entradas[f"avaliador/{nome}"] = avaliacao_oficial.ORIGEM / nome
    registro = {"treino_run_id": pacote["run_id"], "modelo_sha256": MODELO_SHA256,
                "seed": protocolo_cnn["seed"], "bootstrap": avaliacao["bootstrap_reamostras"],
                "confianca": avaliacao["intervalo_confianca"], "max_marcas_oficial": 100,
                "decisao": "0009", "uso_do_teste": 2}
    with rastreamento.iniciar(cfg, "Random Forest centro teste final", "avaliacao_final",
                             registro, entradas) as (cliente, run_id):
        cliente.set_tag(run_id, "teste_utilizado", "true")
        cliente.set_tag(run_id, "avaliacao", "LUNA16_oficial_python3")
        cliente.set_tag(run_id, "treino_run_id", pacote["run_id"])
        print(f"MLflow: {run_id}; {len(uids)} exames de teste", flush=True)
        teste = treino_centro().caracteristicas(divisao, candidatos, pasta, "teste", lados,
                                                cfg["random_forest_centro"]["processos"])
        if list(teste.columns.drop(["candidate_id", "seriesuid", "classe_luna16"])) != pacote["features"]:
            raise ValueError("features do teste diferem das do modelo congelado")
        modelo = pacote["modelo"]
        positiva = int(np.flatnonzero(modelo.classes_ == 1)[0])
        previsoes = teste[["candidate_id", "seriesuid"]].copy()
        posicao = candidatos.loc[teste.candidate_id, ["coordX", "coordY", "coordZ", "class"]]
        previsoes[["coordX", "coordY", "coordZ", "class"]] = posicao.to_numpy()
        previsoes["probability"] = modelo.predict_proba(teste[pacote["features"]])[:, positiva]
        metricas = avaliacao_oficial.avaliar(
            previsoes, uids, caminhos["luna16_anotacoes"], caminhos["luna16_anotacoes_excluidas"],
            destino, protocolo_cnn["seed"], avaliacao["bootstrap_reamostras"],
            avaliacao["intervalo_confianca"])
        previsoes.drop(columns="class").to_csv(destino / "probabilidades_teste.csv", index=False)
        for nome, valor in metricas.items():
            cliente.log_metric(run_id, nome, valor)
        (destino / "execucao.json").write_text(json.dumps({
            "run_id": run_id, "treino_run_id": pacote["run_id"], "modelo_sha256": MODELO_SHA256,
            "teste_utilizado": True, "uso_do_teste": 2, "decisao": "0009", "metricas": metricas,
        }, indent=2), encoding="utf-8")
        cliente.log_artifacts(run_id, str(destino), artifact_path="teste_final")
    print(json.dumps({"run_id": run_id, "cpm": metricas["cpm"], "saida": str(destino)}, indent=2), flush=True)


if __name__ == "__main__":
    main()
