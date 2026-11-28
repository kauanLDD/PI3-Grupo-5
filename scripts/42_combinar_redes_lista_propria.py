"""Média da rede de 32 e da de 16 na nossa lista, com a supressão suave a 16 mm, só na validação.

A rede de 16 pontua a nossa lista agora; as notas da rede de 32 vêm do script 31. Não usa o teste.
Desenho em docs/20, seção "As duas redes na nossa lista".
"""

import importlib.util
import json
from pathlib import Path
import shutil
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
import SimpleITK as sitk
import torch

import config
from detection import candidatos as det
from experimentos import avaliacao_oficial, cnn, rastreamento

VERSOES = ("rede_32", "rede_16", "media")


def script(nome, arquivo):
    spec = importlib.util.spec_from_file_location(nome, Path(__file__).resolve().parent / arquivo)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def carregar_rede_16(cfg, pasta, device):
    pacote = torch.load(pasta / "modelo.pt", map_location="cpu", weights_only=True)
    for chave, arquivo in (("divisao_sha256", "divisao"), ("candidatos_sha256", "luna16_candidatos")):
        if pacote.get(chave) != rastreamento.sha256(cfg["caminhos"][arquivo]):
            raise ValueError(f"{arquivo} difere da entrada congelada no treinamento")
    parametros = pacote["parametros"]
    cnn.fixar_determinismo(pacote["seed"], parametros["threads"], device)
    modelo = cnn.CNN3D(parametros["dropout_rate"])
    modelo.load_state_dict(pacote["state_dict"])
    return modelo.to(device), parametros


def vizinhos_de_nodulo(marcas, nodulos, excluidas, distancia):
    """Acertos e falsos positivos entre as marcas, e quantos falsos positivos ficam perto de um nódulo."""
    rotulos = det.rotular(marcas, nodulos, excluidas)
    falsos = marcas[rotulos == det.FALSO_POSITIVO]
    perto = 0
    for uid, grupo in falsos.groupby("seriesuid"):
        centros = nodulos.loc[nodulos.seriesuid.eq(uid), det.COLUNAS].to_numpy(float)
        if len(centros):
            menor, _ = cKDTree(centros).query(grupo[det.COLUNAS].to_numpy(float))
            perto += int((menor <= distancia).sum())
    return {"marcas": len(marcas), "acertos": int((rotulos == det.ACERTO).sum()),
            "falsos_positivos": len(falsos), "falsos_perto_de_nodulo": perto,
            "nodulos_entre_as_marcas": int(det.alcancados(nodulos, marcas).sum())}


def main():
    cfg = config.carregar()
    config.fixar_semente(cfg["seed"])
    caminhos, fase, suave, avaliacao = (cfg["caminhos"], cfg["combinacao_redes_lista_propria"],
                                        cfg["supressao_suave"], cfg["avaliacao"])
    saida, completa = caminhos["combinacao_redes_lista_propria"], caminhos["combinacao_redes_lista_propria_completa"]
    if saida.exists() or completa.exists():
        raise ValueError(f"preserve a avaliação anterior e apague-a à mão: {saida} / {completa}")
    lista_propria = script("avaliar_lista_propria", "31_avaliar_lista_propria_cnn.py")
    comparar = script("comparar_froc", "27_comparar_froc.py")

    divisao = pd.read_csv(caminhos["divisao"])
    uids = sorted(divisao.loc[divisao.particao.eq("validacao"), "seriesuid"])
    notas = pd.read_csv(config.RAIZ / fase["notas_32"])
    if sorted(notas.seriesuid.unique()) != uids:
        raise ValueError("as notas da rede de 32 cobrem outros exames")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    pasta_16 = config.RAIZ / fase["rede_16"]
    modelo, parametros = carregar_rede_16(cfg, pasta_16, device)
    gravadas = pd.read_csv(pasta_16 / "probabilidades_validacao.csv")
    diferenca = lista_propria.conferir_recorte(modelo, uids, gravadas, caminhos["volumes"], parametros,
                                               cfg["lista_propria"], device)
    print(f"conferência do recorte de 16 na V2: maior diferença {diferenca:.2e}", flush=True)

    inicio = time.perf_counter()
    nota_16 = np.empty(len(notas))
    for i, (uid, grupo) in enumerate(notas.groupby("seriesuid", sort=True), 1):
        imagem = sitk.ReadImage(str(caminhos["volumes"] / f"{uid}.mha"))
        nota_16[grupo.index] = lista_propria.pontuar_exame(
            modelo, imagem, grupo[det.COLUNAS].to_numpy(float), parametros,
            cfg["lista_propria"]["recortes_por_vez"], device)
        if i % 10 == 0:
            print(f"{i}/{len(uids)} exames, {time.perf_counter() - inicio:.0f} s", flush=True)
    segundos = time.perf_counter() - inicio
    notas = notas.rename(columns={"probability": "rede_32"}).assign(rede_16=nota_16)
    notas["media"] = notas[["rede_32", "rede_16"]].mean(axis=1)
    print(f"exames lidos {len(uids)}, com erro 0, descartados 0; pontos pontuados {len(notas)}; "
          f"{segundos:.0f} s", flush=True)
    completa.mkdir(parents=True)
    notas.to_csv(completa / "probabilidades.csv", index=False)

    nodulos = pd.read_csv(caminhos["luna16_anotacoes"])
    nodulos = nodulos[nodulos.seriesuid.isin(uids)].reset_index(drop=True)
    excluidas = pd.read_csv(caminhos["luna16_anotacoes_excluidas"])
    excluidas = excluidas[excluidas.seriesuid.isin(uids)]
    dados, vizinhos = {}, []
    for versao in VERSOES:
        marcas = det.suprimir_suave(notas.assign(probability=notas[versao]), float(suave["raio_mm"]),
                                    "linear", suave["marcas_por_exame"], suave["sigma"])
        destino = completa / versao
        avaliacao_oficial.avaliar(marcas, uids, caminhos["luna16_anotacoes"], caminhos["luna16_anotacoes_excluidas"],
                                  destino, cfg["seed"], avaliacao["bootstrap_reamostras"],
                                  avaliacao["intervalo_confianca"])
        dados[versao] = comparar.carregar(destino)
        vizinhos.append({"versao": versao, **vizinhos_de_nodulo(marcas, nodulos, excluidas,
                                                                fase["distancia_vizinho_mm"])})

    linhas, pares = [], []
    for versao in VERSOES:
        modelos, par, _ = comparar.resumir((versao, "rede_32"), [dados[versao], dados["rede_32"]],
                                           avaliacao["intervalo_confianca"])
        m = modelos[versao]
        linhas.append({"versao": versao, "cpm": m["cpm"], "cpm_ic_inferior": m["cpm_ic"][0],
                       "cpm_ic_superior": m["cpm_ic"][1],
                       **{f"sens_{fp}": s for fp, s in m["sensibilidade"].items()},
                       **{f"sens_{fp}_ic_inferior": s for fp, s in m["ic_inferior"].items()},
                       **{f"sens_{fp}_ic_superior": s for fp, s in m["ic_superior"].items()}})
        if versao != "rede_32":
            pares.append({"versao": versao, "contra": "rede_32", "diferenca_cpm": par["diferenca_cpm"],
                          "ic_inferior": par["diferenca_ic"][0], "ic_superior": par["diferenca_ic"][1],
                          "fracao_reamostras_maior": par["fracao_reamostras_maior"]})
    tabela, pares, vizinhos = pd.DataFrame(linhas), pd.DataFrame(pares), pd.DataFrame(vizinhos)
    cpm_32 = float(tabela.loc[tabela.versao.eq("rede_32"), "cpm"].iloc[0])
    if abs(cpm_32 - fase["cpm_32_gravado"]) > 1e-9:
        raise ValueError(f"a rede de 32 com supressão deu {cpm_32}, e o gravado é {fase['cpm_32_gravado']}")

    saida.mkdir(parents=True)
    for versao in VERSOES:
        (saida / versao).mkdir()
        for arquivo in ("avaliacao.json", "pontos_operacao.csv", "cpm_bootstrap.csv", "seriesuids.csv"):
            shutil.copy2(completa / versao / arquivo, saida / versao / arquivo)
    tabela.to_csv(saida / "versoes.csv", index=False)
    pares.to_csv(saida / "diferencas_pareadas.csv", index=False)
    vizinhos.to_csv(saida / "vizinhos_de_nodulo.csv", index=False)
    (saida / "resumo.json").write_text(json.dumps({
        "teste_utilizado": False, "exames": len(uids), "nodulos": len(nodulos), "pontos": len(notas),
        "device": device, "segundos_pontuacao": round(segundos), "conferencia_recorte_16": diferenca,
        "cpm_32_reproduzido": cpm_32}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(tabela[["versao", "cpm", "cpm_ic_inferior", "cpm_ic_superior", "sens_1", "sens_4"]]
          .round(3).to_string(index=False))
    print(pares.round(3).to_string(index=False))
    print(vizinhos.to_string(index=False))


if __name__ == "__main__":
    main()
