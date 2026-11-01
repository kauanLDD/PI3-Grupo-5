"""Os caminhos de cada máquina entram por cima do config.yaml sem mexer nele."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config

HD = "/media/kauan/HD Samuel/luna/archive"


def test_sem_arquivo_local_os_caminhos_ficam_como_no_yaml(tmp_path):
    cfg = config.carregar(local=tmp_path / "nao_existe.yaml")
    assert cfg["caminhos"]["luna16"] == Path(HD)


def test_trocar_a_raiz_da_base_leva_junto_os_caminhos_dentro_dela(tmp_path):
    local = tmp_path / "caminhos.local.yaml"
    local.write_text('luna16: "/mnt/drive/ PI3-Grupo-5/Dataset"\n', encoding="utf-8")
    c = config.carregar(local=local)["caminhos"]
    assert c["luna16_mascaras"] == Path("/mnt/drive/ PI3-Grupo-5/Dataset/seg-lungs-LUNA16/seg-lungs-LUNA16")
    assert c["luna16_anotacoes"] == Path("/mnt/drive/ PI3-Grupo-5/Dataset/annotations.csv")
    # O que é do repositório não muda.
    assert c["volumes"] == config.RAIZ / "dados/processado/volumes"


def test_raiz_com_nome_parecido_nao_e_trocada():
    trocados = config.trocar_caminhos({"luna16": "/a/archive", "outro": "/a/archive2/x.csv"},
                                      {"luna16": "/b"})
    assert trocados == {"luna16": "/b", "outro": "/a/archive2/x.csv"}


def test_chave_desconhecida_para_em_vez_de_ser_ignorada():
    with pytest.raises(KeyError):
        config.trocar_caminhos({"luna16": "/a"}, {"lunna16": "/b"})
