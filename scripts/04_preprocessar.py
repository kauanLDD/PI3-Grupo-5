"""Pré-processamento de um volume: janela de HU, voxel isotrópico e pulmão isolado."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import SimpleITK as sitk

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "codigo"))
from pi3 import config
from pi3.dados import volumes
from pi3.preprocessamento import volume as pre
from pi3.visualizacao import fatias

cfg = config.carregar()
config.fixar_semente()

hu = (cfg["pre_processamento"]["hu_min"], cfg["pre_processamento"]["hu_max"])
alvo = cfg["pre_processamento"]["espacamento_alvo"]

inventario = pd.read_csv(cfg["caminhos"]["intermediario"] / "inventario_volumes.csv")
nodulos = pd.read_csv(cfg["caminhos"]["luna16_anotacoes"]).merge(inventario, on="seriesuid")

# O maior nódulo entre os volumes de direção identidade.
escolhido = nodulos[nodulos.matriz_identidade].nlargest(1, "diameter_mm").iloc[0]
uid = escolhido.seriesuid

caminho = volumes.caminho_do_volume(cfg["caminhos"]["luna16"], uid, cfg["selecao"]["subsets"])
caminho_mascara = cfg["caminhos"]["luna16_mascaras"] / f"{uid}.mhd"
if caminho is None:
    sys.exit(f"volume não encontrado nos subsets {cfg['selecao']['subsets']}: {uid}")
if not caminho_mascara.exists():
    sys.exit(f"máscara não encontrada: {caminho_mascara}")

original = sitk.ReadImage(str(caminho))
processado, mascara_iso = pre.preprocessar(original, sitk.ReadImage(str(caminho_mascara)), hu, alvo)


def extensao(imagem):
    return [d * e for d, e in zip(imagem.GetSize(), imagem.GetSpacing())]


def descrever(nome, imagem):
    print(f"  {nome:8s} {' x '.join(str(d) for d in imagem.GetSize()):>17s} voxels"
          f"   {' x '.join(f'{e:.4g}' for e in imagem.GetSpacing()):>20s} mm"
          f"   extensão {' x '.join(f'{v:.1f}' for v in extensao(imagem))} mm")


mundo = (escolhido.coordX, escolhido.coordY, escolhido.coordZ)
print(f"{uid}")
print(f"nódulo de {escolhido.diameter_mm:.1f} mm em {tuple(round(v, 1) for v in mundo)} mm\n")

descrever("antes", original)
descrever("depois", processado)

pulmao = sitk.GetArrayFromImage(mascara_iso) > 0
print(f"\npulmão: {pulmao.mean():.1%} dos voxels do volume reamostrado")

arr = sitk.GetArrayFromImage(processado)
print(f"intensidade depois: de {arr.min()} a {arr.max()} HU, dentro da janela {hu[0]} a {hu[1]}")

for nome, imagem in [("antes", original), ("depois", processado)]:
    print(f"o nódulo cai no voxel {imagem.TransformPhysicalPointToIndex(mundo)} {nome}")

saida = cfg["caminhos"]["processado"] / f"{uid}.mha"
saida.parent.mkdir(parents=True, exist_ok=True)
escritor = sitk.ImageFileWriter()
escritor.SetFileName(str(saida))
escritor.UseCompressionOn()
escritor.Execute(processado)
print(f"\n{saida}  {saida.stat().st_size / 1e6:.1f} MB")

figura = cfg["caminhos"]["figuras"] / "preprocessamento.png"
fatias.antes_e_depois(
    original, processado, mundo, escolhido.diameter_mm / 2, hu,
    f"nódulo de {escolhido.diameter_mm:.1f} mm, {escolhido.orientacao}", figura,
)
print(figura)
