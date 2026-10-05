"""O critério de acerto do desafio: candidato a menos de um raio do centro do nódulo."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from detection import candidatos


def nodulo(uid="a", x=0.0, y=0.0, z=0.0, diametro=10.0):
    return pd.DataFrame([{"seriesuid": uid, "coordX": x, "coordY": y, "coordZ": z,
                          "diameter_mm": diametro}])


def pontos(*linhas):
    return pd.DataFrame([{"seriesuid": u, "coordX": x, "coordY": y, "coordZ": z}
                         for u, x, y, z in linhas])


def test_candidato_dentro_do_raio_alcanca():
    assert candidatos.alcancados(nodulo(), pontos(("a", 4.0, 0.0, 0.0))).all()


def test_candidato_fora_do_raio_nao_alcanca():
    assert not candidatos.alcancados(nodulo(), pontos(("a", 6.0, 0.0, 0.0))).any()


def test_a_borda_do_raio_conta_como_acerto():
    """O desafio usa distância menor ou igual ao raio, e a diferença muda a contagem."""
    assert candidatos.alcancados(nodulo(), pontos(("a", 5.0, 0.0, 0.0))).all()


def test_a_distancia_e_nas_tres_dimensoes():
    """Pega implementação que compara eixo a eixo em vez de distância euclidiana."""
    # 3, 4, 0 dá distância 5, dentro. 4, 4, 0 dá 5,66, fora, mas cada eixo sozinho ainda cabe.
    assert candidatos.alcancados(nodulo(), pontos(("a", 3.0, 4.0, 0.0))).all()
    assert not candidatos.alcancados(nodulo(), pontos(("a", 4.0, 4.0, 0.0))).any()


def test_candidato_de_outro_exame_nao_conta():
    """Sem agrupar por exame, ponto de outra tomografia acerta pela coordenada por acaso."""
    assert not candidatos.alcancados(nodulo(), pontos(("b", 0.0, 0.0, 0.0))).any()


def test_exame_sem_candidato_nenhum():
    assert not candidatos.alcancados(nodulo(), pontos(("b", 0.0, 0.0, 0.0))).any()


def test_conta_cada_nodulo_uma_vez():
    dois = pd.concat([nodulo(x=0.0), nodulo(x=100.0)], ignore_index=True)
    resultado = candidatos.alcancados(dois, pontos(("a", 1.0, 0.0, 0.0), ("a", 2.0, 0.0, 0.0)))
    assert resultado.tolist() == [True, False]


def nodulos_em(*exames):
    """Um nódulo por item, com o exame dado, todos no mesmo lugar."""
    return pd.concat([nodulo(uid=u) for u in exames], ignore_index=True)


def test_cobertura_conta_a_fracao():
    medida = candidatos.cobertura(nodulos_em("a", "a", "b", "c"), [True, True, False, True],
                                  reamostras=200)
    assert (medida["alcancados"], medida["nodulos"]) == (3, 4)
    assert medida["cobertura"] == 0.75
    assert medida["ic_inferior"] <= 0.75 <= medida["ic_superior"]


def test_cobertura_tudo_alcancado_nao_tem_intervalo_aberto():
    medida = candidatos.cobertura(nodulos_em("a", "b"), [True, True], reamostras=100)
    assert medida["ic_inferior"] == medida["ic_superior"] == 1.0


def test_cobertura_reamostra_por_exame_e_nao_por_nodulo():
    """Dez nódulos num exame só são uma unidade: o intervalo tem que ir de 0 a 1.

    Reamostrando nódulo solto, a mesma tabela daria um intervalo estreito em volta de 50%.
    """
    exames = ["a"] * 10 + ["b"] * 10
    medida = candidatos.cobertura(nodulos_em(*exames), [True] * 10 + [False] * 10,
                                  reamostras=500)
    assert medida["ic_inferior"] == 0.0
    assert medida["ic_superior"] == 1.0


def test_cobertura_e_reprodutivel_com_a_mesma_semente():
    args = (nodulos_em("a", "b", "c", "d"), [True, False, True, False])
    assert (candidatos.cobertura(*args, reamostras=300, semente=42)
            == candidatos.cobertura(*args, reamostras=300, semente=42))


def test_cobertura_sem_nodulo_nenhum():
    medida = candidatos.cobertura(nodulos_em("a").iloc[:0], [], reamostras=10)
    assert medida["nodulos"] == 0
    assert medida["cobertura"] != medida["cobertura"]  # nan

