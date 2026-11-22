"""
Menu principal da Shaula (barra de menus da janela).

Dá acesso, pela interface, a todas as funcionalidades e a todos os
"modelos" do app: conversas, anexos, lembretes, processos, janelas e
monitores, capturas de tela, rede, internet, calculadora, área de
transferência, esforço e voz.

As ferramentas (as mesmas 40 que o modelo pode chamar) são lidas do
RegistroFerramentas. Cada item de menu abre, quando preciso, um diálogo
montado a partir do esquema de parâmetros da ferramenta e executa a
ferramenta numa thread própria, pelo mesmo RegistroFerramentas — por
isso as confirmações de ações sensíveis continuam valendo. Só as
ferramentas que precisam do modelo (pesquisa na internet e análise de
tela) seguem pelo chat.
"""

import json
import re

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
VERSAO_SHAULA = "4.70"


# ============================================================
# LEITURA DE MATRIZES
# ============================================================

def _numero(texto):
    """'3' -> 3, '2.5' -> 2.5. Levanta ValueError se não for número."""

    valor = float(texto)

    if valor.is_integer() and "." not in texto and "e" not in texto.lower():
        return int(valor)

    return valor


def ler_matriz(texto):
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

    texto = (texto or "").strip()

    if not texto:

        raise ValueError("Informe a matriz.")

    if texto.startswith("["):

        try:

            dados = json.loads(texto)

        except json.JSONDecodeError:

            raise ValueError(
                "Formato inválido. Exemplo: [[1, 2], [3, 4]]"
            )

    else:

        linhas = [
            linha
            for linha in re.split(r"[\n;]+", texto)
            if linha.strip()
        ]

        try:

            dados = [
                [
                    _numero(valor)
                    for valor in re.split(r"[\s,]+", linha.strip())
                    if valor
                ]
                for linha in linhas
            ]

        except ValueError:

            raise ValueError(
                "A matriz só pode ter números (use ponto nos "
                "decimais)."
            )

    if (
        not isinstance(dados, list)
        or not dados
        or not all(isinstance(linha, list) and linha for linha in dados)
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

    return dados


# ============================================================
# DIÁLOGO DE PARÂMETROS
# ============================================================

class DialogoParametros(QDialog):
    """
    Formulário montado a partir do esquema JSON de uma ferramenta
    (o mesmo que o Ollama recebe): texto, inteiro, número, booleano,
    lista de opções (enum) e matriz.
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

    def __init__(self, titulo, parametros, campos=None, pai=None):

        super().__init__(pai)

        self.setWindowTitle(titulo)

        self.setMinimumWidth(420)

        self.setStyleSheet("""
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
        """)

        obrigatorios = set(parametros.get("required", []))

        self._campos = {}

        formulario = QFormLayout()

        for chave, esquema in parametros.get("properties", {}).items():

            if campos is not None and chave not in campos:
                continue

            obrigatorio = chave in obrigatorios

            tipo, widget = self._criar_campo(
                chave,
                esquema,
                obrigatorio
            )

            dica = self.DICAS.get(chave) or esquema.get("description")

            if dica:
                widget.setToolTip(dica)

            rotulo = self.ROTULOS.get(
                chave,
                chave.replace("_", " ").capitalize()
            )

            if not obrigatorio:
                rotulo += " (opcional)"

            formulario.addRow(rotulo + ":", widget)

            self._campos[chave] = (tipo, widget, obrigatorio, rotulo)

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

    # --------------------------------------------------------

    def _criar_campo(self, chave, esquema, obrigatorio):

        tipo = esquema.get("type", "string")

        if esquema.get("enum"):

            combo = QComboBox()

            if not obrigatorio:
                combo.addItem("(padrão)", None)

            for opcao in esquema["enum"]:
                combo.addItem(str(opcao), opcao)

            return "opcoes", combo

        if tipo == "boolean":

            combo = QComboBox()

            if not obrigatorio:
                combo.addItem("(padrão)", None)

            combo.addItem("Sim", True)

            combo.addItem("Não", False)

            return "opcoes", combo

        if tipo == "array":

            campo = QPlainTextEdit()

            campo.setPlaceholderText("2 1\n3 4")

            campo.setFixedHeight(90)

            return "matriz", campo

        return tipo, QLineEdit()

    def _coletar(self):

        argumentos = {}

        for chave, (tipo, widget, obrigatorio, rotulo) in (
            self._campos.items()
        ):

            if tipo == "opcoes":

                valor = widget.currentData()

                if valor is not None:
                    argumentos[chave] = valor

                continue

            if tipo == "matriz":

                texto = widget.toPlainText().strip()

                if not texto:

                    if obrigatorio:
                        raise ValueError(f"Preencha \"{rotulo}\".")

                    continue

                try:

                    argumentos[chave] = ler_matriz(texto)

                except ValueError as erro:

                    raise ValueError(f"{rotulo}: {erro}")

                continue

            texto = widget.text().strip()

            if not texto:

                if obrigatorio:
                    raise ValueError(f"Preencha \"{rotulo}\".")

                continue

            if tipo == "integer":

                try:

                    argumentos[chave] = int(texto)

                except ValueError:

                    raise ValueError(
                        f"\"{rotulo}\" precisa ser um número inteiro."
                    )

            elif tipo == "number":

                try:

                    numero = float(texto.replace(",", "."))

                except ValueError:

                    raise ValueError(
                        f"\"{rotulo}\" precisa ser um número."
                    )

                argumentos[chave] = (
                    int(numero) if numero.is_integer() else numero
                )

            else:

                argumentos[chave] = texto

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
# CATÁLOGO DO MENU
# ============================================================

class ItemFerramenta:
    """Um item de menu ligado a uma ferramenta do registro."""

    def __init__(self, nome, rotulo, prompt=None, campos=None):
        """
        prompt: função(argumentos) -> texto. Se informada, o item não
                executa a ferramenta direto: manda o texto pelo chat
                (para ferramentas que dependem do modelo).
        campos: restringe quais parâmetros aparecem no diálogo.
        """

        self.nome = nome

        self.rotulo = rotulo

        self.prompt = prompt

        self.campos = campos

    @property
    def rotulo_limpo(self):

        return self.rotulo.rstrip("…").strip()


class Submenu:

    def __init__(self, rotulo, itens):

        self.rotulo = rotulo

        self.itens = itens


SEPARADOR = None


def _prompt_analisar_tela(argumentos):

    monitor = argumentos.get("monitor")

    if monitor:
        return f"O que tem na tela do monitor {monitor}?"

    return "O que tem na minha tela?"


class CatalogoMenu:
    """Organização das ferramentas nos menus (nome da ferramenta -> item)."""

    @staticmethod
    def menus():

        F = ItemFerramenta

        return [
            ("&Programas e arquivos", [
                F("abrir_programa", "Abrir programa…"),
                F("fechar_programa", "Fechar programa…"),
                F("abrir_menu_iniciar", "Abrir o menu Iniciar"),
                SEPARADOR,
                F("buscar_arquivo", "Buscar arquivo…"),
                F("abrir_arquivo", "Abrir arquivo…"),
            ]),
            ("&Calculadora", [
                F("calcular", "Calcular expressão…"),
                F("converter_base", "Converter entre bases…"),
                SEPARADOR,
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
            ("&Lembretes", [
                F("criar_lembrete", "Criar lembrete…"),
                F("listar_lembretes", "Listar lembretes"),
                F("cancelar_lembrete", "Cancelar lembrete…"),
            ]),
            ("&Janelas e telas", [
                F("listar_monitores", "Listar monitores"),
                F("listar_janelas_abertas", "Listar janelas abertas"),
                F("controlar_janela", "Controlar janela…"),
                F("mover_programa_monitor", "Mover programa para um monitor…"),
                F("mover_para_outro_monitor", "Mover programa para outro monitor…"),
                SEPARADOR,
                F("tirar_print", "Tirar print…"),
                F(
                    "analisar_tela",
                    "Analisar a tela…",
                    prompt=_prompt_analisar_tela,
                    campos=["monitor"]
                ),
            ]),
            ("&Sistema", [
                F("informacoes_hardware", "Informações do hardware"),
                SEPARADOR,
                F("listar_processos", "Listar processos…"),
                F("listar_processos_protegidos", "Listar processos protegidos"),
                F("finalizar_processo", "Finalizar processo…"),
                SEPARADOR,
                F("bloquear_tela", "Bloquear a tela…"),
                F("desligar_computador", "Desligar o computador…"),
                F("cancelar_desligamento", "Cancelar desligamento"),
                SEPARADOR,
                F("copiar_texto", "Copiar texto para a área de transferência…"),
                F("colar_texto", "Colar da área de transferência"),
            ]),
        ]

    @staticmethod
    def rede():
        """Itens do menu Rede e internet (o liga/desliga é à parte)."""

        F = ItemFerramenta

        return [
            F(
                "pesquisar_internet",
                "Pesquisar na internet…",
                prompt=lambda a: f"Pesquise na internet: {a['consulta']}"
            ),
            SEPARADOR,
            F("obter_ip_local", "Meu endereço IP local"),
            F("verificar_wifi", "Verificar Wi-Fi"),
            F("testar_ping", "Testar ping…"),
        ]

    # Cobertas por ações próprias do menu (alternar_internet).
    FERRAMENTAS_DO_LIGA_DESLIGA = ("ativar_internet", "desativar_internet")

    @classmethod
    def nomes_cobertos(cls):
        """Todas as ferramentas que o menu alcança."""

        nomes = set(cls.FERRAMENTAS_DO_LIGA_DESLIGA)

        def varrer(itens):

            for item in itens:

                if isinstance(item, ItemFerramenta):
                    nomes.add(item.nome)

                elif isinstance(item, Submenu):
                    varrer(item.itens)

        for _titulo, itens in cls.menus():
            varrer(itens)

        varrer(cls.rede())

        return nomes


# ============================================================
# MENU PRINCIPAL
# ============================================================

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


class MenuPrincipal:
    """
    Instala a barra de menus numa ShaulaWindow. Usa só a API pública
    da janela (criar_nova_conversa, abrir_dialogo_anexo, registro,
    gerenciador_conversas etc.).
    """

    def __init__(self, janela):

        self.janela = janela

        self._acao_internet = None

        self._menu_ir_para = None

        self._acao_fixar = None

        self._menu_esforco = None

        self._grupo_esforco = None

    # --------------------------------------------------------
    # MONTAGEM
    # --------------------------------------------------------

    def instalar(self):

        barra = self.janela.menuBar()

        barra.setStyleSheet(ESTILO_BARRA)

        self._montar_arquivo(barra)

        self._montar_conversas(barra)

        for titulo, itens in CatalogoMenu.menus():

            menu = barra.addMenu(titulo)

            self._preencher(menu, itens)

        self._montar_rede(barra)

        self._montar_configuracoes(barra)

        self._montar_ajuda(barra)

    def _acao(self, menu, texto, funcao, atalho=None, marcavel=False):

        acao = QAction(texto, menu)

        if atalho:
            acao.setShortcut(QKeySequence(atalho))

        if marcavel:
            acao.setCheckable(True)

        acao.triggered.connect(lambda *_: funcao())

        menu.addAction(acao)

        return acao

    def _preencher(self, menu, itens):

        for item in itens:

            if item is SEPARADOR:

                menu.addSeparator()

            elif isinstance(item, Submenu):

                self._preencher(menu.addMenu(item.rotulo), item.itens)

            elif self.janela.registro.obter(item.nome) is not None:

                self._acao(
                    menu,
                    item.rotulo,
                    lambda item=item: self._acionar(item)
                )

    def _montar_arquivo(self, barra):

        j = self.janela

        menu = barra.addMenu("&Arquivo")

        self._acao(menu, "Nova conversa", j.criar_nova_conversa, "Ctrl+N")

        self._acao(
            menu,
            "Abrir esta conversa em nova janela",
            lambda: j.abrir_conversa_em_nova_janela(j.id_conversa_atual)
        )

        menu.addSeparator()

        self._acao(
            menu,
            "Anexar arquivo…",
            j.abrir_dialogo_anexo,
            "Ctrl+O"
        )

        menu.addSeparator()

        self._acao(menu, "Sair da Shaula", j.fechar_shaula, "Ctrl+Q")

    def _montar_conversas(self, barra):

        j = self.janela

        menu = barra.addMenu("&Conversas")

        self._menu_ir_para = menu.addMenu("Ir para a conversa")

        self._menu_ir_para.aboutToShow.connect(self._preencher_ir_para)

        menu.addSeparator()

        self._acao(
            menu,
            "Renomear conversa atual…",
            self._renomear_atual
        )

        self._acao_fixar = self._acao(
            menu,
            "Fixar conversa atual",
            self._alternar_fixacao_atual
        )

        self._acao(
            menu,
            "Apagar conversa atual…",
            self._apagar_atual
        )

        menu.aboutToShow.connect(self._atualizar_texto_fixar)

        menu.addSeparator()

        self._acao(
            menu,
            "Mostrar/ocultar barra lateral",
            j.alternar_barra_lateral,
            "Ctrl+B"
        )

    def _montar_rede(self, barra):

        j = self.janela

        menu = barra.addMenu("&Rede e internet")

        self._acao_internet = self._acao(
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

        self._preencher(menu, CatalogoMenu.rede())

    def _montar_configuracoes(self, barra):

        j = self.janela

        menu = barra.addMenu("Con&figurações")

        self._menu_esforco = menu.addMenu("Nível de esforço")

        self._menu_esforco.aboutToShow.connect(self._preencher_esforco)

        menu.addSeparator()

        # O atalho Ctrl+M já pertence à janela (QShortcut); aqui só
        # aparece no texto, para não haver atalho ambíguo.
        self._acao(
            menu,
            "Falar um comando (Ctrl+M)",
            j.alternar_escuta
        )

    def _montar_ajuda(self, barra):

        menu = barra.addMenu("A&juda")

        self._acao(
            menu,
            "Ferramentas disponíveis",
            self._mostrar_ferramentas
        )

        self._acao(menu, "Sobre a Shaula", self._mostrar_sobre)

    # --------------------------------------------------------
    # CONVERSAS
    # --------------------------------------------------------

    def _entrada_atual(self):

        j = self.janela

        return j.gerenciador_conversas.obter_entrada(j.id_conversa_atual)

    def _preencher_ir_para(self):

        j = self.janela

        menu = self._menu_ir_para

        menu.clear()

        conversas = j.gerenciador_conversas.listar_conversas()

        for entrada in conversas:

            titulo = entrada["titulo"].replace("&", "&&")

            if entrada.get("fixado"):
                titulo = "📌 " + titulo

            acao = menu.addAction(titulo)

            acao.setCheckable(True)

            acao.setChecked(entrada["id"] == j.id_conversa_atual)

            acao.triggered.connect(
                lambda *_, id_conversa=entrada["id"]:
                self._ir_para(id_conversa)
            )

        if not conversas:

            menu.addAction("(nenhuma conversa)").setEnabled(False)

    def _ir_para(self, id_conversa):

        lista = self.janela.lista_conversas

        for indice in range(lista.count()):

            item = lista.item(indice)

            if item.data(Qt.UserRole) == id_conversa:

                self.janela.selecionar_conversa(item)

                return

    def _atualizar_texto_fixar(self):

        entrada = self._entrada_atual()

        fixado = bool(entrada and entrada.get("fixado"))

        self._acao_fixar.setText(
            "Desafixar conversa atual" if fixado
            else "Fixar conversa atual"
        )

    def _renomear_atual(self):

        entrada = self._entrada_atual()

        if entrada is None:
            return

        self.janela.renomear_conversa_ui(
            self.janela.id_conversa_atual,
            entrada["titulo"]
        )

    def _alternar_fixacao_atual(self):

        j = self.janela

        j.gerenciador_conversas.alternar_fixado(j.id_conversa_atual)

        j.atualizar_lista_conversas()

    def _apagar_atual(self):

        entrada = self._entrada_atual()

        if entrada is None:
            return

        self.janela.apagar_conversa_ui(
            self.janela.id_conversa_atual,
            entrada["titulo"]
        )

    # --------------------------------------------------------
    # ESFORÇO
    # --------------------------------------------------------

    def _preencher_esforco(self):

        j = self.janela

        menu = self._menu_esforco

        menu.clear()

        self._grupo_esforco = QActionGroup(menu)

        self._grupo_esforco.setExclusive(True)

        atual = j.estado_esforco.perfil

        for perfil in CatalogoEsforco.listar():

            rotulo = perfil.nome

            if perfil.recomendado:
                rotulo += "   (Recomendado)"

            if perfil.aviso:
                rotulo += "   ⚠ mais pesado"

            acao = QAction(rotulo, menu)

            acao.setCheckable(True)

            acao.setChecked(perfil.chave == atual.chave)

            acao.setToolTip(f"{perfil.descricao}\n{perfil.resumo}")

            acao.triggered.connect(
                lambda *_, chave=perfil.chave: j.definir_esforco(chave)
            )

            self._grupo_esforco.addAction(acao)

            menu.addAction(acao)

    # --------------------------------------------------------
    # FERRAMENTAS
    # --------------------------------------------------------

    def _ocupada(self):
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

    def _acionar(self, item):

        j = self.janela

        ferramenta = j.registro.obter(item.nome)

        if ferramenta is None or self._ocupada():
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

        if item.prompt is not None:

            self._enviar_pelo_chat(item.prompt(argumentos))

            return

        self._executar_em_thread(item, argumentos)

    def _enviar_pelo_chat(self, texto):
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
    def _texto_do_pedido(item, argumentos):

        texto = f"[Menu] {item.rotulo_limpo}"

        for chave, valor in argumentos.items():

            if isinstance(valor, list):
                valor = json.dumps(valor)

            texto += f"\n{chave}: {valor}"

        return texto

    def _executar_em_thread(self, item, argumentos):

        j = self.janela

        texto = self._texto_do_pedido(item, argumentos)

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

    # --------------------------------------------------------
    # AJUDA
    # --------------------------------------------------------

    def _mostrar_ferramentas(self):

        j = self.janela

        ferramentas = list(j.registro)

        dialogo = QDialog(j)

        dialogo.setWindowTitle(
            f"Ferramentas disponíveis ({len(ferramentas)})"
        )

        dialogo.resize(640, 520)

        dialogo.setStyleSheet("""
            QDialog { background: #0B1136; }
            QPlainTextEdit {
                background: #111743;
                color: #F2F4FF;
                border: 1px solid #283593;
                border-radius: 6px;
            }
        """)

        texto = QPlainTextEdit()

        texto.setReadOnly(True)

        texto.setPlainText(
            "\n\n".join(
                f"{f.nome}\n    {f.descricao}"
                for f in ferramentas
            )
        )

        layout = QVBoxLayout(dialogo)

        layout.addWidget(texto)

        dialogo.exec()

    def _mostrar_sobre(self):

        QMessageBox.about(
            self.janela,
            "Sobre a Shaula",
            f"<b>Shaula IA {VERSAO_SHAULA}</b><br><br>"
            "Assistente pessoal local para Windows, feita com "
            "PySide6 e Ollama (modelo qwen3.5:9b). Tudo é processado "
            "no seu computador."
        )
