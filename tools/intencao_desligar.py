import re
import unicodedata


class NormalizadorTexto:
    """Minúsculas, sem acento e com espaços simples."""

    def normalizar(self, texto):

        sem_acento = unicodedata.normalize("NFD", str(texto or ""))

        sem_acento = "".join(
            c for c in sem_acento if unicodedata.category(c) != "Mn"
        )

        return re.sub(r"\s+", " ", sem_acento.lower()).strip()


class InterpretadorTempo:
    """
    Extrai o atraso dito na frase ("em 30 segundos", "daqui a 2
    minutos", "agora") já normalizada e devolve os argumentos de
    desligar_computador. Sem tempo dito = {} (a ferramenta usa o
    padrão de AtrasoDesligamento).
    """

    _TEMPO = re.compile(
        r"\b(?:em|daqui(?:\s+a)?|dentro\s+de|depois\s+de)\s+"
        r"(\d+)\s*"
        r"(segundos?|seg|s|minutos?|min|horas?|h)\b"
    )

    _AGORA = re.compile(r"\b(?:agora|imediatamente|ja)\b")

    def interpretar(self, texto_normalizado):

        tempo = self._TEMPO.search(texto_normalizado)

        if tempo:

            valor = int(tempo.group(1))

            unidade = tempo.group(2)

            if unidade.startswith("h"):
                valor *= 3600
            elif unidade.startswith("m"):
                valor *= 60

            return {"segundos": valor}

        if self._AGORA.search(texto_normalizado):
            return {"segundos": 0}

        return {}

    def sem_tempo(self, texto_normalizado):
        """O texto sem as expressões de tempo ("em 30 segundos", "agora")."""

        sem_prazo = self._TEMPO.sub(" ", texto_normalizado)

        return self._AGORA.sub(" ", sem_prazo)


class DetectorDesligar:
    """
    Reconhece, sem passar pelo modelo, um PEDIDO claro para desligar o
    computador ("desligue o computador", "desliga o pc em 30 segundos").

    Por quê: o Qwen local às vezes responde em texto ("ok, desligando")
    ou pergunta o tempo em vez de chamar desligar_computador — e sem a
    chamada a caixa de confirmação nunca aparece. Com este atalho a
    chamada acontece sempre; quem decide é o usuário, na caixa.

    Perguntas ("como desligar o pc?"), negações ("não desligue o pc") e
    textos longos não disparam nada: nesses casos o modelo responde.

    Os colaboradores (normalizador e interpretador de tempo) são
    injetados, como o Confirmador no RegistroFerramentas, e podem ser
    trocados em testes.
    """

    TAMANHO_MAXIMO = 200

    _PEDIDO = re.compile(
        r"\b(?:desligue|desliga|desligar)\s+"
        r"(?:agora\s+|ja\s+)?"
        r"(?:o\s+|meu\s+|esse\s+|este\s+|a\s+)?"
        r"(?:computador|pc|notebook|laptop|maquina)\b"
    )

    _NAO_E_PEDIDO = re.compile(
        r"^\s*(?:como|qual|quais|por\s?que|o\s+que|quando|onde|quem|"
        r"se\s+eu|e\s+se)\b"
        r"|\b(?:nao|nunca|cancel\w*|pare\s+de|para\s+de|sem)\b"
    )

    # "você pode desligar o pc?" é um pedido educado; "desligar o computador
    # é perigoso?" é uma pergunta sobre o assunto.
    _PEDIDO_EDUCADO = re.compile(
        r"^(?:(?:por\s+favor|shaula|ei|oi|ola)[,\s]+)*"
        r"(?:voce\s+)?(?:pode|poderia|consegue|vai)\b"
    )

    # Palavras que mostram que a frase pede MAIS que desligar, ou
    # desligar sob condição. O atalho pula o modelo e só sabe desligar:
    # em "desligue o pc depois de baixar o arquivo" ele desligaria já,
    # ignorando o resto do pedido.
    _CONTINUACAO = re.compile(
        r"\b(?:e|depois|antes|mas|porem|quando|enquanto|apos|se)\b"
    )

    def __init__(self, normalizador=None, interpretador=None):

        self._normalizador = normalizador or NormalizadorTexto()

        self._interpretador = interpretador or InterpretadorTempo()

    def argumentos(self, texto):
        """
        Dicionário de argumentos para desligar_computador, ou None se o
        texto não for um pedido claro.
        """

        t = self._normalizador.normalizar(texto)

        if not t or len(t) > self.TAMANHO_MAXIMO:
            return None

        if self._NAO_E_PEDIDO.search(t):
            return None

        if t.endswith("?") and not self._PEDIDO_EDUCADO.search(t):
            return None

        pedido = self._PEDIDO.search(t)

        if not pedido:
            return None

        resto = self._interpretador.sem_tempo(
            t[:pedido.start()] + " " + t[pedido.end():]
        )

        if self._CONTINUACAO.search(resto):
            return None

        return self._interpretador.interpretar(t)
