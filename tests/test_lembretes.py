import ctypes
import json
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

if not hasattr(ctypes, "windll"):
    ctypes.windll = MagicMock()
    ctypes.WinDLL = MagicMock()
    ctypes.WINFUNCTYPE = ctypes.CFUNCTYPE

from tools import lembretes as modulo_lembretes
from tools.armazenamento import ArmazenamentoJson
from tools.lembretes import GerenciadorLembretes


class NotificadorFalso:
    def __init__(self, sucesso=True):
        self.sucesso = sucesso
        self.avisos = []

    def notificar(self, titulo, texto):
        self.avisos.append((titulo, texto))
        return self.sucesso


def _esperar(condicao, limite=3.0):
    fim = time.time() + limite
    while time.time() < fim:
        if condicao():
            return True
        time.sleep(0.01)
    return condicao()


@pytest.fixture
def arquivo(tmp_path):
    return tmp_path / "lembretes.json"


def _gerenciador(arquivo, notificador=None, **kw):
    notificador = notificador or NotificadorFalso()
    g = GerenciadorLembretes(
        notificador=notificador,
        armazenamento=ArmazenamentoJson(arquivo),
        **kw)
    return g, notificador


def _gravado(arquivo):
    if not arquivo.exists():
        return []
    return json.loads(arquivo.read_text(encoding="utf-8"))


def _escrever(arquivo, itens):
    arquivo.write_text(json.dumps(itens), encoding="utf-8")


@pytest.fixture(autouse=True)
def _entregas_rapidas(monkeypatch):
    monkeypatch.setattr(GerenciadorLembretes, "ATRASO_INICIAL_ENTREGA_S", 0.05)
    monkeypatch.setattr(GerenciadorLembretes, "INTERVALO_ENTRE_ATRASADOS_S", 0.05)


# ---------------- gravação ----------------

def test_criar_grava_o_lembrete_em_disco(arquivo):
    g, _ = _gerenciador(arquivo)
    resposta = g.criar_lembrete("beber água", 10, "minutos")
    assert "#1 criado" in resposta
    dados = _gravado(arquivo)
    assert len(dados) == 1 and dados[0]["id"] == 1 and dados[0]["texto"] == "beber água"
    assert datetime.fromisoformat(dados[0]["disparo_em"]) > datetime.now()


def test_ids_continuam_entre_instancias_e_nao_se_repetem(arquivo):
    a, _ = _gerenciador(arquivo)
    a.criar_lembrete("um", 5, "minutos")
    a.criar_lembrete("dois", 5, "minutos")
    b, _ = _gerenciador(arquivo)
    assert "#3 criado" in b.criar_lembrete("três", 5, "minutos")
    assert [d["id"] for d in _gravado(arquivo)] == [1, 2, 3]


def test_criacao_concorrente_gera_ids_unicos(arquivo):
    g, _ = _gerenciador(arquivo)

    def criar():
        for _ in range(5):
            g.criar_lembrete("x", 10, "minutos")

    ts = [threading.Thread(target=criar) for _ in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    ids = [d["id"] for d in _gravado(arquivo)]
    assert len(ids) == 20 and len(set(ids)) == 20


def test_validacoes_antigas_continuam(arquivo):
    g, _ = _gerenciador(arquivo)
    for tempo in ("nan", "inf", -1, 0, 10**9, "abc"):
        assert "criado" not in g.criar_lembrete("x", tempo, "horas")
    assert "inválida" in g.criar_lembrete("x", 1, "dias")
    assert "o que o lembrete" in g.criar_lembrete("  ", 1, "minutos")
    assert _gravado(arquivo) == []


def test_falha_ao_gravar_avisa_mas_o_lembrete_funciona(tmp_path):
    armazenamento = MagicMock()
    armazenamento.ler.return_value = []
    armazenamento.gravar.return_value = False
    armazenamento.trava = threading.RLock()
    notificador = NotificadorFalso()
    g = GerenciadorLembretes(notificador=notificador, armazenamento=armazenamento)
    resposta = g.criar_lembrete("agora", 0.05, "segundos")
    assert "não consegui gravá-lo em disco" in resposta


# ---------------- disparo ----------------

def test_lembrete_dispara_uma_vez_e_sai_do_arquivo(arquivo):
    g, notificador = _gerenciador(arquivo)
    g.criar_lembrete("hora do café", 0.1, "segundos")
    assert _esperar(lambda: len(notificador.avisos) == 1)
    assert notificador.avisos[0] == ("Shaula — Lembrete", "hora do café")
    assert _esperar(lambda: _gravado(arquivo) == [])
    assert "Não há nenhum" in g.listar_lembretes()


def test_sem_toast_cai_na_caixa_de_mensagem(arquivo, monkeypatch):
    caixa = MagicMock()
    monkeypatch.setattr(modulo_lembretes, "user32", caixa)
    g, _ = _gerenciador(arquivo, NotificadorFalso(sucesso=False))
    g.criar_lembrete("aviso", 0.05, "segundos")
    assert _esperar(lambda: caixa.MessageBoxW.called)


# ---------------- restaurar ao abrir ----------------

def test_lembrete_pendente_volta_a_contar_na_proxima_sessao(arquivo):
    primeira, n1 = _gerenciador(arquivo)
    primeira.criar_lembrete("reunião", 0.4, "segundos")
    # "fecha" a Shaula: os timers da sessão antiga somem com o processo
    for timer in list(primeira._timers.values()):
        timer.cancel()
    segunda, n2 = _gerenciador(arquivo)       # abre de novo
    assert _esperar(lambda: len(n2.avisos) == 1, limite=3)
    assert n2.avisos[0][1] == "reunião"
    assert n1.avisos == []


def test_lembrete_vencido_com_a_shaula_fechada_e_entregue_como_atrasado(arquivo):
    passado = datetime.now() - timedelta(hours=3)
    _escrever(arquivo, [{"id": 1, "texto": "pagar boleto", "disparo_em": passado.isoformat()}])
    g, notificador = _gerenciador(arquivo)
    assert _esperar(lambda: len(notificador.avisos) == 1)
    titulo, texto = notificador.avisos[0]
    assert "atrasado" in titulo
    assert "pagar boleto" in texto and "era para" in texto
    assert _esperar(lambda: _gravado(arquivo) == [])


def test_varios_atrasados_sao_entregues_um_por_vez(arquivo):
    passado = (datetime.now() - timedelta(minutes=5)).isoformat()
    _escrever(arquivo, [
        {"id": i, "texto": f"t{i}", "disparo_em": passado} for i in (1, 2, 3)])
    g, notificador = _gerenciador(arquivo)
    assert _esperar(lambda: len(notificador.avisos) == 3)
    assert sorted(b.split(" —")[0] for _, b in notificador.avisos) == ["t1", "t2", "t3"]


def test_restaurar_false_nao_mexe_em_nada(arquivo):
    passado = (datetime.now() - timedelta(minutes=5)).isoformat()
    _escrever(arquivo, [{"id": 1, "texto": "x", "disparo_em": passado}])
    g, notificador = _gerenciador(arquivo, restaurar=False)
    time.sleep(0.3)
    assert notificador.avisos == [] and len(_gravado(arquivo)) == 1


def test_entradas_invalidas_no_arquivo_sao_ignoradas(arquivo):
    futuro = (datetime.now() + timedelta(minutes=5)).isoformat()
    _escrever(arquivo, [
        {"id": 1, "texto": "ok", "disparo_em": futuro},
        {"texto": "sem id", "disparo_em": futuro},
        {"id": "x", "texto": "id ruim", "disparo_em": futuro},
        {"id": 3, "texto": "data ruim", "disparo_em": "ontem"},
        "lixo", None,
    ])
    g, _ = _gerenciador(arquivo)
    assert "ok" in g.listar_lembretes() and "sem id" not in g.listar_lembretes()


def test_arquivo_corrompido_vira_lista_vazia_e_nao_trava(arquivo):
    arquivo.write_bytes(b"\xff\xfe{{{")
    g, _ = _gerenciador(arquivo)
    assert "Não há nenhum" in g.listar_lembretes()
    assert "#1 criado" in g.criar_lembrete("novo", 5, "minutos")
    arquivo.write_text('{"nao": "lista"}', encoding="utf-8")
    assert "Não há nenhum" in g.listar_lembretes()


# ---------------- várias janelas ----------------

def test_lembrete_nao_e_entregue_duas_vezes_com_duas_janelas(arquivo):
    a, na = _gerenciador(arquivo)
    a.criar_lembrete("compartilhado", 0.3, "segundos")
    b, nb = _gerenciador(arquivo)            # outra janela: também agenda um timer
    assert _esperar(lambda: len(na.avisos) + len(nb.avisos) >= 1)
    time.sleep(0.4)
    assert len(na.avisos) + len(nb.avisos) == 1


def test_despertador_antigo_nao_entrega_lembrete_novo_com_o_mesmo_id(arquivo):
    a, _ = _gerenciador(arquivo, restaurar=False)
    a.criar_lembrete("antigo", 1, "horas")
    b, nb = _gerenciador(arquivo)            # outra janela agenda o despertador do antigo
    a.cancelar_lembrete(1)
    a.criar_lembrete("novo", 2, "horas")     # reaproveita o id 1
    b._disparar(1)                           # o despertador velho da janela b "dispara"
    assert nb.avisos == []                   # antes: entregava "novo" duas horas antes da hora
    assert [e["texto"] for e in _gravado(arquivo)] == ["novo"]
    assert 1 in b._timers                    # e o "novo" continua agendado para a hora certa


def test_listar_e_cancelar_valem_para_todas_as_janelas(arquivo):
    a, na = _gerenciador(arquivo)
    b, nb = _gerenciador(arquivo)
    a.criar_lembrete("da janela A", 0.3, "segundos")
    assert "da janela A" in b.listar_lembretes()
    assert "cancelado" in b.cancelar_lembrete(1)
    time.sleep(0.6)
    assert na.avisos == [] and nb.avisos == []
    assert "Não existe nenhum lembrete #1" in a.cancelar_lembrete(1)


def test_cancelar_valida_o_numero(arquivo):
    g, _ = _gerenciador(arquivo)
    assert "número inteiro" in g.cancelar_lembrete("abc")
    assert "Não existe" in g.cancelar_lembrete(7)


def test_listar_mostra_tempo_restante(arquivo):
    g, _ = _gerenciador(arquivo)
    g.criar_lembrete("daqui a pouco", 2, "minutos")
    texto = g.listar_lembretes()
    assert "#1: 'daqui a pouco'" in texto and "dispara em 1min" in texto


def test_relogio_injetado_define_o_horario_gravado(arquivo):
    fixo = datetime(2030, 1, 1, 12, 0, 0)
    g, _ = _gerenciador(arquivo, relogio=lambda: fixo, restaurar=False)
    g.criar_lembrete("ano novo", 90, "minutos")
    assert _gravado(arquivo)[0]["disparo_em"] == "2030-01-01T13:30:00"
    assert "dispara em 90min 0s" in g.listar_lembretes()
