"""Figuras de fatia de TC com anotação sobreposta."""

from pathlib import Path

import matplotlib

# Sem display: os scripts rodam no terminal.
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import SimpleITK as sitk


def fatia_com_nodulo(volume, indice, raio_px: float, hu, titulo: str, saida: Path, zoom: float = 5.0):
    """Fatia inteira e zoom, com o nódulo circulado. Volume em (z, y, x) e índice em (x, y, z)."""
    x, y, z = (int(round(v)) for v in indice)
    fatia = volume[z]
    margem = max(20, raio_px * zoom)

    figura, (inteira, perto) = plt.subplots(1, 2, figsize=(9, 4.8))
    for eixo in (inteira, perto):
        eixo.imshow(fatia, cmap="gray", vmin=hu[0], vmax=hu[1])
        eixo.add_patch(plt.Circle((x, y), raio_px, fill=False, color="red", linewidth=1.2))
        eixo.set_xticks([])
        eixo.set_yticks([])

    inteira.set_title(f"fatia {z} inteira", fontsize=9)
    perto.set_title(f"aproximado em ({x}, {y})", fontsize=9)
    perto.set_xlim(x - margem, x + margem)
    perto.set_ylim(y + margem, y - margem)

    figura.suptitle(f"{titulo}    janela HU {hu[0]} a {hu[1]}", fontsize=10)
    saida.parent.mkdir(parents=True, exist_ok=True)
    figura.savefig(saida, dpi=150, bbox_inches="tight")
    plt.close(figura)


def antes_e_depois(antes, depois, ponto_mundo, raio_mm: float, faixas, titulo: str, saida: Path):
    """A mesma posição física nos dois volumes. A fatia é escolhida pelo ponto no mundo.

    `faixas` traz o intervalo de cinza de cada painel. O original está em HU e o pré-processado
    já saiu normalizado em [0, 1], então desenhar os dois na mesma escala apaga um dos lados.
    """
    figura, eixos = plt.subplots(1, 2, figsize=(9.5, 5.2))
    for eixo, imagem, faixa, nome in zip(eixos, (antes, depois), faixas, ("antes", "depois")):
        x, y, z = imagem.TransformPhysicalPointToIndex(ponto_mundo)
        arr = sitk.GetArrayFromImage(imagem)
        espacamento = imagem.GetSpacing()

        eixo.imshow(arr[z], cmap="gray", vmin=faixa[0], vmax=faixa[1])
        eixo.add_patch(plt.Circle((x, y), raio_mm / espacamento[0], fill=False, color="red", linewidth=1.2))
        eixo.set_xticks([])
        eixo.set_yticks([])
        eixo.set_title(
            f"{nome}, fatia {z}\n"
            f"{' x '.join(str(d) for d in imagem.GetSize())} voxels de "
            f"{' x '.join(f'{e:.3g}' for e in espacamento)} mm",
            fontsize=9,
        )

    figura.suptitle(titulo, fontsize=10)
    saida.parent.mkdir(parents=True, exist_ok=True)
    figura.savefig(saida, dpi=150, bbox_inches="tight")
    plt.close(figura)
