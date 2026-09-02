"""As cinco figuras da análise exploratória."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

COR = "#3a6ea5"
DESTAQUE = "#c04a3b"


def _salvar(figura, saida: Path):
    saida.parent.mkdir(parents=True, exist_ok=True)
    figura.savefig(saida, dpi=150, bbox_inches="tight")
    plt.close(figura)
    return saida


def espacamento_em_z(inventario, saida: Path, alvo_mm: float):
    # Arredonda o float32 do .mhd antes de contar valores distintos.
    contagem = inventario.espacamento_z.round(4).value_counts().sort_index()

    figura, eixo = plt.subplots(figsize=(7, 4))
    eixo.bar([f"{v:g}" for v in contagem.index], contagem.values, color=COR)
    eixo.axhline(0, color="black", linewidth=0.8)
    for x, q in enumerate(contagem.values):
        eixo.text(x, q + 2, str(q), ha="center", fontsize=8)

    eixo.set_xlabel("espaçamento entre fatias, mm")
    eixo.set_ylabel("volumes")
    eixo.set_title(
        f"Espaçamento em z nos {len(inventario)} volumes\n"
        f"varia por fator de {inventario.espacamento_z.max() / inventario.espacamento_z.min():.0f}, "
        f"e reamostramos para {alvo_mm:g} mm isotrópico",
        fontsize=10,
    )
    eixo.spines[["top", "right"]].set_visible(False)
    return _salvar(figura, saida)


def diametro_dos_nodulos(nodulos, saida: Path, patch_voxels: int, alvo_mm: float):
    lado_mm = patch_voxels * alvo_mm
    acima = int((nodulos.diameter_mm > lado_mm).sum())

    figura, eixo = plt.subplots(figsize=(7, 4))
    eixo.hist(nodulos.diameter_mm, bins=40, color=COR)
    eixo.axvline(lado_mm, color=DESTAQUE, linewidth=1.5)
    eixo.text(lado_mm - 0.6, eixo.get_ylim()[1] * 0.92, f"patch de {patch_voxels} voxels = {lado_mm:g} mm",
              ha="right", color=DESTAQUE, fontsize=8)

    eixo.set_xlabel("diâmetro anotado, mm")
    eixo.set_ylabel("nódulos")
    eixo.set_title(
        f"Diâmetro dos {len(nodulos)} nódulos, mediana {nodulos.diameter_mm.median():.1f} mm\n"
        f"nódulos maiores que o patch: {acima}",
        fontsize=10,
    )
    eixo.spines[["top", "right"]].set_visible(False)
    return _salvar(figura, saida)


def nodulos_por_scan(nodulos, inventario, saida: Path):
    por_scan = nodulos.groupby("seriesuid").size()
    sem_nodulo = len(inventario) - len(por_scan)
    contagem = por_scan.value_counts().sort_index()

    figura, eixo = plt.subplots(figsize=(7, 4))
    eixo.bar([0], [sem_nodulo], color=DESTAQUE)
    eixo.bar(contagem.index, contagem.values, color=COR)
    eixo.text(0, sem_nodulo + 3, str(sem_nodulo), ha="center", fontsize=8, color=DESTAQUE)

    eixo.set_xlabel("nódulos anotados no exame")
    eixo.set_ylabel("exames")
    eixo.set_title(
        f"Nódulos por exame nos {len(inventario)} volumes\n"
        f"{sem_nodulo} exames não têm nenhum nódulo elegível e entram na avaliação mesmo assim",
        fontsize=10,
    )
    eixo.spines[["top", "right"]].set_visible(False)
    return _salvar(figura, saida)


def histograma_de_hu(valores, saida: Path, hu, n_volumes: int):
    dentro = ((valores >= hu[0]) & (valores <= hu[1])).mean()

    figura, eixo = plt.subplots(figsize=(7, 4))
    eixo.hist(valores, bins=200, color=COR)
    for limite in hu:
        eixo.axvline(limite, color=DESTAQUE, linewidth=1.5)
    eixo.axvspan(hu[0], hu[1], color=DESTAQUE, alpha=0.06)

    eixo.set_yscale("log")
    eixo.set_xlabel("unidade Hounsfield")
    eixo.set_ylabel("voxels, escala log")
    eixo.set_title(
        f"HU dentro da máscara de pulmão, {n_volumes} volumes\n"
        f"a janela de {hu[0]} a {hu[1]} guarda {dentro:.1%} dos voxels do pulmão",
        fontsize=10,
    )
    eixo.spines[["top", "right"]].set_visible(False)
    return _salvar(figura, saida)


def desbalanceamento_dos_candidatos(candidatos, saida: Path):
    positivos = int(candidatos["class"].sum())
    negativos = len(candidatos) - positivos
    taxa = positivos / len(candidatos)

    figura, eixo = plt.subplots(figsize=(7, 4))
    eixo.bar(["negativo", "positivo"], [negativos, positivos], color=[COR, DESTAQUE], width=0.5)
    eixo.set_yscale("log")
    for x, q in enumerate([negativos, positivos]):
        eixo.text(x, q * 1.3, f"{q:,}".replace(",", "."), ha="center", fontsize=9)

    eixo.set_ylabel("candidatos, escala log")
    eixo.set_title(
        f"Desbalanceamento em {len(candidatos):,} candidatos".replace(",", ".") + "\n"
        f"positivos são {taxa:.4%}, e responder sempre negativo acerta {1 - taxa:.2%}",
        fontsize=10,
    )
    eixo.spines[["top", "right"]].set_visible(False)
    return _salvar(figura, saida)


def escolha_do_espacamento(tabela, saida: Path):
    """Contraste do nódulo e nódulos perdidos pelo recorte, contra o espaçamento alvo."""
    figura, contraste = plt.subplots(figsize=(7.5, 4.4))
    perdidos = contraste.twinx()

    contraste.errorbar(tabela.alvo, tabela.contraste,
                       yerr=[tabela.contraste - tabela.lo, tabela.hi - tabela.contraste],
                       marker="o", color=COR, capsize=3, linewidth=1.5, label="contraste do nódulo")
    perdidos.plot(tabela.alvo, tabela.fora, marker="s", color=DESTAQUE,
                  linewidth=1.5, label="nódulos que não cabem")

    contraste.set_xlabel("espaçamento alvo, mm")
    contraste.set_ylabel("contraste do nódulo, HU", color=COR)
    perdidos.set_ylabel("nódulos fora do recorte de 32", color=DESTAQUE)
    contraste.tick_params(axis="y", labelcolor=COR)
    perdidos.tick_params(axis="y", labelcolor=DESTAQUE)
    contraste.axvline(1.0, color="black", linewidth=0.8, linestyle=":")
    contraste.set_title("O contraste se mantém até 1 mm, e abaixo dele o recorte começa a cortar nódulo",
                        fontsize=10)
    contraste.spines["top"].set_visible(False)
    perdidos.spines["top"].set_visible(False)
    return _salvar(figura, saida)
