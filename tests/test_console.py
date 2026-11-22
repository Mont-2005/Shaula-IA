import ctypes
import subprocess
from unittest.mock import MagicMock

import pytest

if not hasattr(ctypes, "windll"):
    ctypes.windll = MagicMock()
    ctypes.WinDLL = MagicMock()
    ctypes.WINFUNCTYPE = ctypes.CFUNCTYPE

from tools.console import CodificacaoConsole


def test_opcoes_trocam_a_codificacao_e_nunca_lancam_erro_de_decodificacao():
    opcoes = CodificacaoConsole.opcoes()
    assert opcoes["errors"] == "replace"
    assert opcoes["encoding"] in ("oem", "utf-8")


def test_saida_com_bytes_invalidos_nao_derruba_a_leitura():
    # 0x81 não existe em cp1252: com text=True simples isso lançava
    # UnicodeDecodeError dentro do subprocess.run.
    resultado = subprocess.run(
        ["python3", "-c", "import sys; sys.stdout.buffer.write(b'Estado: conectado \\x81\\x90')"],
        capture_output=True,
        encoding="cp1252",
        errors=CodificacaoConsole.ERROS,
    )
    assert "Estado: conectado" in resultado.stdout


def test_verificar_wifi_usa_a_codificacao_do_console(monkeypatch):
    from tools.rede import InformacoesRede

    recebido = {}

    def falso(comando, **kwargs):
        recebido.update(kwargs)
        return subprocess.CompletedProcess(comando, 0, "", "")

    monkeypatch.setattr(subprocess, "run", falso)
    InformacoesRede().verificar_wifi()
    assert recebido["errors"] == "replace"
    assert recebido["encoding"] == CodificacaoConsole.NOME
