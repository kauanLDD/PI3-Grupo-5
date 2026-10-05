"""Casamento entre ponto candidato e nódulo anotado, pelo critério do desafio."""

import numpy as np
import pandas as pd

COLUNAS = ["coordX", "coordY", "coordZ"]

ACERTO = "acerto"
IGNORADO = "ignorado"
FALSO_POSITIVO = "falso_positivo"

# O annotations_excluded.csv traz diameter_mm = -1 em 30.513 dos 35.192 achados, os que não são
# nódulo. O avaliador oficial troca esse -1 por 10 mm, então o raio vale 5 mm.
DIAMETRO_SEM_MEDIDA_MM = 10.0


def alcancados(nodulos: pd.DataFrame, candidatos: pd.DataFrame) -> np.ndarray:
    """Quais nódulos têm ao menos um candidato dentro do raio deles.

    O critério é o da página de avaliação do LUNA16: acerto é candidato a menos de R do centro,
    com R igual ao diâmetro dividido por dois. Ver docs/decisoes/0002.
    """
    por_exame = {uid: g[COLUNAS].to_numpy(float) for uid, g in candidatos.groupby("seriesuid")}
    alcancado = np.zeros(len(nodulos), dtype=bool)

    for i, nodulo in enumerate(nodulos.itertuples()):
        pontos = por_exame.get(nodulo.seriesuid)
        if pontos is None:
            continue
        centro = np.array([nodulo.coordX, nodulo.coordY, nodulo.coordZ], float)
        raio = nodulo.diameter_mm / 2
        alcancado[i] = bool((((pontos - centro) ** 2).sum(axis=1) <= raio ** 2).any())

    return alcancado


def cobertura(nodulos: pd.DataFrame, alcancado: np.ndarray, reamostras: int,
              confianca: float = 0.95, semente: int = 0) -> dict:
    """Fração de nódulos alcançados, com intervalo de confiança por bootstrap de exame.

    A reamostra é por exame e não por nódulo: os nódulos de um mesmo exame são buscados pela
    mesma rodada no mesmo volume, então não são independentes, e reamostrar nódulo solto
    estreita o intervalo sem motivo. Isto é teto de sensibilidade da lista, não ponto de FROC:
    não há escore nem contagem de falso positivo aqui.
    """
    alcancado = np.asarray(alcancado, dtype=bool)
    if len(nodulos) == 0:
        return {"alcancados": 0, "nodulos": 0, "cobertura": float("nan"),
                "ic_inferior": float("nan"), "ic_superior": float("nan")}

    por_exame = (pd.DataFrame({"seriesuid": nodulos["seriesuid"].to_numpy(), "a": alcancado})
                 .groupby("seriesuid")["a"].agg(["sum", "count"]))
    soma, total = por_exame["sum"].to_numpy(), por_exame["count"].to_numpy()

    gerador = np.random.default_rng(semente)
    sorteio = gerador.integers(0, len(por_exame), size=(reamostras, len(por_exame)))
    fracoes = soma[sorteio].sum(axis=1) / total[sorteio].sum(axis=1)
    cauda = (1 - confianca) / 2

    return {
        "alcancados": int(alcancado.sum()),
        "nodulos": len(nodulos),
        "cobertura": float(alcancado.mean()),
        "ic_inferior": float(np.quantile(fracoes, cauda)),
        "ic_superior": float(np.quantile(fracoes, 1 - cauda)),
    }


def _dentro(pontos: np.ndarray, achados: pd.DataFrame) -> np.ndarray:
    """Para cada ponto, se ele cai a menos de um raio do centro de algum dos achados."""
    if achados.empty or len(pontos) == 0:
        return np.zeros(len(pontos), dtype=bool)
    centros = achados[COLUNAS].to_numpy(float)
    diametros = achados["diameter_mm"].to_numpy(float)
    diametros = np.where(diametros < 0, DIAMETRO_SEM_MEDIDA_MM, diametros)
    distancia2 = ((pontos[:, None, :] - centros[None, :, :]) ** 2).sum(axis=2)
    # Estritamente menor, como no avaliador oficial (`dist < radiusSquared`).
    return (distancia2 < (diametros / 2) ** 2).any(axis=1)


def rotular(candidatos: pd.DataFrame, nodulos: pd.DataFrame,
            excluidos: pd.DataFrame) -> np.ndarray:
    """Acerto, ignorado ou falso positivo, para cada candidato, pela regra do avaliador oficial.

    Reproduz `noduleCADEvaluationLUNA16.py`: o candidato que cai em cima de um nódulo de
    `annotations.csv` é acerto; senão, se cai em cima de um achado de `annotations_excluded.csv`,
    sai da conta, sem ser acerto nem falso positivo; o resto é falso positivo. O nódulo vem antes
    do achado excluído, então candidato em cima dos dois é acerto.
    """
    rotulos = np.full(len(candidatos), FALSO_POSITIVO, dtype=object)
    nodulos_por_exame = dict(tuple(nodulos.groupby("seriesuid")))
    excluidos_por_exame = dict(tuple(excluidos.groupby("seriesuid")))
    vazio = nodulos.iloc[:0]

    todos = candidatos[COLUNAS].to_numpy(float)
    for uid, indices in candidatos.groupby("seriesuid").indices.items():
        pontos = todos[indices]
        acerto = _dentro(pontos, nodulos_por_exame.get(uid, vazio))
        ignorado = ~acerto & _dentro(pontos, excluidos_por_exame.get(uid, vazio))
        rotulos[indices[acerto]] = ACERTO
        rotulos[indices[ignorado]] = IGNORADO

    return rotulos
