import ctypes
from unittest.mock import MagicMock

import pytest

if not hasattr(ctypes, "windll"):
    ctypes.windll = MagicMock()
    ctypes.WinDLL = MagicMock()
    ctypes.WINFUNCTYPE = ctypes.CFUNCTYPE

from tools import janelas
from tools.janelas import GerenciadorJanelas

MONITORES = [
    {"handle": 1, "left": 0, "top": 0, "right": 1920, "bottom": 1080, "primary": True},
    {"handle": 2, "left": 1920, "top": 0, "right": 3840, "bottom": 1080, "primary": False},
]


class Windows:
    """user32 de mentira: uma janela com estado, que pode 'desfazer' movimentos."""

    def __init__(self, rect=(100, 100, 900, 700), estado="normal", ignorar_primeiros_moves=0):
        self.rect = list(rect)
        self.estado = estado
        self.normal = list(rect)
        self.ignorar = ignorar_primeiros_moves
        self.chamadas = []

    def _preencher(self, ref, valores):
        r = ref._obj
        r.left, r.top, r.right, r.bottom = valores

    def GetWindowRect(self, hwnd, ref):
        self._preencher(ref, (-32000, -32000, -31840, -31972) if self.estado == "min" else self.rect)
        return 1

    def IsIconic(self, hwnd):
        return int(self.estado == "min")

    def IsZoomed(self, hwnd):
        return int(self.estado == "max")

    def ShowWindow(self, hwnd, comando):
        self.chamadas.append(("show", comando))
        if comando == 9:  # restaurar
            self.estado = "max" if self.estado == "min_de_max" else "normal"
            if self.estado == "normal":
                self.rect = list(self.normal)
        elif comando == 3:
            self.estado = "max"
            cx = (self.rect[0] + self.rect[2]) // 2
            m = MONITORES[1] if cx >= 1920 else MONITORES[0]
            self.rect = [m["left"], m["top"], m["right"], m["bottom"]]
        return 1

    def SetWindowPos(self, hwnd, apos, x, y, w, h, flags):
        self.chamadas.append(("pos", x, y, w, h))
        if self.ignorar > 0:
            self.ignorar -= 1
            return 1
        self.rect = [x, y, x + w, y + h]
        self.normal = list(self.rect)
        return 1

    def MonitorFromWindow(self, hwnd, flags):
        return -1  # propositalmente não bate com nenhum handle


@pytest.fixture
def gerenciador(monkeypatch):
    g = GerenciadorJanelas(cache=MagicMock())
    monkeypatch.setattr(g, "obter_monitores", lambda: MONITORES)
    monkeypatch.setattr(janelas.time, "sleep", lambda s: None)
    g.ESPERA_MOVER_S = 0.01
    g.ESPERA_ESTADO_S = 0.01
    return g


def _usar(monkeypatch, windows):
    monkeypatch.setattr(janelas, "user32", windows)
    return windows


def test_janela_normal_vai_para_o_centro_do_monitor_2(gerenciador, monkeypatch):
    w = _usar(monkeypatch, Windows())
    assert gerenciador.mover_janela_monitor(1, 2).startswith("Janela movida")
    assert w.rect == [1920 + (1920 - 800) // 2, (1080 - 600) // 2, 1920 + (1920 - 800) // 2 + 800, (1080 - 600) // 2 + 600]


def test_janela_minimizada_e_restaurada_antes_de_mover(gerenciador, monkeypatch):
    w = _usar(monkeypatch, Windows(estado="min"))
    w.normal = [100, 100, 900, 700]
    assert gerenciador.mover_janela_monitor(1, 2).startswith("Janela movida")
    assert w.estado == "normal"
    assert w.rect[0] >= 1920
    assert w.rect[2] - w.rect[0] == 800  # tamanho de verdade, não o do botão da barra


def test_maximizada_move_e_maximiza_no_monitor_de_destino(gerenciador, monkeypatch):
    w = _usar(monkeypatch, Windows(estado="max", rect=(0, 0, 1920, 1080)))
    w.normal = [100, 100, 900, 700]
    assert gerenciador.mover_janela_monitor(1, 2).startswith("Janela movida")
    assert w.estado == "max" and w.rect[0] == 1920


def test_minimizada_que_estava_maximizada_volta_maximizada_no_destino(gerenciador, monkeypatch):
    w = _usar(monkeypatch, Windows(estado="min_de_max"))
    w.estado = "min_de_max"
    w.normal = [100, 100, 900, 700]
    w.IsIconic = lambda h: int(w.estado == "min_de_max")
    assert gerenciador.mover_janela_monitor(1, 2).startswith("Janela movida")
    assert w.estado == "max" and w.rect[0] == 1920


def test_repete_quando_o_windows_ignora_o_primeiro_movimento(gerenciador, monkeypatch):
    w = _usar(monkeypatch, Windows(ignorar_primeiros_moves=2))
    assert gerenciador.mover_janela_monitor(1, 2).startswith("Janela movida")
    assert [c for c in w.chamadas if c[0] == "pos"].__len__() == 3


def test_diz_a_verdade_quando_nao_consegue_mover(gerenciador, monkeypatch):
    _usar(monkeypatch, Windows(ignorar_primeiros_moves=99))
    resultado = gerenciador.mover_janela_monitor(1, 2)
    assert resultado.startswith("Não consegui")


def test_janela_maior_que_o_monitor_de_destino_e_encolhida(gerenciador, monkeypatch):
    pequeno = [dict(MONITORES[0]), {"handle": 2, "left": 1920, "top": 0, "right": 2720, "bottom": 600, "primary": False}]
    monkeypatch.setattr(gerenciador, "obter_monitores", lambda: pequeno)
    w = _usar(monkeypatch, Windows(rect=(0, 0, 1800, 1000)))
    assert gerenciador.mover_janela_monitor(1, 2).startswith("Janela movida")
    assert (w.rect[2] - w.rect[0], w.rect[3] - w.rect[1]) == (800, 600)


def test_monitor_da_janela_vem_da_geometria_mesmo_com_handle_que_nao_bate(gerenciador, monkeypatch):
    _usar(monkeypatch, Windows(rect=(2000, 100, 2800, 700)))
    assert gerenciador.numero_monitor_da_janela(1) == 2
    _usar(monkeypatch, Windows(rect=(100, 100, 900, 700)))
    assert gerenciador.numero_monitor_da_janela(1) == 1


def test_janela_entre_dois_monitores_fica_com_o_que_cobre_mais(gerenciador, monkeypatch):
    _usar(monkeypatch, Windows(rect=(1500, 100, 2300, 700)))  # 420 px no 1, 380 no 2
    assert gerenciador.numero_monitor_da_janela(1) == 1


def test_mover_para_outro_monitor_nao_afirma_sucesso_quando_falha(gerenciador, monkeypatch):
    _usar(monkeypatch, Windows(ignorar_primeiros_moves=99))
    monkeypatch.setattr(gerenciador, "_janelas_com_indice", lambda nome: ([{"hwnd": 1, "titulo": "Firefox"}], None, nome))
    resultado = gerenciador.mover_para_outro_monitor("firefox")
    assert resultado.startswith("Não consegui") and "foi colocado" not in resultado
