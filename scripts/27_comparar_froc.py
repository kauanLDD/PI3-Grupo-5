"""Põe duas avaliações oficiais do mesmo conjunto no mesmo gráfico FROC, com IC95% e diferença pareada de CPM.

Só lê as pastas que o avaliador oficial já gravou. Exemplo de uso em docs/14.
"""

import argparse
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

PONTOS = [0.125, 0.25, 0.5, 1, 2, 4, 8]
ROTULOS = ["0,125", "0,25", "0,5", "1", "2", "4", "8"]
# Paleta legível para daltonismo; marcador e traço também distinguem as duas curvas.
ESTILOS = ({"cor": "#1764a8", "marcador": "o", "traco": "-"},
           {"cor": "#b5651d", "marcador": "s", "traco": "--"})
TINTA, TINTA_SECUNDARIA = "#1f1f1f", "#5c5c5c"


def comparacao_validacao():
    arquivo = Path(__file__).resolve().parent / "23_comparar_validacao.py"
    spec = importlib.util.spec_from_file_location("comparar_validacao", arquivo)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def carregar(pasta):
    pasta = Path(pasta)
    return {"protocolo": json.loads((pasta / "avaliacao.json").read_text(encoding="utf-8")),
            "exames": (pasta / "seriesuids.csv").read_text(encoding="utf-8").split(),
            "pontos": pd.read_csv(pasta / "pontos_operacao.csv"),
            "curva": pd.read_csv(pasta / "curva_froc_completa.csv"),
            "faixa": pd.read_csv(pasta / "froc_predicoes_bootstrapping.csv"),
            "replicas": np.loadtxt(pasta / "cpm_bootstrap.csv", delimiter=","),
            "predicoes": pd.read_csv(pasta / "predicoes.csv")}


def nodulos(pasta):
    """Total de nódulos da referência, como o avaliador oficial escreve no CADAnalysis.txt."""
    for linha in (Path(pasta) / "CADAnalysis.txt").read_text(encoding="utf-8").splitlines():
        if linha.strip().startswith("Total number of nodules:"):
            return int(linha.split(":")[1])
    raise ValueError(f"CADAnalysis.txt sem total de nodulos: {pasta}")


def resumir(rotulos, dados, confianca):
    intervalo = comparacao_validacao().intervalo
    modelos, linhas = {}, []
    for rotulo, d in zip(rotulos, dados):
        pontos = d["pontos"]
        if not np.allclose(pontos.fp_por_exame, PONTOS):
            raise ValueError(f"{rotulo}: pontos de operacao diferentes dos sete oficiais")
        cpm = float(pontos.sensibilidade.mean())
        modelos[rotulo] = {"cpm": cpm, "cpm_ic": intervalo(d["replicas"], confianca),
                           "sensibilidade": dict(zip(map(str, PONTOS), pontos.sensibilidade.round(6))),
                           "ic_inferior": dict(zip(map(str, PONTOS), pontos.ic_inferior.round(6))),
                           "ic_superior": dict(zip(map(str, PONTOS), pontos.ic_superior.round(6)))}
        linhas.append(pontos[["fp_por_exame", "sensibilidade", "ic_inferior", "ic_superior"]].assign(modelo=rotulo))
    a, b = rotulos
    diferenca = dados[0]["replicas"] - dados[1]["replicas"]
    par = {"modelo": a, "contra": b, "diferenca_cpm": modelos[a]["cpm"] - modelos[b]["cpm"],
           "diferenca_ic": intervalo(diferenca, confianca),
           "fracao_reamostras_maior": float((diferenca > 0).mean())}
    tabela = pd.concat(linhas)[["modelo", "fp_por_exame", "sensibilidade", "ic_inferior", "ic_superior"]]
    return modelos, par, tabela


def desenhar(rotulos, dados, modelos, titulo, destino):
    figura, (eixo, quadro) = plt.subplots(2, 1, figsize=(9, 6.6), height_ratios=[4, 0.75])
    for rotulo, d, estilo in zip(rotulos, dados, ESTILOS):
        faixa = d["faixa"]
        dentro = faixa.iloc[:, 0].between(0.125, 8)
        eixo.fill_between(faixa.iloc[:, 0][dentro], faixa.iloc[:, 2][dentro], faixa.iloc[:, 3][dentro],
                          color=estilo["cor"], alpha=0.13, linewidth=0)
        curva = d["curva"]
        eixo.plot(curva.fp_por_exame, curva.sensibilidade, color=estilo["cor"], linestyle=estilo["traco"],
                  linewidth=2, label=f"{rotulo}: CPM {modelos[rotulo]['cpm']:.3f} "
                  f"(IC95% {modelos[rotulo]['cpm_ic'][0]:.3f} a {modelos[rotulo]['cpm_ic'][1]:.3f})".replace(".", ","))
        pontos = d["pontos"]
        eixo.errorbar(pontos.fp_por_exame, pontos.sensibilidade,
                      yerr=[pontos.sensibilidade - pontos.ic_inferior, pontos.ic_superior - pontos.sensibilidade],
                      fmt=estilo["marcador"], color=estilo["cor"], markersize=7, capsize=3, elinewidth=1.2,
                      markeredgecolor="white", markeredgewidth=1.2, zorder=3)
    eixo.set_xscale("log", base=2)
    eixo.set_xlim(0.125 / 1.15, 8 * 1.15)
    eixo.set_ylim(0, 1)
    eixo.set_xticks(PONTOS, ROTULOS)
    eixo.set_yticks(np.linspace(0, 1, 6), [f"{v:.1f}".replace(".", ",") for v in np.linspace(0, 1, 6)])
    eixo.set_xlabel("Falsos positivos por exame", color=TINTA)
    eixo.set_ylabel("Sensibilidade", color=TINTA)
    eixo.set_title(titulo, color=TINTA, loc="left")
    eixo.tick_params(colors=TINTA_SECUNDARIA)
    for lado in ("top", "right"):
        eixo.spines[lado].set_visible(False)
    eixo.grid(alpha=0.25)
    eixo.legend(loc="lower right", fontsize=9, frameon=False, labelcolor=TINTA)

    quadro.axis("off")
    celulas = [[f"{modelos[r]['sensibilidade'][str(p)]:.3f}".replace(".", ",") for p in PONTOS]
               + [f"{modelos[r]['cpm']:.3f}".replace(".", ",")] for r in rotulos]
    tabela = quadro.table(cellText=celulas, rowLabels=rotulos, colLabels=ROTULOS + ["CPM"],
                          loc="center", cellLoc="center")
    tabela.auto_set_font_size(False)
    tabela.set_fontsize(9)
    for (linha, coluna), celula in tabela.get_celld().items():
        celula.set_edgecolor("#d0d0d0")
        celula.get_text().set_color(TINTA)
        if linha == 0:
            celula.get_text().set_color(TINTA_SECUNDARIA)
    figura.text(0.01, 0.01, "Linha: curva FROC completa. Pontos: os sete pontos oficiais com IC95%. "
                "Faixa: IC95% do bootstrap por exame do avaliador oficial (1.000 reamostras).",
                fontsize=7.5, color=TINTA_SECUNDARIA)
    figura.tight_layout(rect=(0, 0.03, 1, 1))
    figura.savefig(destino / "froc.png", dpi=200)
    plt.close(figura)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--avaliacao", action="append", required=True,
                        help="ROTULO=PASTA de uma avaliação oficial; exatamente duas, a primeira é a comparada")
    parser.add_argument("--titulo", required=True, help="conjunto avaliado, por exemplo Teste ou Validação")
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args()
    config.fixar_semente()
    if len(args.avaliacao) != 2:
        raise ValueError("informe exatamente duas avaliacoes")
    rotulos, pastas = zip(*(item.split("=", 1) for item in args.avaliacao))
    pastas = [config.RAIZ / p if not Path(p).is_absolute() else Path(p) for p in pastas]
    dados = [carregar(p) for p in pastas]
    comparacao_validacao().conferir_pareamento(dados[0], dados[1])
    totais = {nodulos(p) for p in pastas}
    if len(totais) != 1:
        raise ValueError("as avaliacoes contam nodulos diferentes")
    confianca = dados[0]["protocolo"]["confianca"]
    modelos, par, tabela = resumir(rotulos, dados, confianca)
    exames, total = len(dados[0]["exames"]), totais.pop()
    titulo = f"{args.titulo}: {exames} exames, {total} nódulos, avaliador oficial LUNA16"
    destino = args.saida if args.saida.is_absolute() else config.RAIZ / args.saida
    destino.mkdir(parents=True, exist_ok=True)
    tabela.to_csv(destino / "pontos_operacao.csv", index=False)
    (destino / "comparacao.json").write_text(json.dumps({
        "conjunto": args.titulo, "exames": exames, "nodulos": total,
        "reamostras": len(dados[0]["replicas"]), "seed_bootstrap": dados[0]["protocolo"]["seed"],
        "avaliacoes": {r: str(p.relative_to(config.RAIZ)) if p.is_relative_to(config.RAIZ) else str(p)
                       for r, p in zip(rotulos, pastas)},
        "modelos": modelos, "diferenca_pareada": par}, indent=2, ensure_ascii=False), encoding="utf-8")
    desenhar(rotulos, dados, modelos, titulo, destino)
    print(tabela.round(3).to_string(index=False), flush=True)
    print(json.dumps(par, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
