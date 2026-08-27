"""As cinco figuras da EDA. Gera o que o dado em disco permitir e declara o que faltou."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "codigo"))
from pi3 import config
from pi3.dados import volumes
from pi3.visualizacao import eda

VOLUMES_PARA_HU = 30

cfg = config.carregar()
config.fixar_semente()

figuras = cfg["caminhos"]["figuras"]
hu = (cfg["pre_processamento"]["hu_min"], cfg["pre_processamento"]["hu_max"])
alvo_mm = cfg["pre_processamento"]["espacamento_alvo"][0]
patch = cfg["candidatos"]["patch"][0]

inventario = pd.read_csv(cfg["caminhos"]["intermediario"] / "inventario_volumes.csv")


def amostrar_hu():
    """Volumes sorteados, com o HU tomado só de dentro da máscara de pulmão do desafio."""
    import SimpleITK as sitk

    amostra = inventario.sample(VOLUMES_PARA_HU, random_state=cfg["seed"])
    valores, lidos = [], 0
    for linha in amostra.itertuples():
        caminho = volumes.caminho_do_volume(
            cfg["caminhos"]["luna16"], linha.seriesuid, cfg["selecao"]["subsets"]
        )
        mascara = cfg["caminhos"]["luna16_mascaras"] / f"{linha.seriesuid}.mhd"
        if caminho is None or not mascara.exists():
            continue
        volume = sitk.GetArrayFromImage(sitk.ReadImage(str(caminho)))
        pulmao = sitk.GetArrayFromImage(sitk.ReadImage(str(mascara))) > 0
        valores.append(volume[pulmao])
        lidos += 1
    return (np.concatenate(valores) if valores else None), lidos


feitas, faltando = [], []
feitas.append(eda.espacamento_em_z(inventario, figuras / "eda_espacamento_z.png", alvo_mm))

if not cfg["caminhos"]["luna16"].is_dir():
    faltando.append(f"as outras quatro: {cfg['caminhos']['luna16']} não está acessível")
else:
    anotacoes = pd.read_csv(cfg["caminhos"]["luna16_anotacoes"])
    nodulos = anotacoes[anotacoes.seriesuid.isin(set(inventario.seriesuid))]
    feitas.append(eda.diametro_dos_nodulos(nodulos, figuras / "eda_diametro.png", patch, alvo_mm))
    feitas.append(eda.nodulos_por_scan(nodulos, inventario, figuras / "eda_nodulos_por_scan.png"))

    valores, lidos = amostrar_hu()
    if valores is None:
        faltando.append("HU: nenhum volume com máscara foi lido")
    else:
        feitas.append(eda.histograma_de_hu(valores, figuras / "eda_hu.png", hu, lidos))

    candidatos = pd.read_csv(cfg["caminhos"]["luna16_candidatos"])
    nossos = candidatos[candidatos.seriesuid.isin(set(inventario.seriesuid))]
    feitas.append(eda.desbalanceamento_dos_candidatos(nossos, figuras / "eda_desbalanceamento.png"))

print(f"{len(feitas)} de 5 figuras geradas")
for f in feitas:
    print(f"  {f.name}")
for f in faltando:
    print(f"  falta {f}")
