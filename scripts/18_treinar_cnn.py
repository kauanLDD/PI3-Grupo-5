"""Treina, rastreia e avalia a CNN3D com o programa oficial LUNA16."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from time import perf_counter

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score, roc_auc_score
import torch

import config
from experimentos import avaliacao_oficial, cnn, rastreamento


def argumentos():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, help="YAML completo; padrão configuracao/config.yaml")
    parser.add_argument("--dados", type=Path, help="pasta com divisao.csv, candidates_V2.csv, annotations*.csv e patches/")
    parser.add_argument("--saida", type=Path, required=True, help="pasta nova para preservar cada execução")
    parser.add_argument("--escopo", default="divisao_completa", help="identificação explícita da população avaliada")
    parser.add_argument("--reproduzir-de", type=Path, help="confere pesos, previsões e FROC contra execução anterior")
    return parser.parse_args()


def metricas_classificacao(dados):
    real = dados["class"].to_numpy()
    previsto = dados.probability.ge(0.5).to_numpy()
    metricas = {"precision": precision_score(real, previsto, zero_division=0),
                "recall": recall_score(real, previsto, zero_division=0),
                "f1": f1_score(real, previsto, zero_division=0)}
    if len(np.unique(real)) == 2:
        metricas.update(auc_roc=roc_auc_score(real, dados.probability),
                        average_precision=average_precision_score(real, dados.probability))
    return {k: float(v) for k, v in metricas.items()}


def conferir_reproducao(anterior, destino, recibo):
    antigo = json.loads((anterior / "execucao.json").read_text(encoding="utf-8"))
    for chave in ("parametros", "dados_sha256", "pesos_sha256"):
        if antigo[chave] != recibo[chave]:
            raise ValueError(f"reproducao divergiu em {chave}")
    verificados = []
    for particao in ("validacao", "teste"):
        for nome in (f"probabilidades_{particao}.csv", f"avaliacao_{particao}/curva_froc_completa.csv",
                     f"avaliacao_{particao}/froc_predicoes_bootstrapping.csv"):
            if rastreamento.sha256(anterior / nome) != rastreamento.sha256(destino / nome):
                raise ValueError(f"reproducao divergiu em {nome}")
            verificados.append(nome)
    return {"execucao_anterior": antigo["run_id"], "pesos_identicos": True,
            "arquivos_identicos": verificados}


def main():
    args = argumentos()
    cfg = config.carregar(args.config)
    parametros = dict(cfg["cnn"])
    if parametros["epochs"] < 1 or parametros["negativos_por_positivo"] < 1:
        raise ValueError("epochs e negativos_por_positivo precisam ser positivos")
    destino = args.saida.resolve()
    if destino.exists():
        raise ValueError(f"preserve a execução existente e escolha uma pasta nova: {destino}")
    if args.reproduzir_de and not (args.reproduzir_de / "execucao.json").is_file():
        raise ValueError("execucao anterior ausente")
    caminhos = cfg["caminhos"]
    if args.dados:
        dados = args.dados.resolve()
        entrada = {"divisao": dados / "divisao.csv", "candidatos": dados / "candidates_V2.csv",
                   "anotacoes": dados / "annotations.csv", "excluidas": dados / "annotations_excluded.csv"}
        pasta = dados / "patches"
    else:
        entrada = {"divisao": caminhos["divisao"], "candidatos": caminhos["luna16_candidatos"],
                   "anotacoes": caminhos["luna16_anotacoes"], "excluidas": caminhos["luna16_anotacoes_excluidas"]}
        pasta = caminhos["processado"] / "patches"
    divisao = pd.read_csv(entrada["divisao"])
    cnn.conferir_divisao(divisao)
    candidatos = pd.read_csv(entrada["candidatos"])
    colunas = ["seriesuid", "coordX", "coordY", "coordZ", "class"]
    if (not set(colunas).issubset(candidatos.columns) or candidatos[colunas].isna().any().any()
            or not candidatos["class"].isin([0, 1]).all()
            or not np.isfinite(candidatos[["coordX", "coordY", "coordZ"]]).all().all()):
        raise ValueError("lista V2 invalida")
    if not set(divisao.seriesuid).issubset(set(candidatos.seriesuid)):
        raise ValueError("exames da divisao ausentes na lista V2")
    for uid in divisao.seriesuid:
        entrada[f"patches/{uid}"] = pasta / f"{uid}.npz"
    for nome in avaliacao_oficial.FONTES:
        entrada[f"avaliador/{nome}"] = avaliacao_oficial.ORIGEM / nome
    origem = config.RAIZ / "notebooks/curvafroc_pesquisa.ipynb"
    entrada["pesquisa_cnn"] = origem
    entrada["configuracao_execucao"] = args.config or config.CAMINHO
    for caminho in entrada.values():
        if not caminho.is_file():
            raise FileNotFoundError(caminho)
    config.fixar_semente(cfg["seed"])
    cnn.fixar_determinismo(cfg["seed"], parametros["threads"])
    device = parametros["device"]
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda" and not torch.cuda.is_available():
        raise ValueError("CUDA solicitada, mas indisponivel")
    registro = {**parametros, "device": device, "seed": cfg["seed"], "torch": torch.__version__,
                "arquitetura": "CNN3D_3conv_16_32_64", "escopo": args.escopo,
                "bootstrap": cfg["avaliacao"]["bootstrap_reamostras"],
                "confianca": cfg["avaliacao"]["intervalo_confianca"],
                "preprocessamento": "V2_normalizado_0_1_mascara_pulmao_1mm_crop_central",
                "sampler": "WeightedRandomSampler_replacement", "max_marcas_oficial": 100}
    versao_dados = hashlib.sha256(json.dumps({
        nome: rastreamento.sha256(p) for nome, p in entrada.items()
        if nome in ("divisao", "candidatos", "anotacoes", "excluidas") or nome.startswith("patches/")
    }, sort_keys=True).encode()).hexdigest()
    registro["dados_sha256"] = versao_dados
    destino.mkdir(parents=True)
    with rastreamento.iniciar(cfg, f"CNN3D {args.escopo}", "treinamento_cnn", registro,
                             entrada) as (cliente, run_id):
        cliente.set_tag(run_id, "teste_utilizado", "true")
        cliente.set_tag(run_id, "avaliacao", "LUNA16_oficial_python3")
        if args.reproduzir_de:
            cliente.set_tag(run_id, "reproducao_de", json.loads(
                (args.reproduzir_de / "execucao.json").read_text(encoding="utf-8"))["run_id"])
        print(f"MLflow: {run_id}; dados: {versao_dados}; device: {device}", flush=True)

        def registrar(linha):
            print(f"Epoca {linha['epoch']}: loss={linha['train_loss']:.6f}", flush=True)
            for nome in ("train_loss", "train_accuracy"):
                cliente.log_metric(run_id, nome, linha[nome], step=linha["epoch"])

        inicio = perf_counter()
        modelo, selecionados, historico = cnn.treinar(candidatos, divisao, pasta, parametros,
                                                     cfg["seed"], device, registrar)
        metricas = {"treino_segundos": perf_counter() - inicio,
                    "treino_candidatos": len(selecionados),
                    "treino_positivos": int(selecionados["class"].sum())}
        peso_hash = cnn.hash_pesos(modelo)
        torch.save({"state_dict": modelo.cpu().state_dict(), "parametros": parametros,
                    "seed": cfg["seed"], "dados_sha256": versao_dados,
                    "run_id": run_id}, destino / "modelo.pt")
        restaurado = cnn.CNN3D(parametros["dropout_rate"])
        restaurado.load_state_dict(torch.load(destino / "modelo.pt", map_location="cpu",
                                             weights_only=True)["state_dict"])
        if cnn.hash_pesos(restaurado) != peso_hash:
            raise ValueError("modelo persistido diverge do modelo treinado")
        restaurado.to(device)
        selecionados.to_csv(destino / "candidatos_treino.csv", index=False)
        historico.to_csv(destino / "historico.csv", index=False)
        divisao.to_csv(destino / "divisao.csv", index=False)
        for particao in ("validacao", "teste"):
            print(f"Prevendo todos os candidatos de {particao}", flush=True)
            previsoes = cnn.prever(restaurado, candidatos, divisao, particao, pasta, parametros, device)
            previsoes.to_csv(destino / f"probabilidades_{particao}.csv", index=False)
            exames = divisao.loc[divisao.particao.eq(particao), "seriesuid"].tolist()
            medidas = {**metricas_classificacao(previsoes), "exames": len(exames),
                       "candidatos": len(previsoes), "positivos": int(previsoes["class"].sum())}
            medidas.update(avaliacao_oficial.avaliar(
                previsoes, exames, entrada["anotacoes"], entrada["excluidas"],
                destino / f"avaliacao_{particao}", cfg["seed"],
                cfg["avaliacao"]["bootstrap_reamostras"], cfg["avaliacao"]["intervalo_confianca"]))
            metricas.update({f"{particao}_{k}": float(v) for k, v in medidas.items()})
        recibo = {"run_id": run_id, "parametros": registro, "dados_sha256": versao_dados,
                  "pesos_sha256": peso_hash, "metricas": metricas, "teste_utilizado": True,
                  "avaliacao_froc": "oficial", "escopo": args.escopo,
                  "entrada_teste_usada_no_treino": False}
        if args.reproduzir_de:
            recibo["reproducao"] = conferir_reproducao(args.reproduzir_de, destino, recibo)
            cliente.log_metric(run_id, "reproducao_identica", 1)
        for nome, valor in metricas.items():
            cliente.log_metric(run_id, nome, float(valor))
        (destino / "execucao.json").write_text(json.dumps(recibo, indent=2), encoding="utf-8")
        cliente.log_artifact(run_id, str(origem), artifact_path="origem")
        cliente.log_artifacts(run_id, str(destino), artifact_path="cnn")
    print(json.dumps({"run_id": run_id, "pesos_sha256": peso_hash,
                      "teste_cpm": metricas["teste_cpm"], "saida": str(destino)}, indent=2), flush=True)


if __name__ == "__main__":
    main()
