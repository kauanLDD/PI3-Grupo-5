"""Mostra um cubo da lista V2 em cortes axial, coronal e sagital."""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def argumentos():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("npz", type=Path, help="arquivo de recortes de um exame")
    escolha = parser.add_mutually_exclusive_group()
    escolha.add_argument("--indice", type=int, help="indice do cubo dentro do arquivo")
    escolha.add_argument("--candidate-id", type=int, help="ID original do candidato na lista V2")
    parser.add_argument("--saida", type=Path, default=Path("relatorios/figuras/recorte_v2.png"))
    return parser.parse_args()


def main():
    args = argumentos()
    with np.load(args.npz, allow_pickle=False) as dados:
        classes = dados["classe_luna16"]
        indice = args.indice
        if args.candidate_id is not None:
            encontrados = np.flatnonzero(dados["candidate_id"] == args.candidate_id)
            if not len(encontrados):
                raise ValueError(f"candidate_id {args.candidate_id} nao encontrado neste exame")
            indice = int(encontrados[0])
        if indice is None:
            positivos = np.flatnonzero(classes == 1)
            indice = int(positivos[0]) if len(positivos) else 0
        if not 0 <= indice < len(classes):
            raise ValueError(f"indice {indice} fora de 0..{len(classes) - 1}")
        cubo = dados["patches"][indice]
        candidato_id = int(dados["candidate_id"][indice])
        classe = int(classes[indice])
        coords = tuple(float(dados[chave][indice]) for chave in ("coordX", "coordY", "coordZ"))

    if cubo.shape != (34, 34, 34):
        raise ValueError(f"cubo com formato inesperado: {cubo.shape}")

    fig = plt.figure(figsize=(10, 5.5), layout="constrained")
    grade = fig.add_gridspec(2, 6, height_ratios=[2, 1])
    cortes = [
        (cubo[17], "Axial · z = 17"),
        (cubo[:, 17, :], "Coronal · y = 17"),
        (cubo[:, :, 17], "Sagital · x = 17"),
    ]
    for coluna, (imagem, titulo) in enumerate(cortes):
        eixo = fig.add_subplot(grade[0, 2 * coluna:2 * coluna + 2])
        eixo.imshow(imagem, cmap="gray", vmin=0, vmax=1, origin="lower",
                    interpolation="bilinear")
        eixo.set_title(titulo)
        eixo.set_xticks([])
        eixo.set_yticks([])

    for coluna, z in enumerate((5, 10, 14, 19, 24, 29)):
        eixo = fig.add_subplot(grade[1, coluna])
        eixo.imshow(cubo[z], cmap="gray", vmin=0, vmax=1, origin="lower",
                    interpolation="bilinear")
        eixo.set_title(f"z = {z}", fontsize=10)
        eixo.set_xticks([])
        eixo.set_yticks([])

    fig.suptitle(
        f"Cubo 34³ · candidato {candidato_id} · classe V2 {classe}\n"
        f"Centro (mm): x={coords[0]:.1f}, y={coords[1]:.1f}, z={coords[2]:.1f}"
        " · exibição bilinear",
        fontsize=11,
    )
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.saida, dpi=160)
    plt.close(fig)
    print(args.saida.resolve())
    print(f"indice={indice} candidate_id={candidato_id} classe={classe} forma={cubo.shape}")


if __name__ == "__main__":
    main()
