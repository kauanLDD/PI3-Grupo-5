"""A rodada retomável da geração de candidatos nos 888 exames."""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from detection import blobs, rodada

PARAMETROS = {"min_sigma": 1.0, "max_sigma": 5.0, "num_sigma": 5, "threshold": 0.1}


def candidatos(uid, n):
    return pd.DataFrame([{"seriesuid": uid, "coordX": float(i), "coordY": 0.0, "coordZ": 0.0,
                          "raio": 1.7} for i in range(n)], columns=blobs.COLUNAS)


def test_pasta_nova_nao_esta_retomando(tmp_path):
    assert rodada.preparar_pasta(tmp_path / "r", PARAMETROS) is False
    assert rodada.preparar_pasta(tmp_path / "r", PARAMETROS) is True


def test_pasta_recusa_continuar_com_outros_parametros(tmp_path):
    """Sem isto, metade dos exames sai de um limiar e metade de outro, sem erro nenhum."""
    rodada.preparar_pasta(tmp_path, PARAMETROS)
    with pytest.raises(ValueError, match="threshold"):
        rodada.preparar_pasta(tmp_path, {**PARAMETROS, "threshold": 0.2})


def test_pendentes_pula_o_que_ja_rodou(tmp_path):
    rodada.gravar_exame(tmp_path, "a", candidatos("a", 2))
    assert rodada.pendentes(tmp_path, ["a", "b", "c"]) == ["b", "c"]


def test_exame_sem_candidato_conta_como_rodado(tmp_path):
    """Zero blobs é resultado, não falha: não pode ser refeito para sempre nem sumir da média."""
    rodada.gravar_exame(tmp_path, "a", candidatos("a", 0))
    assert rodada.pendentes(tmp_path, ["a"]) == []
    assert rodada.situacao(tmp_path, ["a"]).status.tolist() == [rodada.SEM_CANDIDATO]


def test_gravar_nao_deixa_temporario(tmp_path):
    rodada.gravar_exame(tmp_path, "a", candidatos("a", 3))
    assert sorted(p.name for p in tmp_path.iterdir()) == ["a.csv"]


def test_situacao_separa_os_quatro_casos(tmp_path):
    rodada.gravar_exame(tmp_path, "a", candidatos("a", 3))
    rodada.registrar(tmp_path, "a", rodada.CONCLUIDO, 3, 20.0)
    rodada.gravar_exame(tmp_path, "b", candidatos("b", 0))
    rodada.registrar(tmp_path, "b", rodada.SEM_CANDIDATO, 0, 10.0)
    rodada.registrar(tmp_path, "c", rodada.FALHA, segundos=1.0, erro="RuntimeError: x")

    s = rodada.situacao(tmp_path, ["a", "b", "c", "d"]).set_index("seriesuid")

    assert s.status.to_dict() == {"a": rodada.CONCLUIDO, "b": rodada.SEM_CANDIDATO,
                                  "c": rodada.FALHA, "d": rodada.PENDENTE}
    assert s.candidatos.to_dict() == {"a": 3, "b": 0, "c": 0, "d": 0}
    assert s.loc["c", "erro"] == "RuntimeError: x"


def test_falha_que_deu_certo_depois_vira_concluido(tmp_path):
    """O arquivo do exame manda, não a primeira linha do registro."""
    rodada.registrar(tmp_path, "a", rodada.FALHA, erro="OSError: disco")
    rodada.gravar_exame(tmp_path, "a", candidatos("a", 2))
    rodada.registrar(tmp_path, "a", rodada.CONCLUIDO, 2, 15.0)

    linha = rodada.situacao(tmp_path, ["a"]).iloc[0]
    assert linha.status == rodada.CONCLUIDO
    assert linha.segundos == 15.0


def test_juntar_respeita_os_exames_pedidos(tmp_path):
    """Exame que ficou na pasta de uma rodada maior não entra numa lista menor."""
    rodada.gravar_exame(tmp_path, "a", candidatos("a", 2))
    rodada.gravar_exame(tmp_path, "b", candidatos("b", 0))
    rodada.gravar_exame(tmp_path, "c", candidatos("c", 1))

    lista = rodada.juntar(tmp_path, ["a", "b"], blobs.COLUNAS)

    assert list(lista.columns) == blobs.COLUNAS
    assert lista.seriesuid.tolist() == ["a", "a"]


def test_juntar_sem_nada_devolve_tabela_vazia(tmp_path):
    lista = rodada.juntar(tmp_path, ["a"], blobs.COLUNAS)
    assert lista.empty
    assert list(lista.columns) == blobs.COLUNAS


def test_cache_sem_manifesto_nao_recebe_parametros_novos(tmp_path):
    rodada.gravar_exame(tmp_path, "a", candidatos("a", 1))
    with pytest.raises(ValueError, match="sem manifesto"):
        rodada.preparar_pasta(tmp_path, PARAMETROS)


def test_cache_com_outro_exame_nao_e_reutilizado(tmp_path):
    rodada.gravar_exame(tmp_path, "a", candidatos("b", 1))
    with pytest.raises(ValueError, match="exame incorreto"):
        rodada.pendentes(tmp_path, ["a"])
