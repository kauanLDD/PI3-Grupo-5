from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import SimpleITK as sitk


hu_minimo = -1000.0
hu_maximo = 400.0


def normalizar_hu(volume: np.ndarray) -> np.ndarray:
    volume_limitado = np.clip(volume.astype(np.float32), hu_minimo, hu_maximo)
    volume_normalizado = (volume_limitado - hu_minimo) / (hu_maximo - hu_minimo)
    return volume_normalizado.astype(np.float32)


def escolher_corte(volume: np.ndarray) -> int:
    inicio = volume.shape[0] // 4
    fim = 3 * volume.shape[0] // 4
    candidatos = volume[inicio:fim]
    area_pulmonar = ((candidatos > -1000) & (candidatos < -400)).sum(axis=(1, 2))
    return int(inicio + np.argmax(area_pulmonar))


def salvar_comparacao(
    corte_original: np.ndarray,
    corte_normalizado: np.ndarray,
    indice_corte: int,
    destino: Path,
) -> None:
    figura, eixos = plt.subplots(2, 2, figsize=(12, 9), constrained_layout=True)

    imagem_original = eixos[0, 0].imshow(
        corte_original,
        cmap="gray",
        vmin=hu_minimo,
        vmax=hu_maximo,
    )
    eixos[0, 0].set_title(f"antes: valores em hu - corte axial {indice_corte}")
    eixos[0, 0].axis("off")
    figura.colorbar(imagem_original, ax=eixos[0, 0], label="hu", shrink=0.82)

    imagem_normalizada = eixos[0, 1].imshow(
        corte_normalizado,
        cmap="gray",
        vmin=0,
        vmax=1,
    )
    eixos[0, 1].set_title("depois: intensidades normalizadas em [0, 1]")
    eixos[0, 1].axis("off")
    figura.colorbar(imagem_normalizada, ax=eixos[0, 1], label="intensidade", shrink=0.82)

    eixos[1, 0].hist(
        np.clip(corte_original.ravel(), hu_minimo, hu_maximo),
        bins=80,
        color="#8a1538",
    )
    eixos[1, 0].set_title("distribuicao apos janelamento hu")
    eixos[1, 0].set_xlabel("hu")
    eixos[1, 0].set_ylabel("numero de voxels")

    eixos[1, 1].hist(
        corte_normalizado.ravel(),
        bins=80,
        range=(0, 1),
        color="#8a1538",
    )
    eixos[1, 1].set_title("distribuicao apos normalizacao")
    eixos[1, 1].set_xlabel("intensidade normalizada")
    eixos[1, 1].set_ylabel("numero de voxels")

    figura.suptitle(
        "padronizacao de intensidades do luna16: janela [-1000, 400] hu",
        fontsize=15,
        fontweight="bold",
    )
    figura.savefig(destino, dpi=180, bbox_inches="tight")
    plt.close(figura)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="aplica janelamento hu e normalizacao min-max a um volume de ct"
    )
    parser.add_argument("entrada", type=Path, help="arquivo .mha ou .mhd")
    parser.add_argument("--saida-imagem", type=Path, default=Path("comparacao_hu.png"))
    parser.add_argument("--saida-metricas", type=Path, default=Path("metricas_hu.csv"))
    parser.add_argument("--salvar-volume", type=Path, default=None)
    argumentos = parser.parse_args()

    imagem = sitk.ReadImage(str(argumentos.entrada))
    volume = sitk.GetArrayFromImage(imagem).astype(np.float32)
    volume_normalizado = normalizar_hu(volume)

    assert np.isfinite(volume_normalizado).all()
    assert float(volume_normalizado.min()) >= 0.0
    assert float(volume_normalizado.max()) <= 1.0

    indice_corte = escolher_corte(volume)
    salvar_comparacao(
        volume[indice_corte],
        volume_normalizado[indice_corte],
        indice_corte,
        argumentos.saida_imagem,
    )

    metricas = {
        "arquivo": argumentos.entrada.name,
        "dimensoes_zyx": "x".join(map(str, volume.shape)),
        "espacamento_xyz_mm": "x".join(f"{valor:.3f}" for valor in imagem.GetSpacing()),
        "hu_minimo_original": f"{float(volume.min()):.3f}",
        "hu_maximo_original": f"{float(volume.max()):.3f}",
        "intensidade_minima_normalizada": f"{float(volume_normalizado.min()):.6f}",
        "intensidade_maxima_normalizada": f"{float(volume_normalizado.max()):.6f}",
        "media_normalizada": f"{float(volume_normalizado.mean()):.6f}",
        "desvio_padrao_normalizado": f"{float(volume_normalizado.std()):.6f}",
        "corte_axial_exibido": str(indice_corte),
    }

    with argumentos.saida_metricas.open("w", newline="", encoding="utf-8") as arquivo_csv:
        escritor = csv.DictWriter(arquivo_csv, fieldnames=metricas.keys())
        escritor.writeheader()
        escritor.writerow(metricas)

    if argumentos.salvar_volume is not None:
        np.save(argumentos.salvar_volume, volume_normalizado)

    for nome, valor in metricas.items():
        print(f"{nome}: {valor}")


if __name__ == "__main__":
    main()
