"""Evidência da janela de HU e da normalização sobre um volume bruto inteiro."""

import argparse
import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import SimpleITK as sitk

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config
from dataset import volumes
from preprocessing import volume as pre


def escolher_corte(volume: np.ndarray, faixa) -> int:
    """Maior área na faixa de HU na metade central; sem área, usa o meio do volume."""
    if volume.ndim != 3 or any(d == 0 for d in volume.shape):
        raise ValueError("volume precisa ter três dimensões não vazias: z, y, x")
    inicio = volume.shape[0] // 4
    fim = max(inicio + 1, 3 * volume.shape[0] // 4)
    candidatos = volume[inicio:fim]
    area_pulmonar = ((candidatos > faixa[0]) & (candidatos < faixa[1])).sum(axis=(1, 2))
    if not area_pulmonar.any():
        return volume.shape[0] // 2
    return int(inicio + np.argmax(area_pulmonar))


def salvar_comparacao(
    corte_original: np.ndarray,
    corte_normalizado: np.ndarray,
    indice_corte: int,
    destino: Path,
    hu,
) -> None:
    figura, eixos = plt.subplots(2, 2, figsize=(12, 9), constrained_layout=True)

    imagem_original = eixos[0, 0].imshow(
        corte_original,
        cmap="gray",
        vmin=hu[0],
        vmax=hu[1],
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
        np.clip(corte_original.ravel(), *hu),
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
        f"padronizacao de intensidades do luna16: janela [{hu[0]}, {hu[1]}] hu",
        fontsize=15,
        fontweight="bold",
    )
    figura.savefig(destino, dpi=180, bbox_inches="tight")
    plt.close(figura)


def main() -> None:
    cfg = config.carregar()
    config.fixar_semente()
    # A janela preserva ar e tecido pulmonar e limita a contribuição de osso e metal.
    hu = (cfg["pre_processamento"]["hu_min"], cfg["pre_processamento"]["hu_max"])
    parser = argparse.ArgumentParser(
        description="aplica janelamento hu e normalizacao min-max a um volume de ct"
    )
    parser.add_argument("entrada", type=Path, nargs="?", help="volume bruto .mha ou .mhd, em HU")
    parser.add_argument("--saida-imagem", type=Path,
                        default=cfg["caminhos"]["figuras"] / "normalizacao_hu.png")
    parser.add_argument("--saida-metricas", type=Path,
                        default=cfg["caminhos"]["intermediario"] / "evidencia_normalizacao.csv")
    parser.add_argument("--salvar-volume", type=Path, default=None)
    argumentos = parser.parse_args()

    caminho = argumentos.entrada
    if caminho is None:
        uid = cfg["evidencia_normalizacao"]["seriesuid"]
        inventario = pd.read_csv(cfg["caminhos"]["intermediario"] / "inventario_volumes.csv")
        exame = inventario[inventario.seriesuid == uid]
        subsets = exame[exame.subset.isin(cfg["selecao"]["subsets"])].subset.tolist()
        caminho = volumes.caminho_do_volume(cfg["caminhos"]["luna16"], uid, subsets)
        if caminho is None:
            sys.exit(f"exame {uid} não encontrado no inventário selecionado ou no disco")
    else:
        uid = caminho.stem

    imagem = sitk.ReadImage(str(caminho))
    normalizada = pre.normalizar(pre.janela(imagem, *hu), *hu)
    volume = sitk.GetArrayFromImage(imagem)
    volume_normalizado = sitk.GetArrayFromImage(normalizada)

    finitos = bool(np.isfinite(volume_normalizado).all())
    minimo = float(volume_normalizado.min())
    maximo = float(volume_normalizado.max())
    print(f"1 exame lido; valores finitos: {finitos}; mínimo: {minimo}; máximo: {maximo}")
    if not finitos:
        raise ValueError("normalização produziu valores não finitos")
    if minimo < 0.0 or maximo > 1.0:
        raise ValueError(f"normalização fora de [0, 1]: mínimo {minimo}, máximo {maximo}")

    indice_corte = escolher_corte(volume, cfg["evidencia_normalizacao"]["faixa_pulmonar"])
    argumentos.saida_imagem.parent.mkdir(parents=True, exist_ok=True)
    salvar_comparacao(
        volume[indice_corte],
        volume_normalizado[indice_corte],
        indice_corte,
        argumentos.saida_imagem,
        hu,
    )

    metricas = {
        "seriesuid": uid,
        "arquivo": caminho.name,
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

    argumentos.saida_metricas.parent.mkdir(parents=True, exist_ok=True)
    with argumentos.saida_metricas.open("w", newline="", encoding="utf-8") as arquivo_csv:
        escritor = csv.DictWriter(arquivo_csv, fieldnames=metricas.keys())
        escritor.writeheader()
        escritor.writerow(metricas)

    if argumentos.salvar_volume is not None:
        argumentos.salvar_volume.parent.mkdir(parents=True, exist_ok=True)
        np.save(argumentos.salvar_volume, volume_normalizado)

    for nome, valor in metricas.items():
        print(f"{nome}: {valor}")


if __name__ == "__main__":
    main()
