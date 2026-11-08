"""Junta a rede antiga e a rede treinada com a nossa lista, cada uma com três sementes, nas duas listas.

Não treina nem avalia: lê as avaliações oficiais que os scripts 18 e 31 gravaram. Compara as duas
redes semente com semente, nas mesmas reamostras por exame, e aplica a regra fixada no config.yaml
(seção sementes_lista_propria) antes de rodar.
"""

import importlib.util
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config

LISTAS = {"v2": "V2", "propria": "Nossa lista inteira"}
CORES = {"antiga": "#b5651d", "uniforme": "#1764a8"}
NOMES = {"antiga": "Rede antiga", "uniforme": "Rede A (com a nossa lista)"}


def script(nome, arquivo):
    spec = importlib.util.spec_from_file_location(nome, Path(__file__).resolve().parent / arquivo)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def pastas_de_avaliacao(modelo, completa):
    return {"v2": config.RAIZ / modelo / "avaliacao_validacao",
            "propria": config.RAIZ / completa / "sem_supressao"}


def conferir_redes(redes, sementes_cnn):
    for nome, por_semente in redes.items():
        recibos = [json.loads((config.RAIZ / modelo / "execucao.json").read_text(encoding="utf-8"))
                   for modelo, _ in por_semente.values()]
        sementes_cnn.conferir_configuracao(recibos)
        gravadas = [r["parametros"]["seed"] for r in recibos]
        if gravadas != list(por_semente):
            raise ValueError(f"{nome}: semente gravada {gravadas} difere da declarada {list(por_semente)}")


def comparar(redes, comparar_froc, pareamento, confianca):
    linhas, pares = [], []
    for semente in redes["uniforme"]:
        nova = pastas_de_avaliacao(*redes["uniforme"][semente])
        antiga = pastas_de_avaliacao(*redes["antiga"][semente])
        for lista in LISTAS:
            dados = [comparar_froc.carregar(nova[lista]), comparar_froc.carregar(antiga[lista])]
            pareamento(*dados)
            modelos, par, _ = comparar_froc.resumir(("uniforme", "antiga"), dados, confianca)
            for rede, medida in modelos.items():
                linhas.append({"rede": rede, "semente": semente, "lista": lista, "cpm": medida["cpm"],
                               "cpm_ic_inferior": medida["cpm_ic"][0], "cpm_ic_superior": medida["cpm_ic"][1],
                               **{f"sens_{fp}": s for fp, s in medida["sensibilidade"].items()}})
            pares.append({"semente": semente, "lista": lista, "diferenca_cpm": par["diferenca_cpm"],
                          "ic_inferior": par["diferenca_ic"][0], "ic_superior": par["diferenca_ic"][1],
                          "fracao_reamostras_maior": par["fracao_reamostras_maior"]})
    return pd.DataFrame(linhas), pd.DataFrame(pares)


def aplicar_regra(tabela, pares, queda_maxima):
    media = tabela.groupby(["rede", "lista"]).cpm.agg(["mean", "std"])
    propria_sobe = media.loc[("uniforme", "propria"), "mean"] > media.loc[("antiga", "propria"), "mean"]
    pares_positivos = bool(pares.loc[pares.lista.eq("propria"), "diferenca_cpm"].gt(0).all())
    queda_v2 = media.loc[("antiga", "v2"), "mean"] - media.loc[("uniforme", "v2"), "mean"]
    return {"media_desvio": {f"{r}_{l}": {"media": float(m), "desvio_padrao_amostral": float(d)}
                             for (r, l), (m, d) in media.iterrows()},
            "condicao_1_media_nossa_lista_sobe": bool(propria_sobe),
            "condicao_1_pareadas_positivas_nas_tres": pares_positivos,
            "queda_media_cpm_v2": float(queda_v2), "queda_maxima_cpm_v2": queda_maxima,
            "condicao_2_v2_dentro_do_limite": bool(queda_v2 <= queda_maxima),
            "confirmada": bool(propria_sobe and pares_positivos and queda_v2 <= queda_maxima)}


def desenhar(tabela, destino):
    figura, eixos = plt.subplots(1, 2, figsize=(9, 3.8), sharey=True)
    for eixo, (lista, titulo) in zip(eixos, LISTAS.items()):
        for deslocamento, rede in zip((-0.12, 0.12), ("antiga", "uniforme")):
            parte = tabela[tabela.lista.eq(lista) & tabela.rede.eq(rede)].sort_values("semente")
            x = np.arange(len(parte)) + deslocamento
            eixo.errorbar(x, parte.cpm, yerr=[parte.cpm - parte.cpm_ic_inferior, parte.cpm_ic_superior - parte.cpm],
                          fmt="o" if rede == "uniforme" else "s", color=CORES[rede], capsize=3,
                          markeredgecolor="white", label=NOMES[rede])
            eixo.axhline(parte.cpm.mean(), color=CORES[rede], linewidth=1, linestyle="--")
        eixo.set_xticks(range(3), [f"semente {s}" for s in sorted(tabela.semente.unique())])
        eixo.set_title(titulo, fontsize=10)
        eixo.yaxis.set_major_formatter(lambda v, _: f"{v:.1f}".replace(".", ","))
        eixo.grid(axis="y", alpha=0.25)
        for lado in ("top", "right"):
            eixo.spines[lado].set_visible(False)
    eixos[0].set_ylabel("CPM na validação (IC95%)")
    eixos[0].set_ylim(0.3, 0.95)
    eixos[1].legend(loc="lower right", fontsize=8, frameon=False)
    figura.text(0.01, 0.01, "Linha tracejada: média das três sementes. 89 exames, 111 nódulos, avaliador oficial.",
                fontsize=7, color="#5c5c5c")
    figura.tight_layout(rect=(0, 0.04, 1, 1))
    figura.savefig(destino / "cpm_por_semente.png", dpi=200)
    plt.close(figura)


def main():
    cfg = config.carregar()
    redes = cfg["sementes_lista_propria"]["redes"]
    if list(redes["antiga"]) != list(redes["uniforme"]):
        raise ValueError("as duas redes precisam das mesmas sementes")
    faltando = [str(caminho) for rede in redes.values() for modelo, completa in rede.values()
                for caminho in pastas_de_avaliacao(modelo, completa).values() if not caminho.is_dir()]
    if faltando:
        raise FileNotFoundError(f"avaliações ausentes: {faltando}")
    conferir_redes(redes, script("resumir_sementes", "28_resumir_sementes_cnn.py"))
    comparar_froc = script("comparar_froc", "27_comparar_froc.py")
    tabela, pares = comparar(redes, comparar_froc, comparar_froc.comparacao_validacao().conferir_pareamento,
                             cfg["avaliacao"]["intervalo_confianca"])
    regra = aplicar_regra(tabela, pares, cfg["sementes_lista_propria"]["queda_maxima_cpm_v2"])
    destino = cfg["caminhos"]["sementes_lista_propria"]
    destino.mkdir(parents=True, exist_ok=True)
    tabela.to_csv(destino / "sementes.csv", index=False)
    pares.to_csv(destino / "diferencas_pareadas.csv", index=False)
    (destino / "resumo.json").write_text(json.dumps({
        "conjunto": "validacao", "teste_utilizado": False,
        "redes": {r: {str(s): p for s, p in v.items()} for r, v in redes.items()}, **regra},
        indent=2, ensure_ascii=False), encoding="utf-8")
    desenhar(tabela, destino)
    print(tabela[["rede", "semente", "lista", "cpm"]].round(3).to_string(index=False), flush=True)
    print(pares.round(3).to_string(index=False), flush=True)
    print(json.dumps(regra, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
