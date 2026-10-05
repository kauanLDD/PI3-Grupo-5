"""Compara configurações do LoG numa amostra fixa, com validação separada e teste reservado."""

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import time

import numpy as np
import pandas as pd
import SimpleITK as sitk

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config
from detection import blobs, calibracao, candidatos


def hash_arquivo(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def salvar_json(caminho, valor):
    temporario = caminho.with_suffix(".tmp")
    temporario.write_text(json.dumps(valor, indent=2, ensure_ascii=False), encoding="utf-8")
    temporario.replace(caminho)


def preparar(cfg, destino):
    plano = cfg["calibracao_log"]
    intermediario = cfg["caminhos"]["intermediario"]
    pacientes = pd.read_csv(intermediario / "pacientes.csv")
    divisao = calibracao.separar(pacientes, plano)
    anotacoes = pd.read_csv(cfg["caminhos"]["luna16_anotacoes"])
    partes = []
    for subset in plano["desenvolvimento"]:
        partes.append(calibracao.amostrar(
            divisao[divisao.subset == subset], anotacoes,
            plano["positivos_por_subset"], plano["negativos_por_subset"], cfg["seed"],
        ))
    partes.append(calibracao.amostrar(
        divisao[divisao.particao == "validacao"], anotacoes,
        plano["positivos_validacao"], plano["negativos_validacao"], cfg["seed"],
    ))
    amostra = pd.concat(partes).reset_index(drop=True)
    divisao["na_amostra"] = divisao.seriesuid.isin(amostra.seriesuid)
    assinatura = {
        "plano": plano, "seed": cfg["seed"], "avaliacao": cfg["avaliacao"],
        "pacientes_sha256": hash_arquivo(intermediario / "pacientes.csv"),
        "anotacoes_sha256": hash_arquivo(cfg["caminhos"]["luna16_anotacoes"]),
        "codigo": {p: hash_arquivo(config.RAIZ / p) for p in (
            "src/detection/blobs.py", "src/detection/candidatos.py", "src/detection/calibracao.py",
            "scripts/12_calibrar_detector.py",
        )},
        "versoes": {nome: importlib.metadata.version(nome) for nome in (
            "numpy", "pandas", "scipy", "scikit-image", "SimpleITK", "pyyaml",
        )},
        "volumes": {},
    }
    for uid in amostra.seriesuid:
        volume = cfg["caminhos"]["volumes"] / f"{uid}.mha"
        if not volume.is_file():
            raise FileNotFoundError(f"volume selecionado ausente: {uid}")
        assinatura["volumes"][uid] = hash_arquivo(volume)
    manifesto = destino / "protocolo.json"
    if manifesto.exists():
        anterior = json.loads(manifesto.read_text())
        if anterior["assinatura"] != assinatura:
            raise ValueError("protocolo ou entradas mudaram; use uma nova pasta de experimento")
    else:
        destino.mkdir(parents=True, exist_ok=True)
        salvar_json(manifesto, {
            "criado_em": datetime.now(timezone.utc).isoformat(), "assinatura": assinatura,
            "criterio": "Minimizar candidatos sem perder nenhum nódulo alcançado pela configuração inicial no desenvolvimento. Conferir uma vez na validação. Teste não utilizado.",
            "escopo": "Calibração exploratória em amostra estratificada, sem estimativa de FROC ou FP/exame.",
            "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        })
        divisao.to_csv(destino / "divisao.csv", index=False)
        amostra.to_csv(destino / "amostra.csv", index=False)
    anotacoes = anotacoes.reset_index(names="nodulo_id")
    return amostra, anotacoes


def processar(linha, nomes, cfg, anotacoes, destino):
    sitk.ProcessObject.SetGlobalDefaultNumberOfThreads(1)
    config.fixar_semente(cfg["seed"])
    uid = linha["seriesuid"]
    pendentes = [n for n in nomes if not (destino / f"{uid}_{n}.json").exists()]
    if not pendentes:
        return uid, "retomado"
    caminho = cfg["caminhos"]["volumes"] / f"{uid}.mha"
    imagem = sitk.ReadImage(str(caminho))
    if not np.allclose(imagem.GetSpacing(), [1, 1, 1]):
        raise ValueError(f"volume sem espaçamento de 1 mm: {uid}")
    volume = sitk.GetArrayFromImage(imagem)
    if volume.dtype != np.float32 or volume.min() < 0 or volume.max() > 1.000001:
        raise ValueError(f"volume fora do contrato normalizado float32: {uid}")
    referencias = anotacoes[anotacoes.seriesuid == uid]
    for nome in pendentes:
        inicio = time.monotonic()
        achados = blobs.detectar(volume, **cfg["calibracao_log"]["configuracoes"][nome])
        pontos = blobs.candidatos_do_exame(uid, imagem, achados)
        cobertura = candidatos.alcancados(referencias, pontos)
        registro = {
            **linha, "configuracao": nome, "candidatos": len(pontos),
            "alcancados": int(cobertura.sum()), "segundos": time.monotonic() - inicio,
            "erro": "", "nodulo_ids": referencias.nodulo_id.tolist(),
            "cobertura": cobertura.tolist(),
        }
        salvar_json(destino / f"{uid}_{nome}.json", registro)
        print(f"{linha['particao']} {uid[-8:]} {nome}: {len(pontos)} candidatos, "
              f"{int(cobertura.sum())}/{len(referencias)} nódulos, {registro['segundos']:.1f}s", flush=True)
    return uid, "processado"


def executar(amostra, nomes, cfg, anotacoes, destino):
    saidas = destino / "por_exame"
    saidas.mkdir(exist_ok=True)
    falhas = []
    with ProcessPoolExecutor(max_workers=cfg["calibracao_log"]["trabalhadores"]) as pool:
        tarefas = {pool.submit(processar, linha, nomes, cfg, anotacoes, saidas): linha
                   for linha in amostra.to_dict("records")}
        for futuro in as_completed(tarefas):
            linha = tarefas[futuro]
            try:
                futuro.result()
            except (OSError, RuntimeError, ValueError, MemoryError) as erro:
                falhas.append({"seriesuid": linha["seriesuid"], "erro": str(erro)})
                print(f"falha {linha['seriesuid']}: {erro}", flush=True)
    fase = amostra.particao.iloc[0]
    pd.DataFrame(falhas, columns=["seriesuid", "erro"]).to_csv(destino / f"falhas_{fase}.csv", index=False)
    print(f"{fase}: {len(amostra)} selecionados, {len(amostra)-len(falhas)} concluídos, {len(falhas)} falhas", flush=True)
    if falhas:
        raise RuntimeError("há falhas; a escolha de parâmetros foi bloqueada")


def ler_resultados(destino):
    registros, nodulos = [], []
    for caminho in sorted((destino / "por_exame").glob("*.json")):
        registro = json.loads(caminho.read_text())
        ids, acertos = registro.pop("nodulo_ids"), registro.pop("cobertura")
        registros.append(registro)
        nodulos.extend({"particao": registro["particao"], "configuracao": registro["configuracao"],
                        "nodulo_id": nid, "alcancado": acerto}
                       for nid, acerto in zip(ids, acertos))
    return pd.DataFrame(registros), pd.DataFrame(nodulos)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preparar", action="store_true")
    args = parser.parse_args()
    cfg = config.carregar()
    config.fixar_semente()
    destino = cfg["caminhos"]["intermediario"] / "calibracao_log"
    amostra, anotacoes = preparar(cfg, destino)
    print(amostra.groupby("particao").agg(exames=("seriesuid", "size"), nodulos=("nodulos", "sum")).to_string(), flush=True)
    if args.preparar:
        return
    executar(amostra[amostra.particao == "desenvolvimento"],
             list(cfg["calibracao_log"]["configuracoes"]), cfg, anotacoes, destino)
    resultados, cobertura = ler_resultados(destino)
    nome = calibracao.escolher(resultados[resultados.particao == "desenvolvimento"],
                               cobertura[cobertura.particao == "desenvolvimento"])
    selecao = {"configuracao": nome, "parametros": cfg["calibracao_log"]["configuracoes"][nome]}
    salvar_json(destino / "escolha_desenvolvimento.json", selecao)
    print(f"Escolha congelada antes da validação: {nome}", flush=True)
    executar(amostra[amostra.particao == "validacao"], list(dict.fromkeys(["inicial", nome])),
             cfg, anotacoes, destino)
    resultados, cobertura = ler_resultados(destino)
    resultados.to_csv(destino / "resultados_por_exame.csv", index=False)
    cobertura.to_csv(destino / "cobertura_por_nodulo.csv", index=False)
    resumo = calibracao.resumir(resultados, cfg["avaliacao"]["bootstrap_reamostras"],
                               cfg["avaliacao"]["intervalo_confianca"], cfg["seed"])
    resumo.to_csv(destino / "resumo.csv", index=False)
    validado = calibracao.escolher(resultados[resultados.particao == "validacao"],
                                   cobertura[cobertura.particao == "validacao"])
    selecao["preservou_acertos_e_reduziu_candidatos_na_validacao"] = nome != "inicial" and validado == nome
    selecao["status"] = "exploratorio; sem avaliação no teste; configuração de produção não alterada"
    salvar_json(destino / "conclusao.json", selecao)
    print(resumo.to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
