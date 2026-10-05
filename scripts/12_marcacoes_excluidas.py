"""Mede o que as marcações excluídas do desafio tiram da contagem de falso positivo (S3-T5).

Lê o `annotations_excluded.csv` pela chave `luna16_anotacoes_excluidas` do config e rotula cada
candidato do `candidates_V2.csv` como acerto, ignorado ou falso positivo, pela regra do avaliador
oficial (`detection.candidatos.rotular`). Se a lista própria já existir, ela entra também.

O V2 traz a coluna `class`, então o script confere a regra contra o rótulo do próprio desafio:
candidato de classe 1 que sai como falso positivo ou ignorado indica critério de casamento
diferente do que o desafio usou para rotular a lista.
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
excluidos = pd.read_csv(cfg["caminhos"]["luna16_anotacoes_excluidas"])
excluidos = excluidos[excluidos.seriesuid.isin(exames)]

sem_medida = int((excluidos.diameter_mm < 0).sum())
print(f"{len(excluidos)} achados excluídos em {excluidos.seriesuid.nunique()} exames, "
      f"{sem_medida} sem diâmetro, que o avaliador conta como {det.DIAMETRO_SEM_MEDIDA_MM:g} mm")
print(f"{len(nodulos)} nódulos de referência em {len(exames)} exames\n")

listas = [("candidates_V2.csv", cfg["caminhos"]["luna16_candidatos"])]
if cfg["caminhos"]["candidatos_proprios"].exists():
    listas.append(("candidatos.csv (próprio)", cfg["caminhos"]["candidatos_proprios"]))

linhas = []
for nome, caminho in listas:
    lista = pd.read_csv(caminho)
    lista = lista[lista.seriesuid.isin(exames)].reset_index(drop=True)
    rotulos = pd.Series(det.rotular(lista, nodulos, excluidos))
    contagem = rotulos.value_counts()

    acertos = int(contagem.get(det.ACERTO, 0))
    ignorados = int(contagem.get(det.IGNORADO, 0))
    falsos = int(contagem.get(det.FALSO_POSITIVO, 0))
    linhas.append({
        "lista": nome,
        "pontos": len(lista),
        "acertos": acertos,
        "ignorados": ignorados,
        "falsos_positivos": falsos,
        # Sem a regra, todo ponto que não é acerto seria alarme falso.
        "fp_por_exame_sem_regra": (falsos + ignorados) / len(exames),
        "fp_por_exame_com_regra": falsos / len(exames),
    })

    if "class" in lista:
        positivos_perdidos = int(((lista["class"] == 1) & (rotulos == det.FALSO_POSITIVO)).sum())
        ignorados_positivos = int(((lista["class"] == 1) & (rotulos == det.IGNORADO)).sum())
        print(f"{nome}: dos {int((lista['class'] == 1).sum())} candidatos de classe 1, "
              f"{positivos_perdidos} saem como falso positivo e {ignorados_positivos} como "
              f"ignorados. Diferente de zero é critério de casamento diferente do desafio.")

tabela = pd.DataFrame(linhas)
print(f"\n{'lista':>24} {'pontos':>9} {'acertos':>8} {'ignorados':>10} {'FP':>9} "
      f"{'FP/exame sem':>13} {'com regra':>10}")
print("-" * 90)
for linha in tabela.itertuples():
    print(f"{linha.lista:>24} {linha.pontos:9d} {linha.acertos:8d} {linha.ignorados:10d} "
          f"{linha.falsos_positivos:9d} {linha.fp_por_exame_sem_regra:13.1f} "
          f"{linha.fp_por_exame_com_regra:10.1f}")
print(f"\nFP por exame divide por {len(exames)}, os exames sem nódulo inclusos")

saida = cfg["caminhos"]["intermediario"] / "marcacoes_excluidas.csv"
tabela.to_csv(saida, index=False)
print(saida)
