"""FROC calculada pelo grupo em notebooks/curvafroc_pesquisa.ipynb, para comparar com a oficial.

Mesma regra do notebook: cada candidato com escore >= limiar conta como acerto, se o rótulo
é 1, ou como falso positivo, se é 0. O denominador da sensibilidade é o número de candidatos
positivos, não o de nódulos anotados. Não há limite de marcas por exame, nem nódulo sem
candidato, nem marcação excluída. A diferença para o avaliador oficial vem dessas três regras.

O notebook percorre um limiar por vez; aqui as contagens saem de busca binária, com os mesmos
limiares, na mesma ordem, e o mesmo `argsort` final. O resultado é o mesmo, só mais rápido.
"""

import numpy as np

PONTOS = (0.125, 0.25, 0.5, 1, 2, 4, 8)


def compute_froc(y_true, y_scores, n_scans):
    y_true = np.asarray(y_true)
    y_scores = np.asarray(y_scores, dtype=float)
    n_true_nodules = int(y_true.sum())

    thresholds = np.unique(y_scores)
    thresholds = np.concatenate([thresholds, [thresholds.max() + 1e-6]])

    positivos = np.sort(y_scores[y_true == 1])
    negativos = np.sort(y_scores[y_true == 0])
    tp = len(positivos) - np.searchsorted(positivos, thresholds, side="left")
    fp = len(negativos) - np.searchsorted(negativos, thresholds, side="left")

    sens = tp / n_true_nodules if n_true_nodules > 0 else np.zeros(len(thresholds))
    fps_per_scan = fp / n_scans if n_scans > 0 else np.zeros(len(thresholds))

    order = np.argsort(fps_per_scan)
    return fps_per_scan[order], sens[order]


def compute_cpm(fps_per_scan, sensitivities, operating_points=PONTOS):
    sens_at_points = [float(np.interp(p, fps_per_scan, sensitivities)) for p in operating_points]
    return float(np.mean(sens_at_points)), dict(zip(operating_points, sens_at_points))


def bootstrap_froc_metrics(y_true, y_scores, scan_ids, n_bootstrap, seed):
    """Reamostra exames com reposição, como no notebook, e devolve CPM e as 7 sensibilidades."""
    rng = np.random.default_rng(seed)
    y_true = np.asarray(y_true)
    y_scores = np.asarray(y_scores, dtype=float)
    scan_ids = np.asarray(scan_ids)

    unique_scans = np.unique(scan_ids)
    n_scans = len(unique_scans)
    # O notebook chama np.where a cada exame sorteado; o índice é o mesmo, guardado de antemão.
    indices = {s: np.where(scan_ids == s)[0] for s in unique_scans}

    cpm_samples, sens_samples = [], []
    for _ in range(n_bootstrap):
        sampled_scans = rng.choice(unique_scans, size=n_scans, replace=True)
        idx = np.concatenate([indices[s] for s in sampled_scans])
        if len(idx) == 0 or y_true[idx].sum() == 0:
            continue
        fps_b, sens_b = compute_froc(y_true[idx], y_scores[idx], n_scans=n_scans)
        cpm_b, pontos_b = compute_cpm(fps_b, sens_b)
        cpm_samples.append(cpm_b)
        sens_samples.append(list(pontos_b.values()))

    return {"cpm": np.array(cpm_samples), "sensibilidades": np.array(sens_samples)}
