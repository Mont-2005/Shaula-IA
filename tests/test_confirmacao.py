import ctypes
import threading
import time
from unittest.mock import MagicMock

import pytest

if not hasattr(ctypes, "windll"):
    ctypes.windll = MagicMock()
    ctypes.WinDLL = MagicMock()
    ctypes.WINFUNCTYPE = ctypes.CFUNCTYPE

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from tools.confirmacao import (
    Confirmador,
    ConfirmadorFixo,
    ConfirmadorTerminal,
    PedidoConfirmacao,
    PoliticaConfirmacao,
)
from tools.confirmacao_qt import ConfirmadorQt
from tools.registro import RegistroFerramentas


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


# ---------------- política ----------------

@pytest.mark.parametrize("ferramenta,argumentos", [
    ("desligar_computador", {"segundos": 60}),
    ("desligar_computador", {}),
    ("finalizar_processo", {"alvo": "chrome"}),
    ("fechar_programa", {"nome": "discord"}),
    ("controlar_janela", {"nome": "chrome", "acao": "fechar"}),
    ("controlar_janela", {"nome": "chrome", "acao": "FECHAR"}),
    ("abrir_arquivo", {"caminho": r"C:\Users\x\setup.EXE"}),
    ("abrir_arquivo", {"caminho": "script.ps1"}),
    ("abrir_arquivo", {"caminho": "tarefa.py"}),
])
def test_acoes_sensiveis_pedem_confirmacao(ferramenta, argumentos):
    pedido = PoliticaConfirmacao().avaliar(ferramenta, argumentos)
    assert isinstance(pedido, PedidoConfirmacao)
    assert pedido.ferramenta == ferramenta and pedido.descricao


@pytest.mark.parametrize("ferramenta,argumentos", [
    ("controlar_janela", {"nome": "chrome", "acao": "minimizar"}),
    ("abrir_arquivo", {"caminho": "relatorio.pdf"}),
    ("abrir_arquivo", {"caminho": "foto.png"}),
    ("abrir_programa", {"nome": "firefox"}),
    ("cancelar_desligamento", {}),
    ("calcular", {"expressao": "2+2"}),
    ("tirar_print", {}),
    ("ferramenta_inexistente", {}),
])
def test_acoes_comuns_nao_pedem_confirmacao(ferramenta, argumentos):
    assert PoliticaConfirmacao().avaliar(ferramenta, argumentos) is None


def test_descricoes_dizem_o_que_sera_feito():
    p = PoliticaConfirmacao()
    assert "60 segundo" in p.avaliar("desligar_computador", {"segundos": 60}).descricao
    assert "agora" in p.avaliar("desligar_computador", {"segundos": 0}).descricao
    assert "chrome" in p.avaliar("finalizar_processo", {"alvo": "chrome"}).descricao
    assert "discord" in p.avaliar("fechar_programa", {"nome": "discord"}).descricao


def test_politica_desligada_pela_variavel_de_ambiente():
    assert PoliticaConfirmacao.padrao({}).ativa
    assert PoliticaConfirmacao.padrao({"SHAULA_CONFIRMAR": "1"}).ativa
    desligada = PoliticaConfirmacao.padrao({"SHAULA_CONFIRMAR": "0"})
    assert not desligada.ativa
    assert desligada.avaliar("desligar_computador", {"segundos": 1}) is None


def test_politica_lista_as_ferramentas_cobertas():
    assert PoliticaConfirmacao().ferramentas_cobertas == [
        "abrir_arquivo", "abrir_programa", "controlar_janela",
        "desligar_computador", "fechar_programa", "finalizar_processo"]


# ---------------- registro ----------------

def _registro(confirmador):
    return RegistroFerramentas(
        ferramentas_permitidas={"desligar_computador", "calcular", "abrir_arquivo"},
        confirmador=confirmador)


def test_registro_executa_quando_autorizado(monkeypatch):
    registro = _registro(ConfirmadorFixo(True))
    ferramenta = registro.obter("desligar_computador")
    monkeypatch.setattr(ferramenta, "executar", lambda a: "desligando!")
    assert registro.executar("desligar_computador", {"segundos": 30}) == "desligando!"


def test_registro_nao_executa_quando_negado(monkeypatch):
    confirmador = ConfirmadorFixo(False)
    registro = _registro(confirmador)
    ferramenta = registro.obter("desligar_computador")
    monkeypatch.setattr(ferramenta, "executar", lambda a: pytest.fail("não podia executar"))
    resposta = registro.executar("desligar_computador", {"segundos": 30})
    assert resposta.startswith("Ação cancelada") and "desligar o computador" in resposta
    assert len(confirmador.pedidos) == 1


def test_registro_sem_confirmador_recusa_acao_sensivel(monkeypatch):
    registro = _registro(None)
    ferramenta = registro.obter("desligar_computador")
    monkeypatch.setattr(ferramenta, "executar", lambda a: pytest.fail("não podia executar"))
    assert "exige a confirmação" in registro.executar("desligar_computador", {"segundos": 1})


def test_registro_nao_pergunta_para_acoes_comuns():
    confirmador = ConfirmadorFixo(False)
    registro = _registro(confirmador)
    assert registro.executar("calcular", {"expressao": "2+2"}) == "Resultado: 4"
    assert confirmador.pedidos == []


def test_registro_com_politica_desligada_nao_pergunta(monkeypatch):
    confirmador = ConfirmadorFixo(False)
    registro = RegistroFerramentas(
        ferramentas_permitidas={"desligar_computador"},
        politica_confirmacao=PoliticaConfirmacao(ativa=False),
        confirmador=confirmador)
    ferramenta = registro.obter("desligar_computador")
    monkeypatch.setattr(ferramenta, "executar", lambda a: "ok")
    assert registro.executar("desligar_computador", {"segundos": 1}) == "ok"
    assert confirmador.pedidos == []


def test_erro_no_confirmador_vira_negado(monkeypatch):
    class Quebrado(Confirmador):
        def confirmar(self, pedido):
            raise RuntimeError("falhou")

    registro = _registro(Quebrado())
    ferramenta = registro.obter("desligar_computador")
    monkeypatch.setattr(ferramenta, "executar", lambda a: pytest.fail("não podia executar"))
    assert registro.executar("desligar_computador", {"segundos": 1}).startswith("Ação cancelada")


# ---------------- terminal ----------------

@pytest.mark.parametrize("digitado,esperado", [
    ("s", True), ("SIM", True), (" y ", True), ("n", False), ("", False), ("talvez", False)])
def test_confirmador_terminal(digitado, esperado):
    saida = []
    c = ConfirmadorTerminal(entrada=lambda _p: digitado, saida=saida.append)
    pedido = PedidoConfirmacao("fechar_programa", "Fechar programa?", "fechar o programa 'x'")
    assert c.confirmar(pedido) is esperado
    assert any("Fechar programa?" in str(s) for s in saida)


def test_confirmador_terminal_trata_ctrl_d_como_nao():
    def entrada(_p):
        raise EOFError

    pedido = PedidoConfirmacao("f", "t", "d")
    assert ConfirmadorTerminal(entrada=entrada, saida=lambda _s: None).confirmar(pedido) is False


# ---------------- caixa de diálogo (Qt) ----------------

PEDIDO = PedidoConfirmacao("desligar_computador", "Desligar o computador?", "desligar o computador agora")


def _clicar_quando_aparecer(app, rotulo):
    def tentar():
        caixa = QApplication.activeModalWidget()
        if caixa is None:
            QTimer.singleShot(20, tentar)
            return
        for botao in caixa.buttons():
            if botao.text() == rotulo:
                botao.click()
                return
    QTimer.singleShot(20, tentar)


def _confirmar_em_outra_thread(app, confirmador, pedido=PEDIDO, limite=5):
    resultado = {}

    def trabalhar():
        resultado["valor"] = confirmador.confirmar(pedido)

    t = threading.Thread(target=trabalhar)
    t.start()
    fim = time.time() + limite
    while t.is_alive() and time.time() < fim:
        app.processEvents()
        time.sleep(0.01)
    t.join(0.5)
    return resultado.get("valor", "sem resposta")


def test_instancia_e_um_confirmador(app):
    assert isinstance(ConfirmadorQt(), Confirmador)


def test_caixa_sim_devolve_true_para_a_thread_da_ia(app):
    c = ConfirmadorQt()
    _clicar_quando_aparecer(app, "Sim, autorizar")
    assert _confirmar_em_outra_thread(app, c) is True


def test_caixa_nao_devolve_false(app):
    c = ConfirmadorQt()
    _clicar_quando_aparecer(app, "Não")
    assert _confirmar_em_outra_thread(app, c) is False


def test_caixa_mostra_o_que_sera_feito_e_tem_nao_como_padrao(app):
    c = ConfirmadorQt()
    visto = {}

    def inspecionar():
        caixa = QApplication.activeModalWidget()
        if caixa is None:
            QTimer.singleShot(20, inspecionar)
            return
        visto["texto"] = caixa.text() + " " + caixa.informativeText()
        visto["padrao"] = caixa.defaultButton().text()
        visto["icone"] = caixa.icon()
        visto["estilo"] = caixa.styleSheet()
        caixa.reject()

    QTimer.singleShot(20, inspecionar)
    assert _confirmar_em_outra_thread(app, c) is False
    assert "Desligar o computador?" in visto["texto"]
    assert "desligar o computador agora" in visto["texto"]
    assert visto["padrao"] == "Não" and visto["icone"] == QMessageBox.Warning
    assert "background" in visto["estilo"]


def test_fechar_a_caixa_sem_escolher_e_nao(app):
    c = ConfirmadorQt()

    def fechar():
        caixa = QApplication.activeModalWidget()
        if caixa is None:
            QTimer.singleShot(20, fechar)
            return
        caixa.close()

    QTimer.singleShot(20, fechar)
    assert _confirmar_em_outra_thread(app, c) is False


def test_cancelar_pendentes_nega_e_fecha_a_caixa(app):
    c = ConfirmadorQt()

    def cancelar():
        if QApplication.activeModalWidget() is None:
            QTimer.singleShot(20, cancelar)
            return
        c.cancelar_pendentes()

    QTimer.singleShot(20, cancelar)
    assert _confirmar_em_outra_thread(app, c) is False
    assert QApplication.activeModalWidget() is None


def test_tempo_limite_nega_e_fecha_a_caixa(app, monkeypatch):
    monkeypatch.setattr(ConfirmadorQt, "TEMPO_LIMITE_S", 0.3)
    c = ConfirmadorQt()
    assert _confirmar_em_outra_thread(app, c) is False
    for _ in range(20):
        app.processEvents()
        time.sleep(0.01)
    assert QApplication.activeModalWidget() is None


def test_chamado_da_thread_da_interface_tambem_funciona(app):
    c = ConfirmadorQt()
    _clicar_quando_aparecer(app, "Sim, autorizar")
    assert c.confirmar(PEDIDO) is True


def test_pedidos_em_sequencia_sao_respondidos_um_a_um(app):
    c = ConfirmadorQt()
    _clicar_quando_aparecer(app, "Sim, autorizar")
    assert _confirmar_em_outra_thread(app, c) is True
    _clicar_quando_aparecer(app, "Não")
    assert _confirmar_em_outra_thread(app, c) is False


# --- AtrasoDesligamento ---------------------------------------------------

@pytest.mark.parametrize("valor,segundos", [
    (None, 60), ("", 60), ("abc", 60), (True, 60), (float("inf"), 60),
    (0, 0), ("0", 0), (30, 30), ("45", 45), ("1,5", 1),
])
def test_atraso_desligamento_saneia_o_valor(valor, segundos):
    from tools.confirmacao import AtrasoDesligamento
    assert AtrasoDesligamento(valor).segundos == segundos


def test_atraso_desligamento_descricao_bate_com_a_regra():
    from tools.confirmacao import AtrasoDesligamento, PoliticaConfirmacao
    politica = PoliticaConfirmacao()
    for argumentos in ({}, {"segundos": 0}, {"segundos": "45"}):
        atraso = AtrasoDesligamento(argumentos.get("segundos"))
        pedido = politica.avaliar("desligar_computador", argumentos)
        assert atraso.descricao in pedido.descricao
    assert AtrasoDesligamento(0).imediato
    assert not AtrasoDesligamento(None).imediato


# --- contornos da confirmação de executáveis ------------------------------

@pytest.mark.parametrize("caminho", [
    "C:\\x\\run.bat.",                  # o Windows ignora o ponto final
    "C:\\x\\run.bat ..",
    "C:\\x\\run.exe:Zone.Identifier",   # fluxo alternativo
    "C:\\x\\atalho.url",
    "C:\\x\\painel.cpl",
    "C:\\x\\console.msc",
    "C:\\x\\planilha.xlsm",
    "C:\\x\\RUN.EXE",
])
def test_abrir_arquivo_pede_confirmacao_nos_contornos_conhecidos(caminho):
    assert PoliticaConfirmacao().avaliar("abrir_arquivo", {"caminho": caminho})


@pytest.mark.parametrize("caminho", [
    "C:\\x\\relatorio.pdf", "C:\\x\\foto.png", "C:\\x\\nota.txt.", "C:\\x\\pasta",
])
def test_abrir_arquivo_nao_pergunta_para_documentos(caminho):
    assert PoliticaConfirmacao().avaliar("abrir_arquivo", {"caminho": caminho}) is None


@pytest.mark.parametrize("nome", [
    "C:\\Users\\Public\\evil.exe",
    "\\\\servidor\\pasta\\x.exe",
    "http://exemplo.com/x",
    "script.bat",
    "atalho.lnk",
])
def test_abrir_programa_pede_confirmacao_para_caminho_endereco_e_script(nome):
    pedido = PoliticaConfirmacao().avaliar("abrir_programa", {"nome": nome})
    assert pedido and nome in pedido.descricao


@pytest.mark.parametrize("nome", ["notepad", "firefox", "calc", "chrome.exe", "notepad++", ""])
def test_abrir_programa_pelo_nome_simples_nao_pergunta(nome):
    assert PoliticaConfirmacao().avaliar("abrir_programa", {"nome": nome}) is None
