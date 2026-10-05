"""A rodada da geração de candidatos nos 888 exames, retomável.

São horas de execução, e uma queda no meio não pode custar o que já rodou. Cada exame grava o
próprio arquivo, e rodar de novo pula os que já têm. Isso só é seguro se todos os arquivos da
pasta vieram dos mesmos parâmetros, então a pasta guarda os parâmetros com que nasceu e recusa
continuar com outros.
"""

import json
import os
from pathlib import Path

import pandas as pd
import numpy as np

from detection.blobs import COLUNAS

ARQUIVO_PARAMETROS = "parametros.json"
ARQUIVO_REGISTRO = "registro.csv"
COLUNAS_REGISTRO = ["seriesuid", "status", "candidatos", "segundos", "erro"]

CONCLUIDO = "concluido"
SEM_CANDIDATO = "sem_candidato"
FALHA = "falha"
PENDENTE = "pendente"


def preparar_pasta(pasta: Path, parametros: dict) -> bool:
    """Cria a pasta da rodada ou confere que ela é da mesma configuração.

    Devolve True quando está retomando uma rodada anterior. Levanta ValueError quando a pasta
    foi gerada com outros parâmetros: misturar as duas daria uma lista em que cada exame foi
    buscado de um jeito, sem erro nenhum.
    """
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / ARQUIVO_PARAMETROS

    if not arquivo.exists():
        if any(p.name != ARQUIVO_REGISTRO for p in pasta.glob("*.csv")):
            raise ValueError("cache sem manifesto de parametros; origem precisa ser conferida")
        arquivo.write_text(json.dumps(parametros, indent=2, sort_keys=True), encoding="utf-8")
        return False

    anteriores = json.loads(arquivo.read_text(encoding="utf-8"))
    if anteriores != parametros:
        diferentes = sorted(set(anteriores) | set(parametros))
        diferentes = [f"{k}: {anteriores.get(k)} -> {parametros.get(k)}" for k in diferentes
                      if anteriores.get(k) != parametros.get(k)]
        raise ValueError(
            f"{pasta} foi gerada com outros parâmetros ({'; '.join(diferentes)}). "
            "Volte o config.yaml para os parâmetros da pasta ou apague a pasta para recomeçar."
        )
    return True


def caminho_do_exame(pasta: Path, seriesuid: str) -> Path:
    return pasta / f"{seriesuid}.csv"


def pendentes(pasta: Path, seriesuids) -> list:
    """Os exames que ainda não têm arquivo na pasta, na ordem recebida."""
    faltam = []
    for uid in seriesuids:
        caminho = caminho_do_exame(pasta, uid)
        if caminho.exists():
            ler_exame(caminho, uid)
        else:
            faltam.append(uid)
    return faltam


def ler_exame(caminho, seriesuid):
    dados = pd.read_csv(caminho)
    if list(dados.columns) != COLUNAS:
        raise ValueError("colunas invalidas no cache")
    if dados.isna().any().any() or not dados.seriesuid.eq(seriesuid).all():
        raise ValueError("cache com exame incorreto ou valores ausentes")
    if not np.isfinite(dados[COLUNAS[1:]].to_numpy(dtype=float)).all():
        raise ValueError("cache com valores infinitos")
    return dados


def gravar_exame(pasta: Path, seriesuid: str, candidatos: pd.DataFrame) -> None:
    """Grava num temporário e renomeia, para uma queda no meio não deixar exame pela metade.

    Arquivo pela metade seria contado como concluído na próxima rodada e nunca refeito.
    """
    destino = caminho_do_exame(pasta, seriesuid)
    temporario = destino.with_suffix(".csv.tmp")
    candidatos.to_csv(temporario, index=False)
    os.replace(temporario, destino)


def registrar(pasta: Path, seriesuid: str, status: str, candidatos=0, segundos=float("nan"),
              erro="") -> None:
    """Acrescenta uma linha ao registro da rodada, que sobrevive entre execuções."""
    arquivo = pasta / ARQUIVO_REGISTRO
    linha = pd.DataFrame([[seriesuid, status, candidatos, segundos, erro]],
                         columns=COLUNAS_REGISTRO)
    linha.to_csv(arquivo, mode="a", header=not arquivo.exists(), index=False)


def situacao(pasta: Path, seriesuids) -> pd.DataFrame:
    """Uma linha por exame pedido: concluído, sem candidato, falha ou pendente.

    O que manda é o arquivo do exame na pasta. O registro só traz o tempo e a mensagem de erro,
    e quando um exame aparece mais de uma vez nele vale a última tentativa.
    """
    arquivo = pasta / ARQUIVO_REGISTRO
    registro = (pd.read_csv(arquivo, keep_default_na=False, na_values=[""])
                if arquivo.exists() else pd.DataFrame(columns=COLUNAS_REGISTRO))
    ultima = registro.drop_duplicates("seriesuid", keep="last").set_index("seriesuid")

    linhas = []
    for uid in seriesuids:
        caminho = caminho_do_exame(pasta, uid)
        anterior = ultima.loc[uid] if uid in ultima.index else None
        if caminho.exists():
            n = len(ler_exame(caminho, uid))
            status = CONCLUIDO if n else SEM_CANDIDATO
            erro = ""
        else:
            n = 0
            status = FALHA if anterior is not None and anterior.status == FALHA else PENDENTE
            erro = anterior.erro if status == FALHA else ""
        segundos = anterior.segundos if anterior is not None else float("nan")
        linhas.append({"seriesuid": uid, "status": status, "candidatos": n,
                       "segundos": segundos, "erro": erro})

    return pd.DataFrame(linhas, columns=COLUNAS_REGISTRO)


def juntar(pasta: Path, seriesuids, colunas) -> pd.DataFrame:
    """A lista única, na ordem dos exames pedidos, com os que já têm arquivo."""
    partes = [ler_exame(caminho_do_exame(pasta, uid), uid) for uid in seriesuids
              if caminho_do_exame(pasta, uid).exists()]
    partes = [p for p in partes if not p.empty]
    if not partes:
        return pd.DataFrame(columns=colunas)
    return pd.concat(partes, ignore_index=True)[colunas]
