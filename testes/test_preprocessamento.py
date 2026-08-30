"""Janela de HU, reamostragem isotrópica e máscara de pulmão."""

import sys
from pathlib import Path

import numpy as np
import pytest
import SimpleITK as sitk

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "codigo"))
from pi3 import config
from pi3.dados import volumes
from pi3.preprocessamento import volume as pre

HU = (-1000, 400)
ALVO = [1.0, 1.0, 1.0]
ESPACAMENTO = (0.7, 0.7, 2.5)
ORIGEM = (-100.0, -50.0, -200.0)


def sintetico(valor_fundo=-1000, valor_cubo=100):
    """Volume com um cubo denso no meio, em espaçamento anisotrópico."""
    arr = np.full((20, 64, 64), valor_fundo, dtype=np.int16)
    arr[8:12, 28:36, 28:36] = valor_cubo
    imagem = sitk.GetImageFromArray(arr)
    imagem.SetSpacing(ESPACAMENTO)
    imagem.SetOrigin(ORIGEM)
    return imagem


def mascara_sintetica():
    arr = np.zeros((20, 64, 64), dtype=np.uint8)
    arr[6:14, 20:44, 20:32] = 3
    arr[6:14, 20:44, 32:44] = 4
    imagem = sitk.GetImageFromArray(arr)
    imagem.SetSpacing(ESPACAMENTO)
    imagem.SetOrigin(ORIGEM)
    return imagem


def test_janela_corta_nos_dois_lados():
    arr = sitk.GetArrayFromImage(pre.janela(sintetico(valor_fundo=-2000, valor_cubo=3000), *HU))
    assert arr.min() == HU[0] and arr.max() == HU[1]


def test_reamostragem_preserva_origem_e_direcao():
    original = sintetico()
    iso = pre.reamostrar(original, ALVO)
    assert iso.GetOrigin() == original.GetOrigin()
    assert iso.GetDirection() == original.GetDirection()


def test_reamostragem_deixa_o_espacamento_exatamente_no_alvo():
    assert pre.reamostrar(sintetico(), ALVO).GetSpacing() == tuple(ALVO)


def test_reamostragem_preserva_a_extensao_fisica():
    original = sintetico()
    iso = pre.reamostrar(original, ALVO)
    for antes, depois, alvo in zip(
        (d * e for d, e in zip(original.GetSize(), original.GetSpacing())),
        (d * e for d, e in zip(iso.GetSize(), iso.GetSpacing())),
        ALVO,
    ):
        assert abs(antes - depois) <= alvo


def test_o_conteudo_continua_no_mesmo_lugar_do_mundo():
    """O cubo denso continua na mesma posição em milímetro."""
    original = sintetico()
    iso = pre.reamostrar(original, ALVO)

    centro_mundo = original.TransformContinuousIndexToPhysicalPoint([31.5, 31.5, 9.5])
    for imagem in (original, iso):
        indice = imagem.TransformPhysicalPointToIndex(centro_mundo)
        assert sitk.GetArrayFromImage(imagem)[indice[2], indice[1], indice[0]] == 100


def test_a_reamostragem_ingenua_erraria_o_lugar():
    """A fórmula sem a geometria nova cai em outro voxel."""
    iso = pre.reamostrar(sintetico(), ALVO)
    centro_mundo = sintetico().TransformContinuousIndexToPhysicalPoint([31.5, 31.5, 9.5])

    certo = iso.TransformPhysicalPointToIndex(centro_mundo)
    ingenuo = tuple(int(round((m - o) / e)) for m, o, e in zip(centro_mundo, ORIGEM, ESPACAMENTO))
    assert certo != ingenuo


def test_binarizar_aceita_os_rotulos_do_desafio():
    arr = sitk.GetArrayFromImage(pre.binarizar(mascara_sintetica()))
    assert set(np.unique(arr)) == {0, 1}


def test_mascara_continua_binaria_depois_de_reamostrar():
    iso = pre.reamostrar(pre.binarizar(mascara_sintetica()), ALVO, sitk.sitkNearestNeighbor)
    assert set(np.unique(sitk.GetArrayFromImage(iso))) <= {0, 1}


def test_fora_do_pulmao_vira_ar_e_nao_agua():
    processado, mascara = pre.preprocessar(sintetico(), mascara_sintetica(), HU, ALVO)
    arr = sitk.GetArrayFromImage(processado)
    fora = sitk.GetArrayFromImage(mascara) == 0
    assert (arr[fora] == HU[0]).all()


def test_preprocessar_devolve_volume_e_mascara_na_mesma_grade():
    processado, mascara = pre.preprocessar(sintetico(), mascara_sintetica(), HU, ALVO)
    assert processado.GetSize() == mascara.GetSize()
    assert processado.GetSpacing() == mascara.GetSpacing()
    assert processado.GetOrigin() == mascara.GetOrigin()


def um_exame_de_verdade():
    cfg = config.carregar()
    inventario = cfg["caminhos"]["intermediario"] / "inventario_volumes.csv"
    if not inventario.exists():
        return []

    import pandas as pd

    d = pd.read_csv(inventario)
    anotados = pd.read_csv(cfg["caminhos"]["luna16_anotacoes"]).merge(d, on="seriesuid")
    linha = anotados[anotados.matriz_identidade].nlargest(1, "diameter_mm").iloc[0]
    caminho = volumes.caminho_do_volume(cfg["caminhos"]["luna16"], linha.seriesuid, cfg["selecao"]["subsets"])
    mascara = cfg["caminhos"]["luna16_mascaras"] / f"{linha.seriesuid}.mhd"
    if caminho is None or not mascara.exists():
        return []
    return [pytest.param(linha, caminho, mascara, id=f"{linha.diameter_mm:.0f}mm")]


@pytest.mark.parametrize("linha,caminho,caminho_mascara", um_exame_de_verdade())
def test_o_nodulo_sobrevive_ao_preprocessamento(linha, caminho, caminho_mascara):
    """Nódulo real continua denso e na mesma posição depois do pré-processamento."""
    original = sitk.ReadImage(str(caminho))
    processado, _ = pre.preprocessar(original, sitk.ReadImage(str(caminho_mascara)), HU, ALVO)

    mundo = (linha.coordX, linha.coordY, linha.coordZ)
    assert processado.GetSpacing() == tuple(ALVO)

    antes = sitk.GetArrayFromImage(original)
    depois = sitk.GetArrayFromImage(processado)
    ia = original.TransformPhysicalPointToIndex(mundo)
    ip = processado.TransformPhysicalPointToIndex(mundo)

    assert antes[ia[2], ia[1], ia[0]] > -500
    assert depois[ip[2], ip[1], ip[0]] > -500


# Exame em que as duas formas de binarizar discordam. Ver decisão 0002.
EXAME_DA_DISCORDANCIA = "1.3.6.1.4.1.14519.5.2.1.6279.6001.121993590721161347818774929286"


def alcancavel(mascara, indice, raio_mm, espacamento) -> bool:
    """Existe voxel de máscara a menos de R do centro, que é o critério de acerto do desafio."""
    x, y, z = (int(round(v)) for v in indice)
    r = [max(1, int(np.ceil(raio_mm / e))) for e in espacamento]
    z0, y0, x0 = max(0, z - r[2]), max(0, y - r[1]), max(0, x - r[0])
    caixa = mascara[z0:z + r[2] + 1, y0:y + r[1] + 1, x0:x + r[0] + 1]
    if not caixa.size:
        return False
    zz, yy, xx = np.ogrid[z0:z0 + caixa.shape[0], y0:y0 + caixa.shape[1], x0:x0 + caixa.shape[2]]
    dentro = ((zz - z) * espacamento[2]) ** 2 + ((yy - y) * espacamento[1]) ** 2 + ((xx - x) * espacamento[0]) ** 2
    return bool((caixa & (dentro <= raio_mm ** 2)).any())


def o_exame_da_discordancia():
    cfg = config.carregar()
    inventario = cfg["caminhos"]["intermediario"] / "inventario_volumes.csv"
    caminho = cfg["caminhos"]["luna16_mascaras"] / f"{EXAME_DA_DISCORDANCIA}.mhd"
    if not inventario.exists() or not caminho.exists():
        return []

    import pandas as pd

    d = pd.read_csv(inventario)
    linha = d[d.seriesuid == EXAME_DA_DISCORDANCIA]
    anotados = pd.read_csv(cfg["caminhos"]["luna16_anotacoes"])
    nodulos = anotados[anotados.seriesuid == EXAME_DA_DISCORDANCIA]
    if linha.empty or nodulos.empty:
        return []
    return [pytest.param(linha.iloc[0], nodulos, caminho, id="discordancia")]


@pytest.mark.parametrize("linha,nodulos,caminho", o_exame_da_discordancia())
def test_rotulo_zero_recupera_dois_nodulos_que_o_padrao_perde(linha, nodulos, caminho):
    """`> 0` alcança os dois nódulos deste exame e `== 3 ou == 4` não alcança nenhum."""
    from pi3.preprocessamento import coordenadas

    imagem = sitk.ReadImage(str(caminho))
    bruta = sitk.GetArrayFromImage(imagem)
    # Passa pela função de verdade, senão o teste não protege o código.
    nosso = sitk.GetArrayFromImage(pre.binarizar(imagem)) > 0
    da_literatura = np.isin(bruta, [3, 4])

    origem, espacamento, direcao = coordenadas.geometria(linha)
    for n in nodulos.itertuples():
        indice = coordenadas.mundo_para_indice((n.coordX, n.coordY, n.coordZ), origem, espacamento, direcao)
        raio = n.diameter_mm / 2
        assert alcancavel(nosso, indice, raio, espacamento), f"o nosso critério perdeu o nódulo de {n.diameter_mm:.1f} mm"
        assert not alcancavel(da_literatura, indice, raio, espacamento), (
            f"o nódulo de {n.diameter_mm:.1f} mm deixou de ser exclusivo do rótulo 5, "
            "a decisão 0002 precisa ser remedida"
        )


@pytest.mark.parametrize("linha,nodulos,caminho", o_exame_da_discordancia())
def test_a_mascara_do_desafio_tem_o_rotulo_5(linha, nodulos, caminho):
    # Rótulos medidos nas nossas máscaras: 0, 3, 4 e 5.
    presentes = set(np.unique(sitk.GetArrayFromImage(sitk.ReadImage(str(caminho)))).tolist())
    assert 5 in presentes, f"o rótulo 5 sumiu, os rótulos agora são {sorted(presentes)}"
