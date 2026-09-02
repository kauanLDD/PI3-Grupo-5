"""Mapa de exame para paciente, extraído uma vez do metadata do LIDC-IDRI.

O LUNA16 identifica o exame pelo seriesuid e não diz quem é o paciente, mas a seção 3.1 do
enunciado exige divisão por paciente. Este script grava a tabela e depois dela o LIDC-IDRI
deixa de ser necessário.
"""

import csv
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config

METADATA = Path("/media/kauan/HD Samuel/LIDC-IDRI/Imagens LIDC-IDRI/metadata/metadata.csv")

cfg = config.carregar()
config.fixar_semente()

inventario = cfg["caminhos"]["intermediario"] / "inventario_volumes.csv"
if not inventario.exists():
    sys.exit(f"rode antes o 02_inventario_volumes.py: {inventario} não existe")
if not METADATA.exists():
    sys.exit(f"metadata do LIDC-IDRI não encontrado: {METADATA}")

with open(METADATA, newline="", encoding="utf-8-sig") as f:
    de_serie = {l["SeriesInstanceUID"].strip(): l["PatientID"].strip() for l in csv.DictReader(f)}

inv = pd.read_csv(inventario)
inv["paciente"] = inv.seriesuid.map(de_serie)

sem = inv[inv.paciente.isna()]
print(f"{len(inv)} exames, {len(sem)} sem paciente correspondente")
for l in sem.itertuples():
    print(f"  {l.seriesuid}")

tabela = inv[["seriesuid", "paciente", "subset"]].sort_values("seriesuid")
saida = cfg["caminhos"]["intermediario"] / "pacientes.csv"
tabela.to_csv(saida, index=False)

espalhados = tabela.groupby("paciente").subset.nunique()
espalhados = espalhados[espalhados > 1]
print(f"{tabela.paciente.nunique()} pacientes distintos")
print(f"{len(espalhados)} em mais de uma dobra")
for p in espalhados.index:
    print(f"  {p}: subsets {sorted(tabela[tabela.paciente == p].subset)}")
print(saida)
