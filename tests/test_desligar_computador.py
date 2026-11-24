import ctypes
import subprocess
from unittest.mock import MagicMock

import pytest

if not hasattr(ctypes, "windll"):
    ctypes.windll = MagicMock()
    ctypes.WinDLL = MagicMock()
    ctypes.WINFUNCTYPE = ctypes.CFUNCTYPE

from tools.sistema import InformacoesSistema


def _shutdown_devolve(monkeypatch, codigo):
    chamadas = []

    def falso(comando, **kwargs):
        chamadas.append(comando)
        return subprocess.CompletedProcess(comando, codigo, b"", b"")

    monkeypatch.setattr(subprocess, "run", falso)
    return chamadas


def test_programa_o_desligamento(monkeypatch):
    chamadas = _shutdown_devolve(monkeypatch, 0)
    resposta = InformacoesSistema().desligar_computador(30)
    assert chamadas == [["shutdown", "/s", "/t", "30"]]
    assert "30 segundos" in resposta


def test_zero_desliga_agora(monkeypatch):
    _shutdown_devolve(monkeypatch, 0)
    assert "imediatamente" in InformacoesSistema().desligar_computador(0)


def test_desligamento_ja_agendado_tem_mensagem_clara(monkeypatch):
    _shutdown_devolve(monkeypatch, 1190)
    resposta = InformacoesSistema().desligar_computador(30)
    assert "Já existe um desligamento programado" in resposta
    assert "cancele o desligamento" in resposta
    assert "non-zero" not in resposta           # antes: o erro cru do subprocess


@pytest.mark.parametrize("codigo", [5, 87])
def test_outro_erro_do_windows_mostra_o_codigo(monkeypatch, codigo):
    _shutdown_devolve(monkeypatch, codigo)
    assert str(codigo) in InformacoesSistema().desligar_computador(30)


def test_tempo_negativo_nao_chama_o_windows(monkeypatch):
    chamadas = _shutdown_devolve(monkeypatch, 0)
    assert "negativo" in InformacoesSistema().desligar_computador(-5)
    assert chamadas == []
