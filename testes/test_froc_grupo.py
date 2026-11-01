"""A FROC vetorizada do grupo devolve o mesmo que o laço original do notebook."""

from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from experimentos import froc_grupo


def froc_do_notebook(y_true, y_scores, n_scans):
    # Cópia literal de compute_froc em notebooks/curvafroc_pesquisa.ipynb.
    n_true_nodules = int(y_true.sum())
    thresholds = np.unique(y_scores)
    thresholds = np.concatenate([thresholds, [thresholds.max() + 1e-6]])
    sensitivities = []
    fps_per_scan = []
    for t in thresholds:
        predicted_positive = y_scores >= t
        tp = int(np.sum(predicted_positive & (y_true == 1)))
        fp = int(np.sum(predicted_positive & (y_true == 0)))
        sensitivities.append(tp / n_true_nodules if n_true_nodules > 0 else 0.0)
        fps_per_scan.append(fp / n_scans if n_scans > 0 else 0.0)
    order = np.argsort(fps_per_scan)
    return np.array(fps_per_scan)[order], np.array(sensitivities)[order]


def test_mesma_curva_do_notebook():
    gerador = np.random.default_rng(0)
    y_true = gerador.random(3000) < 0.05
    # Escores arredondados para forçar empates, que é onde a ordem dos limiares importa.
    y_scores = np.round(gerador.random(3000), 2)
    esperado = froc_do_notebook(y_true, y_scores, 30)
    obtido = froc_grupo.compute_froc(y_true, y_scores, 30)
    np.testing.assert_array_equal(obtido[0], esperado[0])
    np.testing.assert_array_equal(obtido[1], esperado[1])
    assert froc_grupo.compute_cpm(*obtido)[0] == froc_grupo.compute_cpm(*esperado)[0]


def test_conta_candidato_e_nao_nodulo():
    # Dois candidatos positivos do mesmo nódulo valem dois acertos, e o denominador é 2.
    fps, sens = froc_grupo.compute_froc([1, 1, 0], [.9, .8, .1], n_scans=1)
    assert froc_grupo.compute_cpm(fps, sens)[1][1] == 1.0
