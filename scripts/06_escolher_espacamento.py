"""Compara espaçamentos de reamostragem: contraste do nódulo, custo e cobertura do recorte.

Existe porque o valor de 1 mm entrou no config antes de qualquer medição. Ver decisão 0004.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import SimpleITK as sitk

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config
from dataset import volumes
from preprocessing import volume as pre
from visualization import eda

ALVOS = [0.5, 0.625, 0.7, 0.8, 1.0, 1.25, 1.5, 2.0]
NODULOS = 40
REAMOSTRAS = 1000

cfg = config.carregar()
config.fixar_semente()

hu = (cfg["pre_processamento"]["hu_min"], cfg["pre_processamento"]["hu_max"])
patch = cfg["candidatos"]["patch"][0]

inventario = pd.read_csv(cfg["caminhos"]["intermediario"] / "inventario_volumes.csv")
anotacoes = pd.read_csv(cfg["caminhos"]["luna16_anotacoes"])
nodulos = anotacoes.merge(inventario, on="seriesuid")


def contraste(volume, imagem, mundo, raio_mm, alvo):
    """Quanto o nódulo se destaca do parênquima em volta, em HU."""
    x, y, z = imagem.TransformPhysicalPointToIndex(mundo)
    r = max(1, int(round(raio_mm / alvo)))
    dentro = volume[max(0, z - r):z + r + 1, max(0, y - r):y + r + 1, max(0, x - r):x + r + 1]
    fora = volume[max(0, z - 3 * r):z + 3 * r + 1, max(0, y - 3 * r):y + 3 * r + 1, max(0, x - 3 * r):x + 3 * r + 1]
    if not dentro.size or not fora.size:
        return None
    return float(np.median(dentro) - np.median(fora))


def intervalo(valores):
    v = np.asarray(valores, float)
    rng = np.random.default_rng(cfg["seed"])
    medias = [np.median(rng.choice(v, len(v))) for _ in range(REAMOSTRAS)]
    return np.median(v), np.percentile(medias, 2.5), np.percentile(medias, 97.5)


# Amostra estratificada por diâmetro, só em volumes de direção identidade.
retos = nodulos[nodulos.matriz_identidade]
faixas = [retos[retos.diameter_mm < 6],
          retos[(retos.diameter_mm >= 6) & (retos.diameter_mm < 12)],
          retos[retos.diameter_mm >= 12]]
por_faixa = NODULOS // 3
amostra = pd.concat([f.sample(min(por_faixa, len(f)), random_state=cfg["seed"]) for f in faixas])

medidas = {a: [] for a in ALVOS}
lidos, sem_volume = 0, 0
for linha in amostra.itertuples():
    caminho = volumes.caminho_do_volume(cfg["caminhos"]["luna16"], linha.seriesuid, cfg["selecao"]["subsets"])
    if caminho is None:
        sem_volume += 1
        continue
    bruto = pre.janela(sitk.ReadImage(str(caminho)), *hu)
    mundo = (linha.coordX, linha.coordY, linha.coordZ)
    for alvo in ALVOS:
        iso = pre.reamostrar(bruto, [alvo] * 3, sitk.sitkLinear, fundo=hu[0])
        c = contraste(sitk.GetArrayFromImage(iso), iso, mundo, linha.diameter_mm / 2, alvo)
        if c is not None:
            medidas[alvo].append(c)
    lidos += 1

print(f"{lidos} nódulos medidos, {sem_volume} sem volume em disco")
print(f"diâmetro de {amostra.diameter_mm.min():.1f} a {amostra.diameter_mm.max():.1f} mm\n")

print(f"{'mm':>6} {'contraste (HU)':>24} {'nódulo':>8} {'não cabem':>10} {'volume':>9}")
print(f"{'':>6} {'mediana e IC 95%':>24} {'pontos':>8} {'em 32':>10} {'Mvox':>9}")
print("-" * 62)

linhas = []
for alvo in ALVOS:
    m, lo, hi = intervalo(medidas[alvo])
    fora = int((anotacoes.diameter_mm > patch * alvo).sum())
    mvox = np.prod([np.mean(inventario[f"dim_{e}"] * inventario[f"espacamento_{e}"]) / alvo
                    for e in "xyz"]) / 1e6
    linhas.append({"alvo": alvo, "contraste": m, "lo": lo, "hi": hi,
                   "pontos": anotacoes.diameter_mm.median() / alvo, "fora": fora, "mvox": mvox})
    print(f"{alvo:6.3g} {m:10.0f}  [{lo:5.0f}, {hi:5.0f}] {anotacoes.diameter_mm.median()/alvo:8.1f} "
          f"{fora:10d} {mvox:9.0f}")

tabela = pd.DataFrame(linhas)
saida = cfg["caminhos"]["intermediario"] / "espacamento.csv"
tabela.to_csv(saida, index=False)
print(f"\n{saida}")

figura = eda.escolha_do_espacamento(tabela, cfg["caminhos"]["figuras"] / "eda_espacamento_alvo.png")
print(figura)
