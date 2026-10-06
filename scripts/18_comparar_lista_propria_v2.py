"""Compara a lista própria do blob_log com o candidates_V2 na mesma base (S4-T11).

Produz a tabela que sustenta docs/decisoes/0007: cobertura, candidatos por exame, tempo de
geração e espaço em disco das duas listas, medidas sobre os mesmos exames do inventário e os
mesmos nódulos do annotations.csv, pelo critério de acerto de src/detection/candidatos.py.

Antes de contar, confere que as duas entradas batem: os mesmos exames, os mesmos nódulos, e
nenhum exame da lista própria em falha ou pendente. Também grava o alcance nódulo a nódulo, para
ver quais nódulos uma lista alcança e a outra não.

A cobertura é teto de sensibilidade da lista, não ponto da curva FROC.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config
from detection import candidatos as det
from detection import comparacao

cfg = config.carregar()
config.fixar_semente()

caminhos = cfg["caminhos"]
reamostras = cfg["avaliacao"]["bootstrap_reamostras"]
confianca = cfg["avaliacao"]["intervalo_confianca"]
semente = cfg["seed"]

inventario = pd.read_csv(caminhos["intermediario"] / "inventario_volumes.csv")
exames = set(inventario.seriesuid)
nodulos = pd.read_csv(caminhos["luna16_anotacoes"])
nodulos = nodulos[nodulos.seriesuid.isin(exames)].reset_index(drop=True)
print(f"{len(nodulos)} nódulos anotados em {nodulos.seriesuid.nunique()} exames, "
      f"de {len(exames)} no inventário\n")

colunas = ["seriesuid", *det.COLUNAS]
listas = {
    "candidatos.csv (próprio)": caminhos["candidatos_proprios"],
    "candidates_V2.csv": caminhos["luna16_candidatos"],
}
for nome, caminho in listas.items():
    if not caminho.exists():
        sys.exit(f"{caminho} não existe. A comparação precisa das duas listas: {nome}")

# A lista própria só é comparável se todos os exames rodaram. Exame em falha ou pendente
# tiraria candidatos da conta e baixaria a cobertura por erro de execução, não do método.
situacao = None
if caminhos["situacao_deteccao"].exists():
    situacao = pd.read_csv(caminhos["situacao_deteccao"], keep_default_na=False, na_values=[""])
    incompletos = situacao[situacao.status.isin(["falha", "pendente"])]
    if not incompletos.empty:
        raise ValueError(f"{len(incompletos)} exames da lista própria em falha ou pendentes; "
                         "termine a rodada do scripts/10_detectar_candidatos.py antes")
    if set(situacao.seriesuid) != exames:
        raise ValueError("a situação da detecção não cobre os mesmos exames do inventário")

print("conferência da entrada")
print(f"{'lista':>26} {'lidos':>11} {'fora':>6} {'exames':>7} {'com cand.':>10} {'sem':>5}")
print("-" * 72)
dados, entradas = {}, {}
for nome, caminho in listas.items():
    lista = pd.read_csv(caminho, usecols=colunas)
    entradas[nome] = comparacao.conferir_entrada(lista, exames)
    dados[nome] = lista[lista.seriesuid.isin(exames)]
    e = entradas[nome]
    print(f"{nome:>26} {e['pontos_lidos']:11d} {e['pontos_fora_do_inventario']:6d} "
          f"{e['exames']:7d} {e['exames_com_candidato']:10d} {e['exames_sem_candidato']:5d}")

if len({e["exames"] for e in entradas.values()}) != 1:
    raise ValueError("as duas listas não estão sendo medidas sobre os mesmos exames")
print(f"\nas duas listas medidas sobre os mesmos {len(exames)} exames e os mesmos "
      f"{len(nodulos)} nódulos\n")


def tempo_da_lista_propria():
    """Segundos de geração e de onde o número veio.

    Vale o registro da rodada completa quando ele tem o tempo de todos os exames. Sem isso, a
    estimativa sai da calibração, que mediu exame a exame a mesma configuração de produção.
    """
    if situacao is not None and situacao.segundos.notna().all():
        return float(situacao.segundos.sum()), "medido: soma dos 888 exames da rodada"
    calibracao = caminhos["intermediario"] / "calibracao_log" / "resultados_por_exame.csv"
    if calibracao.exists():
        medidos = pd.read_csv(calibracao)
        medidos = medidos[(medidos.configuracao == "inicial") & medidos.erro.fillna("").eq("")]
        if not medidos.empty:
            media = float(medidos.segundos.mean())
            return media * len(exames), (f"estimado: média de {len(medidos)} exames da "
                                         f"calibração, {media:.1f} s por exame")
    return float("nan"), "não registrado"


tempo_proprio, origem_proprio = tempo_da_lista_propria()
tempos = {
    "candidatos.csv (próprio)": (tempo_proprio, origem_proprio),
    "candidates_V2.csv": (0.0, "pronta: vem do desafio e não é gerada aqui"),
}

alcances, linhas = {}, []
for nome, lista in dados.items():
    alcances[nome] = det.alcancados(nodulos, lista)
    linha = comparacao.resumir(nome, lista, exames, nodulos, alcances[nome],
                               reamostras, confianca, semente)
    tamanho = listas[nome].stat().st_size
    segundos, origem = tempos[nome]
    linha.update({
        "bytes": tamanho,
        "bytes_por_candidato": tamanho / max(1, entradas[nome]["pontos_lidos"]),
        "segundos_geracao": segundos,
        "origem_tempo": origem,
    })
    linhas.append(linha)

tabela = pd.DataFrame(linhas)
print(f"{'lista':>26} {'por exame':>10} {'mediana':>8} {'alcançados':>14} {'cobertura':>10} "
      f"{'IC 95%':>16} {'disco':>10} {'tempo':>9}")
print("-" * 112)
for linha in tabela.itertuples():
    print(f"{linha.lista:>26} {linha.por_exame:10.1f} {linha.mediana_por_exame:8.0f} "
          f"{linha.alcancados:6d} de {linha.nodulos:<5d} {linha.cobertura:9.1%} "
          f"{linha.ic_inferior:7.1%} a {linha.ic_superior:6.1%} "
          f"{linha.bytes / 2**20:7.1f} MiB {linha.segundos_geracao / 3600:7.1f} h")
for linha in tabela.itertuples():
    print(f"tempo de {linha.lista}: {linha.origem_tempo}")
print("cobertura é teto de sensibilidade da lista, não ponto da curva FROC")

propria, v2 = (alcances[n] for n in listas)
cruzamento = comparacao.cruzar(propria, v2)
print(f"\ndos {cruzamento['nodulos']} nódulos: {cruzamento['ambas']} pelas duas, "
      f"{cruzamento['so_a']} só pela própria, {cruzamento['so_b']} só pelo V2, "
      f"{cruzamento['nenhuma']} por nenhuma")
print(f"a união das duas alcançaria {cruzamento['uniao']}, "
      f"{cruzamento['uniao'] / cruzamento['nodulos']:.1%}")

saida = caminhos["comparacao_propria_v2"]
tabela.to_csv(saida, index=False)
print(f"\n{saida}")

por_nodulo = nodulos[["seriesuid", *det.COLUNAS, "diameter_mm"]].copy()
por_nodulo["alcancado_propria"] = propria
por_nodulo["alcancado_v2"] = v2
por_nodulo.to_csv(caminhos["alcance_por_nodulo_propria_v2"], index=False)
print(caminhos["alcance_por_nodulo_propria_v2"])

so_um_lado = por_nodulo[por_nodulo.alcancado_propria != por_nodulo.alcancado_v2]
if not so_um_lado.empty:
    print("\ndiâmetro dos nódulos alcançados por uma lista só:")
    for lado, grupo in so_um_lado.groupby("alcancado_v2"):
        diametros = grupo.diameter_mm.to_numpy(float)
        quem = "só V2" if lado else "só própria"
        print(f"  {quem:>11}: {len(grupo)} nódulos, de {np.min(diametros):.1f} a "
              f"{np.max(diametros):.1f} mm, mediana {np.median(diametros):.1f} mm")
