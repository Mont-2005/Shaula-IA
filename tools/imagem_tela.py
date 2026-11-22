from dataclasses import dataclass, field

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage

from .anexos import redimensionar_e_codificar_jpeg


class ImagemCapturada:
    """
    Pixels crus de uma captura de tela (o que o GDI entrega):
    32 bits por pixel em ordem B, G, R, A, com as linhas de baixo
    para cima (DIB "bottom-up").

    Concentra as três coisas que se faz com eles — virar uma QImage,
    ser salva em PNG e ser codificada em JPEG para o modelo — para
    que CapturadorTela não precise saber de formatos de arquivo.

    Usa só QImage (não QPixmap), então é seguro em qualquer thread,
    inclusive a thread da IA, onde as ferramentas rodam.
    """

    def __init__(self, largura, altura, pixels):

        if largura <= 0 or altura <= 0:
            raise ValueError("Imagem com tamanho inválido.")

        if len(pixels) < largura * altura * 4:
            raise ValueError("Faltam pixels para o tamanho informado.")

        self.largura = largura

        self.altura = altura

        self._pixels = bytes(pixels)

    def para_qimage(self):
        """QImage já na orientação certa (de cima para baixo)."""

        bruta = QImage(
            self._pixels,
            self.largura,
            self.altura,
            self.largura * 4,
            # Em memória é B,G,R,A (little-endian); o GDI deixa o
            # alfa em zero, então usamos RGB32, que o ignora.
            QImage.Format_RGB32
        )

        # Inverte as linhas. Os dois métodos devolvem uma CÓPIA, então
        # a QImage não depende mais do buffer de bytes acima.
        # `flipped` é o nome novo (Qt 6.9+); `mirrored` ficou obsoleto.
        if hasattr(bruta, "flipped"):
            return bruta.flipped(Qt.Vertical)

        return bruta.mirrored(False, True)

    def salvar_png(self, caminho):
        """Grava em PNG (sem perdas, e bem menor que um BMP)."""

        if not self.para_qimage().save(caminho, "PNG"):

            raise OSError(
                f"Não foi possível gravar a imagem em {caminho}."
            )

    def para_jpeg(self, lado_maximo):
        """Bytes JPEG, reduzidos para no máximo `lado_maximo` px."""

        dados = redimensionar_e_codificar_jpeg(
            self.para_qimage(),
            lado_maximo
        )

        if not dados:

            raise OSError("Não foi possível codificar a imagem.")

        return dados


class ResultadoComImagens(str):
    """
    Resultado de ferramenta que, além do texto, traz imagens para o
    modelo ver. É uma `str` de verdade (todo código que trata
    resultados como texto continua funcionando) com o atributo
    `.imagens`: lista de bytes JPEG.

    O Ollama não aceita imagens dentro de mensagens de ferramenta;
    por isso o TrabalhadorIA as entrega numa mensagem de usuário
    logo em seguida.
    """

    def __new__(cls, texto, imagens=None):

        objeto = super().__new__(cls, texto)

        objeto.imagens = list(imagens or [])

        return objeto


@dataclass(frozen=True)
class CapturaParaModelo:
    """Uma captura de tela pronta para ser enviada ao modelo."""

    imagens: list = field(default_factory=list)
    numero_monitor: int = 1
    largura: int = 0
    altura: int = 0
    shaula_ocultada: bool = False
