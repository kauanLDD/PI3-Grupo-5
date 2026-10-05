"""A FROC oficial conta nódulos perdidos e ignora as marcações excluídas."""

from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from experimentos import avaliacao_oficial


def test_froc_oficial_denominador_e_excluidos(tmp_path):
    colunas = ["seriesuid", "coordX", "coordY", "coordZ", "diameter_mm"]
    anotacoes = tmp_path / "annotations.csv"
    excluidas = tmp_path / "annotations_excluded.csv"
    # Um acerto e um nódulo sem qualquer candidato, no mesmo exame.
    pd.DataFrame([["a", 0, 0, 0, 6], ["a", 100, 0, 0, 6]], columns=colunas).to_csv(anotacoes, index=False)
    pd.DataFrame([["a", 20, 0, 0, 6]], columns=colunas).to_csv(excluidas, index=False)
    previsoes = pd.DataFrame([["a", 0, 0, 0, .9], ["a", 20, 0, 0, .95], ["a", 50, 0, 0, .1]],
                            columns=["seriesuid", "coordX", "coordY", "coordZ", "probability"])
    metricas = avaliacao_oficial.avaliar(previsoes, ["a"], anotacoes, excluidas,
                                        tmp_path / "avaliacao", 42, 20, .95)
    assert metricas["cpm"] == pytest.approx(.5)
    assert metricas["sensibilidade_4fp"] == pytest.approx(.5)
    analise = (tmp_path / "avaliacao/CADAnalysis.txt").read_text()
    assert "False negatives: 1" in analise
    assert "False positives: 1" in analise
    assert "Ignored candidates on excluded nodules: 1" in analise
    assert len(pd.read_csv(tmp_path / "avaliacao/froc_predicoes_bootstrapping.csv")) == 10000


def test_sem_nodulos_detectados_tem_sensibilidade_zero(tmp_path):
    colunas = ["seriesuid", "coordX", "coordY", "coordZ", "diameter_mm"]
    anotacoes = tmp_path / "annotations.csv"
    excluidas = tmp_path / "annotations_excluded.csv"
    pd.DataFrame([["a", 0, 0, 0, 6]], columns=colunas).to_csv(anotacoes, index=False)
    pd.DataFrame(columns=colunas).to_csv(excluidas, index=False)
    previsoes = pd.DataFrame([["a", 50, 0, 0, .9]],
                            columns=["seriesuid", "coordX", "coordY", "coordZ", "probability"])
    metricas = avaliacao_oficial.avaliar(previsoes, ["a"], anotacoes, excluidas,
                                        tmp_path / "avaliacao", 42, 20, .95)
    assert metricas["cpm"] == 0
    assert metricas["sensibilidade_4fp_ic_inferior"] == 0
    assert metricas["sensibilidade_4fp_ic_superior"] == 0
