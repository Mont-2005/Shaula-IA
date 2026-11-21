import re
from dataclasses import dataclass

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QSyntaxHighlighter,
    QTextCharFormat,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .pesquisa import FormatadorTexto


# ============================================================
# 1. DIVISÃO DA MENSAGEM EM TEXTO E CÓDIGO (sem Qt)
# ============================================================

@dataclass(frozen=True)
class SegmentoMensagem:
    """
    Um trecho de uma mensagem: texto corrido ("texto") ou um bloco
    de código delimitado por ``` ("codigo"). `linguagem` só tem
    valor em blocos de código e pode ser vazia.
    """

    tipo: str
    conteudo: str
    linguagem: str = ""

    @property
    def eh_codigo(self):

        return self.tipo == "codigo"


class DivisorDeBlocos:
    """
    Separa uma mensagem em segmentos de texto e de código.

    Segue o essencial do Markdown: um bloco abre numa linha que
    começa com ``` (ou ~~~), com o nome da linguagem opcional, e
    fecha numa linha com ao menos a mesma quantidade do mesmo
    caractere. Como os modelos de linguagem às vezes são
    interrompidos (ou esquecem de fechar), um bloco aberto e não
    fechado vai até o fim da mensagem em vez de "engolir" o texto.

    Sem dependência de Qt: pode ser testado sozinho.
    """

    # até 8 espaços de recuo: modelos costumam indentar o bloco
    # quando ele está dentro de um item de lista.
    PADRAO_ABERTURA = re.compile(
        r"^([ \t]{0,8})(`{3,}|~{3,})[ \t]*([\w+#.\-]*)[ \t]*[^`\n]*$"
    )

    PADRAO_FECHAMENTO = re.compile(
        r"^[ \t]{0,8}(`{3,}|~{3,})[ \t]*$"
    )

    @classmethod
    def tem_codigo(cls, texto):

        texto = str(texto)

        if "```" not in texto and "~~~" not in texto:
            return False

        return any(
            segmento.eh_codigo
            for segmento in cls.dividir(texto)
        )

    @classmethod
    def dividir(cls, texto):

        linhas = str(texto).replace("\r\n", "\n").split("\n")

        segmentos = []

        buffer_texto = []

        i = 0

        while i < len(linhas):

            abertura = cls.PADRAO_ABERTURA.match(linhas[i])

            if not abertura:

                buffer_texto.append(linhas[i])

                i += 1

                continue

            cls._guardar_texto(segmentos, buffer_texto)

            buffer_texto = []

            recuo = len(abertura.group(1).expandtabs(4))

            marca = abertura.group(2)

            linguagem = abertura.group(3).lower()

            corpo = []

            i += 1

            while i < len(linhas):

                fechamento = cls.PADRAO_FECHAMENTO.match(linhas[i])

                if (
                    fechamento
                    and fechamento.group(1)[0] == marca[0]
                    and len(fechamento.group(1)) >= len(marca)
                ):

                    i += 1

                    break

                corpo.append(cls._tirar_recuo(linhas[i], recuo))

                i += 1

            codigo = "\n".join(corpo).strip("\n")

            if codigo.strip():

                segmentos.append(
                    SegmentoMensagem("codigo", codigo, linguagem)
                )

        cls._guardar_texto(segmentos, buffer_texto)

        return segmentos

    @staticmethod
    def _tirar_recuo(linha, recuo):
        """Remove até `recuo` espaços do começo (o recuo do ```)."""

        removidos = 0

        while (
            removidos < recuo
            and removidos < len(linha)
            and linha[removidos] == " "
        ):
            removidos += 1

        return linha[removidos:]

    @staticmethod
    def _guardar_texto(segmentos, linhas):

        texto = "\n".join(linhas).strip("\n")

        if texto.strip():

            segmentos.append(SegmentoMensagem("texto", texto))


# ============================================================
# 2. TEXTO -> HTML (com `código embutido`)
# ============================================================

class FormatadorTextoMensagem:
    """
    Converte o texto de uma mensagem em HTML para o QLabel:
    escapa o HTML, quebra linhas, transforma links e destaca
    `trechos entre crases`.

    Antes isso era feito direto em ShaulaWindow.adicionar_mensagem,
    que removia TODOS os "**" da resposta — inclusive os de código
    (ex.: a potência `x ** 2` perdia o operador). Agora o "**" só é
    removido do texto comum, nunca de dentro de crases.
    """

    PADRAO_CODIGO_EMBUTIDO = re.compile(r"`([^`\n]+)`")

    ESTILO_CODIGO_EMBUTIDO = (
        "font-family:'Cascadia Mono',Consolas,'Courier New',monospace;"
        "background-color:#1B2160;color:#E8EAF6;"
    )

    @staticmethod
    def escapar(texto):

        return (
            texto
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    @classmethod
    def para_html(cls, texto, remover_negrito=False):

        partes = cls.PADRAO_CODIGO_EMBUTIDO.split(str(texto))

        # split com um grupo de captura: índices pares = texto,
        # ímpares = o que estava entre crases.
        resultado = []

        for indice, parte in enumerate(partes):

            if indice % 2 == 1:

                resultado.append(
                    f'<span style="{cls.ESTILO_CODIGO_EMBUTIDO}">'
                    f"&nbsp;{cls.escapar(parte)}&nbsp;</span>"
                )

                continue

            if remover_negrito:
                parte = parte.replace("**", "")

            html = cls.escapar(parte).replace("\n", "<br>")

            resultado.append(
                FormatadorTexto.linkificar_html(html)
            )

        return "".join(resultado)


# ============================================================
# 3. REALCE DE SINTAXE (leve, sem dependências)
# ============================================================

@dataclass(frozen=True)
class PerfilLinguagem:
    nome: str
    palavras_chave: frozenset
    comentario_linha: tuple = ()
    comentario_bloco: tuple = ()
    aspas_triplas: bool = False
    crase_e_string: bool = False
    ignora_caixa: bool = False
    nativas: frozenset = frozenset()


def _palavras(texto):

    return frozenset(texto.split())


class CatalogoLinguagens:
    """
    Perfis das linguagens que recebem cores. Qualquer outra
    linguagem (ou sem nome) usa o perfil genérico: só strings e
    números são coloridos.
    """

    PYTHON = PerfilLinguagem(
        "python",
        _palavras(
            "and as assert async await break class continue def del "
            "elif else except finally for from global if import in is "
            "lambda nonlocal not or pass raise return try while with "
            "yield None True False match case"
        ),
        comentario_linha=("#",),
        aspas_triplas=True,
        nativas=_palavras(
            "print len range int str float list dict set tuple bool "
            "input open sum min max abs sorted enumerate zip map "
            "filter isinstance type super self"
        ),
    )

    JAVASCRIPT = PerfilLinguagem(
        "javascript",
        _palavras(
            "async await break case catch class const continue default "
            "delete do else export extends finally for from function if "
            "import in instanceof let new of return static super switch "
            "this throw try typeof var void while yield null undefined "
            "true false interface type enum implements public private "
            "protected readonly"
        ),
        comentario_linha=("//",),
        comentario_bloco=("/*", "*/"),
        crase_e_string=True,
    )

    C_E_PARECIDAS = PerfilLinguagem(
        "c",
        _palavras(
            "abstract auto bool boolean break byte case catch char class "
            "const continue default delete do double else enum extends "
            "false final finally float for goto if implements import "
            "include inline instanceof int interface long namespace new "
            "null nullptr operator override package private protected "
            "public return short signed sizeof static string struct "
            "super switch template this throw throws true try typedef "
            "union unsigned using virtual void volatile while var "
            "foreach in readonly"
        ),
        comentario_linha=("//",),
        comentario_bloco=("/*", "*/"),
    )

    GO = PerfilLinguagem(
        "go",
        _palavras(
            "break case chan const continue default defer else "
            "fallthrough for func go goto if import interface map "
            "package range return select struct switch type var nil "
            "true false"
        ),
        comentario_linha=("//",),
        comentario_bloco=("/*", "*/"),
        crase_e_string=True,
    )

    RUST = PerfilLinguagem(
        "rust",
        _palavras(
            "as async await break const continue crate dyn else enum "
            "extern false fn for if impl in let loop match mod move mut "
            "pub ref return self Self static struct super trait true "
            "type unsafe use where while"
        ),
        comentario_linha=("//",),
        comentario_bloco=("/*", "*/"),
    )

    SQL = PerfilLinguagem(
        "sql",
        _palavras(
            "select from where insert into values update set delete "
            "create table drop alter add join inner left right outer on "
            "group by order having limit offset as and or not null "
            "distinct union all in is like between exists case when then "
            "else end primary key foreign references index view"
        ),
        comentario_linha=("--",),
        comentario_bloco=("/*", "*/"),
        ignora_caixa=True,
    )

    SHELL = PerfilLinguagem(
        "shell",
        _palavras(
            "if then else elif fi for while do done case esac function "
            "in return exit echo export local cd set unset source"
        ),
        comentario_linha=("#",),
    )

    JSON = PerfilLinguagem(
        "json",
        _palavras("true false null"),
    )

    GENERICO = PerfilLinguagem("generico", frozenset())

    APELIDOS = {
        "python": PYTHON, "py": PYTHON, "python3": PYTHON,
        "javascript": JAVASCRIPT, "js": JAVASCRIPT, "jsx": JAVASCRIPT,
        "typescript": JAVASCRIPT, "ts": JAVASCRIPT, "tsx": JAVASCRIPT,
        "java": C_E_PARECIDAS, "c": C_E_PARECIDAS, "cpp": C_E_PARECIDAS,
        "c++": C_E_PARECIDAS, "cs": C_E_PARECIDAS, "csharp": C_E_PARECIDAS,
        "c#": C_E_PARECIDAS, "kotlin": C_E_PARECIDAS, "php": C_E_PARECIDAS,
        "go": GO, "golang": GO, "rust": RUST, "rs": RUST,
        "sql": SQL, "bash": SHELL, "sh": SHELL, "shell": SHELL,
        "zsh": SHELL, "json": JSON,
    }

    @classmethod
    def perfil(cls, linguagem):

        return cls.APELIDOS.get(
            str(linguagem or "").lower(),
            cls.GENERICO
        )


class RealceSintaxe(QSyntaxHighlighter):
    """
    Colore palavras-chave, strings, comentários e números de um
    bloco de código. É propositalmente simples (expressões
    regulares por linha, com estado só para strings de três aspas e
    comentários de bloco que atravessam linhas): serve para leitura,
    não é um analisador de verdade.
    """

    ESTADO_NORMAL = 0
    ESTADO_TRIPLA_DUPLA = 1
    ESTADO_TRIPLA_SIMPLES = 2
    ESTADO_COMENTARIO_BLOCO = 3

    CORES = {
        "palavra": ("#C792EA", False, True),
        "nativa": ("#82AAFF", False, False),
        "string": ("#C3E88D", False, False),
        "comentario": ("#7F8CB0", True, False),
        "numero": ("#F78C6C", False, False),
    }

    def __init__(self, documento, linguagem=""):

        super().__init__(documento)

        self.perfil = CatalogoLinguagens.perfil(linguagem)

        self._formatos = {
            tipo: self._criar_formato(*estilo)
            for tipo, estilo in self.CORES.items()
        }

        self._padrao = self._montar_padrao(self.perfil)

    @staticmethod
    def _criar_formato(cor, italico, negrito):

        formato = QTextCharFormat()

        formato.setForeground(QColor(cor))

        formato.setFontItalic(italico)

        if negrito:
            formato.setFontWeight(QFont.DemiBold)

        return formato

    @staticmethod
    def _montar_padrao(perfil):

        alternativas = []

        if perfil.comentario_bloco:

            alternativas.append(
                "(?P<bcom>" + re.escape(perfil.comentario_bloco[0]) + ")"
            )

        if perfil.comentario_linha:

            alternativas.append(
                "(?P<lcom>"
                + "|".join(
                    re.escape(prefixo)
                    for prefixo in perfil.comentario_linha
                )
                + ").*"
            )

        if perfil.aspas_triplas:

            alternativas.append('(?P<tdq>""")')

            alternativas.append("(?P<tsq>''')")

        aspas = r"\"(?:\\.|[^\"\\])*\"?|'(?:\\.|[^'\\])*'?"

        if perfil.crase_e_string:
            aspas += r"|`(?:\\.|[^`\\])*`?"

        alternativas.append(f"(?P<str>{aspas})")

        alternativas.append(
            r"(?P<num>\b0[xX][0-9a-fA-F_]+\b"
            r"|\b\d[\d_]*(?:\.\d+)?(?:[eE][+-]?\d+)?\b)"
        )

        alternativas.append(r"(?P<word>[A-Za-z_][A-Za-z0-9_]*)")

        return re.compile("|".join(alternativas))

    def highlightBlock(self, texto):

        self.setCurrentBlockState(self.ESTADO_NORMAL)

        i = 0

        estado = self.previousBlockState()

        delimitadores = {
            self.ESTADO_TRIPLA_DUPLA: ('"""', "string"),
            self.ESTADO_TRIPLA_SIMPLES: ("'''", "string"),
            self.ESTADO_COMENTARIO_BLOCO: (
                self.perfil.comentario_bloco[1]
                if self.perfil.comentario_bloco
                else "",
                "comentario",
            ),
        }

        if estado in delimitadores and delimitadores[estado][0]:

            fim_texto, tipo = delimitadores[estado]

            fim = texto.find(fim_texto)

            if fim == -1:

                self.setFormat(0, len(texto), self._formatos[tipo])

                self.setCurrentBlockState(estado)

                return

            i = fim + len(fim_texto)

            self.setFormat(0, i, self._formatos[tipo])

        while i < len(texto):

            achado = self._padrao.search(texto, i)

            if not achado:
                break

            tipo = achado.lastgroup

            inicio, fim = achado.span()

            if tipo in ("lcom", "str"):

                self.setFormat(
                    inicio,
                    fim - inicio,
                    self._formatos[
                        "comentario" if tipo == "lcom" else "string"
                    ]
                )

            elif tipo == "num":

                self.setFormat(
                    inicio, fim - inicio, self._formatos["numero"]
                )

            elif tipo == "word":

                palavra = achado.group()

                chave = (
                    palavra.lower()
                    if self.perfil.ignora_caixa
                    else palavra
                )

                if chave in self.perfil.palavras_chave:

                    self.setFormat(
                        inicio, fim - inicio, self._formatos["palavra"]
                    )

                elif palavra in self.perfil.nativas:

                    self.setFormat(
                        inicio, fim - inicio, self._formatos["nativa"]
                    )

            else:

                # bcom, tdq ou tsq: abre algo que pode atravessar linhas
                delimitador_fim, estado_novo, formato = {
                    "bcom": (
                        self.perfil.comentario_bloco[1]
                        if self.perfil.comentario_bloco
                        else "",
                        self.ESTADO_COMENTARIO_BLOCO,
                        "comentario",
                    ),
                    "tdq": ('"""', self.ESTADO_TRIPLA_DUPLA, "string"),
                    "tsq": ("'''", self.ESTADO_TRIPLA_SIMPLES, "string"),
                }[tipo]

                encerra = texto.find(delimitador_fim, fim)

                if encerra == -1:

                    self.setFormat(
                        inicio,
                        len(texto) - inicio,
                        self._formatos[formato]
                    )

                    self.setCurrentBlockState(estado_novo)

                    return

                fim = encerra + len(delimitador_fim)

                self.setFormat(
                    inicio, fim - inicio, self._formatos[formato]
                )

            i = max(fim, i + 1)


# ============================================================
# 4. WIDGETS
# ============================================================

class EditorCodigo(QPlainTextEdit):
    """
    Área de leitura do código: fonte monoespaçada, sem quebra de
    linha (linhas longas ganham barra de rolagem horizontal) e
    altura que se ajusta ao conteúdo, para que a rolagem vertical
    fique sempre com a conversa — a roda do mouse sobre o código
    continua rolando o chat.
    """

    def __init__(self, codigo, linguagem="", parent=None):

        super().__init__(parent)

        self.setReadOnly(True)

        self.setFrameShape(QFrame.NoFrame)

        self.setLineWrapMode(QPlainTextEdit.NoWrap)

        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed
        )

        fonte = QFont("Consolas")

        fonte.setStyleHint(QFont.Monospace)

        fonte.setFixedPitch(True)

        fonte.setPixelSize(14)

        self.setFont(fonte)

        self.setTabStopDistance(
            4 * self.fontMetrics().horizontalAdvance(" ")
        )

        self.setStyleSheet("""
            QPlainTextEdit {
                background: #0B1136;
                color: #E8EAF6;
                border: none;
                padding: 4px 8px;
                selection-background-color: #3949AB;
            }
            QScrollBar:horizontal {
                height: 10px;
                background: transparent;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: #283593;
                border-radius: 5px;
                min-width: 30px;
            }
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {
                background: none;
            }
        """)

        self.setPlainText(codigo)

        self.realce = RealceSintaxe(self.document(), linguagem)

        self._linhas = codigo.count("\n") + 1

        self.horizontalScrollBar().rangeChanged.connect(
            lambda *_: self._ajustar_altura()
        )

        self._ajustar_altura()

    def _altura_de_uma_linha(self):
        """
        Altura real de uma linha segundo o layout do documento.
        fontMetrics().lineSpacing() não bate com a altura que o
        QPlainTextEdit usa de fato (varia com a fonte escolhida
        pelo sistema), e a diferença, multiplicada pelas linhas,
        cortava as últimas linhas do código.
        """

        bloco = self.document().firstBlock()

        altura = self.document().documentLayout().blockBoundingRect(
            bloco
        ).height()

        return altura if altura > 0 else self.fontMetrics().lineSpacing()

    def _ajustar_altura(self):

        margem = int(self.document().documentMargin())

        altura = int(
            self._linhas * self._altura_de_uma_linha()
            + 2 * margem
            + 8  # padding vertical do stylesheet (4 + 4)
            + 2  # folga de arredondamento
        )

        if self.horizontalScrollBar().maximum() > 0:

            altura += self.horizontalScrollBar().sizeHint().height()

        self.setFixedHeight(altura)


class BlocoCodigo(QFrame):
    """
    Bloco de código de uma resposta: cabeçalho com o nome da
    linguagem e o botão "Copiar", e abaixo o código com realce.
    O botão copia o código INTEIRO (sem as crases e sem o recuo
    do bloco) para a área de transferência e mostra "Copiado"
    por um instante.
    """

    TEXTO_COPIAR = "Copiar"

    TEXTO_COPIADO = "✓ Copiado"

    DURACAO_AVISO_MS = 1800

    def __init__(self, codigo, linguagem="", parent=None):

        super().__init__(parent)

        self._codigo = codigo

        self._linguagem = linguagem

        self.setObjectName("bloco_codigo")

        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Minimum
        )

        self.setStyleSheet("""
            #bloco_codigo {
                background: #0B1136;
                border: 1px solid #283593;
                border-radius: 10px;
            }
            #cabecalho_codigo {
                background: #141B4F;
                border: none;
                border-top-left-radius: 9px;
                border-top-right-radius: 9px;
            }
            #nome_linguagem {
                color: #9FA8DA;
                font-size: 12px;
                background: transparent;
            }
            #botao_copiar_codigo {
                background: transparent;
                color: #C5CAE9;
                border: none;
                border-radius: 6px;
                padding: 3px 10px;
                font-size: 12px;
            }
            #botao_copiar_codigo:hover {
                background: #283593;
                color: #FFFFFF;
            }
        """)

        layout = QVBoxLayout(self)

        layout.setContentsMargins(1, 1, 1, 1)

        layout.setSpacing(0)

        cabecalho = QFrame()

        cabecalho.setObjectName("cabecalho_codigo")

        layout_cabecalho = QHBoxLayout(cabecalho)

        layout_cabecalho.setContentsMargins(12, 4, 6, 4)

        self.rotulo_linguagem = QLabel(
            linguagem if linguagem else "código"
        )

        self.rotulo_linguagem.setObjectName("nome_linguagem")

        layout_cabecalho.addWidget(self.rotulo_linguagem)

        layout_cabecalho.addStretch(1)

        self.botao_copiar = QPushButton(self.TEXTO_COPIAR)

        self.botao_copiar.setObjectName("botao_copiar_codigo")

        self.botao_copiar.setCursor(Qt.PointingHandCursor)

        self.botao_copiar.setToolTip("Copiar o código")

        self.botao_copiar.setFocusPolicy(Qt.NoFocus)

        self.botao_copiar.clicked.connect(self.copiar)

        # Largura fixa para caber o texto mais longo ("✓ Copiado"):
        # sem isso o botão mudava de tamanho (ou cortava o texto)
        # ao trocar de "Copiar" para "Copiado".
        maior = max(
            self.botao_copiar.fontMetrics().horizontalAdvance(texto)
            for texto in (self.TEXTO_COPIAR, self.TEXTO_COPIADO)
        )

        self.botao_copiar.setMinimumWidth(maior + 32)

        layout_cabecalho.addWidget(self.botao_copiar)

        layout.addWidget(cabecalho)

        self.editor = EditorCodigo(codigo, linguagem)

        layout.addWidget(self.editor)

        self._timer_aviso = QTimer(self)

        self._timer_aviso.setSingleShot(True)

        self._timer_aviso.timeout.connect(self._restaurar_botao)

    @property
    def codigo(self):

        return self._codigo

    def copiar(self):

        QGuiApplication.clipboard().setText(self._codigo)

        self.botao_copiar.setText(self.TEXTO_COPIADO)

        self._timer_aviso.start(self.DURACAO_AVISO_MS)

    def _restaurar_botao(self):

        self.botao_copiar.setText(self.TEXTO_COPIAR)


class ConteudoMensagemShaula(QWidget):
    """
    Corpo de uma resposta da Shaula que contém blocos de código:
    uma coluna com o texto (em QLabels) e os blocos (BlocoCodigo)
    na ordem em que aparecem. O prefixo "Shaula:" vai no primeiro
    trecho de texto (ou sozinho, quando a resposta começa por um
    bloco de código).
    """

    ESTILO_TEXTO = """
        QLabel {
            background: transparent;
            color: #F2F4FF;
            padding: 5px 0px;
            font-size: 15px;
        }
    """

    PREFIXO_HTML = '<b style="color:#9FA8DA;">Shaula:</b>'

    # Blocos de código precisam de largura: o balão ocupa a largura
    # máxima permitida em vez da mínima (ver ShaulaWindow).
    ocupa_largura_maxima = True

    def __init__(self, texto, parent=None):

        super().__init__(parent)

        self.blocos = []

        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Minimum
        )

        layout = QVBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.setSpacing(6)

        segmentos = DivisorDeBlocos.dividir(texto)

        prefixo_pendente = True

        for segmento in segmentos:

            if segmento.eh_codigo:

                if prefixo_pendente:

                    layout.addWidget(
                        self._criar_rotulo(self.PREFIXO_HTML)
                    )

                    prefixo_pendente = False

                bloco = BlocoCodigo(
                    segmento.conteudo,
                    segmento.linguagem
                )

                self.blocos.append(bloco)

                layout.addWidget(bloco)

                continue

            html = FormatadorTextoMensagem.para_html(
                segmento.conteudo,
                remover_negrito=True
            )

            if prefixo_pendente:

                html = f"{self.PREFIXO_HTML} {html}"

                prefixo_pendente = False

            layout.addWidget(self._criar_rotulo(html))

    def _criar_rotulo(self, html):

        rotulo = QLabel()

        rotulo.setTextFormat(Qt.RichText)

        rotulo.setWordWrap(True)

        rotulo.setTextInteractionFlags(
            Qt.TextSelectableByMouse
            | Qt.LinksAccessibleByMouse
        )

        rotulo.setOpenExternalLinks(True)

        rotulo.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Minimum
        )

        rotulo.setText(html)

        rotulo.setStyleSheet(self.ESTILO_TEXTO)

        return rotulo
