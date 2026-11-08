"""Supressão suave contra a supressão dura a 16 mm, na validação e nos pares de nódulos próximos do treino.

Na validação lê as notas que o script 31 gravou para as três sementes. Nos exames de treino com um
par de nódulos a até 16 mm, pontua a nossa lista com a rede antiga (semente 42) e só conta nódulos
mantidos. Não usa o teste. Desenho em docs/19, seção 10.
"""

import importlib.util
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
from scipy.spatial.distance import pdist
import SimpleITK as sitk
import torch

import config
from detection import candidatos as det
from experimentos import avaliacao_oficial, cnn


def script(nome, arquivo):
    spec = importlib.util.spec_from_file_location(nome, Path(__file__).resolve().parent / arquivo)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def exames_com_par(nodulos, distancia):
    return sorted(uid for uid, g in nodulos.groupby("seriesuid")
                  if len(g) > 1 and (pdist(g[det.COLUNAS].to_numpy(float)) <= distancia).any())


def primeiras(marcas, quantas):
    return (marcas.sort_values("probability", ascending=False, kind="stable")
            .groupby("seriesuid", sort=False).head(quantas))


def aplicar_regra(tabela, pares_treino, queda_maxima):
    medias = tabela.groupby("variante").cpm.mean()
    mantidos = pares_treino.groupby("variante").mantido.sum()
    passaram = [f for f in medias.index if f != "dura_16"
                and mantidos[f] > mantidos["dura_16"] and medias["dura_16"] - medias[f] <= queda_maxima]
    return {"cpm_media": {v: float(m) for v, m in medias.items()},
            "nodulos_mantidos_nos_pares_do_treino": {v: int(m) for v, m in mantidos.items()},
            "nodulos_nos_exames_com_par": int(pares_treino.groupby("variante").size().iloc[0]),
            "queda_maxima_cpm": queda_maxima,
            "passaram": passaram,
            "adotada": max(passaram, key=lambda f: medias[f]) if passaram else "dura_16"}


def pontuar_pares(cfg, fase, uids, listas):
    caminhos = cfg["caminhos"]
    pasta = config.RAIZ / fase["modelo_pares"]
    pacote = torch.load(pasta / "modelo.pt", map_location="cpu", weights_only=True)
    parametros = pacote["parametros"]
    device = "cuda" if torch.cuda.is_available() else "cpu"
    cnn.fixar_determinismo(pacote["seed"], parametros["threads"], device)
    modelo = cnn.CNN3D(parametros["dropout_rate"])
    modelo.load_state_dict(pacote["state_dict"])
    modelo.to(device)
    propria = listas.ler_lista_propria(caminhos["candidatos_proprios"], set(uids))
    if sorted(propria.seriesuid.unique()) != uids:
        raise ValueError("exames de treino com par sem candidato na nossa lista")
    partes = []
    for uid, grupo in propria.groupby("seriesuid", sort=True):
        imagem = sitk.ReadImage(str(caminhos["volumes"] / f"{uid}.mha"))
        notas = listas.pontuar_exame(modelo, imagem, grupo[det.COLUNAS].to_numpy(float), parametros,
                                     cfg["lista_propria"]["recortes_por_vez"], device)
        partes.append(grupo.assign(probability=notas))
    return pd.concat(partes, ignore_index=True)


def main():
    cfg = config.carregar()
    config.fixar_semente(cfg["seed"])
    caminhos, fase, avaliacao = cfg["caminhos"], cfg["supressao_suave"], cfg["avaliacao"]
    saida, completa = caminhos["supressao_suave"], caminhos["supressao_suave_completa"]
    if saida.exists() or completa.exists():
        raise ValueError(f"preserve a avaliação anterior e apague-a à mão: {saida} / {completa}")
    comparar = script("comparar_froc", "27_comparar_froc.py")
    conferir_exames = script("supressao_lista_propria", "34_supressao_lista_propria.py").conferir_exames
    raio, quantas = float(fase["raio_mm"]), fase["marcas_por_exame"]

    def suavizar(notas, forma):
        return det.suprimir_suave(notas, raio, forma, quantas, fase["sigma"])

    linhas, pares = [], []
    for semente, pasta in cfg["supressao_lista_propria"]["sementes"].items():
        notas = pd.read_csv(config.RAIZ / pasta / "probabilidades.csv")
        dura = comparar.carregar(caminhos["supressao_lista_propria_completa"] / f"raio_{fase['raio_mm']}" / str(semente))
        uids = dura["exames"]
        if sorted(notas.seriesuid.unique()) != uids:
            raise ValueError(f"semente {semente}: notas cobrem outros exames")
        medida = comparar.resumir(("dura_16", "-"), [dura, dura], avaliacao["intervalo_confianca"])[0]["dura_16"]
        linhas.append({"variante": "dura_16", "semente": semente, "cpm": medida["cpm"],
                       "cpm_ic_inferior": medida["cpm_ic"][0], "cpm_ic_superior": medida["cpm_ic"][1],
                       **{f"sens_{fp}": s for fp, s in medida["sensibilidade"].items()}})
        for forma in fase["formas"]:
            destino = completa / forma / str(semente)
            avaliacao_oficial.avaliar(suavizar(notas, forma), uids, caminhos["luna16_anotacoes"],
                                      caminhos["luna16_anotacoes_excluidas"], destino, cfg["seed"],
                                      avaliacao["bootstrap_reamostras"], avaliacao["intervalo_confianca"])
            dados = comparar.carregar(destino)
            conferir_exames(dados, dura)
            modelos, par, _ = comparar.resumir((forma, "dura_16"), [dados, dura], avaliacao["intervalo_confianca"])
            linhas.append({"variante": forma, "semente": semente, "cpm": modelos[forma]["cpm"],
                           "cpm_ic_inferior": modelos[forma]["cpm_ic"][0], "cpm_ic_superior": modelos[forma]["cpm_ic"][1],
                           **{f"sens_{fp}": s for fp, s in modelos[forma]["sensibilidade"].items()}})
            pares.append({"variante": forma, "semente": semente, "contra": "dura_16",
                          "diferenca_cpm": par["diferenca_cpm"], "ic_inferior": par["diferenca_ic"][0],
                          "ic_superior": par["diferenca_ic"][1]})
            print(f"{forma}, semente {semente}: CPM {modelos[forma]['cpm']:.3f}, contra a dura "
                  f"{par['diferenca_cpm']:+.3f} ({par['diferenca_ic'][0]:+.3f} a {par['diferenca_ic'][1]:+.3f})",
                  flush=True)

    divisao = pd.read_csv(caminhos["divisao"])
    treino = set(divisao.loc[divisao.particao.eq("treino"), "seriesuid"])
    nodulos = pd.read_csv(caminhos["luna16_anotacoes"])
    nodulos = nodulos[nodulos.seriesuid.isin(treino)].reset_index(drop=True)
    uids = exames_com_par(nodulos, fase["distancia_pares_mm"])
    nodulos = nodulos[nodulos.seriesuid.isin(uids)].reset_index(drop=True)
    notas = pontuar_pares(cfg, fase, uids, script("avaliar_lista_propria", "31_avaliar_lista_propria_cnn.py"))
    print(f"exames de treino com par lidos {len(uids)}, com erro 0, descartados 0; "
          f"nódulos {len(nodulos)}; pontos pontuados {len(notas)}", flush=True)
    variantes = {"sem_supressao": primeiras(notas, quantas),
                 "dura_16": primeiras(det.suprimir_vizinhos(notas, raio), quantas),
                 **{f: suavizar(notas, f) for f in fase["formas"]}}
    pares_treino = pd.concat([nodulos[["seriesuid", *det.COLUNAS, "diameter_mm"]]
                              .assign(variante=v, mantido=det.alcancados(nodulos, marcas))
                              for v, marcas in variantes.items()], ignore_index=True)
    completa.mkdir(parents=True, exist_ok=True)
    notas.to_csv(completa / "notas_exames_com_par.csv", index=False)

    tabela, pares = pd.DataFrame(linhas), pd.DataFrame(pares)
    regra = aplicar_regra(tabela, pares_treino[pares_treino.variante.ne("sem_supressao")], fase["queda_maxima_cpm"])
    regra["nodulos_mantidos_sem_supressao"] = int(pares_treino.loc[pares_treino.variante.eq("sem_supressao"),
                                                                   "mantido"].sum())
    saida.mkdir(parents=True)
    tabela.to_csv(saida / "validacao.csv", index=False)
    pares.to_csv(saida / "diferencas_pareadas.csv", index=False)
    pares_treino.to_csv(saida / "pares_treino.csv", index=False)
    (saida / "resumo.json").write_text(json.dumps({
        "teste_utilizado": False, "exames_treino_com_par": len(uids), **regra},
        indent=2, ensure_ascii=False), encoding="utf-8")
    print(tabela[["variante", "semente", "cpm"]].round(3).to_string(index=False), flush=True)
    print(json.dumps(regra, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
