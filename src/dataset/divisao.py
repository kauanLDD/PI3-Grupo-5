"""Cria a divisão fixa de exames sem separar séries do mesmo paciente."""

import pandas as pd


PARTICOES = ("treino", "validacao", "teste")


def criar(pacientes, plano):
    faltantes = {"seriesuid", "paciente", "subset"} - set(pacientes.columns)
    if faltantes:
        raise ValueError(f"colunas ausentes no mapa de pacientes: {sorted(faltantes)}")
    if pacientes.seriesuid.isna().any() or pacientes.seriesuid.duplicated().any():
        raise ValueError("cada exame precisa de um seriesuid único")
    if pacientes.paciente.isna().any():
        raise ValueError("todo exame precisa de um paciente")

    if set(plano) != set(PARTICOES):
        raise ValueError(f"o plano precisa conter somente: {', '.join(PARTICOES)}")

    de_subset = {}
    for particao in PARTICOES:
        subsets = plano[particao]
        if not subsets:
            raise ValueError(f"a partição {particao} está vazia")
        for subset in subsets:
            if subset in de_subset:
                raise ValueError(f"subset {subset} aparece em mais de uma partição")
            de_subset[subset] = particao

    tabela = pacientes[["seriesuid", "paciente", "subset"]].copy()
    tabela["particao"] = tabela.subset.map(de_subset)
    if tabela.particao.isna().any():
        sem_particao = sorted(tabela.loc[tabela.particao.isna(), "subset"].unique())
        raise ValueError(f"subsets sem partição: {sem_particao}")

    partes_por_paciente = tabela.groupby("paciente").particao.nunique()
    vazamento = sorted(partes_por_paciente[partes_por_paciente > 1].index)
    if vazamento:
        raise ValueError(f"paciente presente em mais de uma partição: {vazamento}")

    return tabela.sort_values("seriesuid").reset_index(drop=True)


def resumir(tabela):
    return (
        tabela.groupby("particao", sort=False)
        .agg(exames=("seriesuid", "size"), pacientes=("paciente", "nunique"))
        .reindex(PARTICOES)
    )
