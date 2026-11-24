"""Figuras de fatia de TC com anotação sobreposta."""

from pathlib import Path

import matplotlib

# Sem display: os scripts rodam no terminal.
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
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


def fatia_com_candidatos(volume, faixa, indice_nodulo, raio_nodulo_px: float, candidatos_px,
                          titulo: str, saida: Path, zoom: float = 4.0):
    """Fatia no z do nódulo anotado (verde), com os candidatos do blob_log por cima (vermelho)."""
    x, y, z = (int(round(v)) for v in indice_nodulo)
    fatia = volume[z]
    margem = max(20, raio_nodulo_px * zoom)

    figura, (inteira, perto) = plt.subplots(1, 2, figsize=(9.5, 5.2))
    for eixo in (inteira, perto):
        eixo.imshow(fatia, cmap="gray", vmin=faixa[0], vmax=faixa[1])
        eixo.add_patch(plt.Circle((x, y), raio_nodulo_px, fill=False, color="lime", linewidth=1.4))
        for cx, cy, craio in candidatos_px:
            eixo.add_patch(plt.Circle((cx, cy), craio, fill=False, color="red", linewidth=1.0))
        eixo.set_xticks([])
        eixo.set_yticks([])

    inteira.set_title(f"fatia {z} inteira", fontsize=9)
    perto.set_title(f"aproximado em ({x}, {y})", fontsize=9)
    perto.set_xlim(x - margem, x + margem)
    perto.set_ylim(y + margem, y - margem)

    figura.suptitle(f"{titulo}\nverde = nódulo anotado, vermelho = candidato do blob_log", fontsize=10)
    saida.parent.mkdir(parents=True, exist_ok=True)
    figura.savefig(saida, dpi=150, bbox_inches="tight")
    plt.close(figura)


def antes_e_depois(antes, depois, ponto_mundo, raio_mm: float, faixas, titulo: str, saida: Path):
    """A mesma posição física nos dois volumes. A fatia é escolhida pelo ponto no mundo."""
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


def tres_planos(eixos, volume, centro_zyx, meio_lado: int, raio: float | None = None):
    """Axial, coronal e sagital passando pelo centro, num recorte de 2 * meio_lado voxels."""
    z, y, x = (int(round(v)) for v in centro_zyx)
    fundo = np.zeros((2 * meio_lado,) * 3, dtype=np.float32)
    inicio = np.array([z, y, x]) - meio_lado
    origem = np.maximum(inicio, 0)
    limite = np.minimum(inicio + 2 * meio_lado, volume.shape)
    fundo[tuple(slice(a - i, b - i) for a, b, i in zip(origem, limite, inicio))] = \
        volume[tuple(slice(a, b) for a, b in zip(origem, limite))]
    cortes = (fundo[meio_lado], fundo[:, meio_lado, :], fundo[:, :, meio_lado])
    for eixo, corte, nome in zip(eixos, cortes, ("axial", "coronal", "sagital")):
        # Coronal e sagital com o z crescendo para cima, como no exame.
        eixo.imshow(corte, cmap="gray", vmin=0, vmax=1, origin="upper" if nome == "axial" else "lower")
        if raio:
            eixo.add_patch(plt.Circle((meio_lado, meio_lado), raio, fill=False, color="lime", linewidth=1))
        else:
            eixo.plot([meio_lado], [meio_lado], marker="+", color="red", markersize=9, markeredgewidth=1)
        eixo.set_xticks([])
        eixo.set_yticks([])
