"""Casamento entre ponto candidato e nódulo anotado, pelo critério do desafio."""

import numpy as np
import pandas as pd

COLUNAS = ["coordX", "coordY", "coordZ"]


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

