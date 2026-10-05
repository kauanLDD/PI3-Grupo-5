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


def test_candidato_em_achado_excluido_nao_vira_falso_positivo():
    """O caso pequeno do card S3-T5: um nódulo, um achado excluído e três candidatos.

    Sem a regra, o candidato em cima do achado excluído contaria como alarme falso.
    """
    nodulos = nodulo(x=0.0, diametro=10.0)
    excluidos = nodulo(x=50.0, diametro=6.0)
    pontos_ = pontos(("a", 1.0, 0.0, 0.0), ("a", 51.0, 0.0, 0.0), ("a", 100.0, 0.0, 0.0))

    rotulos = candidatos.rotular(pontos_, nodulos, excluidos)

    assert rotulos.tolist() == [candidatos.ACERTO, candidatos.IGNORADO, candidatos.FALSO_POSITIVO]


def test_sem_a_lista_de_excluidos_o_mesmo_candidato_vira_falso_positivo():
    """O contraste do caso acima: é a lista de excluídos que muda o rótulo, e não outra coisa."""
    rotulos = candidatos.rotular(pontos(("a", 51.0, 0.0, 0.0)), nodulo(x=0.0),
                                 nodulo(x=50.0, diametro=6.0).iloc[:0])
    assert rotulos.tolist() == [candidatos.FALSO_POSITIVO]


def test_achado_excluido_sem_diametro_vale_raio_de_5_mm():
    """30.513 dos 35.192 excluídos vêm com diameter_mm = -1, e o avaliador usa 10 mm no lugar.

    Tratar o -1 como raio negativo faria nenhum desses achados casar com candidato nenhum.
    """
    excluidos = nodulo(x=0.0, diametro=-1)
    rotulos = candidatos.rotular(pontos(("a", 4.9, 0.0, 0.0), ("a", 5.1, 0.0, 0.0)),
                                 nodulo(x=500.0), excluidos)
    assert rotulos.tolist() == [candidatos.IGNORADO, candidatos.FALSO_POSITIVO]


def test_candidato_em_nodulo_e_em_excluido_ao_mesmo_tempo_e_acerto():
    """O avaliador casa os nódulos antes dos excluídos, então o acerto não pode virar ignorado."""
    rotulos = candidatos.rotular(pontos(("a", 1.0, 0.0, 0.0)), nodulo(x=0.0),
                                 nodulo(x=2.0, diametro=-1))
    assert rotulos.tolist() == [candidatos.ACERTO]


def test_achado_excluido_de_outro_exame_nao_tira_candidato_da_conta():
    rotulos = candidatos.rotular(pontos(("a", 0.0, 0.0, 0.0)), nodulo(uid="b"),
                                 nodulo(uid="b", diametro=-1))
    assert rotulos.tolist() == [candidatos.FALSO_POSITIVO]


def test_rotular_usa_distancia_estritamente_menor_como_o_avaliador():
    """`dist < radiusSquared` no noduleCADEvaluationLUNA16.py: na borda exata não é acerto."""
    rotulos = candidatos.rotular(pontos(("a", 5.0, 0.0, 0.0)), nodulo(diametro=10.0),
                                 nodulo().iloc[:0])
    assert rotulos.tolist() == [candidatos.FALSO_POSITIVO]


def test_rotular_preserva_a_ordem_com_exames_intercalados():
    pontos_ = pontos(("b", 0.0, 0.0, 0.0), ("a", 0.0, 0.0, 0.0), ("b", 99.0, 0.0, 0.0))
    rotulos = candidatos.rotular(pontos_, nodulo(uid="a"), nodulo(uid="b", diametro=-1))
    assert rotulos.tolist() == [candidatos.IGNORADO, candidatos.ACERTO, candidatos.FALSO_POSITIVO]
