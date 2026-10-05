"""Confere a conversao de coordenadas e o formato dos arquivos de recortes."""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import SimpleITK as sitk


CAMINHO = Path(__file__).resolve().parents[1] / "scripts" / "09_extrair_patches.py"
ESPECIFICACAO = importlib.util.spec_from_file_location("extrair_patches_script", CAMINHO)
script = importlib.util.module_from_spec(ESPECIFICACAO)
ESPECIFICACAO.loader.exec_module(script)


def test_recorte_e_metadados_correspondem_ao_ponto_v2(tmp_path):
    volume = np.arange(50 ** 3, dtype=np.float32).reshape(50, 50, 50) / (50 ** 3)
    imagem = sitk.GetImageFromArray(volume)
    imagem.SetOrigin((-10.0, 20.0, 30.0))
    imagem.SetDirection((-1.0, 0.0, 0.0, 0.0, -1.0, 0.0, 0.0, 0.0, 1.0))
    centro = (24, 23, 22)
    x, y, z = imagem.TransformIndexToPhysicalPoint(centro)
    grupo = pd.DataFrame([{"coordX": x, "coordY": y, "coordZ": z, "class": 1}], index=[127])
    recortes = script.extrair(imagem, grupo, (34, 34, 34))
    destino = tmp_path / "exame.npz"
    script.salvar(destino, grupo, recortes, (34, 34, 34))

    assert script.validar_arquivo(destino, grupo, (34, 34, 34)) > 0
    with np.load(destino) as dados:
        assert dados["patches"].shape == (1, 34, 34, 34)
        assert dados["patches"][0, 17, 17, 17] == volume[22, 23, 24]
        assert dados["candidate_id"].tolist() == [127]
        assert dados["classe_luna16"].tolist() == [1]
        assert [dados[nome][0] for nome in ("coordX", "coordY", "coordZ")] == pytest.approx(
            [x, y, z]
        )

    outra_classe = grupo.copy()
    outra_classe["class"] = 0
    with pytest.raises(ValueError, match="classe_luna16"):
        script.validar_arquivo(destino, outra_classe, (34, 34, 34))


def test_seriesuid_e_retomada_recriam_arquivo_invalido(tmp_path, monkeypatch):
    uid = "exame-a"
    volumes = tmp_path / "volumes"
    volumes.mkdir()
    imagem = sitk.GetImageFromArray(np.full((40, 40, 40), 0.5, dtype=np.float32))
    sitk.WriteImage(imagem, str(volumes / f"{uid}.mha"))
    lista = tmp_path / "candidates_V2.csv"
    pd.DataFrame([{"seriesuid": uid, "coordX": 20, "coordY": 20, "coordZ": 20,
                   "class": 1}]).to_csv(lista, index=False)
    saida = tmp_path / "patches"
    relatorios = tmp_path / "relatorios"
    monkeypatch.setattr(script.config, "carregar", lambda: {
        "candidatos": {"patch": [34, 34, 34]},
        "caminhos": {"luna16_candidatos": lista, "volumes": volumes,
                     "processado": tmp_path, "intermediario": relatorios},
    })
    monkeypatch.setattr(sys, "argv", ["09_extrair_patches.py", "--seriesuid", uid,
                                       "--candidatos", str(lista), "--volumes", str(volumes),
                                       "--saida", str(saida)])

    script.main()
    resumo = relatorios / f"resumo_patches_{uid}.json"
    assert json.loads(resumo.read_text())["criado"] == 1
    assert json.loads(resumo.read_text())["recortes_validos"] == 1

    script.main()
    assert json.loads(resumo.read_text())["existente"] == 1

    (saida / f"{uid}.npz").write_bytes(b"arquivo incompleto")
    script.main()
    assert json.loads(resumo.read_text())["recriado"] == 1
    assert script.validar_arquivo(saida / f"{uid}.npz", pd.read_csv(lista), (34, 34, 34)) > 0
