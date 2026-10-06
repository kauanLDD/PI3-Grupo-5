"""Comparação entre duas listas de candidatos na mesma base, nódulo a nódulo (S4-T11).

As duas listas só são comparáveis se forem medidas sobre os mesmos exames e os mesmos nódulos.
Uma lista que perdeu exames, ou que traz exames de fora do inventário, mudaria o denominador da
média de candidatos e da cobertura sem erro nenhum. Por isso a conferência da entrada vem antes
de qualquer conta.

Nada aqui é FROC. A cobertura é o teto de sensibilidade da lista, sem escore e sem contagem de
falso positivo.
"""

import numpy as np
import pandas as pd

from detection import candidatos as det


def conferir_entrada(lista: pd.DataFrame, exames) -> dict:
    """Quantos pontos e exames da lista entram na comparação, e quantos ficam de fora.

    Levanta ValueError quando falta coluna ou quando há coordenada ausente ou infinita: ponto sem
    coordenada não alcança nódulo nenhum e baixaria a cobertura em silêncio.
    """
    faltam = [c for c in ["seriesuid", *det.COLUNAS] if c not in lista.columns]
    if faltam:
        raise ValueError(f"colunas ausentes na lista: {faltam}")
    coordenadas = lista[det.COLUNAS].to_numpy(dtype=float)
    if not np.isfinite(coordenadas).all():
        raise ValueError("lista com coordenada ausente ou infinita")

    exames = set(exames)
    dentro = lista.seriesuid.isin(exames)
    com_candidato = set(lista.seriesuid[dentro])
    return {
        "pontos_lidos": len(lista),
        "pontos_fora_do_inventario": int((~dentro).sum()),
        "exames": len(exames),
        "exames_com_candidato": len(com_candidato),
        "exames_sem_candidato": len(exames - com_candidato),
    }


def candidatos_por_exame(lista: pd.DataFrame, exames) -> pd.Series:
    """Contagem por exame, com zero para o exame sem candidato.

    O exame sem candidato entra no denominador, como entra na média de falso positivo da FROC.
    """
    exames = sorted(set(exames))
    return lista[lista.seriesuid.isin(exames)].groupby("seriesuid").size().reindex(
        exames, fill_value=0)


def resumir(nome: str, lista: pd.DataFrame, exames, nodulos: pd.DataFrame,
            alcancado: np.ndarray, reamostras: int, confianca: float, semente: int) -> dict:
    """Uma linha da tabela: quantidade de candidatos e cobertura, com o intervalo por exame."""
    contagem = candidatos_por_exame(lista, exames)
    medida = det.cobertura(nodulos, alcancado, reamostras, confianca, semente)
    return {
        "lista": nome,
        "exames": len(contagem),
        "pontos": int(contagem.sum()),
        "por_exame": float(contagem.mean()),
        "mediana_por_exame": float(contagem.median()),
        "minimo_por_exame": int(contagem.min()),
        "maximo_por_exame": int(contagem.max()),
        **medida,
    }


def cruzar(alcance_a: np.ndarray, alcance_b: np.ndarray) -> dict:
    """Quais nódulos cada lista alcança e a outra não.

    Duas listas com a mesma cobertura podem alcançar nódulos diferentes. O que uma alcança e a
    outra não é o que justificaria juntar as duas, e a união é o teto dessa junção.
    """
    a = np.asarray(alcance_a, dtype=bool)
    b = np.asarray(alcance_b, dtype=bool)
    if a.shape != b.shape:
        raise ValueError("os dois alcances precisam ser dos mesmos nódulos, na mesma ordem")
    return {
        "nodulos": int(a.size),
        "ambas": int((a & b).sum()),
        "so_a": int((a & ~b).sum()),
        "so_b": int((~a & b).sum()),
        "nenhuma": int((~a & ~b).sum()),
        "uniao": int((a | b).sum()),
    }
