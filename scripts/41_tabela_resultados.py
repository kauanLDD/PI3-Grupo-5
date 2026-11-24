"""Junta numa tabela única os resultados do avaliador oficial que já estão em disco (T31)."""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

import config

COLUNAS = ["cpm", "cpm_ic_inferior", "cpm_ic_superior", "sens_1", "sens_1_ic_inferior", "sens_1_ic_superior",
           "sens_4", "sens_4_ic_inferior", "sens_4_ic_superior"]


def ler_json(caminho):
    m = json.loads(caminho.read_text(encoding="utf-8"))["metricas"]
    saida = {"cpm": m["cpm"], "cpm_ic_inferior": m["cpm_ic_inferior"], "cpm_ic_superior": m["cpm_ic_superior"]}
    for fp in (1, 4):
        for sufixo in ("", "_ic_inferior", "_ic_superior"):
            saida[f"sens_{fp}{sufixo}"] = m[f"sensibilidade_{fp}fp{sufixo}"]
    return saida


def ler_csv(caminho, filtro):
    tabela = pd.read_csv(caminho)
    for coluna, valor in filtro.items():
        tabela = tabela[tabela[coluna].astype(str).eq(str(valor))]
    if len(tabela) != 1:
        raise ValueError(f"{caminho} com filtro {filtro} deu {len(tabela)} linhas, esperava 1")
    linha = tabela.iloc[0]
    # Algumas tabelas de resumo não gravaram o intervalo da sensibilidade; fica vazio, sem estimar.
    return {c: linha[c] if c in linha else None for c in COLUNAS}


def main():
    cfg = config.carregar()
    config.fixar_semente(cfg["seed"])
    linhas = []
    for item in cfg["tabela_resultados"]["linhas"]:
        caminho = config.RAIZ / item["arquivo"]
        valores = ler_json(caminho) if caminho.suffix == ".json" else ler_csv(caminho, item["filtro"])
        linhas.append({"modelo": item["modelo"], "lista": item["lista"], "conjunto": item["conjunto"],
                       **valores, "arquivo": item["arquivo"]})
    tabela = pd.DataFrame(linhas)
    destino = cfg["caminhos"]["tabela_resultados"]
    destino.mkdir(parents=True, exist_ok=True)
    tabela.to_csv(destino / "tabela.csv", index=False)
    print(f"{len(tabela)} linhas, {tabela.conjunto.eq('teste').sum()} do teste")
    print(tabela[["modelo", "lista", "conjunto", "cpm", "sens_4"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
