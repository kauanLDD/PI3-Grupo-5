"""Montagem do treino com a V2 e a nossa lista: partição, ignorados, sorteio e cotas."""

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest
import SimpleITK as sitk

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from detection import recorte
from experimentos import cnn

VIZINHOS = {"fracao": 0.5, "distancia_maxima_mm": 16, "distancia_minima_diametros": 1.0}


def divisao():
    return pd.DataFrame({"seriesuid": ["a", "b", "c"], "paciente": ["p1", "p2", "p3"],
                         "subset": [0, 7, 8], "particao": ["treino", "validacao", "teste"]})


def nodulos():
    return pd.DataFrame({"seriesuid": ["a", "b"], "coordX": [0., 0.], "coordY": [0., 0.],
                         "coordZ": [0., 0.], "diameter_mm": [6., 6.]})


def excluidos():
    return pd.DataFrame({"seriesuid": ["a"], "coordX": [100.], "coordY": [100.], "coordZ": [100.],
                         "diameter_mm": [-1.]})


def lista_v2():
    linhas = []
    for uid in "abc":
        linhas += [(uid, 0., 0., 0., 1), (uid, 0.5, 0., 0., 1)]
        linhas += [(uid, 200. + i, 0., 0., 0) for i in range(30)]
    return pd.DataFrame(linhas, columns=["seriesuid", "coordX", "coordY", "coordZ", "class"])


def lista_propria():
    pontos = [(1., 0., 0.),            # acerto: dentro do raio de 3 mm
              (4., 0., 0.),            # colado: fora do raio, a menos de um diâmetro
              (101., 100., 100.),      # ignorado: em cima do achado excluído
              (10., 0., 0.), (12., 0., 0.), (-10., 0., 0.), (0., 14., 0.)]  # vizinhos
    pontos += [(50. + i, 0., 0.) for i in range(20)]
    linhas = [(uid, *p, 1.7) for uid in "abc" for p in pontos]
    return pd.DataFrame(linhas, columns=["seriesuid", "coordX", "coordY", "coordZ", "raio"])


def selecionar(semente=42, vizinhos=None, por_bloco=None):
    propria = lista_propria()
    tamanho = por_bloco or len(propria)
    blocos = (propria.iloc[i:i + tamanho] for i in range(0, len(propria), tamanho))
    return cnn.selecionar_misto(lista_v2(), blocos, divisao(), nodulos(), excluidos(), 4, 0.5,
                                vizinhos, semente)


@pytest.mark.parametrize("vizinhos", [None, VIZINHOS])
def test_so_usa_exames_de_treino_e_nunca_ignorado_nem_colado(vizinhos):
    selecionados, contagem = selecionar(vizinhos=vizinhos)
    assert set(selecionados.seriesuid) == {"a"}
    propria = selecionados[selecionados.origem.eq("propria")]
    assert not ((propria.coordX == 101) & (propria.coordY == 100)).any()
    assert contagem["ignorado"] == 1 and contagem["acerto"] == 1
    if vizinhos is not None:
        assert not (propria.coordX == 4).any()
        assert contagem["colado"] == 1 and contagem["vizinho"] == 4


def test_negativos_meio_a_meio_e_acertos_nao_aumentam_negativos():
    selecionados, _ = selecionar()
    negativos = selecionados[selecionados["class"].eq(0)]
    assert len(negativos) == 2 * 4
    assert negativos.origem.value_counts().to_dict() == {"v2": 4, "propria": 4}
    positivos = selecionados[selecionados["class"].eq(1)]
    assert positivos.origem.value_counts().to_dict() == {"v2": 2, "propria": 1}
    assert positivos.loc[positivos.origem.eq("propria"), "coordX"].tolist() == [1.]


def test_cota_de_vizinhos_na_variante_b():
    selecionados, _ = selecionar(vizinhos=VIZINHOS)
    negativos = selecionados[selecionados["class"].eq(0) & selecionados.origem.eq("propria")]
    assert negativos.grupo.value_counts().to_dict() == {"vizinho": 2, "comum": 2}
    vizinhos = negativos[negativos.grupo.eq("vizinho")]
    distancia = np.linalg.norm(vizinhos[["coordX", "coordY", "coordZ"]].to_numpy(), axis=1)
    assert ((distancia >= 6) & (distancia <= 16)).all()


@pytest.mark.parametrize("vizinhos", [None, VIZINHOS])
def test_mesma_semente_mesmo_sorteio_e_outra_semente_outro(vizinhos):
    primeiro, _ = selecionar(42, vizinhos)
    pd.testing.assert_frame_equal(primeiro, selecionar(42, vizinhos)[0])
    assert not primeiro.equals(selecionar(43, vizinhos)[0])


def test_sorteio_nao_depende_do_tamanho_do_bloco():
    pd.testing.assert_frame_equal(selecionar(por_bloco=7)[0], selecionar()[0])


def test_recusa_cota_maior_que_os_vizinhos_disponiveis():
    vizinhos = {**VIZINHOS, "fracao": 1.0}
    with pytest.raises(ValueError, match="grupo vizinho"):
        cnn.selecionar_misto(lista_v2(), [lista_propria()], divisao(), nodulos(), excluidos(), 4, 1.0,
                             vizinhos, 42)


def test_treinar_e_o_laco_sobre_os_cubos_do_disco(tmp_path):
    gerador = np.random.default_rng(0)
    candidatos = lista_v2().iloc[:12].copy()
    candidatos["class"] = [1, 1] + [0] * 10
    cubos = gerador.random((12, 34, 34, 34), dtype=np.float32)
    np.savez_compressed(tmp_path / "a.npz", patches=cubos, candidate_id=candidatos.index.to_numpy(),
                        coordX=candidatos.coordX.to_numpy(np.float32),
                        coordY=candidatos.coordY.to_numpy(np.float32),
                        coordZ=candidatos.coordZ.to_numpy(np.float32),
                        classe_luna16=candidatos["class"].to_numpy(np.int8))
    parametros = {"patch_size": 32, "batch_size": 4, "learning_rate": 3e-4, "epochs": 1,
                  "dropout_rate": 0.3, "weight_decay": 1e-5, "negativos_por_positivo": 5, "aumento": True}
    cnn.fixar_determinismo(42, 1)
    modelo, selecionados, _ = cnn.treinar(candidatos, divisao(), tmp_path, parametros, 42, "cpu",
                                          lambda linha: None)
    recortes, grupo = cnn.ler_exame(tmp_path, "a", candidatos, 32)
    mascara = grupo.index.isin(selecionados.index)
    cnn.fixar_determinismo(42, 1)
    direto, _ = cnn.treinar_cubos(recortes[mascara], grupo.loc[mascara, "class"].to_numpy(np.int64),
                                  parametros, 42, "cpu", lambda linha: None)
    assert cnn.hash_pesos(modelo) == cnn.hash_pesos(direto)


def test_cubos_seguem_a_ordem_da_selecao_e_a_conferencia_pega_divergencia(tmp_path):
    volume = np.random.default_rng(1).random((60, 70, 80), dtype=np.float32)
    imagem = sitk.GetImageFromArray(volume)
    imagem.SetOrigin((-40., -35., -30.))
    imagem.SetSpacing((1., 1., 1.))
    sitk.WriteImage(imagem, str(tmp_path / "a.mha"))
    v2 = pd.DataFrame({"seriesuid": ["a"] * 3, "coordX": [0., 5., -5.], "coordY": [0., 3., -2.],
                       "coordZ": [0., 1., -1.], "class": [1, 0, 0]}, index=[7, 8, 9])
    pontos = v2[["coordX", "coordY", "coordZ"]].to_numpy(float)
    np.savez_compressed(tmp_path / "a.npz", patches=recorte.recortar(imagem, volume, pontos, (34,) * 3),
                        candidate_id=v2.index.to_numpy(), coordX=v2.coordX.to_numpy(np.float32),
                        coordY=v2.coordY.to_numpy(np.float32), coordZ=v2.coordZ.to_numpy(np.float32),
                        classe_luna16=v2["class"].to_numpy(np.int8))
    selecionados = pd.DataFrame({"origem": ["propria", "v2", "v2"], "candidate_id": [-1, 9, 7],
                                 "seriesuid": ["a"] * 3, "coordX": [2., -5., 0.], "coordY": [2., -2., 0.],
                                 "coordZ": [2., -1., 0.]})
    cubos = cnn.montar_cubos(selecionados, v2, tmp_path, tmp_path, 32)
    esperado = recorte.recortar(imagem, volume, selecionados[["coordX", "coordY", "coordZ"]].to_numpy(float),
                                (32,) * 3)
    np.testing.assert_allclose(cubos, esperado, rtol=0, atol=0)
    assert cnn.conferir_recorte(v2, ["a"], tmp_path, tmp_path, 32, 1e-5) == 0
    with np.load(tmp_path / "a.npz") as dados:
        alterado = dict(dados)
    alterado["patches"] = alterado["patches"].copy()
    alterado["patches"][0, 17, 17, 17] += 0.5
    np.savez_compressed(tmp_path / "a.npz", **alterado)
    with pytest.raises(ValueError, match="diverge"):
        cnn.conferir_recorte(v2, ["a"], tmp_path, tmp_path, 32, 1e-5)
