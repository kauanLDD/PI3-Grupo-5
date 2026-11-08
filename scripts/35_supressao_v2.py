"""A supressão a 16 mm da decisão 0012 aplicada também à V2, na validação, para comparar as duas listas.

Lê as notas que a rede antiga deu à V2 com três sementes e as avaliações do script 34 para a nossa
lista. Não treina e não usa o teste.
"""

import importlib.util
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

import config
from detection import candidatos as det
from experimentos import avaliacao_oficial


def script(nome, arquivo):
    spec = importlib.util.spec_from_file_location(nome, Path(__file__).resolve().parent / arquivo)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def main():
    cfg = config.carregar()
    config.fixar_semente(cfg["seed"])
    caminhos, fase, avaliacao = cfg["caminhos"], cfg["supressao_v2"], cfg["avaliacao"]
    saida, completa = caminhos["supressao_v2"], caminhos["supressao_v2_completa"]
    if saida.exists() or completa.exists():
        raise ValueError(f"preserve a avaliação anterior e apague-a à mão: {saida} / {completa}")
    comparar = script("comparar_froc", "27_comparar_froc.py")
    conferir_exames = script("supressao_lista_propria", "34_supressao_lista_propria.py").conferir_exames
    raio = fase["raio_mm"]
    propria = caminhos["supressao_lista_propria_completa"] / f"raio_{raio}"
    confianca = avaliacao["intervalo_confianca"]

    linhas, pares = [], []

    def parear(semente, rotulos, dados):
        conferir_exames(*dados)
        modelos, par, _ = comparar.resumir(rotulos, dados, confianca)
        pares.append({"semente": semente, "lista": rotulos[0], "contra": rotulos[1],
                      "diferenca_cpm": par["diferenca_cpm"], "ic_inferior": par["diferenca_ic"][0],
                      "ic_superior": par["diferenca_ic"][1], "fracao_reamostras_maior": par["fracao_reamostras_maior"]})
        print(f"semente {semente}, {rotulos[0]} contra {rotulos[1]}: {par['diferenca_cpm']:+.3f} "
              f"({par['diferenca_ic'][0]:+.3f} a {par['diferenca_ic'][1]:+.3f})", flush=True)
        return modelos

    for semente, pasta in fase["modelos"].items():
        modelo = config.RAIZ / pasta
        inteira = comparar.carregar(modelo / "avaliacao_validacao")
        notas = pd.read_csv(modelo / "probabilidades_validacao.csv")
        if sorted(notas.seriesuid.unique()) != inteira["exames"]:
            raise ValueError(f"semente {semente}: notas da V2 cobrem outros exames")
        marcas = det.suprimir_vizinhos(notas, float(raio))
        destino = completa / str(semente)
        avaliacao_oficial.avaliar(marcas, inteira["exames"], caminhos["luna16_anotacoes"],
                                  caminhos["luna16_anotacoes_excluidas"], destino, cfg["seed"],
                                  avaliacao["bootstrap_reamostras"], confianca)
        suprimida = comparar.carregar(destino)
        modelos = parear(semente, ("v2_suprimida", "v2"), [suprimida, inteira])
        modelos |= parear(semente, ("propria_suprimida", "v2_suprimida"),
                          [comparar.carregar(propria / str(semente)), suprimida])
        for lista, marcas_lista in (("v2", len(notas)), ("v2_suprimida", len(marcas)), ("propria_suprimida", None)):
            medida = modelos[lista]
            linhas.append({"semente": semente, "lista": lista, "marcas": marcas_lista, "cpm": medida["cpm"],
                           "cpm_ic_inferior": medida["cpm_ic"][0], "cpm_ic_superior": medida["cpm_ic"][1],
                           **{f"sens_{fp}": s for fp, s in medida["sensibilidade"].items()}})
        print(f"semente {semente}: exames lidos {len(inteira['exames'])}, com erro 0, descartados 0; "
              f"marcas da V2 {len(notas)} antes e {len(marcas)} depois da supressão", flush=True)

    tabela, pares = pd.DataFrame(linhas), pd.DataFrame(pares)
    saida.mkdir(parents=True)
    tabela.to_csv(saida / "listas.csv", index=False)
    pares.to_csv(saida / "diferencas_pareadas.csv", index=False)
    medias = tabela.groupby("lista").cpm.agg(["mean", "std"])
    (saida / "resumo.json").write_text(json.dumps({
        "conjunto": "validacao", "teste_utilizado": False, "raio_mm": raio,
        "cpm_media_desvio": {l: {"media": float(m), "desvio_padrao_amostral": float(d)}
                             for l, (m, d) in medias.iterrows()}}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(tabela[["semente", "lista", "marcas", "cpm"]].round(3).to_string(index=False), flush=True)
    print(medias.round(3).to_string(), flush=True)


if __name__ == "__main__":
    main()
