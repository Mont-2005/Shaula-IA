import re

from .intencao_desligar import NormalizadorTexto


class ComandosLocais:
    """
    Frases que a Shaula trata sozinha, sem chamar o modelo: fechar a
    Shaula e apagar a conversa.

    SAÍDA tolera pontuação e o nome dela na frente ("Sair.", "Shaula,
    pode fechar!"): a transcrição de voz devolve o texto pontuado, e
    com a comparação exata o comando falado nunca funcionava. Fechar a
    Shaula não perde nada.

    APAGAR A CONVERSA continua exigindo a frase exata, sem pontuação
    nem palavras a mais: é irreversível e não pede confirmação, então
    uma frase falada e mal reconhecida não pode apagar o histórico.

    Maiúsculas e acentos não importam em nenhum dos dois.
    """

    FRASES_SAIDA = frozenset({
        "sair", "fechar", "feche", "encerre", "encerrar",
        "fechar shaula", "feche a shaula", "encerre a shaula",
        "sair da shaula",
        "pode sair", "pode fechar", "pode encerrar",
    })

    FRASES_APAGAR_CONVERSA = frozenset({
        "excluir conversa", "apagar conversa", "limpar conversa",
        "esquecer conversa", "excluir historico", "apagar historico",
        "esquecer tudo", "limpar memoria", "apagar memoria",
    })

    _PONTUACAO = re.compile(r"[.!?,;:]+")

    def __init__(self, normalizador=None):

        self._normalizador = normalizador or NormalizadorTexto()

    def eh_saida(self, texto):

        t = self._normalizador.normalizar(texto)

        t = " ".join(self._PONTUACAO.sub(" ", t).split())

        if t in self.FRASES_SAIDA:
            return True

        return (
            t.startswith("shaula ")
            and t[len("shaula "):] in self.FRASES_SAIDA
        )

    def eh_apagar_conversa(self, texto):

        return (
            self._normalizador.normalizar(texto)
            in self.FRASES_APAGAR_CONVERSA
        )
