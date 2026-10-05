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
