"""Terceiro uso do teste (decisão 0013): a rede congelada com a supressão suave a 16 mm, nas duas listas.

Pontua a nossa lista nos exames de teste com a rede da decisão 0008, aplica a supressão escolhida na
validação às duas listas e avalia uma vez com o avaliador oficial. Não escolhe nada.
"""

import importlib.util
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
import SimpleITK as sitk
import torch

import config
from detection import candidatos as det
from experimentos import avaliacao_oficial, cnn, rastreamento


def script(nome, arquivo):
    spec = importlib.util.spec_from_file_location(nome, Path(__file__).resolve().parent / arquivo)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def main():
    cfg = config.carregar()
    config.fixar_semente(cfg["seed"])
    caminhos, fase, avaliacao = cfg["caminhos"], cfg["teste_supressao"], cfg["avaliacao"]
    suave, lista = cfg["supressao_suave"], cfg["lista_propria"]
    saida, completa = caminhos["teste_supressao"], caminhos["teste_supressao_completa"]
    if saida.exists() or completa.exists():
        raise ValueError(f"o teste já foi usado para isto; preserve a avaliação anterior: {saida} / {completa}")
    comparar = script("comparar_froc", "27_comparar_froc.py")
    conferir_exames = script("supressao_lista_propria", "34_supressao_lista_propria.py").conferir_exames
    listas = script("avaliar_lista_propria", "31_avaliar_lista_propria_cnn.py")

    pasta_modelo = config.RAIZ / fase["modelo"]
    pacote = torch.load(pasta_modelo / "modelo.pt", map_location="cpu", weights_only=True)
    for chave, arquivo in (("divisao_sha256", "divisao"), ("candidatos_sha256", "luna16_candidatos")):
        if pacote.get(chave) != rastreamento.sha256(caminhos[arquivo]):
            raise ValueError(f"{arquivo} difere da entrada congelada no treinamento")
    divisao = pd.read_csv(caminhos["divisao"])
    cnn.conferir_divisao(divisao)
    uids = sorted(divisao.loc[divisao.particao.eq("teste"), "seriesuid"])
    pasta_v2 = config.RAIZ / fase["avaliacao_v2"]
    v2 = comparar.carregar(pasta_v2)
    if v2["exames"] != uids:
        raise ValueError("a avaliação da V2 no teste usa outros exames")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    parametros = pacote["parametros"]
    cnn.fixar_determinismo(pacote["seed"], parametros["threads"], device)
    modelo = cnn.CNN3D(parametros["dropout_rate"])
    modelo.load_state_dict(pacote["state_dict"])
    modelo.to(device)

    # As notas da V2 no teste saíram da CPU (script 20). Na GPU a nota muda até 1,5e-03 (medido em
    # 08/11/2026), então o recorte é conferido no mesmo aparelho em que elas foram gravadas.
    conferencia = cnn.CNN3D(parametros["dropout_rate"])
    conferencia.load_state_dict(pacote["state_dict"])
    diferenca = listas.conferir_recorte(conferencia, uids, v2["predicoes"], caminhos["volumes"], parametros, lista,
                                        fase["dispositivo_conferencia"])
    print(f"conferência do recorte na V2 do teste, {lista['exames_conferencia']} exames, "
          f"{fase['dispositivo_conferencia']}: maior diferença de probabilidade {diferenca:.2e}", flush=True)

    propria = listas.ler_lista_propria(caminhos["candidatos_proprios"], set(uids))
    sem_candidato = sorted(set(uids) - set(propria.seriesuid))
    if sem_candidato:
        raise ValueError(f"{len(sem_candidato)} exames de teste sem candidato na nossa lista")
    inicio = time.perf_counter()
    partes = []
    for uid, grupo in propria.groupby("seriesuid", sort=True):
        imagem = sitk.ReadImage(str(caminhos["volumes"] / f"{uid}.mha"))
        notas = listas.pontuar_exame(modelo, imagem, grupo[det.COLUNAS].to_numpy(float), parametros,
                                     lista["recortes_por_vez"], device)
        partes.append(grupo.assign(probability=notas))
    notas = pd.concat(partes, ignore_index=True)
    segundos = time.perf_counter() - inicio
    print(f"exames lidos {len(uids)}, com erro 0, descartados 0; pontos pontuados {len(notas)}; {segundos:.0f} s",
          flush=True)
    completa.mkdir(parents=True)
    notas.to_csv(completa / "probabilidades.csv", index=False)

    def suavizar(marcas):
        return det.suprimir_suave(marcas, float(suave["raio_mm"]), fase["forma"], suave["marcas_por_exame"],
                                  suave["sigma"])

    avaliacoes = {"v2": v2}
    for nome, marcas in (("propria", notas), ("propria_suave", suavizar(notas)),
                         ("v2_suave", suavizar(v2["predicoes"]))):
        destino = completa / nome
        avaliacao_oficial.avaliar(marcas, uids, caminhos["luna16_anotacoes"], caminhos["luna16_anotacoes_excluidas"],
                                  destino, cfg["seed"], avaliacao["bootstrap_reamostras"],
                                  avaliacao["intervalo_confianca"])
        avaliacoes[nome] = comparar.carregar(destino)
    for dados in avaliacoes.values():
        conferir_exames(dados, v2)

    confianca = avaliacao["intervalo_confianca"]
    linhas, pares = [], []
    for nome, dados in avaliacoes.items():
        medida = comparar.resumir((nome, "-"), [dados, dados], confianca)[0][nome]
        linhas.append({"lista": nome, "cpm": medida["cpm"], "cpm_ic_inferior": medida["cpm_ic"][0],
                       "cpm_ic_superior": medida["cpm_ic"][1],
                       **{f"sens_{fp}": s for fp, s in medida["sensibilidade"].items()},
                       **{f"sens_{fp}_ic_inferior": s for fp, s in medida["ic_inferior"].items()},
                       **{f"sens_{fp}_ic_superior": s for fp, s in medida["ic_superior"].items()}})
    for a, b in (("propria_suave", "propria"), ("v2_suave", "v2"), ("propria_suave", "v2_suave"), ("propria", "v2")):
        par = comparar.resumir((a, b), [avaliacoes[a], avaliacoes[b]], confianca)[1]
        pares.append({"lista": a, "contra": b, "diferenca_cpm": par["diferenca_cpm"],
                      "ic_inferior": par["diferenca_ic"][0], "ic_superior": par["diferenca_ic"][1],
                      "fracao_reamostras_maior": par["fracao_reamostras_maior"]})
    tabela, pares = pd.DataFrame(linhas), pd.DataFrame(pares)
    saida.mkdir(parents=True)
    tabela.to_csv(saida / "listas.csv", index=False)
    pares.to_csv(saida / "diferencas_pareadas.csv", index=False)
    (saida / "resumo.json").write_text(json.dumps({
        "conjunto": "teste", "teste_utilizado": True, "decisao": "0013", "exames": len(uids),
        "modelo": fase["modelo"], "forma": fase["forma"], "raio_mm": suave["raio_mm"],
        "conferencia_recorte": diferenca, "pontos_lista_propria": len(notas), "segundos_pontuacao": round(segundos)},
        indent=2, ensure_ascii=False), encoding="utf-8")
    for nome in ("propria", "propria_suave", "v2_suave"):
        rotulos = (nome, "v2")
        modelos, _, _ = comparar.resumir(rotulos, [avaliacoes[nome], v2], confianca)
        (saida / nome).mkdir()
        comparar.desenhar(rotulos, [avaliacoes[nome], v2], modelos,
                          f"Teste: {len(uids)} exames, avaliador oficial LUNA16", saida / nome)
    print(tabela[["lista", "cpm", "cpm_ic_inferior", "cpm_ic_superior", "sens_1", "sens_4"]].round(3).to_string(index=False),
          flush=True)
    print(pares.round(3).to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
