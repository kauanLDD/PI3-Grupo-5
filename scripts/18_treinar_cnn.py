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
    parser.add_argument("--variante", help="nome em experimentos_cnn do YAML; sobrescreve chaves de cnn")
    parser.add_argument("--semente", type=int,
                        help="semente de treino no lugar de seed do YAML; o bootstrap da avaliação mantém seed (decisão 0010)")
    parser.add_argument("--lista-propria",
                        help="nome em treino_lista_propria.variantes do YAML; treina também com pontos da nossa lista")
    return parser.parse_args()


def aplicar_variante(cfg, nome):
    parametros = dict(cfg["cnn"])
    if nome is None:
        return parametros
    mudancas = cfg.get("experimentos_cnn", {}).get(nome)
    if mudancas is None:
        raise ValueError(f"variante inexistente em experimentos_cnn: {nome}")
    desconhecidas = set(mudancas) - set(parametros) - {"aumento"}
    if desconhecidas:
        raise ValueError(f"chaves desconhecidas na variante {nome}: {sorted(desconhecidas)}")
    return {**parametros, **mudancas}


def treinar_misto(cfg, nome, candidatos, divisao, pasta, entrada, parametros, semente, device, registrar):
    """Treino com cubos da V2 e da nossa lista (docs/19, seção 6)."""
    misto, volumes, lado = cfg["treino_lista_propria"], cfg["caminhos"]["volumes"], parametros["patch_size"]
    treino = sorted(divisao.loc[divisao.particao.eq("treino"), "seriesuid"])
    diferenca = cnn.conferir_recorte(candidatos, treino[:misto["exames_conferencia"]], pasta, volumes, lado,
                                     misto["tolerancia_conferencia"])
    print(f"conferência do recorte na V2, {misto['exames_conferencia']} exames de treino: "
          f"maior diferença {diferenca:.2e}", flush=True)
    blocos = pd.read_csv(entrada["candidatos_proprios"], chunksize=misto["linhas_por_bloco"])
    selecionados, contagem = cnn.selecionar_misto(
        candidatos, blocos, divisao, pd.read_csv(entrada["anotacoes"]), pd.read_csv(entrada["excluidas"]),
        parametros["negativos_por_positivo"], misto["fracao_negativos_propria"],
        misto["variantes"][nome]["vizinhos"], semente)
    grupos = selecionados.groupby(["origem", "grupo"]).size().to_dict()
    print(f"nossa lista nos exames de treino: {contagem}", flush=True)
    print(f"treino: {len(selecionados)} cubos, {grupos}", flush=True)
    if len(selecionados) > misto["maximo_cubos"]:
        raise ValueError(f"{len(selecionados)} cubos passam do máximo de {misto['maximo_cubos']}")
    inicio = perf_counter()
    cubos = cnn.montar_cubos(selecionados, candidatos, pasta, volumes, lado)
    exames, montagem = selecionados.seriesuid.nunique(), perf_counter() - inicio
    print(f"cubos montados de {exames} exames, com erro 0, descartados 0; {montagem:.0f} s", flush=True)
    modelo, historico = cnn.treinar_cubos(cubos, selecionados["class"].to_numpy(np.int64), parametros,
                                          semente, device, registrar)
    extras = {"conferencia_recorte": diferenca, "lista_propria_treino": contagem,
              "treino_grupos": {f"{o}_{g}": int(n) for (o, g), n in grupos.items()},
              "treino_exames": int(exames), "montagem_cubos_segundos": montagem}
    return modelo, selecionados, historico, extras


def conferir_reproducao(anterior, destino, recibo):
    antigo = json.loads((anterior / "execucao.json").read_text(encoding="utf-8"))
    for chave in ("parametros", "dados_sha256", "pesos_sha256"):
        if antigo[chave] != recibo[chave]:
            raise ValueError(f"reproducao divergiu em {chave}")
    verificados = []
    for particao in ("validacao",):
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
    parametros = aplicar_variante(cfg, args.variante)
    if parametros["epochs"] < 1 or parametros["negativos_por_positivo"] < 1:
        raise ValueError("epochs e negativos_por_positivo precisam ser positivos")
    destino = args.saida.resolve()
    if destino.exists():
        raise ValueError(f"preserve a execução existente e escolha uma pasta nova: {destino}")
    if args.reproduzir_de and not (args.reproduzir_de / "execucao.json").is_file():
        raise ValueError("execucao anterior ausente")
    if args.lista_propria:
        misto = cfg["treino_lista_propria"]
        if args.lista_propria not in misto["variantes"]:
            raise ValueError(f"variante inexistente em treino_lista_propria: {args.lista_propria}")
        if args.variante != misto["variante_rede"] or args.dados:
            raise ValueError(f"--lista-propria usa --variante {misto['variante_rede']} e os dados do config")
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
    ativos = divisao.loc[divisao.particao.isin(["treino", "validacao"])]
    cnn.conferir_origem(pasta, caminhos["volumes"], ativos.seriesuid)
    for uid in ativos.seriesuid:
        entrada[f"patches/{uid}"] = pasta / f"{uid}.npz"
    for nome in avaliacao_oficial.FONTES:
        entrada[f"avaliador/{nome}"] = avaliacao_oficial.ORIGEM / nome
    origem = config.RAIZ / "notebooks/curvafroc_pesquisa.ipynb"
    entrada["pesquisa_cnn"] = origem
    entrada["configuracao_execucao"] = args.config or config.CAMINHO
    if args.lista_propria:
        entrada["candidatos_proprios"] = caminhos["candidatos_proprios"]
    for caminho in entrada.values():
        if not caminho.is_file():
            raise FileNotFoundError(caminho)
    device = parametros["device"]
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda" and not torch.cuda.is_available():
        raise ValueError("CUDA solicitada, mas indisponivel")
    # A semente de treino muda amostra de negativos, sorteio do sampler, aumento e pesos iniciais.
    # A da avaliação fica em seed, para todas as sementes usarem as mesmas reamostras por exame.
    semente = cfg["seed"] if args.semente is None else args.semente
    config.fixar_semente(semente)
    cnn.fixar_determinismo(semente, parametros["threads"], device)
    registro = {**parametros, "device": device, "seed": semente, "torch": torch.__version__,
                "determinismo": "estrito" if device == "cpu" else "parcial_gpu",
                "gpu": torch.cuda.get_device_name() if device == "cuda" else "nenhuma",
                "arquitetura": "CNN3D_3conv_16_32_64", "escopo": args.escopo,
                "variante": args.variante or "base", "aumento": parametros.get("aumento", False),
                "bootstrap": cfg["avaliacao"]["bootstrap_reamostras"],
                "confianca": cfg["avaliacao"]["intervalo_confianca"],
                "preprocessamento": "V2_normalizado_0_1_mascara_pulmao_1mm_crop_central",
                "sampler": "WeightedRandomSampler_replacement", "max_marcas_oficial": 100}
    if args.semente is not None:
        registro["seed_avaliacao"] = cfg["seed"]
    if args.lista_propria:
        registro["lista_propria"] = args.lista_propria
        registro["treino_lista_propria"] = json.dumps({
            "fracao_negativos_propria": cfg["treino_lista_propria"]["fracao_negativos_propria"],
            **cfg["treino_lista_propria"]["variantes"][args.lista_propria]})
    versao_dados = hashlib.sha256(json.dumps({
        nome: rastreamento.sha256(p) for nome, p in entrada.items()
        if nome in ("divisao", "candidatos", "anotacoes", "excluidas", "candidatos_proprios")
        or nome.startswith("patches/")
    }, sort_keys=True).encode()).hexdigest()
    registro["dados_sha256"] = versao_dados
    destino.mkdir(parents=True)
    with rastreamento.iniciar(cfg, f"CNN3D {args.escopo}", "treinamento_cnn", registro,
                             entrada) as (cliente, run_id):
        cliente.set_tag(run_id, "teste_utilizado", "false")
        cliente.set_tag(run_id, "avaliacao", "LUNA16_oficial_python3")
        if args.reproduzir_de:
            cliente.set_tag(run_id, "reproducao_de", json.loads(
                (args.reproduzir_de / "execucao.json").read_text(encoding="utf-8"))["run_id"])
        print(f"MLflow: {run_id}; dados: {versao_dados}; device: {device}", flush=True)

        def registrar(linha):
            print(f"Epoca {linha['epoch']}: loss={linha['train_loss']:.6f}", flush=True)
            for nome in ("train_loss",):
                cliente.log_metric(run_id, nome, linha[nome], step=linha["epoch"])

        inicio = perf_counter()
        extras = {}
        if args.lista_propria:
            modelo, selecionados, historico, extras = treinar_misto(
                cfg, args.lista_propria, candidatos, divisao, pasta, entrada, parametros, semente, device,
                registrar)
        else:
            modelo, selecionados, historico = cnn.treinar(candidatos, divisao, pasta, parametros,
                                                         semente, device, registrar)
        metricas = {"treino_segundos": perf_counter() - inicio,
                    "treino_candidatos": len(selecionados),
                    "treino_positivos": int(selecionados["class"].sum())}
        peso_hash = cnn.hash_pesos(modelo)
        torch.save({"state_dict": modelo.cpu().state_dict(), "parametros": parametros,
                    "seed": semente, "dados_sha256": versao_dados,
                    "run_id": run_id, "divisao_sha256": rastreamento.sha256(entrada["divisao"]),
                    "candidatos_sha256": rastreamento.sha256(entrada["candidatos"]),
                    **({"candidatos_proprios_sha256": rastreamento.sha256(entrada["candidatos_proprios"]),
                        "lista_propria": args.lista_propria} if args.lista_propria else {})},
                   destino / "modelo.pt")
        restaurado = cnn.CNN3D(parametros["dropout_rate"])
        restaurado.load_state_dict(torch.load(destino / "modelo.pt", map_location="cpu",
                                             weights_only=True)["state_dict"])
        if cnn.hash_pesos(restaurado) != peso_hash:
            raise ValueError("modelo persistido diverge do modelo treinado")
        restaurado.to(device)
        selecionados.to_csv(destino / "candidatos_treino.csv", index=False)
        historico.to_csv(destino / "historico.csv", index=False)
        divisao.to_csv(destino / "divisao.csv", index=False)
        for particao in ("validacao",):
            print(f"Prevendo todos os candidatos de {particao}", flush=True)
            previsoes = cnn.prever(restaurado, candidatos, divisao, particao, pasta, parametros, device)
            previsoes.to_csv(destino / f"probabilidades_{particao}.csv", index=False)
            exames = divisao.loc[divisao.particao.eq(particao), "seriesuid"].tolist()
            medidas = {"exames": len(exames),
                       "candidatos": len(previsoes), "positivos": int(previsoes["class"].sum())}
            medidas.update(avaliacao_oficial.avaliar(
                previsoes, exames, entrada["anotacoes"], entrada["excluidas"],
                destino / f"avaliacao_{particao}", cfg["seed"],
                cfg["avaliacao"]["bootstrap_reamostras"], cfg["avaliacao"]["intervalo_confianca"]))
            metricas.update({f"{particao}_{k}": float(v) for k, v in medidas.items()})
        recibo = {"run_id": run_id, "parametros": registro, "dados_sha256": versao_dados,
                  "pesos_sha256": peso_hash, "metricas": metricas, "teste_utilizado": False,
                  "avaliacao_froc": "oficial", "escopo": args.escopo,
                  "entrada_teste_usada_no_treino": False}
        if extras:
            recibo["treino_lista_propria"] = extras
        if args.reproduzir_de:
            recibo["reproducao"] = conferir_reproducao(args.reproduzir_de, destino, recibo)
            cliente.log_metric(run_id, "reproducao_identica", 1)
        for nome, valor in metricas.items():
            cliente.log_metric(run_id, nome, float(valor))
        (destino / "execucao.json").write_text(json.dumps(recibo, indent=2), encoding="utf-8")
        cliente.log_artifact(run_id, str(origem), artifact_path="origem")
        cliente.log_artifacts(run_id, str(destino), artifact_path="cnn")
    print(json.dumps({"run_id": run_id, "pesos_sha256": peso_hash,
                      "validacao_cpm": metricas["validacao_cpm"], "saida": str(destino)}, indent=2), flush=True)


if __name__ == "__main__":
    main()
