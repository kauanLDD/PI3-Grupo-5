"""Extrai características dos candidatos de treino ou validação com retomada por exame."""

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import sys
import time
from pathlib import Path

import pandas as pd
import SimpleITK as sitk

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config
from detection import features, patches


COLUNAS_SAIDA = [
    "candidate_id", "seriesuid", "paciente", "subset", "particao",
    "coordX", "coordY", "coordZ", "classe_luna16", *features.COLUNAS,
]
COLUNAS_AUDITORIA = ["candidate_id", "seriesuid", "status", "motivo"]


def argumentos():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--amostra",
        action="store_true",
        help="processa somente a amostra técnica definida no config.yaml",
    )
    parser.add_argument("--particao", choices=["treino", "validacao"], default="treino")
    args = parser.parse_args()
    if args.amostra and args.particao != "treino":
        parser.error("--amostra so pode ser usada com treino")
    return args


def salvar_csv(tabela: pd.DataFrame, destino: Path, colunas):
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(f".tmp{destino.suffix}")
    tabela.reindex(columns=colunas).to_csv(temporario, index=False)
    temporario.replace(destino)


def carregar_candidatos(caminho: Path, divisao: pd.DataFrame, particao: str):
    if particao not in {"treino", "validacao"}:
        raise ValueError("particao permitida: treino ou validacao")
    if divisao[["seriesuid", "paciente", "subset", "particao"]].isna().any().any():
        raise ValueError("divisao contem dados ausentes")
    if (divisao.groupby("paciente").particao.nunique() > 1).any():
        raise ValueError("paciente presente em mais de uma particao")
    candidatos = pd.read_csv(caminho).reset_index(names="candidate_id")
    if candidatos.candidate_id.duplicated().any():
        raise ValueError("candidate_id repetido")
    if divisao.seriesuid.duplicated().any():
        raise ValueError("seriesuid repetido na divisao")

    colunas_divisao = ["seriesuid", "paciente", "subset", "particao"]
    candidatos = candidatos.merge(
        divisao[colunas_divisao], on="seriesuid", how="left", validate="many_to_one"
    )
    sem_divisao = candidatos.particao.isna()
    if sem_divisao.any():
        raise ValueError(f"{int(sem_divisao.sum())} candidatos sem particao")
    return candidatos[candidatos.particao == particao].copy(), len(candidatos)


def atualizar_hash_arquivo(resumo, caminho: Path):
    with open(caminho, "rb") as arquivo:
        while bloco := arquivo.read(1024 * 1024):
            resumo.update(bloco)


def chave_da_execucao(cfg, modo: str, particao: str):
    resumo = hashlib.sha256()
    for caminho in (Path(features.__file__), Path(patches.__file__), Path(__file__)):
        atualizar_hash_arquivo(resumo, caminho)
    for chave in ("luna16_candidatos", "divisao"):
        atualizar_hash_arquivo(resumo, cfg["caminhos"][chave])
    resumo.update(json.dumps({
        "modo": modo,
        "particao": particao,
        "patch": cfg["candidatos"]["patch"],
        "amostra": cfg["caracteristicas"]["amostra_treino"],
        "seed": cfg["seed"],
    }, sort_keys=True).encode())
    divisao = pd.read_csv(cfg["caminhos"]["divisao"])
    for uid in sorted(divisao.loc[divisao.particao == particao, "seriesuid"]):
        caminho = cfg["caminhos"]["volumes"] / f"{uid}.mha"
        estado = caminho.stat() if caminho.exists() else None
        resumo.update(json.dumps([
            str(caminho), estado.st_size if estado else None,
            estado.st_mtime_ns if estado else None,
        ]).encode())
    return resumo.hexdigest()[:12]


def cache_valido(destino: Path, destino_auditoria: Path, candidatos: pd.DataFrame):
    if not destino.exists() or not destino_auditoria.exists():
        return False
    try:
        extraidas = pd.read_csv(destino, usecols=["candidate_id"])
        auditoria = pd.read_csv(
            destino_auditoria, usecols=COLUNAS_AUDITORIA
        )
    except (OSError, ValueError, pd.errors.ParserError):
        return False

    if auditoria.status.isna().any() or not auditoria.status.isin(["produzido", "descartado"]).all():
        return False
    if auditoria.motivo.fillna("").str.startswith("falha_exame:").any():
        return False
    esperados = set(candidatos.candidate_id.astype(int))
    auditados = set(auditoria.candidate_id.astype(int))
    produzidos = int((auditoria.status == "produzido").sum())
    return (
        len(auditoria) == len(candidatos)
        and len(auditoria) == auditoria.candidate_id.nunique()
        and esperados == auditados
        and set(extraidas.candidate_id) == set(
            auditoria.loc[auditoria.status == "produzido", "candidate_id"]
        )
        and len(extraidas) == produzidos
        and extraidas.candidate_id.nunique() == len(extraidas)
    )


def auditoria_de_erro(candidatos: pd.DataFrame, motivo: str):
    return pd.DataFrame({
        "candidate_id": candidatos.candidate_id.astype(int),
        "seriesuid": candidatos.seriesuid,
        "status": "descartado",
        "motivo": motivo,
    })


def processar_exame(tarefa):
    seriesuid, candidatos, caminho_volume, destino, destino_auditoria, tamanho_patch = tarefa
    destino = Path(destino)
    destino_auditoria = Path(destino_auditoria)
    if cache_valido(destino, destino_auditoria, candidatos):
        auditoria = pd.read_csv(destino_auditoria, usecols=["status"])
        produzidos = int((auditoria.status == "produzido").sum())
        return seriesuid, produzidos, len(candidatos) - produzidos, None, True

    try:
        imagem = sitk.ReadImage(caminho_volume)
        extraidas, auditoria = features.extrair_da_imagem(
            imagem, candidatos, tamanho_patch
        )
        salvar_csv(extraidas, destino, COLUNAS_SAIDA)
        salvar_csv(auditoria, destino_auditoria, COLUNAS_AUDITORIA)
        produzidos = len(extraidas)
        return seriesuid, produzidos, len(candidatos) - produzidos, None, False
    except (OSError, RuntimeError, ValueError, MemoryError) as erro:
        motivo = f"falha_exame: {type(erro).__name__}: {erro}"
        auditoria = auditoria_de_erro(candidatos, motivo)
        salvar_csv(pd.DataFrame(columns=COLUNAS_SAIDA), destino, COLUNAS_SAIDA)
        salvar_csv(auditoria, destino_auditoria, COLUNAS_AUDITORIA)
        return seriesuid, 0, len(candidatos), motivo, False


def juntar_csvs(series, pasta: Path, destino: Path, colunas):
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(f".tmp{destino.suffix}")
    escreveu_cabecalho = False
    with open(temporario, "wb") as saida:
        for seriesuid in series:
            origem = pasta / f"{seriesuid}.csv"
            if not origem.exists():
                raise FileNotFoundError(f"cache ausente: {origem}")
            with open(origem, "rb") as entrada:
                if escreveu_cabecalho:
                    entrada.readline()
                else:
                    escreveu_cabecalho = True
                while bloco := entrada.read(1024 * 1024):
                    saida.write(bloco)
    if not escreveu_cabecalho:
        pd.DataFrame(columns=colunas).to_csv(temporario, index=False)
    temporario.replace(destino)


def validar_resultado(candidatos, destino, destino_auditoria):
    extraidas = pd.read_csv(destino, usecols=["candidate_id"])
    auditoria = pd.read_csv(
        destino_auditoria, usecols=COLUNAS_AUDITORIA
    )
    if len(auditoria) != len(candidatos):
        raise RuntimeError("auditoria final nao fecha com os candidatos selecionados")
    if auditoria.candidate_id.nunique() != len(auditoria):
        raise RuntimeError("candidate_id repetido na auditoria final")
    if set(auditoria.candidate_id) != set(candidatos.candidate_id):
        raise RuntimeError("candidate_id ausente ou adicional na auditoria final")
    if auditoria.status.isna().any() or not auditoria.status.isin(["produzido", "descartado"]).all():
        raise RuntimeError("status invalido na auditoria")
    if set(extraidas.candidate_id) != set(auditoria.loc[auditoria.status == "produzido", "candidate_id"]):
        raise RuntimeError("identificadores produzidos diferem da auditoria")
    produzidos = int((auditoria.status == "produzido").sum())
    if len(extraidas) != produzidos or extraidas.candidate_id.nunique() != len(extraidas):
        raise RuntimeError("caracteristicas finais nao fecham com a auditoria")
    return len(extraidas), len(auditoria) - produzidos


def main():
    args = argumentos()
    cfg = config.carregar()
    config.fixar_semente()
    divisao = pd.read_csv(cfg["caminhos"]["divisao"])
    candidatos, total_base = carregar_candidatos(
        cfg["caminhos"]["luna16_candidatos"], divisao, args.particao
    )

    modo = "amostra" if args.amostra else "completo"
    if args.amostra:
        plano = cfg["caracteristicas"]["amostra_treino"]
        candidatos = features.selecionar_amostra(
            candidatos,
            positivos=plano["positivos"],
            negativos=plano["negativos"],
            semente=cfg["seed"],
        )
        destino = cfg["caminhos"]["caracteristicas_treino_amostra"]
        destino_auditoria = cfg["caminhos"]["auditoria_caracteristicas_treino_amostra"]
    else:
        destino = cfg["caminhos"][f"caracteristicas_{args.particao}"]
        destino_auditoria = cfg["caminhos"][f"auditoria_caracteristicas_{args.particao}"]

    chave = chave_da_execucao(cfg, modo, args.particao)
    pasta_cache = cfg["caminhos"]["cache_caracteristicas"] / chave
    pasta_features = pasta_cache / "features"
    pasta_auditoria = pasta_cache / "auditoria"
    pasta_features.mkdir(parents=True, exist_ok=True)
    pasta_auditoria.mkdir(parents=True, exist_ok=True)

    tarefas = [
        (
            seriesuid,
            grupo,
            str(cfg["caminhos"]["volumes"] / f"{seriesuid}.mha"),
            str(pasta_features / f"{seriesuid}.csv"),
            str(pasta_auditoria / f"{seriesuid}.csv"),
            cfg["candidatos"]["patch"],
        )
        for seriesuid, grupo in candidatos.groupby("seriesuid", sort=True)
    ]

    falhas = []
    produzidos = 0
    descartados = 0
    retomados = 0
    inicio = time.time()
    trabalhadores = cfg["caracteristicas"]["trabalhadores"]
    with ProcessPoolExecutor(max_workers=trabalhadores) as executor:
        futuros = [executor.submit(processar_exame, tarefa) for tarefa in tarefas]
        for numero, futuro in enumerate(as_completed(futuros), start=1):
            seriesuid, feitos, rejeitados, erro, retomado = futuro.result()
            produzidos += feitos
            descartados += rejeitados
            retomados += int(retomado)
            if erro:
                falhas.append({"seriesuid": seriesuid, "erro": erro})
            if numero % 25 == 0 or numero == len(tarefas):
                print(f"{numero}/{len(tarefas)} exames em {time.time() - inicio:.0f}s")

    series = sorted(candidatos.seriesuid.unique())
    juntar_csvs(series, pasta_features, destino, COLUNAS_SAIDA)
    juntar_csvs(series, pasta_auditoria, destino_auditoria, COLUNAS_AUDITORIA)
    produzidos_finais, descartados_finais = validar_resultado(
        candidatos, destino, destino_auditoria
    )
    if (produzidos, descartados) != (produzidos_finais, descartados_finais):
        raise RuntimeError("contagem dos processos nao fecha com os arquivos finais")

    destino_falhas = (
        pasta_cache / "falhas.csv" if args.amostra
        else cfg["caminhos"][f"falhas_caracteristicas_{args.particao}"]
    )
    salvar_csv(
        pd.DataFrame(falhas), destino_falhas, ["seriesuid", "erro"]
    )

    print(f"candidatos na base: {total_base}")
    print(f"candidatos selecionados: {len(candidatos)}")
    print(f"exames selecionados: {len(tarefas)}")
    print(f"exames retomados do cache: {retomados}")
    print(f"exames com erro: {len(falhas)}")
    print(f"caracteristicas produzidas: {produzidos_finais}")
    print(f"candidatos descartados: {descartados_finais}")
    print(destino)
    print(destino_auditoria)
    print(destino_falhas)
    if falhas:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
