"""
Menu principal da Shaula (barra de menus da janela).

Dá acesso, pela interface, a todas as funcionalidades e a todos os
"modelos" do app: conversas, anexos, lembretes, processos, janelas e
monitores, capturas de tela, rede, internet, calculadora, área de
transferência, esforço e voz.

Organização orientada a objetos:

  Catálogo (padrão Composite)
      ItemMenu            base abstrata de tudo o que aparece num menu
        Separador         linha separadora
        ItemFerramenta    executa uma ferramenta do RegistroFerramentas
          ItemPeloChat    (abstrata) ferramentas que dependem do modelo
            ItemPesquisaInternet
            ItemAnalisarTela
        Submenu           agrupa outros itens (inclusive outros submenus)
      CatalogoMenu        define o que há em cada menu

  Formulário gerado do esquema da ferramenta (Factory + polimorfismo)
      CampoParametro      base abstrata de um campo
        CampoTexto > CampoInteiro, CampoNumero
        CampoMatriz
        CampoOpcoes > CampoBooleano
      FabricaDeCampos     escolhe o campo certo para cada parâmetro
      DialogoParametros   monta o formulário e valida os valores
      LeitorMatriz        converte o texto digitado em matriz

  Execução
      ExecutorMenu        executa um item (diálogo, thread ou chat)
      TrabalhadorFerramenta  thread que chama RegistroFerramentas

  Montagem da barra
      MenuPrincipal       monta a barra e liga os itens à janela
      SubmenuDinamico     base de submenus preenchidos ao abrir
        SubmenuConversas, SubmenuEsforco
      AcoesDaConversaAtual  renomear, fixar e apagar a conversa atual
      DialogoFerramentas  lista das ferramentas (Ajuda)

As ferramentas (as mesmas 40 que o modelo pode chamar) são lidas do
RegistroFerramentas e executadas por ele — por isso as confirmações de
ações sensíveis continuam valendo. Só as ferramentas que precisam do
modelo (pesquisa na internet e análise de tela) seguem pelo chat.
"""

import json
import re
from abc import ABC, abstractmethod

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
)

from tools.esforco import CatalogoEsforco


# Atualize junto com o README / a documentação.
VERSAO_SHAULA = "4.75"


ESTILO_BARRA = """
    QMenuBar {
        background: #0B1136;
        color: #F2F4FF;
        border-bottom: 1px solid #151B55;
        padding: 2px 4px;
    }

    QMenuBar::item {
        background: transparent;
        padding: 5px 8px;
        border-radius: 6px;
    }

    QMenuBar::item:selected {
        background: #283593;
    }

    QMenuBar::item:pressed {
        background: #1A237E;
    }
"""

ESTILO_DIALOGO = """
    QDialog { background: #0B1136; }
    QLabel { color: #F2F4FF; }
    QLineEdit, QPlainTextEdit, QComboBox {
        background: #111743;
        color: #F2F4FF;
        border: 1px solid #283593;
        border-radius: 6px;
        padding: 5px;
    }
    QComboBox QAbstractItemView {
        background: #111743;
        color: #F2F4FF;
        selection-background-color: #283593;
    }
    QPushButton {
        background: #1A237E;
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        padding: 7px 16px;
    }
    QPushButton:hover { background: #283593; }
"""


# ============================================================
# LEITURA DE MATRIZES
# ============================================================

class LeitorMatriz:
    """
    Converte o texto digitado numa matriz (lista de listas de números).

    Aceita duas formas:
      - JSON:    [[1, 2], [3, 4]]
      - linhas:  uma linha da matriz por linha (ou separadas por ';'),
                 com os valores separados por espaço ou vírgula:
                     1 2
                     3 4

    Levanta ValueError com uma mensagem clara se o texto não formar uma
    matriz retangular de números.
    """

    @classmethod
    def ler(cls, texto):

        texto = (texto or "").strip()

        if not texto:

            raise ValueError("Informe a matriz.")

        if texto.startswith("["):

            dados = cls._ler_json(texto)

        else:

            dados = cls._ler_linhas(texto)

        cls._validar(dados)

        return dados

    @staticmethod
    def _numero(texto):
        """'3' -> 3, '2.5' -> 2.5. Levanta ValueError se não for número."""

        valor = float(texto)

        if (
            valor.is_integer()
            and "." not in texto
            and "e" not in texto.lower()
        ):

            return int(valor)

        return valor

    @staticmethod
    def _ler_json(texto):

        try:

            return json.loads(texto)

        except json.JSONDecodeError:

            raise ValueError(
                "Formato inválido. Exemplo: [[1, 2], [3, 4]]"
            )

    @classmethod
    def _ler_linhas(cls, texto):

        linhas = [
            linha
            for linha in re.split(r"[\n;]+", texto)
            if linha.strip()
        ]

        try:

            return [
                [
                    cls._numero(valor)
                    for valor in re.split(r"[\s,]+", linha.strip())
                    if valor
                ]
                for linha in linhas
            ]

        except ValueError:

            raise ValueError(
                "A matriz só pode ter números (use ponto nos decimais)."
            )

    @staticmethod
    def _validar(dados):

        if (
            not isinstance(dados, list)
            or not dados
            or not all(
                isinstance(linha, list) and linha
                for linha in dados
            )
        ):

            raise ValueError("A matriz precisa ter ao menos uma linha.")

        for linha in dados:

            for valor in linha:

                if isinstance(valor, bool) or not isinstance(
                    valor, (int, float)
                ):

                    raise ValueError("A matriz só pode ter números.")

        if len({len(linha) for linha in dados}) != 1:

            raise ValueError(
                "Todas as linhas precisam ter o mesmo número de valores."
            )


# ============================================================
# CAMPOS DO FORMULÁRIO (polimorfismo)
# ============================================================

# Valor devolvido por um campo opcional deixado em branco: o parâmetro
# simplesmente não é enviado e a ferramenta usa o padrão dela.
AUSENTE = object()


class CampoParametro(ABC):
    """
    Um campo do formulário, ligado a um parâmetro de uma ferramenta.

    valor() é um template method: lê o que foi digitado, trata o campo
    vazio (erro se obrigatório, AUSENTE se opcional) e delega a
    conversão ao campo concreto.
    """

    ROTULOS = {
        "nome": "Nome",
        "unidade": "Unidade (ex.: C:)",
        "caminho": "Caminho do arquivo",
        "expressao": "Expressão",
        "a": "Matriz A",
        "b": "Matriz B",
        "escalar": "Número (escalar)",
        "potencia": "Potência (inteiro)",
        "valor": "Valor",
        "base_origem": "Base de origem",
        "base_destino": "Base de destino",
        "segundos": "Tempo até desligar (segundos)",
        "atraso": "Atraso (segundos)",
        "host": "Endereço (ex.: google.com)",
        "consulta": "O que pesquisar",
        "monitor": "Monitor (número)",
        "todos": "Todos os monitores",
        "destino": "Destino da captura",
        "acao": "Ação",
        "texto": "Texto",
        "tempo": "Tempo",
        "id_lembrete": "Número do lembrete",
        "ordenar_por": "Ordenar por",
        "limite": "Quantidade de processos",
        "alvo": "Processo (nome ou PID)",
    }

    DICAS = {
        "a": "Uma linha da matriz por linha, valores separados por "
             "espaço. Ex.:\n2 1\n3 4",
        "b": "Uma linha da matriz por linha, valores separados por "
             "espaço. Ex.:\n2 1\n3 4",
    }

    def __init__(self, chave, esquema, obrigatorio):

        self.chave = chave

        self.esquema = esquema

        self.obrigatorio = obrigatorio

        self.rotulo = self.ROTULOS.get(
            chave,
            chave.replace("_", " ").capitalize()
        )

        if not obrigatorio:
            self.rotulo += " (opcional)"

        self.widget = self._criar_widget()

        dica = self.DICAS.get(chave) or esquema.get("description")

        if dica:
            self.widget.setToolTip(dica)

    @abstractmethod
    def _criar_widget(self):
        """Cria o widget Qt que recebe o valor."""

    @abstractmethod
    def _ler_texto(self):
        """Devolve o que foi digitado (vazio = não preenchido)."""

    @abstractmethod
    def _converter(self, texto):
        """Converte o texto no valor do parâmetro (ValueError se inválido)."""

    def valor(self):

        texto = self._ler_texto()

        if not texto:

            if self.obrigatorio:
                raise ValueError(f"Preencha \"{self.rotulo}\".")

            return AUSENTE

        return self._converter(texto)


class CampoTexto(CampoParametro):

    def _criar_widget(self):

        return QLineEdit()

    def _ler_texto(self):

        return self.widget.text().strip()

    def _converter(self, texto):

        return texto


class CampoInteiro(CampoTexto):

    def _converter(self, texto):

        try:

            return int(texto)

        except ValueError:

            raise ValueError(
                f"\"{self.rotulo}\" precisa ser um número inteiro."
            )


class CampoNumero(CampoTexto):

    def _converter(self, texto):

        try:

            numero = float(texto.replace(",", "."))

        except ValueError:

            raise ValueError(f"\"{self.rotulo}\" precisa ser um número.")

        return int(numero) if numero.is_integer() else numero


class CampoMatriz(CampoParametro):

    def _criar_widget(self):

        campo = QPlainTextEdit()

        campo.setPlaceholderText("2 1\n3 4")

        campo.setFixedHeight(90)

        return campo

    def _ler_texto(self):

        return self.widget.toPlainText().strip()

    def _converter(self, texto):

        try:

            return LeitorMatriz.ler(texto)

        except ValueError as erro:

            raise ValueError(f"{self.rotulo}: {erro}")


class CampoOpcoes(CampoParametro):
    """Lista de opções fixas (enum do esquema)."""

    def _opcoes(self):

        return [(str(opcao), opcao) for opcao in self.esquema["enum"]]

    def _criar_widget(self):

        combo = QComboBox()

        if not self.obrigatorio:
            combo.addItem("(padrão)", None)

        for texto, dado in self._opcoes():
            combo.addItem(texto, dado)

        return combo

    def valor(self):

        dado = self.widget.currentData()

        return AUSENTE if dado is None else dado

    def _ler_texto(self):

        return self.widget.currentText()

    def _converter(self, texto):

        return self.widget.currentData()


class CampoBooleano(CampoOpcoes):
    """Sim/Não; opcional começa em (padrão) e não é enviado."""

    def _opcoes(self):

        return [("Sim", True), ("Não", False)]


class FabricaDeCampos:
    """Escolhe o campo certo para o esquema de cada parâmetro."""

    @staticmethod
    def criar(chave, esquema, obrigatorio):

        tipo = esquema.get("type", "string")

        if esquema.get("enum"):
            classe = CampoOpcoes

        elif tipo == "boolean":
            classe = CampoBooleano

        elif tipo == "array":
            classe = CampoMatriz

        elif tipo == "integer":
            classe = CampoInteiro

        elif tipo == "number":
            classe = CampoNumero

        else:
            classe = CampoTexto

        return classe(chave, esquema, obrigatorio)


# ============================================================
# DIÁLOGO DE PARÂMETROS
# ============================================================

class DialogoParametros(QDialog):
    """
    Formulário montado a partir do esquema JSON de uma ferramenta (o
    mesmo que o Ollama recebe). Cada parâmetro vira um CampoParametro.
    """

    def __init__(self, titulo, parametros, campos=None, pai=None):

        super().__init__(pai)

        self.setWindowTitle(titulo)

        self.setMinimumWidth(420)

        self.setStyleSheet(ESTILO_DIALOGO)

        obrigatorios = set(parametros.get("required", []))

        self._campos = {}

        formulario = QFormLayout()

        for chave, esquema in parametros.get("properties", {}).items():

            if campos is not None and chave not in campos:
                continue

            campo = FabricaDeCampos.criar(
                chave,
                esquema,
                chave in obrigatorios
            )

            self._campos[chave] = campo

            formulario.addRow(campo.rotulo + ":", campo.widget)

        self._rotulo_erro = QLabel("")

        self._rotulo_erro.setStyleSheet("color: #EF9A9A;")

        self._rotulo_erro.setWordWrap(True)

        botoes = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )

        botoes.button(QDialogButtonBox.Ok).setText("Executar")

        botoes.button(QDialogButtonBox.Cancel).setText("Cancelar")

        botoes.accepted.connect(self._validar)

        botoes.rejected.connect(self.reject)

        layout = QVBoxLayout(self)

        layout.addLayout(formulario)

        layout.addWidget(self._rotulo_erro)

        layout.addWidget(botoes)

        self._argumentos = {}

    def _coletar(self):

        argumentos = {}

        for chave, campo in self._campos.items():

            valor = campo.valor()

            if valor is not AUSENTE:
                argumentos[chave] = valor

        return argumentos

    def _validar(self):

        try:

            self._argumentos = self._coletar()

        except ValueError as erro:

            self._rotulo_erro.setText(str(erro))

            return

        self.accept()

    def argumentos(self):

        return dict(self._argumentos)


# ============================================================
# EXECUÇÃO EM THREAD
# ============================================================

class TrabalhadorFerramenta(QThread):
    """
    Executa uma ferramenta pelo RegistroFerramentas fora da thread da
    interface (a mesma ideia do TrabalhadorIA, mas sem o modelo).
    Expõe interromper() para ser tratado como o TrabalhadorIA pelo
    código de fechamento da janela.
    """

    concluido = Signal(str)

    def __init__(self, registro, nome, argumentos):

        super().__init__()

        self._registro = registro

        self._nome = nome

        self._argumentos = argumentos

    def interromper(self):
        """Uma ferramenta já iniciada não pode ser interrompida."""

    def run(self):

        try:

            resultado = self._registro.executar(
                self._nome,
                self._argumentos
            )

        except Exception as erro:

            self.concluido.emit(
                f"Erro ao executar '{self._nome}': {erro}"
            )

            return

        self.concluido.emit(str(resultado))


# ============================================================
# CATÁLOGO DO MENU (Composite)
# ============================================================

class ItemMenu(ABC):
    """Tudo o que pode aparecer dentro de um menu."""

    @abstractmethod
    def adicionar_em(self, menu, menu_principal):
        """Cria as ações Qt deste item dentro de 'menu'."""

    @abstractmethod
    def nomes_de_ferramentas(self):
        """Conjunto das ferramentas do registro que este item alcança."""


class Separador(ItemMenu):

    def adicionar_em(self, menu, menu_principal):

        menu.addSeparator()

    def nomes_de_ferramentas(self):

        return set()


class ItemFerramenta(ItemMenu):
    """Um item de menu ligado a uma ferramenta do registro."""

    def __init__(self, nome, rotulo, campos=None):
        """
        campos: restringe quais parâmetros aparecem no diálogo.
        """

        self.nome = nome

        self.rotulo = rotulo

        self.campos = campos

    @property
    def rotulo_limpo(self):

        return self.rotulo.rstrip("…").strip()

    def adicionar_em(self, menu, menu_principal):

        if not menu_principal.tem_ferramenta(self.nome):
            return

        menu_principal.criar_acao(
            menu,
            self.rotulo,
            lambda: menu_principal.executor.acionar(self)
        )

    def nomes_de_ferramentas(self):

        return {self.nome}

    def executar(self, executor, argumentos):
        """Executa direto, em thread, sem passar pelo modelo."""

        executor.executar_em_thread(self, argumentos)


class ItemPeloChat(ItemFerramenta, ABC):
    """
    Ferramenta que depende do modelo: em vez de executar direto, monta
    uma frase e a envia pelo mesmo fluxo da mensagem digitada.
    """

    @abstractmethod
    def montar_texto(self, argumentos):
        """Frase enviada ao chat."""

    def executar(self, executor, argumentos):

        executor.enviar_pelo_chat(self.montar_texto(argumentos))


class ItemPesquisaInternet(ItemPeloChat):

    def __init__(self):

        super().__init__("pesquisar_internet", "Pesquisar na internet…")

    def montar_texto(self, argumentos):

        return f"Pesquise na internet: {argumentos['consulta']}"


class ItemAnalisarTela(ItemPeloChat):

    def __init__(self):

        super().__init__(
            "analisar_tela",
            "Analisar a tela…",
            campos=["monitor"]
        )

    def montar_texto(self, argumentos):

        monitor = argumentos.get("monitor")

        if monitor:
            return f"O que tem na tela do monitor {monitor}?"

        return "O que tem na minha tela?"


class Submenu(ItemMenu):
    """Agrupa outros itens (Composite). Também serve de menu da barra."""

    def __init__(self, rotulo, itens):

        self.rotulo = rotulo

        self.itens = itens

    def preencher(self, menu, menu_principal):

        for item in self.itens:
            item.adicionar_em(menu, menu_principal)

    def adicionar_em(self, menu, menu_principal):

        self.preencher(menu.addMenu(self.rotulo), menu_principal)

    def nomes_de_ferramentas(self):

        nomes = set()

        for item in self.itens:
            nomes |= item.nomes_de_ferramentas()

        return nomes


class CatalogoMenu:
    """Define em qual menu fica cada ferramenta."""

    # Cobertas pela chave "Internet ligada" (alternar_internet).
    FERRAMENTAS_DO_LIGA_DESLIGA = ("ativar_internet", "desativar_internet")

    def menus(self):
        """Menus montados a partir das ferramentas (entre Conversas e Rede)."""

        F = ItemFerramenta

        return [
            Submenu("&Programas e arquivos", [
                F("abrir_programa", "Abrir programa…"),
                F("fechar_programa", "Fechar programa…"),
                F("abrir_menu_iniciar", "Abrir o menu Iniciar"),
                Separador(),
                F("buscar_arquivo", "Buscar arquivo…"),
                F("abrir_arquivo", "Abrir arquivo…"),
            ]),
            Submenu("&Calculadora", [
                F("calcular", "Calcular expressão…"),
                F("converter_base", "Converter entre bases…"),
                Separador(),
                Submenu("Matrizes", [
                    F("matriz_soma", "Soma…"),
                    F("matriz_subtracao", "Subtração…"),
                    F("matriz_multiplicacao", "Multiplicação…"),
                    F("matriz_escalar", "Multiplicar por escalar…"),
                    F("matriz_transposta", "Transposta…"),
                    F("matriz_determinante", "Determinante…"),
                    F("matriz_inversa", "Inversa…"),
                    F("matriz_potencia", "Potência…"),
                ]),
            ]),
            Submenu("&Lembretes", [
                F("criar_lembrete", "Criar lembrete…"),
                F("listar_lembretes", "Listar lembretes"),
                F("cancelar_lembrete", "Cancelar lembrete…"),
            ]),
            Submenu("&Janelas e telas", [
                F("listar_monitores", "Listar monitores"),
                F("listar_janelas_abertas", "Listar janelas abertas"),
                F("controlar_janela", "Controlar janela…"),
                F("mover_programa_monitor", "Mover programa para um monitor…"),
                F("mover_para_outro_monitor", "Mover programa para outro monitor…"),
                Separador(),
                F("tirar_print", "Tirar print…"),
                ItemAnalisarTela(),
            ]),
            Submenu("&Sistema", [
                F("informacoes_hardware", "Informações do hardware"),
                Separador(),
                F("listar_processos", "Listar processos…"),
                F("listar_processos_protegidos", "Listar processos protegidos"),
                F("finalizar_processo", "Finalizar processo…"),
                Separador(),
                F("bloquear_tela", "Bloquear a tela…"),
                F("desligar_computador", "Desligar o computador…"),
                F("cancelar_desligamento", "Cancelar desligamento"),
                Separador(),
                F("copiar_texto", "Copiar texto para a área de transferência…"),
                F("colar_texto", "Colar da área de transferência"),
            ]),
        ]

    def menu_rede(self):
        """Itens do menu Rede e internet (o liga/desliga é à parte)."""

        F = ItemFerramenta

        return Submenu("&Rede e internet", [
            ItemPesquisaInternet(),
            Separador(),
            F("obter_ip_local", "Meu endereço IP local"),
            F("verificar_wifi", "Verificar Wi-Fi"),
            F("testar_ping", "Testar ping…"),
        ])

    def nomes_cobertos(self):
        """Todas as ferramentas que o menu alcança."""

        nomes = set(self.FERRAMENTAS_DO_LIGA_DESLIGA)

        for menu in self.menus():
            nomes |= menu.nomes_de_ferramentas()

        nomes |= self.menu_rede().nomes_de_ferramentas()

        return nomes


# ============================================================
# EXECUÇÃO DE UM ITEM
# ============================================================

class ExecutorMenu:
    """
    Executa o item de menu escolhido: confere se a Shaula está livre,
    abre o diálogo de parâmetros, e entrega a execução ao próprio item
    (direto, em thread, ou pelo chat).
    """

    def __init__(self, janela):

        self.janela = janela

    def ocupada(self):
        """True (e avisa) se a Shaula está fazendo outra coisa."""

        j = self.janela

        if j.encerrando:
            return True

        if (
            j._ia_ocupada()
            or (j.trabalhador is not None and j.trabalhador.isRunning())
        ):

            QMessageBox.information(
                j,
                "Shaula",
                "Espere a Shaula terminar o que está fazendo antes "
                "de usar o menu."
            )

            return True

        if j._fase_voz is not None:

            QMessageBox.information(
                j,
                "Shaula",
                "Termine a gravação de voz (Ctrl+M) antes de usar o menu."
            )

            return True

        return False

    def acionar(self, item):

        j = self.janela

        ferramenta = j.registro.obter(item.nome)

        if ferramenta is None or self.ocupada():
            return

        propriedades = ferramenta.parametros.get("properties", {})

        visiveis = [
            chave
            for chave in propriedades
            if item.campos is None or chave in item.campos
        ]

        argumentos = {}

        if visiveis:

            dialogo = DialogoParametros(
                item.rotulo_limpo,
                ferramenta.parametros,
                item.campos,
                j
            )

            if dialogo.exec() != QDialog.Accepted:
                return

            argumentos = dialogo.argumentos()

        item.executar(self, argumentos)

    def enviar_pelo_chat(self, texto):
        """Manda o texto como se o usuário o tivesse digitado."""

        j = self.janela

        if j.anexos_pendentes:

            QMessageBox.information(
                j,
                "Shaula",
                "Remova os anexos pendentes antes: esta ação usa o "
                "modelo sem anexos."
            )

            return

        anterior = j.entrada.toPlainText()

        j.entrada.setPlainText(texto)

        j.enviar()

        if anterior:
            j.entrada.setPlainText(anterior)

    @staticmethod
    def texto_do_pedido(item, argumentos):

        texto = f"[Menu] {item.rotulo_limpo}"

        for chave, valor in argumentos.items():

            if isinstance(valor, list):
                valor = json.dumps(valor)

            texto += f"\n{chave}: {valor}"

        return texto

    def executar_em_thread(self, item, argumentos):

        j = self.janela

        texto = self.texto_do_pedido(item, argumentos)

        primeira = len(j.historico.mensagens) == 1

        j.adicionar_mensagem("Você", texto)

        j.historico.adicionar("user", texto)

        if primeira:

            j.gerenciador_conversas.atualizar_titulo_automatico(
                j.id_conversa_atual,
                item.rotulo_limpo
            )

            j.atualizar_lista_conversas()

        j.status.setText(f"● Executando: {item.rotulo_limpo}...")

        trabalhador = TrabalhadorFerramenta(
            j.registro,
            item.nome,
            argumentos
        )

        trabalhador.concluido.connect(self._ao_concluir)

        # Como o TrabalhadorIA, fica em janela.trabalhador: assim o
        # resto da janela (enviar, trocar/apagar conversa, fechar)
        # já espera a ferramenta terminar.
        j.trabalhador = trabalhador

        trabalhador.start()

    def _ao_concluir(self, resultado):

        j = self.janela

        if j.encerrando:
            return

        j.status.setText(j.texto_status_padrao())

        j.receber_resposta(resultado)

        j.entrada.setFocus()


# ============================================================
# SUBMENUS PREENCHIDOS AO ABRIR
# ============================================================

class SubmenuDinamico(ABC):
    """Submenu cujo conteúdo é refeito toda vez que ele é aberto."""

    def __init__(self, janela):

        self.janela = janela

        self.menu = None

    def instalar_em(self, menu_pai, titulo):

        self.menu = menu_pai.addMenu(titulo)

        self.menu.aboutToShow.connect(self.preencher)

    @abstractmethod
    def preencher(self):
        """Refaz as ações do submenu."""


class SubmenuConversas(SubmenuDinamico):
    """'Ir para a conversa': lista todas, marcando a atual."""

    def preencher(self):

        j = self.janela

        self.menu.clear()

        conversas = j.gerenciador_conversas.listar_conversas()

        for entrada in conversas:

            titulo = entrada["titulo"].replace("&", "&&")

            if entrada.get("fixado"):
                titulo = "📌 " + titulo

            acao = self.menu.addAction(titulo)

            acao.setCheckable(True)

            acao.setChecked(entrada["id"] == j.id_conversa_atual)

            acao.triggered.connect(
                lambda *_, id_conversa=entrada["id"]:
                self.ir_para(id_conversa)
            )

        if not conversas:

            self.menu.addAction("(nenhuma conversa)").setEnabled(False)

    def ir_para(self, id_conversa):

        lista = self.janela.lista_conversas

        for indice in range(lista.count()):

            item = lista.item(indice)

            if item.data(Qt.UserRole) == id_conversa:

                self.janela.selecionar_conversa(item)

                return


class SubmenuEsforco(SubmenuDinamico):
    """'Nível de esforço': um item por perfil, o atual marcado."""

    def __init__(self, janela):

        super().__init__(janela)

        self._grupo = None

    def preencher(self):

        j = self.janela

        self.menu.clear()

        self._grupo = QActionGroup(self.menu)

        self._grupo.setExclusive(True)

        atual = j.estado_esforco.perfil

        for perfil in CatalogoEsforco.listar():

            rotulo = perfil.nome

            if perfil.recomendado:
                rotulo += "   (Recomendado)"

            if perfil.aviso:
                rotulo += "   ⚠ mais pesado"

            acao = QAction(rotulo, self.menu)

            acao.setCheckable(True)

            acao.setChecked(perfil.chave == atual.chave)

            acao.setToolTip(f"{perfil.descricao}\n{perfil.resumo}")

            acao.triggered.connect(
                lambda *_, chave=perfil.chave: j.definir_esforco(chave)
            )

            self._grupo.addAction(acao)

            self.menu.addAction(acao)


class AcoesDaConversaAtual:
    """Renomear, fixar e apagar a conversa que está aberta."""

    def __init__(self, janela):

        self.janela = janela

    def entrada(self):

        return self.janela.gerenciador_conversas.obter_entrada(
            self.janela.id_conversa_atual
        )

    def esta_fixada(self):

        entrada = self.entrada()

        return bool(entrada and entrada.get("fixado"))

    def renomear(self):

        entrada = self.entrada()

        if entrada is None:
            return

        self.janela.renomear_conversa_ui(
            self.janela.id_conversa_atual,
            entrada["titulo"]
        )

    def alternar_fixacao(self):

        j = self.janela

        j.gerenciador_conversas.alternar_fixado(j.id_conversa_atual)

        j.atualizar_lista_conversas()

    def apagar(self):

        entrada = self.entrada()

        if entrada is None:
            return

        self.janela.apagar_conversa_ui(
            self.janela.id_conversa_atual,
            entrada["titulo"]
        )


# ============================================================
# AJUDA
# ============================================================

class DialogoFerramentas(QDialog):
    """Lista, gerada a partir do registro, de todas as ferramentas."""

    def __init__(self, ferramentas, pai=None):

        super().__init__(pai)

        self.setWindowTitle(
            f"Ferramentas disponíveis ({len(ferramentas)})"
        )

        self.resize(640, 520)

        self.setStyleSheet(ESTILO_DIALOGO)

        texto = QPlainTextEdit()

        texto.setReadOnly(True)

        texto.setPlainText(
            "\n\n".join(
                f"{f.nome}\n    {f.descricao}"
                for f in ferramentas
            )
        )

        layout = QVBoxLayout(self)

        layout.addWidget(texto)


# ============================================================
# MENU PRINCIPAL
# ============================================================

class MenuPrincipal:
    """
    Instala a barra de menus numa ShaulaWindow. Usa só a API pública
    da janela (criar_nova_conversa, abrir_dialogo_anexo, registro,
    gerenciador_conversas etc.) e delega a execução dos itens ao
    ExecutorMenu.
    """

    def __init__(self, janela):

        self.janela = janela

        self.catalogo = CatalogoMenu()

        self.executor = ExecutorMenu(janela)

        self.acoes_da_conversa = AcoesDaConversaAtual(janela)

        self.submenu_conversas = SubmenuConversas(janela)

        self.submenu_esforco = SubmenuEsforco(janela)

        self._acao_internet = None

        self._acao_fixar = None

    # --------------------------------------------------------
    # API usada pelos itens do catálogo
    # --------------------------------------------------------

    def tem_ferramenta(self, nome):

        return self.janela.registro.obter(nome) is not None

    def criar_acao(self, menu, texto, funcao, atalho=None, marcavel=False):

        acao = QAction(texto, menu)

        if atalho:
            acao.setShortcut(QKeySequence(atalho))

        if marcavel:
            acao.setCheckable(True)

        acao.triggered.connect(lambda *_: funcao())

        menu.addAction(acao)

        return acao

    # --------------------------------------------------------
    # MONTAGEM
    # --------------------------------------------------------

    def instalar(self):

        barra = self.janela.menuBar()

        barra.setStyleSheet(ESTILO_BARRA)

        self._montar_arquivo(barra)

        self._montar_conversas(barra)

        for grupo in self.catalogo.menus():

            grupo.preencher(barra.addMenu(grupo.rotulo), self)

        self._montar_rede(barra)

        self._montar_configuracoes(barra)

        self._montar_ajuda(barra)

    def _montar_arquivo(self, barra):

        j = self.janela

        menu = barra.addMenu("&Arquivo")

        self.criar_acao(menu, "Nova conversa", j.criar_nova_conversa, "Ctrl+N")

        self.criar_acao(
            menu,
            "Abrir esta conversa em nova janela",
            lambda: j.abrir_conversa_em_nova_janela(j.id_conversa_atual)
        )

        menu.addSeparator()

        self.criar_acao(
            menu,
            "Anexar arquivo…",
            j.abrir_dialogo_anexo,
            "Ctrl+O"
        )

        menu.addSeparator()

        self.criar_acao(menu, "Sair da Shaula", j.fechar_shaula, "Ctrl+Q")

    def _montar_conversas(self, barra):

        j = self.janela

        acoes = self.acoes_da_conversa

        menu = barra.addMenu("&Conversas")

        self.submenu_conversas.instalar_em(menu, "Ir para a conversa")

        menu.addSeparator()

        self.criar_acao(menu, "Renomear conversa atual…", acoes.renomear)

        self._acao_fixar = self.criar_acao(
            menu,
            "Fixar conversa atual",
            acoes.alternar_fixacao
        )

        self.criar_acao(menu, "Apagar conversa atual…", acoes.apagar)

        menu.aboutToShow.connect(self._atualizar_texto_fixar)

        menu.addSeparator()

        self.criar_acao(
            menu,
            "Mostrar/ocultar barra lateral",
            j.alternar_barra_lateral,
            "Ctrl+B"
        )

    def _atualizar_texto_fixar(self):

        self._acao_fixar.setText(
            "Desafixar conversa atual"
            if self.acoes_da_conversa.esta_fixada()
            else "Fixar conversa atual"
        )

    def _montar_rede(self, barra):

        j = self.janela

        rede = self.catalogo.menu_rede()

        menu = barra.addMenu(rede.rotulo)

        self._acao_internet = self.criar_acao(
            menu,
            "Internet ligada",
            j.alternar_internet,
            marcavel=True
        )

        menu.aboutToShow.connect(
            lambda: self._acao_internet.setChecked(
                bool(j.registro.estado_internet.ativa)
            )
        )

        menu.addSeparator()

        rede.preencher(menu, self)

    def _montar_configuracoes(self, barra):

        j = self.janela

        menu = barra.addMenu("Con&figurações")

        self.submenu_esforco.instalar_em(menu, "Nível de esforço")

        menu.addSeparator()

        # O atalho Ctrl+M já pertence à janela (QShortcut); aqui só
        # aparece no texto, para não haver atalho ambíguo.
        self.criar_acao(
            menu,
            "Falar um comando (Ctrl+M)",
            j.alternar_escuta
        )

    def _montar_ajuda(self, barra):

        menu = barra.addMenu("A&juda")

        self.criar_acao(
            menu,
            "Ferramentas disponíveis",
            self._mostrar_ferramentas
        )

        self.criar_acao(menu, "Sobre a Shaula", self._mostrar_sobre)

    def _mostrar_ferramentas(self):

        DialogoFerramentas(list(self.janela.registro), self.janela).exec()

    def _mostrar_sobre(self):

        QMessageBox.about(
            self.janela,
            "Sobre a Shaula",
            f"<b>Shaula IA {VERSAO_SHAULA}</b><br><br>"
            "Assistente pessoal local para Windows, feita com "
            "PySide6 e Ollama (modelo qwen3.5:9b). Tudo é processado "
            "no seu computador."
        )
