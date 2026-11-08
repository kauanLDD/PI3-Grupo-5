"""Avalia a rede escolhida, congelada, na lista de candidatos que nós geramos (LoG), na validação.

A lista própria tem cerca de 16 mil candidatos por exame, perto de 20 vezes a V2, e os cubos dela
não estão em disco: são recortados na hora do volume pré-processado. Antes de pontuar a lista
própria, o recorte feito na hora é conferido contra as probabilidades da V2 já gravadas.

Duas versões, fixadas antes de rodar: a lista inteira e a lista com supressão de vizinhos.
"""

import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import time

import numpy as np
import pandas as pd
import SimpleITK as sitk
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config
from detection import candidatos as det
from detection import recorte
from experimentos import avaliacao_oficial, cnn, rastreamento

# O que sai da pasta completa para a versionada: tudo menos as marcas e a curva de cada uma.
ARQUIVOS_PEQUENOS = ("avaliacao.json", "pontos_operacao.csv", "CADAnalysis.txt", "cpm_bootstrap.csv",
                     "froc_predicoes_bootstrapping.csv", "seriesuids.csv")


def script_27():
    arquivo = Path(__file__).resolve().parent / "27_comparar_froc.py"
    spec = importlib.util.spec_from_file_location("comparar_froc", arquivo)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def pontuar_exame(modelo, imagem, pontos, parametros, por_vez, device):
    volume = sitk.GetArrayFromImage(imagem)
    lado = (parametros["patch_size"],) * 3
    probabilidades = []
    for inicio in range(0, len(pontos), por_vez):
        cubos = recorte.recortar(imagem, volume, pontos[inicio:inicio + por_vez], lado)
        probabilidades.extend(cnn.pontuar(modelo, cubos, parametros["batch_size"], device))
    return np.asarray(probabilidades)


def conferir_recorte(modelo, uids, gravadas, volumes, parametros, lista, device):
    """Maior diferença entre a probabilidade do cubo recortado na hora e a do cubo em disco, na V2."""
    maior = 0.0
    for uid in uids[:lista["exames_conferencia"]]:
        grupo = gravadas[gravadas.seriesuid == uid]
        imagem = sitk.ReadImage(str(volumes / f"{uid}.mha"))
        obtidas = pontuar_exame(modelo, imagem, grupo[det.COLUNAS].to_numpy(float), parametros,
                                lista["recortes_por_vez"], device)
        maior = max(maior, float(np.abs(obtidas - grupo.probability.to_numpy()).max()))
    if maior > lista["tolerancia_conferencia"]:
        raise ValueError(f"recorte na hora diverge dos cubos em disco: {maior:.2e}")
    return maior


def ler_lista_propria(caminho, uids):
    partes = [c[c.seriesuid.isin(uids)] for c in pd.read_csv(caminho, chunksize=2_000_000)]
    return pd.concat(partes, ignore_index=True)


def argumentos(cfg):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--modelo", default=cfg["lista_propria"]["modelo"], help="pasta da rede em modelos/")
    parser.add_argument("--saida", type=Path, default=cfg["caminhos"]["lista_propria_cnn"],
                        help="pasta nova para as saídas versionadas")
    parser.add_argument("--completa", type=Path, default=cfg["caminhos"]["lista_propria_cnn_completa"],
                        help="pasta nova, fora do git, para as marcas e as avaliações completas")
    return parser.parse_args()


def main():
    cfg = config.carregar()
    config.fixar_semente(cfg["seed"])
    caminhos, lista, avaliacao = cfg["caminhos"], cfg["lista_propria"], cfg["avaliacao"]
    args = argumentos(cfg)
    saida, completa = config.RAIZ / args.saida, config.RAIZ / args.completa
    if saida.exists() or completa.exists():
        raise ValueError(f"preserve a avaliação anterior e apague-a à mão: {saida} / {completa}")

    pasta_modelo = config.RAIZ / args.modelo
    pacote = torch.load(pasta_modelo / "modelo.pt", map_location="cpu", weights_only=True)
    for chave, arquivo in (("divisao_sha256", "divisao"), ("candidatos_sha256", "luna16_candidatos")):
        if pacote.get(chave) != rastreamento.sha256(caminhos[arquivo]):
            raise ValueError(f"{arquivo} difere da entrada congelada no treinamento")
    divisao = pd.read_csv(caminhos["divisao"])
    cnn.conferir_divisao(divisao)
    uids = sorted(divisao.loc[divisao.particao.eq(lista["particao"]), "seriesuid"])

    referencia = pasta_modelo / "avaliacao_validacao"
    protocolo_v2 = json.loads((referencia / "avaliacao.json").read_text(encoding="utf-8"))
    if (referencia / "seriesuids.csv").read_text(encoding="utf-8").split() != uids:
        raise ValueError("a avaliação da V2 usa outros exames")
    if (protocolo_v2["seed"], protocolo_v2["bootstrap"], protocolo_v2["confianca"]) != (
            cfg["seed"], avaliacao["bootstrap_reamostras"], avaliacao["intervalo_confianca"]):
        raise ValueError("a avaliação da V2 usa outro protocolo de bootstrap")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    parametros = pacote["parametros"]
    cnn.fixar_determinismo(pacote["seed"], parametros["threads"], device)
    modelo = cnn.CNN3D(parametros["dropout_rate"])
    modelo.load_state_dict(pacote["state_dict"])
    modelo.to(device)

    gravadas = pd.read_csv(pasta_modelo / "probabilidades_validacao.csv")
    diferenca = conferir_recorte(modelo, uids, gravadas, caminhos["volumes"], parametros, lista, device)
    print(f"conferência do recorte na V2, {lista['exames_conferencia']} exames: "
          f"maior diferença de probabilidade {diferenca:.2e}", flush=True)

    propria = ler_lista_propria(caminhos["candidatos_proprios"], set(uids))
    sem_candidato = sorted(set(uids) - set(propria.seriesuid))
    if sem_candidato:
        raise ValueError(f"{len(sem_candidato)} exames da validação sem candidato na lista própria")
    inicio = time.perf_counter()
    partes = []
    for i, (uid, grupo) in enumerate(propria.groupby("seriesuid", sort=True), 1):
        imagem = sitk.ReadImage(str(caminhos["volumes"] / f"{uid}.mha"))
        grupo = grupo.assign(probability=pontuar_exame(modelo, imagem, grupo[det.COLUNAS].to_numpy(float),
                                                       parametros, lista["recortes_por_vez"], device))
        partes.append(grupo)
        if i % 10 == 0:
            print(f"{i}/{len(uids)} exames, {time.perf_counter() - inicio:.0f} s", flush=True)
    previsoes = pd.concat(partes, ignore_index=True)
    segundos = time.perf_counter() - inicio
    print(f"exames lidos {len(uids)}, com erro 0, descartados 0; candidatos pontuados {len(previsoes)}; "
          f"{segundos:.0f} s", flush=True)
    completa.mkdir(parents=True)
    previsoes.to_csv(completa / "probabilidades.csv", index=False)

    nodulos = pd.read_csv(caminhos["luna16_anotacoes"])
    nodulos = nodulos[nodulos.seriesuid.isin(uids)].reset_index(drop=True)
    excluidas = pd.read_csv(caminhos["luna16_anotacoes_excluidas"])
    v2 = pd.read_csv(caminhos["luna16_candidatos"])
    versoes = {"sem_supressao": previsoes,
               "com_supressao": det.suprimir_vizinhos(previsoes, lista["raio_supressao_mm"])}
    listas = {"v2": v2[v2.seriesuid.isin(uids)], **versoes}
    rotulos_excluidas = {nome: pd.Series(det.rotular(marcas, nodulos, excluidas[excluidas.seriesuid.isin(uids)]))
                         .value_counts().to_dict() for nome, marcas in listas.items()}
    cobertura = {nome: det.cobertura(nodulos, det.alcancados(nodulos, marcas), avaliacao["bootstrap_reamostras"],
                                     avaliacao["intervalo_confianca"], cfg["seed"])
                 for nome, marcas in listas.items()}

    comparar = script_27()
    dados_v2 = comparar.carregar(referencia)
    resumo = {"modelo": args.modelo, "particao": lista["particao"], "exames": len(uids),
              "nodulos": len(nodulos), "device": device, "segundos_pontuacao": round(segundos),
              "conferencia_recorte": {"exames": lista["exames_conferencia"], "maior_diferenca": diferenca},
              "raio_supressao_mm": lista["raio_supressao_mm"],
              "candidatos": {nome: len(marcas) for nome, marcas in listas.items()},
              "candidatos_por_exame_mediana": {nome: float(marcas.groupby("seriesuid").size().median())
                                               for nome, marcas in listas.items()},
              "rotulos": {n: {k: int(v) for k, v in r.items()} for n, r in rotulos_excluidas.items()},
              "cobertura": cobertura, "versoes": {}}
    for nome, marcas in versoes.items():
        destino = completa / nome
        avaliacao_oficial.avaliar(marcas, uids, caminhos["luna16_anotacoes"], caminhos["luna16_anotacoes_excluidas"],
                                  destino, cfg["seed"], avaliacao["bootstrap_reamostras"],
                                  avaliacao["intervalo_confianca"])
        rotulos = ("Lista própria" if nome == "sem_supressao" else "Lista própria com supressão", "Lista V2")
        dados = [comparar.carregar(destino), dados_v2]
        modelos, par, tabela = comparar.resumir(rotulos, dados, avaliacao["intervalo_confianca"])
        versionada = saida / nome
        versionada.mkdir(parents=True)
        for arquivo in ARQUIVOS_PEQUENOS:
            shutil.copy2(destino / arquivo, versionada / arquivo)
        tabela.to_csv(versionada / "comparacao_com_v2.csv", index=False)
        comparar.desenhar(rotulos, dados, modelos,
                          f"Validação: {len(uids)} exames, {len(nodulos)} nódulos, avaliador oficial LUNA16",
                          versionada)
        resumo["versoes"][nome] = {"marcas": len(marcas), "modelos": modelos, "diferenca_pareada": par}
        print(tabela.round(3).to_string(index=False), flush=True)
        print(json.dumps(par, indent=2, ensure_ascii=False), flush=True)

    (saida / "resumo.json").write_text(json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"candidatos": resumo["candidatos"], "cobertura": cobertura}, indent=2), flush=True)


if __name__ == "__main__":
    main()
