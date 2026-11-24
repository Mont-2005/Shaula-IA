from PySide6.QtCore import Qt, QRect, QSize
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)


class VisualizadorImagem(QDialog):
    """
    Mostra uma imagem inteira sobre a janela da Shaula, como o
    visualizador do Claude: fundo escuro cobrindo a janela, a imagem
    centralizada (reduzida para caber, nunca ampliada além do tamanho
    real), o nome do arquivo embaixo e um ✕ no canto.

    Fecha com Esc, com o ✕ ou clicando no fundo escuro (fora da
    imagem). Clicar na própria imagem não fecha.

    Uso: VisualizadorImagem.abrir(nome, bytes_da_imagem, janela)
    """

    COR_FUNDO = QColor(0, 0, 0, 220)

    MARGEM = 40

    ALTURA_BARRA_TOPO = 56

    ALTURA_NOME = 44

    LADO_BOTAO_FECHAR = 40

    ESTILO = """
        #visualizador_nome {
            color: #E6E8F2;
            font-size: 14px;
            background: transparent;
        }

        #visualizador_fechar {
            color: #FFFFFF;
            background-color: rgba(255, 255, 255, 28);
            border: none;
            border-radius: 20px;
            font-size: 18px;
        }

        #visualizador_fechar:hover {
            background-color: rgba(255, 255, 255, 60);
        }
    """

    @classmethod
    def abrir(
        cls,
        nome,
        dados,
        parent=None
    ):
        """
        Abre o visualizador e só volta quando ele fecha. Devolve False
        (sem abrir nada) se os bytes não forem uma imagem legível.
        """

        pixmap = QPixmap()

        if not dados or not pixmap.loadFromData(
            dados
        ):

            return False

        visualizador = cls(
            nome,
            pixmap,
            parent
        )

        visualizador.exec()

        return True

    def __init__(
        self,
        nome,
        pixmap,
        parent=None
    ):

        super().__init__(
            parent,
            Qt.Dialog
            | Qt.FramelessWindowHint
        )

        self._nome = nome

        self._original = pixmap

        # Retângulo (em coordenadas do diálogo) que a imagem ocupa
        # agora — usado para distinguir clique na imagem de clique
        # no fundo.
        self._retangulo_imagem = QRect()

        self.setAttribute(
            Qt.WA_TranslucentBackground,
            True
        )

        self.setStyleSheet(
            self.ESTILO
        )

        self._cobrir_janela_pai()

        self._criar_widgets()

        self._ajustar_imagem()

    # ========================================================
    # CONSTRUÇÃO
    # ========================================================

    def _cobrir_janela_pai(self):

        if self.parentWidget() is not None:

            self.setGeometry(
                self.parentWidget()
                .window()
                .geometry()
            )

        else:

            self.resize(
                960,
                640
            )

    def _criar_widgets(self):

        layout = QVBoxLayout(
            self
        )

        # Margem de cima + altura do botão = ALTURA_BARRA_TOPO: a
        # conta de _area_disponivel() depende de os dois baterem.
        layout.setContentsMargins(
            self.MARGEM,
            self.ALTURA_BARRA_TOPO - self.LADO_BOTAO_FECHAR,
            self.MARGEM,
            0
        )

        layout.setSpacing(
            0
        )

        barra = QHBoxLayout()

        barra.setContentsMargins(
            0,
            0,
            0,
            0
        )

        barra.addStretch(
            1
        )

        self.botao_fechar = QPushButton(
            "✕"
        )

        self.botao_fechar.setObjectName(
            "visualizador_fechar"
        )

        self.botao_fechar.setFixedSize(
            self.LADO_BOTAO_FECHAR,
            self.LADO_BOTAO_FECHAR
        )

        self.botao_fechar.setCursor(
            Qt.PointingHandCursor
        )

        self.botao_fechar.setAutoDefault(
            False
        )

        self.botao_fechar.setToolTip(
            "Fechar (Esc)"
        )

        self.botao_fechar.clicked.connect(
            self.close
        )

        barra.addWidget(
            self.botao_fechar
        )

        layout.addLayout(
            barra
        )

        self.rotulo_imagem = QLabel()

        self.rotulo_imagem.setAlignment(
            Qt.AlignCenter
        )

        # Ignored: o tamanho da imagem não pode empurrar o diálogo —
        # é o diálogo que dita o tamanho em que a imagem cabe.
        self.rotulo_imagem.setSizePolicy(
            QSizePolicy.Ignored,
            QSizePolicy.Ignored
        )

        self.rotulo_imagem.setMinimumSize(
            1,
            1
        )

        layout.addWidget(
            self.rotulo_imagem,
            1
        )

        self.rotulo_nome = QLabel()

        self.rotulo_nome.setObjectName(
            "visualizador_nome"
        )

        self.rotulo_nome.setAlignment(
            Qt.AlignCenter
        )

        # Texto puro: o nome do arquivo nunca deve ser lido como HTML.
        self.rotulo_nome.setTextFormat(
            Qt.PlainText
        )

        self.rotulo_nome.setFixedHeight(
            self.ALTURA_NOME
        )

        layout.addWidget(
            self.rotulo_nome
        )

    # ========================================================
    # IMAGEM
    # ========================================================

    def _area_disponivel(self):
        """Tamanho (lógico) em que a imagem precisa caber."""

        largura = self.width() - 2 * self.MARGEM

        altura = (
            self.height()
            - self.ALTURA_BARRA_TOPO
            - self.ALTURA_NOME
        )

        return QSize(
            max(largura, 1),
            max(altura, 1)
        )

    def _ajustar_imagem(self):
        """Reduz a imagem para caber na janela e posiciona o nome."""

        area = self._area_disponivel()

        proporcao = self.devicePixelRatioF()

        alvo = QSize(
            int(area.width() * proporcao),
            int(area.height() * proporcao)
        )

        pixmap = self._original

        if (
            pixmap.width() > alvo.width()
            or pixmap.height() > alvo.height()
        ):

            pixmap = pixmap.scaled(
                alvo,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            # Em telas de alta densidade a imagem reduzida tem mais
            # pixels do que o espaço lógico; sem isto ela ficaria
            # grande demais e borrada.
            pixmap.setDevicePixelRatio(
                proporcao
            )

        self.rotulo_imagem.setPixmap(
            pixmap
        )

        self.rotulo_nome.setText(
            QFontMetrics(
                self.rotulo_nome.font()
            ).elidedText(
                self._nome,
                Qt.ElideMiddle,
                area.width()
            )
        )

        self.rotulo_nome.setToolTip(
            self._nome
        )

        largura = int(
            pixmap.width() / pixmap.devicePixelRatio()
        )

        altura = int(
            pixmap.height() / pixmap.devicePixelRatio()
        )

        self._retangulo_imagem = QRect(
            self.MARGEM + (area.width() - largura) // 2,
            self.ALTURA_BARRA_TOPO + (area.height() - altura) // 2,
            largura,
            altura
        )

    # ========================================================
    # EVENTOS
    # ========================================================

    def resizeEvent(
        self,
        event
    ):

        super().resizeEvent(
            event
        )

        self._ajustar_imagem()

    def paintEvent(
        self,
        event
    ):

        pintor = QPainter(
            self
        )

        pintor.fillRect(
            self.rect(),
            self.COR_FUNDO
        )

        pintor.end()

    def mousePressEvent(
        self,
        event
    ):

        if (
            event.button() == Qt.LeftButton
            and not self._retangulo_imagem.contains(
                event.position().toPoint()
            )
        ):

            self.close()

            return

        super().mousePressEvent(
            event
        )
