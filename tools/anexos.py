import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage


# ================================================================
# EXCEÇÕES
# ================================================================

class DependenciaFaltando(Exception):
    """
    Levantada quando o tipo de arquivo é suportado em tese, mas a
    biblioteca opcional necessária para processá-lo não está
    instalada (ex.: anexar um PDF sem ter o pymupdf instalado).

    Separada de "arquivo inválido" de propósito: são dois avisos
    bem diferentes para o usuário — um pede para trocar de
    arquivo, o outro pede para rodar um pip install.
    """

    def __init__(self, pacote_pip, caminho):

        self.pacote_pip = pacote_pip
        self.caminho = caminho

        super().__init__(
            f"Falta instalar '{pacote_pip}' para abrir "
            f"{os.path.basename(caminho)}"
        )


# ================================================================
# ANEXO — resultado pronto de qualquer estratégia
# ================================================================

class Anexo:
    """
    Representa um único arquivo já processado e pronto para ser
    enviado ao modelo.

    Um anexo carrega DUAS formas de conteúdo, dependendo de qual
    estratégia o gerou — nunca as duas ao mesmo tempo:

    - `imagens`: lista de bytes JPEG (uma imagem, várias páginas
      de um PDF escaneado, ou vários frames de um vídeo). Vai
      para o campo "images" da mensagem do Ollama.
    - `texto`: conteúdo extraído como texto puro (um .py, um
      .txt, ou o texto de um PDF que não é escaneado). Vai como
      um bloco de referência numa mensagem de sistema — nunca
      colado direto na mensagem do usuário (ver TrabalhadorIA em
      interface.py para o porquê).
    """

    def __init__(
        self,
        nome_arquivo,
        imagens=None,
        texto=None,
        nota_exibicao=None
    ):

        self.nome_arquivo = nome_arquivo
        self.imagens = imagens or []
        self.texto = texto

        # Texto curto usado na miniatura/nota do histórico —
        # por padrão, o próprio nome do arquivo.
        self.nota_exibicao = (
            nota_exibicao
            or nome_arquivo
        )

    @property
    def eh_imagem(self):
        return bool(self.imagens)


# ================================================================
# UTILITÁRIO COMPARTILHADO — redimensionar + codificar JPEG
# ================================================================

def redimensionar_e_codificar_jpeg(
    imagem_qt,
    lado_maximo
):
    """
    Recebe uma QImage já carregada, reduz para no máximo
    `lado_maximo` pixels no lado maior (se precisar) e devolve
    os bytes JPEG prontos. Compartilhado pela EstrategiaImagem e
    pela EstrategiaPDF (renderização de página escaneada) — o
    vídeo usa o encoder do próprio OpenCV, que é mais rápido para
    o volume de frames envolvido.
    """

    from PySide6.QtCore import QBuffer, QIODevice

    maior_lado = max(
        imagem_qt.width(),
        imagem_qt.height()
    )

    if maior_lado > lado_maximo:

        imagem_qt = imagem_qt.scaled(
            lado_maximo,
            lado_maximo,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

    buffer = QBuffer()

    buffer.open(
        QIODevice.WriteOnly
    )

    sucesso = imagem_qt.save(
        buffer,
        "JPEG",
        85
    )

    dados = bytes(
        buffer.data()
    )

    buffer.close()

    if not sucesso or not dados:
        return None

    return dados


# ================================================================
# ESTRATÉGIAS
# ================================================================

class EstrategiaAnexo:
    """
    Interface que toda estratégia de anexo segue. Mesmo desenho
    do MecanismoBusca em tools/pesquisa.py: GerenciadorAnexos não
    sabe COMO cada tipo de arquivo é lido, só pergunta "você lida
    com esse arquivo?" (suporta) e delega (processar).
    """

    EXTENSOES = frozenset()

    # MB — cada subclasse pode sobrescrever com um limite mais
    # adequado ao tipo de arquivo que ela trata.
    TAMANHO_MAXIMO_MB = 25

    def suporta(
        self,
        caminho
    ):

        _, extensao = os.path.splitext(
            caminho
        )

        return (
            extensao.lower()
            in self.EXTENSOES
        )

    def dentro_do_limite(
        self,
        caminho
    ):

        try:

            tamanho_mb = (
                os.path.getsize(caminho)
                / (1024 * 1024)
            )

        except OSError:
            return False

        return tamanho_mb <= self.TAMANHO_MAXIMO_MB

    def processar(
        self,
        caminho
    ):
        raise NotImplementedError


class EstrategiaImagem(EstrategiaAnexo):

    EXTENSOES = frozenset({
        ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif",
    })

    TAMANHO_MAXIMO_MB = 25

    # Foto de celular sem redimensionar (ex.: 4000x3000) custa
    # muito mais tempo de inferência sem ganho real de leitura —
    # ver limitações conhecidas de hardware no README.
    LADO_MAXIMO_PX = 1568

    def processar(
        self,
        caminho
    ):

        imagem = QImage(caminho)

        if imagem.isNull():
            return None

        dados = redimensionar_e_codificar_jpeg(
            imagem,
            self.LADO_MAXIMO_PX
        )

        if dados is None:
            return None

        return Anexo(
            nome_arquivo=os.path.basename(caminho),
            imagens=[dados]
        )


class EstrategiaPDF(EstrategiaAnexo):
    """
    PDF de texto (a grande maioria: artigos, contratos, manuais)
    vira TEXTO — mais barato e mais confiável para o modelo ler
    do que decifrar a página como imagem.

    PDF escaneado (só imagem, sem texto selecionável — comum em
    documentos digitalizados) cai automaticamente para
    renderizar cada página como imagem, senão o conteúdo se
    perderia por completo.
    """

    EXTENSOES = frozenset({".pdf"})

    TAMANHO_MAXIMO_MB = 50

    PAGINAS_MAXIMAS_RENDERIZADAS = 8
    CARACTERES_MAXIMOS_TEXTO = 12000

    # Menos que isso de texto extraído, em média por página,
    # tratamos como "provavelmente escaneado" e caímos para
    # imagem em vez de mandar um texto quase vazio.
    CARACTERES_MINIMOS_POR_PAGINA = 20

    def processar(
        self,
        caminho
    ):

        try:
            import pymupdf as fitz
        except ImportError:
            raise DependenciaFaltando(
                "pymupdf",
                caminho
            )

        documento = fitz.open(caminho)

        try:

            texto_paginas = [
                pagina.get_text()
                for pagina in documento
            ]

            texto_total = "\n".join(
                texto_paginas
            ).strip()

            media_por_pagina = (
                len(texto_total) / max(len(documento), 1)
            )

            eh_pdf_de_texto = (
                media_por_pagina
                >= self.CARACTERES_MINIMOS_POR_PAGINA
            )

            if eh_pdf_de_texto:
                return self._como_texto(
                    caminho,
                    documento,
                    texto_total
                )

            return self._como_imagens(
                caminho,
                documento
            )

        finally:
            documento.close()

    def _como_texto(
        self,
        caminho,
        documento,
        texto_total
    ):

        truncado = (
            len(texto_total)
            > self.CARACTERES_MAXIMOS_TEXTO
        )

        if truncado:

            texto_total = (
                texto_total[
                    :self.CARACTERES_MAXIMOS_TEXTO
                ]
                + "\n[... conteúdo truncado, PDF muito longo ...]"
            )

        nota = (
            f"{os.path.basename(caminho)} "
            f"({len(documento)} página(s))"
        )

        return Anexo(
            nome_arquivo=os.path.basename(caminho),
            texto=texto_total,
            nota_exibicao=nota
        )

    def _como_imagens(
        self,
        caminho,
        documento
    ):

        import pymupdf as fitz

        # Escala de renderização: fitz trabalha em 72 DPI por
        # padrão, o que fica ilegível para texto pequeno. 2x
        # (~144 DPI) equilibra legibilidade com o mesmo cuidado
        # de custo de inferência da EstrategiaImagem.
        matriz = fitz.Matrix(2, 2)

        imagens = []

        for pagina in documento[
            :self.PAGINAS_MAXIMAS_RENDERIZADAS
        ]:

            pixmap = pagina.get_pixmap(
                matrix=matriz
            )

            imagem_qt = QImage(
                pixmap.samples,
                pixmap.width,
                pixmap.height,
                pixmap.stride,
                (
                    QImage.Format_RGBA8888
                    if pixmap.alpha
                    else QImage.Format_RGB888
                )
            )

            dados = redimensionar_e_codificar_jpeg(
                imagem_qt,
                EstrategiaImagem.LADO_MAXIMO_PX
            )

            if dados is not None:
                imagens.append(dados)

        if not imagens:
            return None

        paginas_ignoradas = (
            len(documento) - len(imagens)
        )

        nota = (
            f"{os.path.basename(caminho)} "
            f"(PDF escaneado, {len(imagens)} página(s) lida(s)"
            + (
                f", {paginas_ignoradas} ignorada(s) por limite)"
                if paginas_ignoradas > 0
                else ")"
            )
        )

        return Anexo(
            nome_arquivo=os.path.basename(caminho),
            imagens=imagens,
            nota_exibicao=nota
        )


class EstrategiaVideo(EstrategiaAnexo):
    """
    Não existe envio de vídeo "de verdade" no Ollama local — só
    imagens. Aqui a leitura é POR AMOSTRAGEM: extrai alguns
    frames espaçados ao longo do vídeo e manda como se fossem
    várias imagens anexadas. A Shaula não "assiste" o vídeo, nem
    ouve o áudio — só vê alguns retratos dele. Isso é deixado
    claro na nota de exibição, para não passar confiança demais
    para o usuário sobre o que foi realmente analisado.
    """

    EXTENSOES = frozenset({
        ".mp4", ".mov", ".avi", ".mkv", ".webm",
    })

    TAMANHO_MAXIMO_MB = 300

    NUMERO_DE_FRAMES = 6
    LADO_MAXIMO_PX = EstrategiaImagem.LADO_MAXIMO_PX

    def processar(
        self,
        caminho
    ):

        try:
            import cv2
        except ImportError:
            raise DependenciaFaltando(
                "opencv-python-headless",
                caminho
            )

        captura = cv2.VideoCapture(
            caminho
        )

        if not captura.isOpened():
            captura.release()
            return None

        total_frames = int(
            captura.get(
                cv2.CAP_PROP_FRAME_COUNT
            )
        )

        if total_frames <= 0:
            captura.release()
            return None

        indices = self._indices_espacados(
            total_frames
        )

        imagens = []

        for indice in indices:

            captura.set(
                cv2.CAP_PROP_POS_FRAMES,
                indice
            )

            lido, frame = captura.read()

            if not lido:
                continue

            dados = self._codificar_frame(
                cv2,
                frame
            )

            if dados is not None:
                imagens.append(dados)

        captura.release()

        if not imagens:
            return None

        nota = (
            f"{os.path.basename(caminho)} "
            f"(vídeo — {len(imagens)} frame(s) de amostra, "
            "sem áudio)"
        )

        return Anexo(
            nome_arquivo=os.path.basename(caminho),
            imagens=imagens,
            nota_exibicao=nota
        )

    def _indices_espacados(
        self,
        total_frames
    ):

        quantidade = min(
            self.NUMERO_DE_FRAMES,
            total_frames
        )

        passo = total_frames / (quantidade + 1)

        return [
            int(passo * (posicao + 1))
            for posicao in range(quantidade)
        ]

    def _codificar_frame(
        self,
        cv2,
        frame
    ):

        altura, largura = frame.shape[:2]

        maior_lado = max(altura, largura)

        if maior_lado > self.LADO_MAXIMO_PX:

            escala = self.LADO_MAXIMO_PX / maior_lado

            frame = cv2.resize(
                frame,
                (
                    int(largura * escala),
                    int(altura * escala)
                )
            )

        sucesso, buffer_codificado = cv2.imencode(
            ".jpg",
            frame,
            [cv2.IMWRITE_JPEG_QUALITY, 85]
        )

        if not sucesso:
            return None

        return buffer_codificado.tobytes()


class EstrategiaTexto(EstrategiaAnexo):
    """
    Arquivos de texto puro e código-fonte — o formato mais
    simples de todos, já que o modelo lê texto nativamente sem
    nenhum processamento visual. O maior risco aqui não é
    técnico, é de PROMPT: uma tentativa anterior de anexo de
    texto foi abandonada porque o modelo ecoava fragmentos do
    arquivo em vez de seguir a instrução do usuário. A correção
    não é feita aqui — é responsabilidade de quem monta a
    mensagem final (TrabalhadorIA) isolar esse texto numa
    mensagem de sistema claramente rotulada como "referência, não
    instrução". Esta classe só entrega o texto bruto, já
    truncado por segurança.
    """

    EXTENSOES = frozenset({
        ".txt", ".md", ".markdown", ".log", ".csv",
        ".json", ".yaml", ".yml", ".xml", ".ini", ".cfg",
        ".py", ".js", ".ts", ".java", ".c", ".cpp", ".h",
        ".cs", ".sql", ".bat", ".sh", ".html", ".css",
    })

    TAMANHO_MAXIMO_MB = 5

    CARACTERES_MAXIMOS = 12000

    def processar(
        self,
        caminho
    ):

        conteudo = self._ler_com_fallback_de_codificacao(
            caminho
        )

        if conteudo is None:
            return None

        truncado = (
            len(conteudo) > self.CARACTERES_MAXIMOS
        )

        if truncado:

            conteudo = (
                conteudo[:self.CARACTERES_MAXIMOS]
                + "\n[... conteúdo truncado, arquivo muito "
                "longo ...]"
            )

        return Anexo(
            nome_arquivo=os.path.basename(caminho),
            texto=conteudo
        )

    def _ler_com_fallback_de_codificacao(
        self,
        caminho
    ):

        for codificacao in ("utf-8", "latin-1"):

            try:

                with open(
                    caminho,
                    "r",
                    encoding=codificacao
                ) as arquivo:

                    return arquivo.read()

            except (UnicodeDecodeError, OSError):
                continue

        return None


# ================================================================
# GERENCIADOR — fachada única usada pela interface
# ================================================================

class GerenciadorAnexos:
    """
    Ponto único que a interface usa para lidar com anexos. Não
    sabe nada sobre PySide6 além do necessário para decodificar
    imagens — delega todo o trabalho pesado às estratégias.
    """

    def __init__(self):

        self.estrategias = [
            EstrategiaImagem(),
            EstrategiaPDF(),
            EstrategiaVideo(),
            EstrategiaTexto(),
        ]

    def caminho_valido(
        self,
        caminho
    ):

        return any(
            estrategia.suporta(caminho)
            for estrategia in self.estrategias
        )

    def filtro_dialogo(self):
        """
        Monta a string de filtro do QFileDialog a partir das
        extensões de todas as estratégias — assim, adicionar uma
        estratégia nova no futuro não exige lembrar de atualizar
        o diálogo em interface.py separadamente.
        """

        todas_extensoes = sorted(
            extensao
            for estrategia in self.estrategias
            for extensao in estrategia.EXTENSOES
        )

        padroes = " ".join(
            f"*{extensao}"
            for extensao in todas_extensoes
        )

        return f"Arquivos suportados ({padroes})"

    def carregar(
        self,
        caminho
    ):
        """
        Devolve um Anexo pronto, ou None se o arquivo não existe,
        não é de um tipo suportado, ou passou do limite de
        tamanho daquele tipo.

        Deixa DependenciaFaltando propagar para quem chamou —
        é um aviso acionável (rodar um pip install), diferente
        de "esse arquivo não é suportado".
        """

        if not os.path.isfile(caminho):
            return None

        for estrategia in self.estrategias:

            if not estrategia.suporta(caminho):
                continue

            if not estrategia.dentro_do_limite(caminho):
                return None

            try:
                return estrategia.processar(caminho)
            except DependenciaFaltando:
                raise
            except Exception:
                # Qualquer outra falha ao processar (arquivo
                # corrompido, PDF protegido por senha, etc.)
                # vira "não foi possível anexar" — sem derrubar a
                # Shaula.
                return None

        return None
