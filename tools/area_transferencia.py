import os

from PySide6.QtGui import QImage, QPixmap


class ConteudoColado:
    """
    O que há de aproveitável na área de transferência quando o
    usuário aperta Ctrl+V no campo de mensagem:

    - ARQUIVOS: arquivos copiados no Explorer (caminhos locais);
    - IMAGEM: uma imagem copiada (print da tela, "Copiar imagem" do
      navegador...), já como QImage;
    - TEXTO: qualquer outra coisa — o campo cola como sempre.
    """

    ARQUIVOS = "arquivos"

    IMAGEM = "imagem"

    TEXTO = "texto"

    def __init__(
        self,
        tipo,
        caminhos=None,
        imagem=None
    ):

        self.tipo = tipo

        self.caminhos = caminhos or []

        self.imagem = imagem

    @property
    def eh_arquivos(self):
        return self.tipo == self.ARQUIVOS

    @property
    def eh_imagem(self):
        return self.tipo == self.IMAGEM

    @property
    def eh_texto(self):
        return self.tipo == self.TEXTO


class InterpretadorAreaTransferencia:
    """
    Decide o que fazer com um QMimeData colado. Só olha e classifica
    — quem anexa (ou cola o texto) é o campo de mensagem e a janela.

    Ordem de prioridade:

    1. Arquivos locais copiados no Explorer viram anexos, igual a
       arrastar-e-soltar.
    2. Imagem copiada vira anexo. Exceção: se vier junto um texto de
       verdade (copiar células do Excel traz o texto E uma imagem da
       tabela), o texto ganha — a menos que o HTML da área de
       transferência contenha uma <img>, que é o caso de "Copiar
       imagem" nos navegadores.
    3. O resto é texto, colado normalmente.
    """

    def interpretar(
        self,
        mime
    ):

        caminhos = self._caminhos_locais(
            mime
        )

        if caminhos:

            return ConteudoColado(
                ConteudoColado.ARQUIVOS,
                caminhos=caminhos
            )

        if mime.hasImage() and self._imagem_vale_mais_que_o_texto(
            mime
        ):

            imagem = self._imagem_do(
                mime
            )

            if imagem is not None:

                return ConteudoColado(
                    ConteudoColado.IMAGEM,
                    imagem=imagem
                )

        return ConteudoColado(
            ConteudoColado.TEXTO
        )

    def _caminhos_locais(
        self,
        mime
    ):
        """Arquivos locais que existem; pastas e links da web não contam."""

        if not mime.hasUrls():
            return []

        return [
            url.toLocalFile()
            for url in mime.urls()
            if url.isLocalFile()
            and os.path.isfile(
                url.toLocalFile()
            )
        ]

    def _imagem_vale_mais_que_o_texto(
        self,
        mime
    ):

        texto = (
            mime.text().strip()
            if mime.hasText()
            else ""
        )

        if not texto:
            return True

        html = (
            mime.html().lower()
            if mime.hasHtml()
            else ""
        )

        return "<img" in html

    def _imagem_do(
        self,
        mime
    ):
        """A imagem como QImage, ou None se não der para decodificar."""

        dados = mime.imageData()

        if isinstance(
            dados,
            QPixmap
        ):

            dados = dados.toImage()

        if not isinstance(
            dados,
            QImage
        ):

            return None

        if dados.isNull():

            return None

        return dados
