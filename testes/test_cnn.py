"""Identidade dos candidatos, separação de pacientes e amostragem só no treino."""

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from experimentos import cnn


def divisao():
    return pd.DataFrame({"seriesuid": ["a", "b", "c"], "paciente": ["p1", "p2", "p3"],
                         "subset": [0, 7, 8], "particao": ["treino", "validacao", "teste"]})


def test_recusa_vazamento_de_paciente():
    tabela = divisao()
    tabela.loc[2, "paciente"] = "p1"
    with pytest.raises(ValueError, match="compartilhado"):
        cnn.conferir_divisao(tabela)


def test_amostra_preserva_todos_positivos_e_nunca_usa_teste():
    candidatos = pd.DataFrame({"seriesuid": ["a"] * 22 + ["b", "c"],
                               "class": [1, 1] + [0] * 20 + [1, 1]})
    primeiro = cnn.selecionar_treino(candidatos, divisao(), 5, 42)
    segundo = cnn.selecionar_treino(candidatos, divisao(), 5, 42)
    pd.testing.assert_frame_equal(primeiro, segundo)
    assert len(primeiro) == 12 and primeiro["class"].sum() == 2
    assert set(primeiro.seriesuid) == {"a"}
    assert set(primeiro.loc[primeiro["class"].eq(1), "candidate_id"]) == {0, 1}


def test_inferencia_cobre_todos_candidatos_e_preserva_coordenadas(tmp_path):
    candidatos = pd.DataFrame({"seriesuid": ["c"] * 3, "coordX": [1., 2., 3.],
                               "coordY": [4., 5., 6.], "coordZ": [7., 8., 9.],
                               "class": [1, 0, 0]}, index=[10, 11, 12])
    cubos = np.zeros((3, 34, 34, 34), dtype=np.float32)
    cubos[:, 17, 17, 17] = 1
    np.savez_compressed(tmp_path / "c.npz", patches=cubos,
                        candidate_id=candidatos.index.to_numpy(),
                        coordX=candidatos.coordX.to_numpy(dtype=np.float32),
                        coordY=candidatos.coordY.to_numpy(dtype=np.float32),
                        coordZ=candidatos.coordZ.to_numpy(dtype=np.float32),
                        classe_luna16=candidatos["class"].to_numpy(dtype=np.int8))
    recortes, _ = cnn.ler_exame(tmp_path, "c", candidatos, 32)
    assert recortes.shape == (3, 32, 32, 32)
    assert (recortes[:, 16, 16, 16] == 1).all()
    cnn.fixar_determinismo(42, 1)
    resultado = cnn.prever(cnn.CNN3D(), candidatos, divisao(), "teste", tmp_path,
                           {"patch_size": 32, "batch_size": 2}, "cpu")
    assert resultado.candidate_id.tolist() == [10, 11, 12]
    assert resultado.coordX.tolist() == [1., 2., 3.]
    assert resultado.probability.between(0, 1).all()
    corrompidos = candidatos.copy()
    corrompidos.loc[10, "coordX"] = 100
    with pytest.raises(ValueError, match="coordX diverge"):
        cnn.ler_exame(tmp_path, "c", corrompidos, 32)


def test_recorte_de_16_e_o_centro_do_cubo_de_34(tmp_path):
    """A rede de conferência lê os mesmos recortes de 34 do disco e fica só com os 16 do meio."""
    candidatos = pd.DataFrame({"seriesuid": ["c"] * 2, "coordX": [1., 2.], "coordY": [3., 4.],
                               "coordZ": [5., 6.], "class": [1, 0]}, index=[20, 21])
    cubos = np.random.default_rng(0).random((2, 34, 34, 34), dtype=np.float32)
    np.savez_compressed(tmp_path / "c.npz", patches=cubos,
                        candidate_id=candidatos.index.to_numpy(),
                        coordX=candidatos.coordX.to_numpy(dtype=np.float32),
                        coordY=candidatos.coordY.to_numpy(dtype=np.float32),
                        coordZ=candidatos.coordZ.to_numpy(dtype=np.float32),
                        classe_luna16=candidatos["class"].to_numpy(dtype=np.int8))
    recortes, grupo = cnn.ler_exame(tmp_path, "c", candidatos, 16)
    assert recortes.shape == (2, 16, 16, 16) and recortes.flags.c_contiguous
    # Margem de 9 voxels em cada lado: índices 9 a 24 do cubo de 34.
    np.testing.assert_array_equal(recortes, cubos[:, 9:25, 9:25, 9:25])
    # O voxel central 17 do cubo de 34 cai no 8 do cubo de 16, como cai no 16 do cubo de 32.
    np.testing.assert_array_equal(recortes[:, 8, 8, 8], cubos[:, 17, 17, 17])
    np.testing.assert_array_equal(recortes, cnn.ler_exame(tmp_path, "c", candidatos, 32)[0][:, 8:24, 8:24, 8:24])
    assert grupo.index.tolist() == [20, 21]
    with torch.inference_mode():
        assert cnn.CNN3D()(torch.from_numpy(recortes).unsqueeze(1)).shape == (2, 2)
    with pytest.raises(ValueError, match="16, 32 ou 34"):
        cnn.ler_exame(tmp_path, "c", candidatos, 24)


def test_checkpoint_restaurado_preserva_logits(tmp_path):
    cnn.fixar_determinismo(42, 1)
    modelo = cnn.CNN3D().eval()
    entrada = torch.rand(2, 1, 32, 32, 32)
    torch.save(modelo.state_dict(), tmp_path / "modelo.pt")
    restaurado = cnn.CNN3D().eval()
    restaurado.load_state_dict(torch.load(tmp_path / "modelo.pt", weights_only=True))
    with torch.inference_mode():
        torch.testing.assert_close(modelo(entrada), restaurado(entrada), rtol=0, atol=0)
    assert cnn.hash_pesos(modelo) == cnn.hash_pesos(restaurado)


def test_determinismo_estrito_na_cpu_e_so_aviso_na_gpu():
    cnn.fixar_determinismo(42, 1, "cuda")
    assert torch.are_deterministic_algorithms_enabled()
    assert torch.is_deterministic_algorithms_warn_only_enabled()
    cnn.fixar_determinismo(42, 1)
    assert not torch.is_deterministic_algorithms_warn_only_enabled()


def test_aumento_preserva_forma_valores_e_centro_a_um_voxel():
    cubos = torch.zeros(8, 1, 32, 32, 32)
    cubos[:, 0, 16, 16, 16] = 1
    gerador = torch.Generator().manual_seed(0)
    saida = cnn.aumentar(cubos, gerador)
    assert saida.shape == cubos.shape
    assert torch.equal(saida.sum(dim=(1, 2, 3, 4)), cubos.sum(dim=(1, 2, 3, 4)))
    # O centro de um cubo de 32 fica entre os índices 15 e 16; espelhar troca um pelo outro.
    marcados = saida[:, 0].nonzero()[:, 1:]
    assert ((marcados >= 15) & (marcados <= 16)).all()


def exames_sinteticos(pasta):
    linhas, gerador = [], np.random.default_rng(0)
    for uid in ("a", "b"):
        classes = np.array([1, 0, 0, 0, 1, 0, 0, 0])
        cubos = gerador.random((len(classes), 34, 34, 34), dtype=np.float32) * 0.5
        cubos[classes == 1, 13:21, 13:21, 13:21] = 1
        ids = np.arange(len(linhas), len(linhas) + len(classes))
        coords = np.arange(len(classes), dtype=np.float32)
        np.savez_compressed(Path(pasta) / f"{uid}.npz", patches=cubos, candidate_id=ids,
                            coordX=coords, coordY=coords, coordZ=coords,
                            classe_luna16=classes.astype(np.int8))
        linhas += [{"seriesuid": uid, "coordX": c, "coordY": c, "coordZ": c, "class": k}
                   for c, k in zip(coords.astype(float), classes)]
    candidatos = pd.DataFrame(linhas)
    tabela = pd.DataFrame({"seriesuid": ["a", "b", "c"], "paciente": ["p1", "p2", "p3"],
                           "subset": [0, 0, 1], "particao": ["treino", "treino", "validacao"]})
    return candidatos, tabela


def pesos_treinados(pasta, candidatos, tabela, **extra):
    parametros = {"negativos_por_positivo": 3, "patch_size": 32, "batch_size": 4,
                  "dropout_rate": 0.3, "learning_rate": 1e-3, "weight_decay": 0.0, "epochs": 2, **extra}
    cnn.fixar_determinismo(42, 1)
    modelo, _, _ = cnn.treinar(candidatos, tabela, pasta, parametros, 42, "cpu", lambda linha: None)
    return cnn.hash_pesos(modelo)


def test_aumento_desligado_treina_igual_ao_caminho_sem_o_parametro(tmp_path):
    candidatos, tabela = exames_sinteticos(tmp_path)
    sem_parametro = pesos_treinados(tmp_path, candidatos, tabela)
    assert pesos_treinados(tmp_path, candidatos, tabela, aumento=False) == sem_parametro
    assert pesos_treinados(tmp_path, candidatos, tabela, aumento=True) != sem_parametro
