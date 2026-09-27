import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from abc import ABC, abstractmethod


# ============================================================
# FORMATAÇÃO DE TEXTO (linkificação, extração de URLs)
# ============================================================

class FormatadorTexto:
    """
    Utilitários de formatação de texto relacionados a pesquisa:
    transformar links em HTML clicável e extrair URLs de um
    texto simples. Agrupados numa classe (métodos estáticos)
    porque são funções puras, sem estado — não precisam de
    instância, só de um "dono" organizacional.
    """

    _PADRAO_LINK_MARKDOWN = re.compile(
        r"\[([^\]\n]+)\]\((https?://[^\s\)]+)\)"
    )

    _PADRAO_URL_BRUTA = re.compile(
        r'(?<!["\'>])\bhttps?://[^\s<>\)\]"\']+'
    )

    _PADRAO_URL_TEXTO = re.compile(
        r"https?://\S+"
    )

    @staticmethod
    def linkificar_html(texto_html):
        """
        Converte links no estilo markdown ([texto](url)) e URLs
        soltas (ex.: "URL: https://exemplo.com") em tags <a>
        clicáveis, para que apareçam como link de verdade na
        conversa em vez de texto cru.

        Recebe o texto QUE JÁ FOI ESCAPADO (&, <, > substituídos),
        então é seguro aplicar essas substituições por cima sem
        risco de injeção de HTML vindo de conteúdo pesquisado na
        internet.
        """

        def _sub_markdown(correspondencia):

            rotulo = correspondencia.group(1)
            url = correspondencia.group(2)

            return (
                f'<a href="{url}" '
                f'style="color:#8AB4F8;">'
                f'{rotulo}</a>'
            )

        texto_html = FormatadorTexto._PADRAO_LINK_MARKDOWN.sub(
            _sub_markdown,
            texto_html
        )

        def _sub_bruta(correspondencia):

            url = correspondencia.group(0)

            return (
                f'<a href="{url}" '
                f'style="color:#8AB4F8;">'
                f'{url}</a>'
            )

        texto_html = FormatadorTexto._PADRAO_URL_BRUTA.sub(
            _sub_bruta,
            texto_html
        )

        return texto_html

    @staticmethod
    def extrair_urls(texto):
        """
        Extrai todas as URLs de um texto simples (não-HTML).
        Usado para conferir se a resposta final do modelo já
        cita as fontes retornadas pela pesquisa.
        """

        return FormatadorTexto._PADRAO_URL_TEXTO.findall(
            texto
        )


# ============================================================
# DETECÇÃO DE PERGUNTA FACTUAL
# ============================================================

class DetectorPerguntaFactual:
    """
    Decide, de forma determinística (sem depender do modelo),
    se uma mensagem do usuário parece ser uma pergunta sobre
    fatos — e portanto vale a pena pesquisar automaticamente
    quando a internet estiver ligada.

    Isso existe porque confiar só no modelo para decidir
    "preciso pesquisar isso?" se mostrou pouco confiável na
    prática: a mesma pergunta às vezes disparava uma pesquisa,
    às vezes não. Uma heurística simples é mais previsível,
    mesmo que não seja perfeita — é intencionalmente permissiva
    (prefere pesquisar demais a pesquisar de menos).
    """

    PALAVRAS_INTERROGATIVAS = (
        "quem",
        "o que",
        "oque",
        "quando",
        "onde",
        "como",
        "por que",
        "porque",
        "pra que",
        "para que",
        "qual",
        "quais",
        "quanto",
        "quantos",
        "quanta",
        "quantas",
        "existe",
        "existem",
        "é verdade",
        "verdade que",
    )

    @classmethod
    def parece_factual(cls, texto):

        texto_normalizado = (
            texto
            .strip()
            .lower()
        )

        if not texto_normalizado:

            return False

        if texto_normalizado.endswith(
            (
                "?",
                "？"
            )
        ):

            return True

        for palavra in cls.PALAVRAS_INTERROGATIVAS:

            if texto_normalizado.startswith(
                palavra + " "
            ):

                return True

        return False


# ============================================================
# PARSERS DE HTML DOS MECANISMOS DE BUSCA
# ============================================================

class DuckParser(HTMLParser):
    """
    Extrai título, URL e o trecho de texto (snippet) de cada
    resultado da página de busca do DuckDuckGo (versão HTML
    sem Javascript).

    Estrutura por resultado:
        <a class="result__a" href="...">Título</a>
        <a class="result__snippet" href="...">Trecho do texto...</a>

    O título e o snippet vêm em duas tags <a> separadas, uma
    logo depois da outra — por isso um resultado só é fechado
    (adicionado a self.resultados) quando o próximo resultado
    começa, ou quando finalizar() é chamado no final do feed.
    """

    def __init__(self):

        super().__init__()

        self.resultados = []

        self._pendente = None
        self._modo = None  # None | "titulo" | "snippet"

    def handle_starttag(self, tag, attrs):

        if tag != "a":
            return

        atributos = dict(attrs)

        classe = atributos.get("class", "") or ""
        href = atributos.get("href", "")

        if "result__a" in classe:

            self._fechar_pendente()

            self._pendente = {
                "titulo": "",
                "url": href,
                "snippet": ""
            }

            self._modo = "titulo"

        elif (
            "result__snippet" in classe
            and self._pendente is not None
        ):

            self._modo = "snippet"

    def handle_data(self, data):

        if self._pendente is None:
            return

        if self._modo == "titulo":

            self._pendente["titulo"] += data

        elif self._modo == "snippet":

            self._pendente["snippet"] += data

    def handle_endtag(self, tag):

        if tag == "a":

            self._modo = None

    def _fechar_pendente(self):

        if (
            self._pendente
            and self._pendente.get("titulo")
        ):

            self._pendente["titulo"] = " ".join(
                self._pendente["titulo"].split()
            )

            self._pendente["snippet"] = " ".join(
                self._pendente["snippet"].split()
            )

            self.resultados.append(
                self._pendente
            )

        self._pendente = None

    def finalizar(self):
        """
        Chame depois de feed() — fecha o último resultado
        pendente, que não tem um próximo resultado para
        disparar o fechamento automático.
        """

        self._fechar_pendente()


class BingParser(HTMLParser):
    """
    Extrai título, URL e snippet dos resultados do Bing —
    usado como mecanismo de busca reserva, caso o DuckDuckGo
    falhe ou não retorne nada (bloqueio temporário, instável
    etc.).

    Estrutura por resultado:
        <li class="b_algo">
            <h2><a href="...">Título</a></h2>
            ...
            <div class="b_caption"><p>Trecho do texto...</p></div>
        </li>
    """

    def __init__(self):

        super().__init__()

        self.resultados = []

        self._em_algo = False
        self._profundidade_li = 0

        self._em_h2 = False
        self._titulo_capturado = False

        self._em_caption = False
        self._profundidade_caption_div = 0
        self._em_p = False

        self._pendente = None

    def handle_starttag(self, tag, attrs):

        atributos = dict(attrs)
        classe = atributos.get("class", "") or ""

        if tag == "li" and "b_algo" in classe:

            self._em_algo = True
            self._profundidade_li = 1
            self._pendente = {
                "titulo": "",
                "url": "",
                "snippet": ""
            }
            return

        if not self._em_algo:
            return

        if tag == "li":

            self._profundidade_li += 1
            return

        if tag == "h2":

            self._em_h2 = True
            self._titulo_capturado = False
            return

        if (
            tag == "a"
            and self._em_h2
            and not self._titulo_capturado
        ):

            href = atributos.get("href", "")

            if href and self._pendente is not None:

                self._pendente["url"] = href

            return

        if tag == "div" and "b_caption" in classe:

            self._em_caption = True
            self._profundidade_caption_div = 1
            return

        if self._em_caption and tag == "div":

            self._profundidade_caption_div += 1
            return

        if (
            self._em_caption
            and tag == "p"
            and self._pendente is not None
            and not self._pendente["snippet"]
        ):

            self._em_p = True
            return

    def handle_data(self, data):

        if self._pendente is None:
            return

        if self._em_h2 and not self._titulo_capturado:

            self._pendente["titulo"] += data

        elif self._em_p:

            self._pendente["snippet"] += data

    def handle_endtag(self, tag):

        if tag == "h2" and self._em_h2:

            self._em_h2 = False
            self._titulo_capturado = True

        elif tag == "p" and self._em_p:

            self._em_p = False

        elif tag == "div" and self._em_caption:

            self._profundidade_caption_div -= 1

            if self._profundidade_caption_div <= 0:

                self._em_caption = False

        elif tag == "li" and self._em_algo:

            self._profundidade_li -= 1

            if self._profundidade_li <= 0:

                self._em_algo = False

                if (
                    self._pendente
                    and self._pendente.get("titulo")
                    and self._pendente.get("url")
                ):

                    self._pendente["titulo"] = " ".join(
                        self._pendente["titulo"].split()
                    )

                    self._pendente["snippet"] = " ".join(
                        self._pendente["snippet"].split()
                    )

                    self.resultados.append(
                        self._pendente
                    )

                self._pendente = None


# ============================================================
# MECANISMOS DE BUSCA (Strategy pattern)
# ============================================================
#
# MecanismoBusca é a interface comum; DuckDuckGo e Bing são
# implementações concretas. PesquisaInternet (mais abaixo) tenta
# cada mecanismo em ordem até um funcionar — trocar a ordem, ou
# adicionar um novo mecanismo, não exige mudar mais nada além de
# criar uma nova classe MecanismoBusca e adicionar na lista.

_USER_AGENT = (
    "Mozilla/5.0 "
    "(Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 "
    "(KHTML, like Gecko) "
    "Chrome/131.0 Safari/537.36"
)


class MecanismoBusca(ABC):

    @property
    @abstractmethod
    def nome(self):
        """Nome do mecanismo, usado para indicar a fonte da pesquisa."""

        raise NotImplementedError

    @abstractmethod
    def buscar(self, consulta):
        """
        Executa a busca. Devolve uma tupla (resultados, erro):
        resultados é uma lista de dicts {"titulo","snippet","url"},
        erro é None em caso de sucesso ou uma string descrevendo
        o problema.
        """

        raise NotImplementedError

    def _requisitar_html(self, url):

        requisicao = urllib.request.Request(
            url,
            headers={"User-Agent": _USER_AGENT}
        )

        with urllib.request.urlopen(
            requisicao,
            timeout=10
        ) as resposta:

            return resposta.read().decode(
                "utf-8",
                errors="ignore"
            )


class DuckDuckGo(MecanismoBusca):

    @property
    def nome(self):
        return "DuckDuckGo"

    def _limpar_url(self, url):

        if not url:

            return url

        try:

            url_completa = urllib.parse.urljoin(
                "https://html.duckduckgo.com",
                url
            )

            partes = urllib.parse.urlparse(
                url_completa
            )

            parametros = urllib.parse.parse_qs(
                partes.query
            )

            if "uddg" in parametros:

                destino = parametros["uddg"][0]

                return urllib.parse.unquote(
                    destino
                )

        except Exception:

            pass

        return url

    def buscar(self, consulta):

        try:

            url = (
                "https://html.duckduckgo.com/html/?q="
                + urllib.parse.quote(consulta)
            )

            html = self._requisitar_html(url)

            parser = DuckParser()

            parser.feed(html)
            parser.finalizar()

            resultados = []

            for resultado in parser.resultados[:7]:

                resultados.append({
                    "titulo": resultado["titulo"],
                    "snippet": resultado.get("snippet", ""),
                    "url": self._limpar_url(
                        resultado["url"]
                    )
                })

            return resultados, None

        except Exception as erro:

            return [], str(erro)


class Bing(MecanismoBusca):

    @property
    def nome(self):
        return "Bing"

    def buscar(self, consulta):

        try:

            url = (
                "https://www.bing.com/search?q="
                + urllib.parse.quote(consulta)
            )

            html = self._requisitar_html(url)

            parser = BingParser()

            parser.feed(html)

            resultados = []

            for resultado in parser.resultados[:7]:

                resultados.append({
                    "titulo": resultado["titulo"],
                    "snippet": resultado.get("snippet", ""),
                    "url": resultado["url"]
                })

            return resultados, None

        except Exception as erro:

            return [], str(erro)


# ============================================================
# ORQUESTRADOR DA PESQUISA
# ============================================================

class PesquisaInternet:
    """
    Orquestra a pesquisa: checa se a internet está ligada, tenta
    cada MecanismoBusca em ordem até um devolver resultados, e
    formata a resposta final em texto.

    Recebe um EstadoInternet (ver internet.py) em vez de ler uma
    variável global — assim não depende de nenhum estado
    compartilhado implícito.
    """

    def __init__(self, estado_internet, mecanismos=None):

        self.estado_internet = estado_internet

        self.mecanismos = (
            mecanismos
            if mecanismos is not None
            else [DuckDuckGo(), Bing()]
        )

    def buscar(self, consulta):

        if not self.estado_internet.ativa:

            return (
                "A internet está desativada. "
                "Não foi realizada nenhuma pesquisa externa. "
                "Para consultar informações atuais ou fontes "
                "da internet, ative a internet pelo botão."
            )

        consulta = str(consulta).strip()

        if not consulta:

            return "Nenhuma pesquisa foi informada."

        resultados = []
        fonte = None
        erros = {}

        for mecanismo in self.mecanismos:

            resultados_mecanismo, erro = mecanismo.buscar(
                consulta
            )

            if resultados_mecanismo:

                resultados = resultados_mecanismo
                fonte = mecanismo.nome

                break

            if erro:

                erros[mecanismo.nome] = erro

        if not resultados:

            # Só reportamos como "falha técnica" se TODOS os
            # mecanismos tentados realmente deram erro — se
            # algum simplesmente não achou nada (sem erro), é
            # só "não encontrei resultados", não uma falha.
            if erros and len(erros) == len(self.mecanismos):

                linhas_erro = "\n".join(
                    f"{nome}: {erro}"
                    for nome, erro in erros.items()
                )

                return (
                    "Não consegui realizar a pesquisa na "
                    "internet (todos os mecanismos de busca "
                    f"falharam).\n{linhas_erro}"
                )

            return (
                "Não encontrei resultados para "
                f"'{consulta}'."
            )

        saida = [
            f"Resultados da pesquisa para: {consulta}",
            f"(fonte: {fonte})",
            "",
            "Use os resultados abaixo como fontes.",
            ""
        ]

        for i, resultado in enumerate(resultados, start=1):

            titulo = resultado["titulo"]

            snippet = resultado.get(
                "snippet",
                ""
            ).strip()

            url_real = resultado["url"]

            saida.append(f"{i}. {titulo}")

            if snippet:

                if len(snippet) > 300:

                    snippet = (
                        snippet[:300].rstrip() + "..."
                    )

                saida.append(f"Resumo: {snippet}")

            saida.append(f"URL: {url_real}")

            saida.append("")

        return "\n".join(saida)
