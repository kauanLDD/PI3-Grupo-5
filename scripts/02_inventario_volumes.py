"""Inventário dos volumes do LUNA16: uma linha por .mhd dos subsets baixados."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "codigo"))
from pi3 import config
from pi3.dados import volumes

cfg = config.carregar()
config.fixar_semente()

luna = cfg["caminhos"]["luna16"]
saida = cfg["caminhos"]["intermediario"] / "inventario_volumes.csv"


def coletar():
    linhas, erros, ausentes = [], [], []
    for subset in cfg["selecao"]["subsets"]:
        pasta = volumes.pasta_do_subset(luna, subset)
        if not pasta.is_dir():
            ausentes.append(f"subset{subset} não encontrado em {pasta}")
            continue
        lidas, falhas = volumes.inventariar(pasta, subset)
        linhas += lidas
        erros += falhas
    return linhas, erros, ausentes


def relatar(df, erros, ausentes):
    por_subset = " ".join(f"{n}:{q}" for n, q in df.subset.value_counts().sort_index().items())
    print(f"{len(df)} volumes, {len(erros)} com erro  (subset {por_subset})")
    for aviso in erros + ausentes:
        print(f"  {aviso}")

    # Arredonda o float32 do .mhd antes de contar.
    espacamento_z = df.espacamento_z.round(4)
    contagem = "  ".join(f"{v:g}:{q}" for v, q in espacamento_z.value_counts().sort_index().items())
    # 2,5 mm é o critério de exclusão do desafio.
    print(f"espaçamento em z, mm  {contagem}  (acima de 2,5: {int((espacamento_z > 2.5).sum())})")

    matriz = ", ".join(sorted({f"{x} por {y}" for x, y in zip(df.dim_x, df.dim_y)}))
    print(f"matriz {matriz}, no plano de {df.espacamento_x.min():.4f} a {df.espacamento_x.max():.4f} mm")
    print(f"fatias de {df.dim_z.min()} a {df.dim_z.max()}, mediana {df.dim_z.median():.0f}")

    fora = df[~df.matriz_identidade]
    print(f"direção diferente de identidade: {len(fora)}")
    for l in fora.itertuples():
        print(f"  {l.seriesuid}  {l.direcao}  {l.orientacao}")


linhas, erros, ausentes = coletar()
if not linhas:
    sys.exit(f"Nenhum volume lido. Confira caminhos.luna16 em configuracao/config.yaml: {luna}")

df = pd.DataFrame(linhas)
saida.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(saida, index=False)

relatar(df, erros, ausentes)
print(saida)
