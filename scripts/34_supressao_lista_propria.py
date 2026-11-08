"""Supressão de vizinhos com raio maior e média das sementes sobre a nossa lista, sem treino, na validação.

Lê as notas que o script 31 gravou para a rede antiga com três sementes, aplica as variantes fixadas
no config.yaml (seção supressao_lista_propria) e avalia cada uma com o avaliador oficial.
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
from detection import candidatos as det
from experimentos import avaliacao_oficial

CHAVE = ["seriesuid", *det.COLUNAS]


def script_27():
    arquivo = Path(__file__).resolve().parent / "27_comparar_froc.py"
    spec = importlib.util.spec_from_file_location("comparar_froc", arquivo)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def conferir_exames(a, b):
    """O sorteio do avaliador depende só da lista de exames e da semente, então isso basta para parear."""
    if a["exames"] != b["exames"]:
        raise ValueError("as avaliações usam exames diferentes")
    for chave in ("seed", "bootstrap", "confianca", "max_marcas_por_exame"):
        if a["protocolo"][chave] != b["protocolo"][chave]:
            raise ValueError(f"protocolo diverge em {chave}")


def media_das_sementes(notas: dict) -> pd.DataFrame:
    ordenadas = [n.sort_values(CHAVE, kind="stable").reset_index(drop=True) for n in notas.values()]
    base = ordenadas[0]
    for outra in ordenadas[1:]:
        if len(outra) != len(base) or not (outra[CHAVE].to_numpy() == base[CHAVE].to_numpy()).all():
            raise ValueError("as sementes pontuaram pontos diferentes")
    probabilidade = np.mean([o.probability.to_numpy() for o in ordenadas], axis=0)
    return base[CHAVE].assign(probability=probabilidade)


def aplicar_regra(tabela, pares, cpm_inteira):
    supressoes = tabela[tabela.variante.str.startswith("raio_")]
    medias = supressoes.groupby("variante").cpm.mean()
    positivas = pares[pares.variante.str.startswith("raio_")].groupby("variante").diferenca_cpm.apply(
        lambda d: bool(d.gt(0).all()))
    passaram = [v for v in medias.index if medias[v] > cpm_inteira and positivas[v]]
    media = tabela.loc[tabela.variante.eq("media_sementes"), "cpm"].iloc[0]
    media_positiva = bool(pares.loc[pares.variante.eq("media_sementes"), "diferenca_cpm"].gt(0).all())
    return {"cpm_lista_inteira_media_sementes": cpm_inteira,
            "supressao": {v: {"cpm_media": float(medias[v]), "pareadas_positivas_nas_tres": bool(positivas[v]),
                              "passou": v in passaram} for v in medias.index},
            "supressao_adotada": max(passaram, key=lambda v: medias[v]) if passaram else None,
            "media_sementes": {"cpm": float(media), "pareadas_positivas_contra_cada_semente": media_positiva,
                               "passou": bool(media > cpm_inteira and media_positiva)}}


def desenhar(tabela, cpm_inteira, destino):
    figura, eixo = plt.subplots(figsize=(7.5, 3.8))
    raios = sorted(int(v.removeprefix("raio_")) for v in tabela.variante.unique() if v.startswith("raio_"))
    variantes = ["lista_inteira"] + [f"raio_{r}" for r in raios]
    nomes = ["Lista inteira"] + [f"Supressão {r} mm" for r in raios]
    for i, variante in enumerate(variantes):
        parte = tabela[tabela.variante.eq(variante)].sort_values("semente")
        x = i + np.array([-0.15, 0, 0.15])
        eixo.errorbar(x, parte.cpm, yerr=[parte.cpm - parte.cpm_ic_inferior, parte.cpm_ic_superior - parte.cpm],
                      fmt="o", color="#1764a8", capsize=3, markeredgecolor="white")
    media = tabela[tabela.variante.eq("media_sementes")].iloc[0]
    eixo.errorbar([len(variantes)], [media.cpm], yerr=[[media.cpm - media.cpm_ic_inferior], [media.cpm_ic_superior - media.cpm]],
                  fmt="s", color="#b5651d", capsize=3, markeredgecolor="white")
    eixo.axhline(cpm_inteira, color="#5c5c5c", linewidth=1, linestyle="--")
    eixo.set_xticks(range(len(variantes) + 1), nomes + ["Média das sementes"])
    eixo.set_ylabel("CPM na validação (IC95%)")
    eixo.yaxis.set_major_formatter(lambda v, _: f"{v:.2f}".replace(".", ","))
    eixo.grid(axis="y", alpha=0.25)
    for lado in ("top", "right"):
        eixo.spines[lado].set_visible(False)
    figura.text(0.01, 0.01, "Pontos azuis: sementes 42, 43 e 44. Tracejado: média da lista inteira nas três "
                "sementes. 89 exames, 111 nódulos, avaliador oficial.", fontsize=7, color="#5c5c5c")
    figura.tight_layout(rect=(0, 0.04, 1, 1))
    figura.savefig(destino / "cpm_por_variante.png", dpi=200)
    plt.close(figura)


def main():
    cfg = config.carregar()
    config.fixar_semente(cfg["seed"])
    caminhos, fase, avaliacao = cfg["caminhos"], cfg["supressao_lista_propria"], cfg["avaliacao"]
    saida, completa = caminhos["supressao_lista_propria"], caminhos["supressao_lista_propria_completa"]
    if saida.exists() or completa.exists():
        raise ValueError(f"preserve a avaliação anterior e apague-a à mão: {saida} / {completa}")
    comparar = script_27()

    pastas = {semente: config.RAIZ / pasta for semente, pasta in fase["sementes"].items()}
    inteiras = {s: comparar.carregar(p / "sem_supressao") for s, p in pastas.items()}
    primeira = next(iter(inteiras.values()))
    uids = primeira["exames"]
    for dados in inteiras.values():
        conferir_exames(dados, primeira)
    protocolo = primeira["protocolo"]
    if (protocolo["seed"], protocolo["bootstrap"], protocolo["confianca"]) != (
            cfg["seed"], avaliacao["bootstrap_reamostras"], avaliacao["intervalo_confianca"]):
        raise ValueError("as avaliações da lista inteira usam outro protocolo de bootstrap")
    notas = {s: pd.read_csv(p / "probabilidades.csv") for s, p in pastas.items()}
    for semente, n in notas.items():
        if sorted(n.seriesuid.unique()) != uids:
            raise ValueError(f"semente {semente}: notas cobrem outros exames")
    print(f"exames lidos {len(uids)}, com erro 0, descartados 0; pontos por semente "
          f"{ {s: len(n) for s, n in notas.items()} }", flush=True)

    def avaliar(marcas, destino):
        avaliacao_oficial.avaliar(marcas, uids, caminhos["luna16_anotacoes"], caminhos["luna16_anotacoes_excluidas"],
                                  destino, cfg["seed"], avaliacao["bootstrap_reamostras"],
                                  avaliacao["intervalo_confianca"])
        return comparar.carregar(destino)

    linhas, pares = [], []

    def medir(variante, semente, dados, marcas):
        medida = comparar.resumir((variante, "-"), [dados, dados], avaliacao["intervalo_confianca"])[0][variante]
        linhas.append({"variante": variante, "semente": semente, "marcas": marcas, "cpm": medida["cpm"],
                       "cpm_ic_inferior": medida["cpm_ic"][0], "cpm_ic_superior": medida["cpm_ic"][1],
                       **{f"sens_{fp}": s for fp, s in medida["sensibilidade"].items()}})

    def parear(variante, semente, dados, contra, rotulo_contra):
        conferir_exames(dados, contra)
        par = comparar.resumir((variante, rotulo_contra), [dados, contra], avaliacao["intervalo_confianca"])[1]
        pares.append({"variante": variante, "semente": semente, "contra": rotulo_contra,
                      "diferenca_cpm": par["diferenca_cpm"], "ic_inferior": par["diferenca_ic"][0],
                      "ic_superior": par["diferenca_ic"][1], "fracao_reamostras_maior": par["fracao_reamostras_maior"]})
        print(f"{variante}, semente {semente}, contra {rotulo_contra}: {par['diferenca_cpm']:+.3f} "
              f"({par['diferenca_ic'][0]:+.3f} a {par['diferenca_ic'][1]:+.3f})", flush=True)

    for semente, dados in inteiras.items():
        medir("lista_inteira", semente, dados, len(notas[semente]))
    cpm_inteira = float(np.mean([l["cpm"] for l in linhas]))

    for raio in fase["raios_mm"]:
        variante = f"raio_{raio}"
        for semente, n in notas.items():
            marcas = det.suprimir_vizinhos(n, float(raio))
            dados = avaliar(marcas, completa / variante / str(semente))
            medir(variante, semente, dados, len(marcas))
            parear(variante, semente, dados, inteiras[semente], "lista_inteira")

    media = media_das_sementes(notas)
    dados = avaliar(media, completa / "media_sementes")
    medir("media_sementes", "42, 43 e 44", dados, len(media))
    for semente, contra in inteiras.items():
        parear("media_sementes", semente, dados, contra, f"semente_{semente}")

    tabela, pares = pd.DataFrame(linhas), pd.DataFrame(pares)
    regra = aplicar_regra(tabela, pares, cpm_inteira)
    saida.mkdir(parents=True)
    tabela.to_csv(saida / "variantes.csv", index=False)
    pares.to_csv(saida / "diferencas_pareadas.csv", index=False)
    (saida / "resumo.json").write_text(json.dumps({
        "conjunto": "validacao", "teste_utilizado": False, "exames": len(uids),
        "sementes": {str(s): str(p.relative_to(config.RAIZ)) for s, p in pastas.items()},
        "raios_mm": fase["raios_mm"], **regra}, indent=2, ensure_ascii=False), encoding="utf-8")
    desenhar(tabela, cpm_inteira, saida)
    print(tabela[["variante", "semente", "marcas", "cpm"]].round(3).to_string(index=False), flush=True)
    print(json.dumps(regra, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
