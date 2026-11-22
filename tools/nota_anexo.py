import os
import re


class DescricaoAnexo:
    """
    O que o chat mostra de um arquivo enviado: nome, formato (a
    extensão em maiúsculas, como "PDF") e um detalhe opcional ("128
    página(s)"). Também diz de que TIPO o arquivo é, para a interface
    escolher o ícone e a cor.
    """

    IMAGENS = frozenset({
        ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif",
    })

    VIDEOS = frozenset({
        ".mp4", ".mov", ".avi", ".mkv", ".webm",
    })

    CODIGOS = frozenset({
        ".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".cs",
        ".sql", ".bat", ".sh", ".html", ".css", ".json", ".yaml",
        ".yml", ".xml", ".ini", ".cfg",
    })

    TEXTOS = frozenset({
        ".txt", ".md", ".markdown", ".log", ".csv",
    })

    def __init__(self, nome, detalhe=None):

        self.nome = nome

        self.detalhe = detalhe or None

    @property
    def extensao(self):

        return os.path.splitext(self.nome)[1].lower()

    @property
    def formato(self):
        """Rótulo curto do formato: "PDF", "PNG", "PY"..."""

        return self.extensao.lstrip(".").upper() or "ARQ"

    @property
    def tipo(self):
        """"pdf", "imagem", "video", "codigo", "texto" ou "outro"."""

        extensao = self.extensao

        if extensao == ".pdf":
            return "pdf"

        if extensao in self.IMAGENS:
            return "imagem"

        if extensao in self.VIDEOS:
            return "video"

        if extensao in self.CODIGOS:
            return "codigo"

        if extensao in self.TEXTOS:
            return "texto"

        return "outro"

    @property
    def linha_detalhe(self):
        """Segunda linha do cartão: o formato e, se houver, o detalhe."""

        if not self.detalhe:
            return self.formato

        return f"{self.formato} · {self.detalhe}"


class NotaAnexo:
    """
    A nota que a Shaula grava no histórico quando uma mensagem leva
    arquivos:

        [2 arquivo(s) anexado(s): a.pdf (12 página(s)), b.png]

    O MODELO lê essa nota (é como ele sabe que um arquivo foi enviado
    naquele ponto da conversa), então o formato dela não muda. Já a
    TELA não precisa mostrar o texto cru: `separar()` tira a nota do
    texto e devolve uma DescricaoAnexo por arquivo, para a interface
    desenhar um cartão — tanto na hora do envio quanto ao reabrir uma
    conversa antiga.
    """

    _NOTA = re.compile(
        r"(?:\n\n)?\[(\d+) arquivo\(s\) anexado\(s\): (.*)\]\Z",
        re.S
    )

    _ITEM = re.compile(
        r"^(?P<nome>.+?\.[^\s.()]{1,8})"
        r"(?:\s*\((?P<detalhe>.*)\))?$",
        re.S
    )

    def montar(self, notas_exibicao):
        """Texto da nota a partir de Anexo.nota_exibicao de cada arquivo."""

        return (
            f"[{len(notas_exibicao)} arquivo(s) "
            f"anexado(s): {', '.join(notas_exibicao)}]"
        )

    def anexar_ao_texto(self, texto, notas_exibicao):
        """Texto do usuário + nota (ou só a nota, se não houver texto)."""

        if not notas_exibicao:
            return texto

        nota = self.montar(notas_exibicao)

        return f"{texto}\n\n{nota}" if texto else nota

    def separar(self, texto):
        """
        (texto sem a nota, [DescricaoAnexo]). Sem nota no fim do texto,
        devolve o texto como veio e uma lista vazia.
        """

        texto = str(texto or "")

        achou = self._NOTA.search(texto)

        if not achou:
            return texto, []

        itens = self._dividir_itens(
            achou.group(2),
            int(achou.group(1))
        )

        descricoes = [self._descrever(item) for item in itens]

        return texto[:achou.start()].rstrip(), descricoes

    def _dividir_itens(self, lista, esperado):
        """
        Divide a lista pelas vírgulas que estão FORA de parênteses (os
        detalhes têm vírgulas: "PDF escaneado, 3 página(s) lida(s)").
        Se um nome de arquivo tiver ", " dentro, os pedaços sem extensão
        são recolados ao seguinte.
        """

        partes = []

        atual = ""

        profundidade = 0

        i = 0

        while i < len(lista):

            c = lista[i]

            if c == "(":
                profundidade += 1
            elif c == ")":
                profundidade = max(profundidade - 1, 0)

            if (
                c == ","
                and profundidade == 0
                and lista[i + 1:i + 2] == " "
            ):
                partes.append(atual)
                atual = ""
                i += 2
                continue

            atual += c

            i += 1

        partes.append(atual)

        if len(partes) > esperado:

            colados = []

            pendente = ""

            for parte in partes:

                candidato = f"{pendente}, {parte}" if pendente else parte

                if self._ITEM.match(candidato):
                    colados.append(candidato)
                    pendente = ""
                else:
                    pendente = candidato

            if pendente:
                colados.append(pendente)

            partes = colados

        return partes

    def _descrever(self, item):

        item = item.strip()

        achou = self._ITEM.match(item)

        if not achou:
            return DescricaoAnexo(item)

        nome = achou.group("nome")

        detalhe = achou.group("detalhe")

        if detalhe:

            formato = DescricaoAnexo(nome).formato

            prefixo = formato.lower() + " "

            # "PDF escaneado, 3 página(s)" vira "escaneado, 3 página(s)":
            # o formato já aparece na linha do cartão.
            if detalhe.lower().startswith(prefixo):
                detalhe = detalhe[len(prefixo):]

        return DescricaoAnexo(nome, detalhe)
