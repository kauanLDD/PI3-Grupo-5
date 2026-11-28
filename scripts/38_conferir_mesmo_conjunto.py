"""A rede e o Random Forest usam os mesmos candidatos? E algum paciente aparece em dois conjuntos?

Pedido do professor no feedback da Sprint 4. Lê só arquivos já gravados pelos treinos e pelas
avaliações (a divisão, os candidatos de treino da rede e as previsões dos dois modelos na validação
e no teste); não treina, não pontua e não avalia nada de novo. Conta o que encontra em cada conjunto
e compara as listas dos dois modelos ponto a ponto.
"""

import json
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config
from dataset.divisao import PARTICOES

PONTO = ["seriesuid", "coordX", "coordY", "coordZ"]


def pacientes_em_mais_de_um_conjunto(divisao):
    """Pacientes cujas séries caem em mais de uma partição. Vazio quando não há vazamento."""
    partes = divisao.groupby("paciente").particao.nunique()
    return sorted(partes[partes > 1].index)


def resumir_divisao(divisao):
    """Exames, pacientes e subsets de cada partição, e os pacientes com mais de uma série."""
    linhas = []
    for particao in PARTICOES:
        parte = divisao.loc[divisao.particao.eq(particao)]
        series = parte.groupby("paciente").size()
        linhas.append({"conjunto": particao, "exames": len(parte), "pacientes": parte.paciente.nunique(),
                       "subsets": " ".join(map(str, sorted(parte.subset.unique()))),
                       "pacientes_com_mais_de_uma_serie": " ".join(sorted(series[series > 1].index))})
    return pd.DataFrame(linhas)


def contar(marcas, divisao, particao, modelo, fonte):
    """Uma linha da tabela: exames, pacientes, candidatos, positivos e negativos de uma lista.

    Recusa a lista se algum exame dela não for da partição esperada. Sem a coluna `class`, positivos
    e negativos ficam vazios: a contagem não é inventada.
    """
    da_particao = divisao.loc[divisao.particao.eq(particao)]
    fora = sorted(set(marcas.seriesuid) - set(da_particao.seriesuid))
    if fora:
        raise ValueError(f"{modelo}, {particao}: {len(fora)} exames de fora da partição")
    pacientes = da_particao.loc[da_particao.seriesuid.isin(marcas.seriesuid), "paciente"]
    positivos = int(marcas["class"].sum()) if "class" in marcas else None
    return {"conjunto": particao, "modelo": modelo, "exames": marcas.seriesuid.nunique(),
            "pacientes": pacientes.nunique(), "candidatos": len(marcas), "positivos": positivos,
            "negativos": None if positivos is None else len(marcas) - positivos, "fonte": fonte}


def comparar_pontos(a, b, chave):
    """Quantos pontos ficam só em a, só em b e nos dois, pela chave dada."""
    for nome, tabela in (("a", a), ("b", b)):
        if tabela.duplicated(chave).any():
            raise ValueError(f"lista {nome} com ponto repetido pela chave {chave}")
    juntos = a[chave].merge(b[chave], on=chave, how="outer", indicator=True)
    return {"so_na_rede": int(juntos._merge.eq("left_only").sum()),
            "so_no_random_forest": int(juntos._merge.eq("right_only").sum()),
            "nos_dois": int(juntos._merge.eq("both").sum())}


def main():
    cfg = config.carregar()
    config.fixar_semente(cfg["seed"])
    caminhos, fase = cfg["caminhos"], cfg["mesmo_conjunto"]
    raiz = config.RAIZ
    saida = caminhos["mesmo_conjunto"]

    divisao = pd.read_csv(raiz / fase["divisao"])
    vazamento = pacientes_em_mais_de_um_conjunto(divisao)
    exames_repetidos = int(divisao.seriesuid.duplicated().sum())
    resumo_divisao = resumir_divisao(divisao)
    print(resumo_divisao.to_string(index=False), flush=True)
    print(f"exames repetidos na divisão: {exames_repetidos}; pacientes em mais de um conjunto: {len(vazamento)}",
          flush=True)

    rede, floresta = raiz / fase["rede"], raiz / fase["random_forest"]
    recibo_rede = json.loads((rede / "execucao.json").read_text(encoding="utf-8"))
    recibo_floresta = json.loads((floresta / "execucao.json").read_text(encoding="utf-8"))

    # Treino. A lista de treino da rede está versionada; a do Random Forest (as características de
    # todos os candidatos V2 dos exames de treino) fica fora do git, e sem ela a linha sai do recibo.
    treino_rede = pd.read_csv(rede / "candidatos_treino.csv")
    linhas = [contar(treino_rede, divisao, "treino", "rede", f"{fase['rede']}/candidatos_treino.csv")]
    caracteristicas = caminhos["caracteristicas_centro"] / "treino.csv"
    treino_floresta = None
    if caracteristicas.exists():
        treino_floresta = pd.read_csv(caracteristicas, usecols=["candidate_id", "seriesuid", "classe_luna16"])
        treino_floresta = treino_floresta.rename(columns={"classe_luna16": "class"})
        linhas.append(contar(treino_floresta, divisao, "treino", "random_forest", str(caracteristicas)))
    else:
        metricas = recibo_floresta["metricas"]
        treino = divisao.loc[divisao.particao.eq("treino")]
        linhas.append({"conjunto": "treino", "modelo": "random_forest", "exames": len(treino),
                       "pacientes": treino.paciente.nunique(), "candidatos": metricas["treino_candidatos"],
                       "positivos": metricas["treino_positivos"],
                       "negativos": metricas["treino_candidatos"] - metricas["treino_positivos"],
                       "fonte": f"{fase['random_forest']}/execucao.json"})

    # Validação: as duas listas têm candidate_id, a da rede tem também o rótulo.
    validacao_rede = pd.read_csv(rede / "probabilidades_validacao.csv")
    validacao_floresta = pd.read_csv(floresta / "probabilidades_validacao.csv")
    rotulo = validacao_rede.set_index("candidate_id")["class"]
    validacao_floresta = validacao_floresta.assign(**{"class": validacao_floresta.candidate_id.map(rotulo)})
    if validacao_floresta["class"].isna().any():
        validacao_floresta = validacao_floresta.drop(columns="class")
    linhas.append(contar(validacao_rede, divisao, "validacao", "rede", f"{fase['rede']}/probabilidades_validacao.csv"))
    linhas.append(contar(validacao_floresta, divisao, "validacao", "random_forest",
                         f"{fase['random_forest']}/probabilidades_validacao.csv"))

    # Teste: nenhuma das duas listas gravadas tem o rótulo; positivos e negativos ficam vazios.
    teste_rede = pd.read_csv(raiz / fase["teste_rede"] / "predicoes.csv")
    teste_floresta = pd.read_csv(raiz / fase["teste_random_forest"] / "probabilidades_teste.csv")
    linhas.append(contar(teste_rede, divisao, "teste", "rede", f"{fase['teste_rede']}/predicoes.csv"))
    linhas.append(contar(teste_floresta, divisao, "teste", "random_forest",
                         f"{fase['teste_random_forest']}/probabilidades_teste.csv"))
    contagens = pd.DataFrame(linhas).astype({"positivos": "Int64", "negativos": "Int64"})

    comparacoes = []
    if treino_floresta is not None:
        comparacoes.append({"conjunto": "treino", "chave": "candidate_id",
                            **comparar_pontos(treino_rede, treino_floresta, ["candidate_id"])})
    for chave in (["candidate_id"], PONTO):
        comparacoes.append({"conjunto": "validacao", "chave": "+".join(chave),
                            **comparar_pontos(validacao_rede, validacao_floresta, chave)})
    comparacoes.append({"conjunto": "teste", "chave": "+".join(PONTO),
                        **comparar_pontos(teste_rede, teste_floresta, PONTO)})
    comparacoes = pd.DataFrame(comparacoes)

    def mesma_lista(conjunto):
        linhas = comparacoes.loc[comparacoes.conjunto.eq(conjunto)]
        return bool(len(linhas)) and bool(linhas.so_na_rede.eq(0).all() and linhas.so_no_random_forest.eq(0).all())

    saida.mkdir(parents=True, exist_ok=True)
    resumo_divisao.to_csv(saida / "divisao.csv", index=False)
    contagens.to_csv(saida / "contagens.csv", index=False)
    comparacoes.to_csv(saida / "comparacao_pontos.csv", index=False)
    (saida / "resumo.json").write_text(json.dumps({
        "teste_utilizado": False, "divisao": fase["divisao"], "exames_repetidos_na_divisao": exames_repetidos,
        "pacientes_em_mais_de_um_conjunto": vazamento,
        "mesmos_candidatos_validacao": mesma_lista("validacao"), "mesmos_candidatos_teste": mesma_lista("teste"),
        # No treino a rede usa uma amostra: todos os positivos e 20 negativos por positivo.
        "negativos_por_positivo_rede": recibo_rede["parametros"]["negativos_por_positivo"],
        "treino_rede_dentro_do_random_forest": None if treino_floresta is None
        else bool(set(treino_rede.candidate_id) <= set(treino_floresta.candidate_id))},
        indent=2, ensure_ascii=False), encoding="utf-8")
    print(contagens.drop(columns="fonte").to_string(index=False), flush=True)
    print(comparacoes.to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
