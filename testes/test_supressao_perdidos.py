"""Nódulos perdidos pela supressão suave no teste: repetição da supressão e causa de cada perda (T30)."""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import SimpleITK as sitk

RAIZ = Path(__file__).resolve().parents[1]

import sys

sys.path.insert(0, str(RAIZ / "src"))
from detection import candidatos as det


def carregar():
    arquivo = RAIZ / "scripts" / "39_supressao_perdidos_teste.py"
    spec = importlib.util.spec_from_file_location("supressao_perdidos_teste", arquivo)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def pontos(xyz, notas, uid="a"):
    xyz = np.asarray(xyz, float)
    return pd.DataFrame({"seriesuid": uid, "coordX": xyz[:, 0], "coordY": xyz[:, 1], "coordZ": xyz[:, 2],
                         "probability": notas})


@pytest.mark.parametrize("forma", ["linear", "gaussiana"])
def test_rastrear_suave_repete_a_supressao_original(forma):
    gerador = np.random.default_rng(42)
    exame = pontos(gerador.uniform(0, 60, size=(300, 3)), gerador.uniform(0, 1, size=300))
    escolhidas, finais, _ = carregar().rastrear_suave(exame, 16.0, forma, 40, 0.5)
    original = det.suprimir_suave(exame, 16.0, forma, 40, 0.5)
    assert original.index.tolist() == exame.index[escolhidas].tolist()
    assert np.allclose(original.probability.to_numpy(), finais[escolhidas])


def test_so_em_compara_pelo_centro_do_nodulo():
    modulo = carregar()
    sem = pd.DataFrame([["a", "None", 0.0, 0.0, 0.0, 5.0, -1]], columns=modulo.SEM_MARCA)
    com = pd.concat([sem, sem.assign(coordX=30.0)], ignore_index=True)
    assert modulo.so_em(com, sem).coordX.tolist() == [30.0]
    assert modulo.so_em(sem, com).empty


def test_tipo_do_ponto_separa_nodulo_excluida_e_falso_alarme():
    modulo = carregar()
    nodulos = pd.DataFrame({"seriesuid": ["a"], "coordX": [0.0], "coordY": [0.0], "coordZ": [0.0],
                            "diameter_mm": [6.0]})
    excluidas = nodulos.assign(coordX=20.0, diameter_mm=-1.0)
    assert modulo.tipo_do_ponto([1, 0, 0], nodulos, excluidas)[0] == modulo.OUTRO_NODULO
    assert modulo.tipo_do_ponto([22, 0, 0], nodulos, excluidas)[0] == modulo.EXCLUIDA
    assert modulo.tipo_do_ponto([40, 0, 0], nodulos, excluidas)[0] == modulo.FALSO_ALARME


def test_analisar_nodulo_acha_o_vizinho_que_rebaixou():
    modulo = carregar()
    # Dois nódulos a 8 mm; o de nota maior é escolhido e rebaixa o outro abaixo de um falso alarme.
    exame = pontos([[0, 0, 0], [8, 0, 0], [50, 0, 0]], [0.9, 0.8, 0.5])
    nodulos = pd.DataFrame({"seriesuid": "a", "coordX": [0.0, 8.0], "coordY": 0.0, "coordZ": 0.0,
                            "diameter_mm": [6.0, 4.0]})
    escolhidas, finais, rebaixos = modulo.rastrear_suave(exame, 16.0, "linear", 2, 0.5)
    assert escolhidas == [0, 2]
    linha = modulo.analisar_nodulo(nodulos.iloc[1], exame, escolhidas, finais, rebaixos, nodulos, nodulos.iloc[:0])
    assert linha["tipo_vizinho"] == modulo.OUTRO_NODULO
    assert linha["nota_antes"] == pytest.approx(0.8)
    assert linha["nota_depois"] == pytest.approx(0.8 * 0.5)
    assert linha["distancia_vizinho_mm"] == pytest.approx(8.0)
    assert linha["diametro_do_outro_nodulo_mm"] == pytest.approx(6.0)


def test_conferir_marcas_recusa_marcas_diferentes():
    modulo = carregar()
    exame = pontos([[0, 0, 0], [50, 0, 0]], [0.9, 0.5])
    escolhidas, finais, _ = modulo.rastrear_suave(exame, 16.0, "linear", 2, 0.5)
    gravadas = exame.copy()
    modulo.conferir_marcas(exame, escolhidas, finais, gravadas)
    with pytest.raises(ValueError, match="difere"):
        modulo.conferir_marcas(exame, escolhidas, finais, gravadas.assign(probability=[0.9, 0.4]))


def test_escolher_casos_divide_por_causa_e_completa():
    modulo = carregar()
    tabela = pd.DataFrame({"seriesuid": list("abcde"), "diametro_mm": [3, 9, 5, 7, 4],
                           "tipo_vizinho": [modulo.OUTRO_NODULO] + [modulo.FALSO_ALARME] * 4})
    assert modulo.escolher_casos(tabela, 4).seriesuid.tolist() == ["a", "b", "d", "c"]


def test_script_de_ponta_a_ponta_em_dados_sinteticos(tmp_path, monkeypatch):
    """Um exame, dois nódulos a 8 mm: o menor some das 2 marcas só com a supressão."""
    modulo = carregar()
    uid = "1.2.3"
    completa, volumes = tmp_path / "teste_supressao", tmp_path / "volumes"
    for pasta in (completa / "propria", completa / "propria_suave", volumes):
        pasta.mkdir(parents=True)
    notas = pontos([[0, 0, 0], [8, 0, 0], [40, 0, 0]], [0.9, 0.8, 0.5], uid)
    notas.to_csv(completa / "probabilidades.csv", index=False)
    det.suprimir_suave(notas, 16.0, "linear", 2, 0.5).to_csv(completa / "propria_suave" / "predicoes.csv",
                                                              index=False)
    (completa / "propria" / "nodulesWithoutCandidate_predicoes.txt").write_text("")
    (completa / "propria_suave" / "nodulesWithoutCandidate_predicoes.txt").write_text(
        f"{uid},None,8.0,0.0,0.0,4.0,-1\n")
    nodulos = pd.DataFrame({"seriesuid": uid, "coordX": [0.0, 8.0], "coordY": 0.0, "coordZ": 0.0,
                            "diameter_mm": [6.0, 4.0]})
    nodulos.to_csv(tmp_path / "annotations.csv", index=False)
    nodulos.iloc[:0].to_csv(tmp_path / "excluidas.csv", index=False)
    imagem = sitk.GetImageFromArray(np.zeros((80, 80, 80), np.float32))
    imagem.SetOrigin((-20.0, -40.0, -40.0))
    sitk.WriteImage(imagem, str(volumes / f"{uid}.mha"))

    cfg = {"seed": 42, "caminhos": {"teste_supressao_completa": completa, "supressao_perdidos": tmp_path / "saida",
                                    "luna16_anotacoes": tmp_path / "annotations.csv",
                                    "luna16_anotacoes_excluidas": tmp_path / "excluidas.csv", "volumes": volumes},
           "supressao_perdidos": {"perdidos_esperados": 1, "casos_figura": 1, "lado_figura_mm": 64},
           "supressao_suave": {"raio_mm": 16, "marcas_por_exame": 2, "sigma": 0.5},
           "teste_supressao": {"forma": "linear"}}
    monkeypatch.setattr(modulo.config, "carregar", lambda: cfg)
    modulo.main()

    tabela = pd.read_csv(tmp_path / "saida" / "nodulos.csv")
    resumo = json.loads((tmp_path / "saida" / "resumo.json").read_text(encoding="utf-8"))
    assert len(tabela) == 1 and tabela.tipo_vizinho.iloc[0] == modulo.OUTRO_NODULO
    assert resumo["por_causa"] == {modulo.OUTRO_NODULO: 1, modulo.EXCLUIDA: 0, modulo.FALSO_ALARME: 0}
    assert (tmp_path / "saida" / "casos.png").exists()
