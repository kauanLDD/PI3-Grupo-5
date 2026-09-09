"""Compara as duas listas de candidatos do desafio contra os 1.186 nódulos anotados.

Produz a tabela que sustenta a adoção do candidates_V2 em docs/criterios_inclusao_luna16.md.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config
from detection import candidatos as det

cfg = config.carregar()
config.fixar_semente()

inventario = pd.read_csv(cfg["caminhos"]["intermediario"] / "inventario_volumes.csv")
exames = set(inventario.seriesuid)
nodulos = pd.read_csv(cfg["caminhos"]["luna16_anotacoes"])
nodulos = nodulos[nodulos.seriesuid.isin(exames)]

print(f"{len(nodulos)} nódulos anotados em {nodulos.seriesuid.nunique()} exames, "
      f"de {len(exames)} no inventário\n")

linhas = []
for nome, caminho in [("candidates.csv", cfg["caminhos"]["luna16_candidatos_original"]),
                      ("candidates_V2.csv", cfg["caminhos"]["luna16_candidatos"])]:
    lista = pd.read_csv(caminho)
    lista = lista[lista.seriesuid.isin(exames)]
    alcancados = int(det.alcancados(nodulos, lista).sum())
    linhas.append({
        "lista": nome,
        "pontos": len(lista),
        "positivos": int((lista["class"] == 1).sum()),
        "por_exame": len(lista) / len(exames),
        "alcancados": alcancados,
        "nodulos": len(nodulos),
        "teto": alcancados / len(nodulos),
    })

tabela = pd.DataFrame(linhas)
print(f"{'lista':>18} {'pontos':>9} {'positivos':>10} {'por exame':>10} "
      f"{'alcançados':>11} {'teto':>7}")
print("-" * 70)
for linha in tabela.itertuples():
    print(f"{linha.lista:>18} {linha.pontos:9d} {linha.positivos:10d} {linha.por_exame:10.0f} "
          f"{linha.alcancados:6d} de {linha.nodulos} {linha.teto:6.1%}")

primeira, segunda = tabela.iloc[0], tabela.iloc[1]
print(f"\no V2 alcança {segunda.alcancados - primeira.alcancados} nódulos a mais, "
      f"com {segunda.pontos / primeira.pontos - 1:.0%} mais pontos")
print(f"{segunda.nodulos - segunda.alcancados} nódulos ficam sem candidato mesmo no V2")

saida = cfg["caminhos"]["intermediario"] / "comparacao_candidatos.csv"
tabela.to_csv(saida, index=False)
print(f"\n{saida}")
