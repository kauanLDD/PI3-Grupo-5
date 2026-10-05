"""Protege a separação por paciente e a identidade dos escores do baseline."""

from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from detection.features import COLUNAS
from experimentos import floresta


def dados(particao="treino", inicio=0):
    n = 40
    rng = np.random.default_rng(42)
    tabela = pd.DataFrame(rng.normal(size=(n, len(COLUNAS))), columns=COLUNAS)
    tabela["candidate_id"] = np.arange(inicio, inicio + n)
    tabela["paciente"] = [f"{particao}-{i // 5}" for i in range(n)]
    tabela["seriesuid"] = tabela.paciente
    tabela["particao"] = particao
    tabela["classe_luna16"] = (tabela.media > 0).astype(int)
    for eixo in ("coordX", "coordY", "coordZ"):
        tabela[eixo] = np.arange(n)
    return tabela


def modelo(treino):
    return floresta.treinar(treino, {"n_estimators": 5, "max_depth": 3,
                                   "class_weight": "balanced", "n_jobs": 1}, 42)


def test_treino_serializacao_e_previsoes_preservam_identidade(tmp_path):
    treino = dados()
    validacao = dados("validacao", 100).iloc[::-1]
    rf = modelo(treino)
    saida = floresta.prever_validacao(rf, validacao, treino)
    assert list(rf.feature_names_in_) == list(COLUNAS)
    assert saida.candidate_id.tolist() == validacao.candidate_id.tolist()
    assert saida.probability.between(0, 1).all()
    assert saida.probability.nunique() > 1
    destino = tmp_path / "modelo.joblib"
    joblib.dump(rf, destino)
    pd.testing.assert_frame_equal(
        saida, floresta.prever_validacao(joblib.load(destino), validacao, treino)
    )


@pytest.mark.parametrize("particao", ["validacao", "teste"])
def test_recusa_ajustar_modelo_fora_do_treino(particao):
    with pytest.raises(ValueError, match="somente a particao treino"):
        modelo(dados(particao))


@pytest.mark.parametrize("coluna", ["paciente", "seriesuid", "candidate_id"])
def test_recusa_vazamento(coluna):
    treino = dados()
    validacao = dados("validacao", 100)
    validacao.loc[0, coluna] = treino.loc[0, coluna]
    with pytest.raises(ValueError, match="compartilhado"):
        floresta.prever_validacao(modelo(treino), validacao, treino)


def test_recusa_valores_invalidos_e_classe_unica():
    treino = dados()
    treino.loc[0, "media"] = np.inf
    with pytest.raises(ValueError, match="infinitos"):
        modelo(treino)
    treino = dados()
    treino["classe_luna16"] = 0
    with pytest.raises(ValueError, match="duas classes"):
        modelo(treino)


def test_previsao_independe_dos_rotulos_de_validacao():
    treino = dados()
    validacao = dados("validacao", 100)
    rf = modelo(treino)
    antes = floresta.prever_validacao(rf, validacao, treino)
    validacao["classe_luna16"] = 1 - validacao.classe_luna16
    pd.testing.assert_frame_equal(antes, floresta.prever_validacao(rf, validacao, treino))
