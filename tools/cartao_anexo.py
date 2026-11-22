from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QPixmap,
    QTextOption,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
)


class IconeArquivo:
    """
    Desenha o ícone de um arquivo: uma folha com o canto dobrado, na
    cor do tipo (PDF, imagem, vídeo, código, texto) e com o formato
    escrito embaixo ("PDF", "PY"...). É desenhado por código, sem
    arquivos de imagem nem fontes de ícone, e em dobro de resolução
    para ficar nítido em telas de alta densidade.
    """

    LARGURA = 34

    ALTURA = 42

    DOBRA = 11

    ESCALA = 2

    CORES = {
        "pdf": "#E5484D",
        "imagem": "#8E4EC6",
        "video": "#D6409F",
        "codigo": "#30A46C",
        "texto": "#4F6FD8",
        "outro": "#6B7280",
    }

    def pixmap(self, descricao):
        """Ícone da folha para uma DescricaoAnexo."""

        largura = self.LARGURA

        altura = self.ALTURA

        dobra = self.DOBRA

        pixmap = QPixmap(
            int(largura * self.ESCALA),
            int(altura * self.ESCALA)
        )

        pixmap.setDevicePixelRatio(self.ESCALA)

        pixmap.fill(Qt.transparent)

        cor = QColor(
            self.CORES.get(descricao.tipo, self.CORES["outro"])
        )

        pintor = QPainter(pixmap)

        pintor.setRenderHint(QPainter.Antialiasing, True)

        folha = QPainterPath()

        folha.moveTo(1, 1)

        folha.lineTo(largura - 1 - dobra, 1)

        folha.lineTo(largura - 1, 1 + dobra)

        folha.lineTo(largura - 1, altura - 1)

        folha.lineTo(1, altura - 1)

        folha.closeSubpath()

        pintor.fillPath(folha, QBrush(cor))

        canto = QPainterPath()

        canto.moveTo(largura - 1 - dobra, 1)

        canto.lineTo(largura - 1 - dobra, 1 + dobra)

        canto.lineTo(largura - 1, 1 + dobra)

        canto.closeSubpath()

        pintor.fillPath(canto, QBrush(cor.lighter(135)))

        # Cabem 4 letras na folha ("JSON", "HTML"); ".markdown" viraria
        # "MARKDOWN" e estouraria as bordas do ícone.
        formato = descricao.formato[:4]

        fonte = QFont()

        fonte.setBold(True)

        fonte.setPixelSize(10 if len(formato) <= 3 else 8)

        pintor.setFont(fonte)

        pintor.setPen(QColor("#FFFFFF"))

        pintor.drawText(
            QRectF(0, altura * 0.42, largura, altura * 0.5),
            formato,
            QTextOption(Qt.AlignCenter)
        )

        pintor.end()

        return pixmap

    def miniatura(self, dados, lado=42):
        """
        Recorte quadrado (centralizado) de uma imagem enviada, para
        usar no lugar do ícone. None se os bytes não forem uma imagem.
        """

        original = QPixmap()

        if not original.loadFromData(dados):
            return None

        reduzida = original.scaled(
            lado,
            lado,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation
        )

        return reduzida.copy(
            (reduzida.width() - lado) // 2,
            (reduzida.height() - lado) // 2,
            lado,
            lado
        )


class CartaoAnexo(QFrame):
    """
    Cartão de um arquivo enviado, como no chat do Claude: ícone (ou a
    miniatura, se for imagem), o nome do arquivo e, embaixo, o formato
    com o detalhe ("PDF · 128 página(s)"). Nomes longos são cortados no
    meio, com o nome inteiro na dica (tooltip).
    """

    LARGURA_MAXIMA = 300

    LADO_ICONE = 42

    MARGEM_ESQUERDA = 10

    MARGEM_DIREITA = 14

    ESPACO = 10

    def __init__(
        self,
        descricao,
        icones,
        miniatura_bytes=None,
        parent=None
    ):

        super().__init__(parent)

        self.setObjectName("cartao_anexo")

        self.setMaximumWidth(self.LARGURA_MAXIMA)

        self.setSizePolicy(
            QSizePolicy.Maximum,
            QSizePolicy.Fixed
        )

        layout = QHBoxLayout(self)

        layout.setContentsMargins(
            self.MARGEM_ESQUERDA,
            8,
            self.MARGEM_DIREITA,
            8
        )

        layout.setSpacing(self.ESPACO)

        icone = QLabel()

        icone.setObjectName("cartao_anexo_icone")

        miniatura = (
            icones.miniatura(miniatura_bytes, self.LADO_ICONE)
            if miniatura_bytes
            else None
        )

        icone.setPixmap(miniatura or icones.pixmap(descricao))

        icone.setFixedSize(
            self.LADO_ICONE,
            self.LADO_ICONE
        )

        icone.setAlignment(Qt.AlignCenter)

        layout.addWidget(icone)

        largura_texto = (
            self.LARGURA_MAXIMA
            - self.MARGEM_ESQUERDA
            - self.MARGEM_DIREITA
            - self.ESPACO
            - self.LADO_ICONE
        )

        coluna = QVBoxLayout()

        coluna.setContentsMargins(0, 0, 0, 0)

        coluna.setSpacing(2)

        nome = QLabel()

        nome.setObjectName("cartao_anexo_nome")

        fonte_nome = nome.font()

        fonte_nome.setPixelSize(13)

        fonte_nome.setBold(True)

        nome.setFont(fonte_nome)

        nome.setText(
            QFontMetrics(fonte_nome).elidedText(
                descricao.nome,
                Qt.ElideMiddle,
                largura_texto
            )
        )

        nome.setToolTip(descricao.nome)

        # Texto puro: o nome do arquivo nunca deve ser lido como HTML.
        nome.setTextFormat(Qt.PlainText)

        detalhe = QLabel()

        detalhe.setObjectName("cartao_anexo_detalhe")

        fonte_detalhe = detalhe.font()

        fonte_detalhe.setPixelSize(12)

        detalhe.setFont(fonte_detalhe)

        detalhe.setText(
            QFontMetrics(fonte_detalhe).elidedText(
                descricao.linha_detalhe,
                Qt.ElideRight,
                largura_texto
            )
        )

        detalhe.setToolTip(descricao.linha_detalhe)

        detalhe.setTextFormat(Qt.PlainText)

        coluna.addWidget(nome)

        coluna.addWidget(detalhe)

        layout.addLayout(coluna)
