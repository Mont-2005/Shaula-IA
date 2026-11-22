import threading

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtWidgets import QApplication, QMessageBox

from .confirmacao import Confirmador


class _EsperaResposta:
    """Um pedido aguardando resposta (compartilhado entre threads)."""

    def __init__(self, pedido):

        self.pedido = pedido

        self.evento = threading.Event()

        self.resposta = False


class ConfirmadorQt(QObject):
    """
    Pergunta ao usuário numa caixa de diálogo do Qt, a partir de
    qualquer thread.

    As ferramentas rodam na thread da IA (TrabalhadorIA), mas só a
    thread da interface pode abrir janelas. Então `confirmar()`
    envia o pedido por um sinal, a interface mostra a caixa, e a
    thread da IA espera a resposta. A espera termina com "não" se:

    - o usuário clicar em Não, fechar a caixa ou apertar Esc;
    - a resposta for interrompida (botão ■ / Esc → cancelar_pendentes);
    - a janela for fechada (cancelar_pendentes);
    - passar TEMPO_LIMITE_S sem resposta.

    A resposta padrão é sempre "não".

    Não herda de Confirmador porque a metaclasse do QObject não se
    combina com a ABC; em vez disso é registrado como subclasse
    virtual (isinstance(x, Confirmador) continua verdadeiro).
    """

    TEMPO_LIMITE_S = 120

    # O stylesheet da janela principal pinta TODO QWidget de branco
    # (QWidget { color: #F2F4FF }), mas o fundo de uma QMessageBox
    # continua claro (o do sistema): texto branco sobre fundo claro,
    # ilegível. Por isso a caixa recebe o seu próprio estilo escuro.
    ESTILO_CAIXA = """
        QMessageBox {
            background: #0D1340;
        }
        QMessageBox QLabel {
            color: #F2F4FF;
            font-size: 14px;
        }
        QMessageBox QPushButton {
            background: #1A237E;
            color: #FFFFFF;
            border: 1px solid #283593;
            border-radius: 8px;
            padding: 7px 18px;
            min-width: 120px;
        }
        QMessageBox QPushButton:hover {
            background: #283593;
        }
        QMessageBox QPushButton:default {
            border: 1px solid #9FA8DA;
        }
    """

    _solicitar = Signal(object)

    _fechar_dialogo = Signal()

    def __init__(self, janela_pai=None):

        super().__init__(janela_pai)

        self._janela_pai = janela_pai

        self._pendentes = []

        self._trava = threading.Lock()

        self._dialogo = None

        self._solicitar.connect(
            self._exibir,
            Qt.QueuedConnection
        )

        self._fechar_dialogo.connect(
            self._fechar_agora,
            Qt.QueuedConnection
        )

    # --------------------------------------------------------
    # API (qualquer thread)
    # --------------------------------------------------------

    def confirmar(self, pedido):

        espera = _EsperaResposta(pedido)

        # Chamado da própria thread da interface (ex.: testes ou
        # uso direto): mostra a caixa na hora.
        if QThread.currentThread() is self.thread():

            self._exibir(espera)

            return espera.resposta

        with self._trava:

            self._pendentes.append(espera)

        self._solicitar.emit(espera)

        respondido = espera.evento.wait(self.TEMPO_LIMITE_S)

        with self._trava:

            if espera in self._pendentes:
                self._pendentes.remove(espera)

        if not respondido:

            # Venceu o tempo: marca como negado e pede à interface
            # para fechar a caixa que ainda esteja aberta.
            espera.resposta = False

            espera.evento.set()

            self._fechar_dialogo.emit()

        return espera.resposta

    def cancelar_pendentes(self):
        """
        Nega todos os pedidos em espera e fecha a caixa aberta.
        Deve ser chamado pela thread da interface (interromper a
        resposta, fechar a janela).
        """

        with self._trava:

            pendentes = list(self._pendentes)

        for espera in pendentes:

            espera.resposta = False

            espera.evento.set()

        self._fechar_agora()

    # --------------------------------------------------------
    # THREAD DA INTERFACE
    # --------------------------------------------------------

    @Slot(object)
    def _exibir(self, espera):

        # Cancelado (ou vencido) antes de a caixa chegar a abrir.
        if espera.evento.is_set():
            return

        pedido = espera.pedido

        caixa = QMessageBox(self._janela_pai)

        caixa.setStyleSheet(self.ESTILO_CAIXA)

        caixa.setIcon(QMessageBox.Warning)

        caixa.setWindowTitle("Shaula — confirmar ação")

        caixa.setText(pedido.titulo)

        caixa.setInformativeText(
            f"A Shaula quer {pedido.descricao}.\n\n"
            "Ela só fará isso se você autorizar."
        )

        sim = caixa.addButton(
            "Sim, autorizar",
            QMessageBox.AcceptRole
        )

        nao = caixa.addButton(
            "Não",
            QMessageBox.RejectRole
        )

        caixa.setDefaultButton(nao)

        caixa.setEscapeButton(nao)

        # A confirmação costuma chegar por voz, com a Shaula minimizada
        # ou atrás de outro programa. Sem isto a caixa abria escondida
        # (o Windows não deixa uma janela "roubar" o foco), o usuário
        # nunca a via e a ação expirava em silêncio — daí "só às vezes".
        caixa.setWindowFlag(Qt.WindowStaysOnTopHint, True)

        pai = self._janela_pai

        if pai is not None and pai.isMinimized():
            pai.showNormal()

        self._dialogo = caixa

        caixa.show()

        caixa.raise_()

        caixa.activateWindow()

        QApplication.alert(caixa, 0)

        try:

            caixa.exec()

        finally:

            self._dialogo = None

        # Se algo já respondeu (cancelamento/tempo), isso vale.
        if not espera.evento.is_set():

            espera.resposta = caixa.clickedButton() is sim

        espera.evento.set()

    @Slot()
    def _fechar_agora(self):

        if self._dialogo is not None:

            self._dialogo.reject()


Confirmador.register(ConfirmadorQt)
