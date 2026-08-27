"""Figuras de fatia de TC com anotação sobreposta."""

from pathlib import Path

import matplotlib

# Sem display: os scripts rodam no terminal.
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def fatia_com_nodulo(volume, indice, raio_px: float, hu, titulo: str, saida: Path, zoom: float = 5.0):
    """O volume vem em (z, y, x) e o índice em (x, y, z), que é a troca que engana.

    Dois painéis: a fatia inteira situa o achado, e o aproximado é o que deixa julgar se
    o círculo caiu no nódulo. Num corte de 512 sem zoom, nódulo nenhum é visível.
    """
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
