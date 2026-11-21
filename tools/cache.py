import os

from .armazenamento import ArmazenamentoJson


class CacheComandos:
    """
    Cache persistente, em disco, para a Shaula memorizar coisas
    que já custaram tempo para descobrir uma vez — como o
    caminho completo de um arquivo já encontrado numa busca
    anterior, ou em qual monitor um programa costuma ficar.

    Antes disso era um módulo com funções soltas operando sobre
    duas variáveis globais (PASTA_CACHE/ARQUIVO_CACHE). Como
    classe, o caminho do arquivo é injetável pelo construtor —
    útil tanto para testes (cada teste usa uma pasta temporária
    isolada, sem precisar mexer em estado global) quanto para,
    no futuro, ter mais de um cache independente se for preciso.

    Formato do arquivo (JSON):
    {
        "arquivos": {"relatorio.docx@perfil": "C:\\Users\\...\\relatorio.docx"},
        "monitores": {"firefox": 2}
    }
    """

    def __init__(self, caminho_arquivo=None):

        if caminho_arquivo is None:

            pasta_padrao = os.path.join(
                os.path.expanduser("~"),
                ".shaula"
            )

            caminho_arquivo = os.path.join(
                pasta_padrao,
                "cache_comandos.json"
            )

        self.caminho_arquivo = caminho_arquivo

        self._armazenamento = ArmazenamentoJson(
            caminho_arquivo
        )

    def _carregar_bruto(self):

        dados = self._armazenamento.ler(padrao={})

        # Cache corrompido ou ilegível: em vez de travar a
        # Shaula, tratamos como cache vazio.
        if not isinstance(dados, dict):
            return {}

        return dados

    def _salvar_bruto(self, dados):

        # Se não conseguirmos salvar o cache, não é motivo para
        # travar a operação que estava sendo feita — a Shaula
        # simplesmente vai continuar sem memorizar isso.
        return self._armazenamento.gravar(dados)

    def obter(self, categoria, chave):
        """Retorna o valor memorizado, ou None se não existir."""

        dados = self._carregar_bruto()

        return dados.get(
            categoria,
            {}
        ).get(
            chave
        )

    def definir(self, categoria, chave, valor):
        """Memoriza um valor para (categoria, chave)."""

        with self._armazenamento.trava:

            dados = self._carregar_bruto()

            dados.setdefault(
                categoria,
                {}
            )[chave] = valor

            self._salvar_bruto(dados)

    def remover(self, categoria, chave):
        """
        Remove uma entrada memorizada (por exemplo, quando o
        caminho memorizado não existe mais no disco).
        """

        with self._armazenamento.trava:

            dados = self._carregar_bruto()

            if (
                categoria in dados
                and chave in dados[categoria]
            ):

                del dados[categoria][chave]

                self._salvar_bruto(dados)

    def limpar_categoria(self, categoria):
        """
        Apaga tudo o que foi memorizado numa categoria (ex.: só
        os caminhos de arquivo, mantendo o resto).
        """

        with self._armazenamento.trava:

            dados = self._carregar_bruto()

            if categoria in dados:

                dados[categoria] = {}

                self._salvar_bruto(dados)

    def limpar_tudo(self):
        """Apaga todo o cache de comandos memorizados."""

        self._salvar_bruto({})
