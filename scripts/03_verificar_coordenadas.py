"""Verifica a conversão de coordenada: onde cada nódulo anotado cai dentro do volume."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import SimpleITK as sitk

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config
from dataset import volumes
from preprocessing import coordenadas
from visualization import fatias

AMOSTRA_HU = 12
CANDIDATOS_POR_FIGURA = 10

cfg = config.carregar()
config.fixar_semente()

luna = cfg["caminhos"]["luna16"]
subsets = cfg["selecao"]["subsets"]
hu = (cfg["pre_processamento"]["hu_min"], cfg["pre_processamento"]["hu_max"])

inventario = pd.read_csv(cfg["caminhos"]["intermediario"] / "inventario_volumes.csv")
anotacoes = pd.read_csv(cfg["caminhos"]["luna16_anotacoes"])
nodulos = anotacoes.merge(inventario, on="seriesuid")


def indice_do_nodulo(linha):
    origem, espacamento, direcao = coordenadas.geometria(linha)
    return coordenadas.mundo_para_indice(
        (linha["coordX"], linha["coordY"], linha["coordZ"]), origem, espacamento, direcao
    )


def indice_ingenuo(linha):
    """A fórmula sem direção, para comparação."""
    origem, espacamento, _ = coordenadas.geometria(linha)
    mundo = np.array([linha["coordX"], linha["coordY"], linha["coordZ"]])
    return (mundo - np.array(origem)) / np.array(espacamento)


def conferir(quais, indice_de):
    fora = []
    for linha in quais.itertuples():
        indice = indice_de(linha._asdict())
        if not coordenadas.dentro_do_volume(indice, (linha.dim_x, linha.dim_y, linha.dim_z)):
            fora.append((linha.seriesuid, indice))
    return fora


def carregar(seriesuid):
    caminho = volumes.caminho_do_volume(luna, seriesuid, subsets)
    return sitk.GetArrayFromImage(sitk.ReadImage(str(caminho)))


def hu_no_nodulo(volume, indice, diametro_mm, espacamento):
    """Mediana de HU dentro do nódulo, com raio por eixo."""
    x, y, z = (int(round(v)) for v in indice)
    rx, ry, rz = (max(1, int(round((diametro_mm / 2) / e * 0.6))) for e in espacamento)
    caixa = volume[max(0, z - rz):z + rz + 1, max(0, y - ry):y + ry + 1, max(0, x - rx):x + rx + 1]
    return np.median(caixa) if caixa.size else np.nan


def comparar_com_espelhado(amostra):
    """Compara o HU no índice convertido com o do índice espelhado."""
    certo, espelhado = [], []
    for linha in amostra.itertuples():
        volume = carregar(linha.seriesuid)
        campos = linha._asdict()
        _, espacamento, _ = coordenadas.geometria(campos)
        indice = indice_do_nodulo(campos)
        oposto = (linha.dim_x - 1 - indice[0], linha.dim_y - 1 - indice[1], indice[2])
        certo.append(hu_no_nodulo(volume, indice, linha.diameter_mm, espacamento))
        espelhado.append(hu_no_nodulo(volume, oposto, linha.diameter_mm, espacamento))
    return np.median(certo), np.median(espelhado)


def escolher(quais):
    """O mais sólido entre os maiores."""
    maiores = quais.nlargest(CANDIDATOS_POR_FIGURA, "diameter_mm")
    densidade = []
    for linha in maiores.itertuples():
        campos = linha._asdict()
        _, espacamento, _ = coordenadas.geometria(campos)
        volume = carregar(linha.seriesuid)
        densidade.append(hu_no_nodulo(volume, indice_do_nodulo(campos), linha.diameter_mm, espacamento))
    return maiores.iloc[int(np.argmax(densidade))]


def figura(linha, rotulo):
    volume = carregar(linha["seriesuid"])
    _, espacamento, _ = coordenadas.geometria(linha)
    indice = indice_do_nodulo(linha)
    raio = (linha["diameter_mm"] / 2) / espacamento[0]

    saida = cfg["caminhos"]["figuras"] / f"coordenada_{rotulo}.png"
    titulo = f"{linha['orientacao']}, nódulo de {linha['diameter_mm']:.1f} mm"
    fatias.fatia_com_nodulo(volume, indice, raio, hu, titulo, saida)

    dentro = hu_no_nodulo(volume, indice, linha["diameter_mm"], espacamento)
    return saida, indice, dentro, np.median(volume[int(round(indice[2]))])


invertidos = nodulos[~nodulos.matriz_identidade]
retos = nodulos[nodulos.matriz_identidade]

fora = conferir(nodulos, indice_do_nodulo)
print(f"{len(nodulos)} nódulos em {nodulos.seriesuid.nunique()} volumes, {len(fora)} fora do volume")
for uid, indice in fora[:10]:
    print(f"  {uid}  {np.round(indice, 1)}")

fora_ingenua = conferir(invertidos, indice_ingenuo)
print(f"{len(invertidos)} nódulos nos volumes invertidos, {len(fora_ingenua)} cairiam fora sem a direção")

certo, espelhado = comparar_com_espelhado(nodulos.sample(AMOSTRA_HU, random_state=cfg["seed"]))
print(f"HU mediano em {AMOSTRA_HU} nódulos: {certo:.0f} no índice convertido, {espelhado:.0f} no espelhado")

for rotulo, quais in [("rai", retos), ("lpi", invertidos)]:
    saida, indice, dentro, na_fatia = figura(escolher(quais), rotulo)
    print(f"{saida.name}  voxel {np.round(indice, 1)}  HU {dentro:.0f} no nódulo, {na_fatia:.0f} na fatia")
