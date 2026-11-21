import json
import os
import threading
import time


class ArmazenamentoJson:
    """
    Leitura e escrita de um arquivo JSON de forma segura.

    Por que existe: conversas.py, memoria.py e cache.py gravavam
    direto com open(caminho, "w"), o que trunca o arquivo ANTES de
    escrever o conteúdo novo. Se o programa fosse fechado (ou o
    Windows reiniciasse) nesse intervalo, ou se duas janelas da
    Shaula gravassem o mesmo índice ao mesmo tempo, o arquivo
    ficava vazio/cortado — e o código tratava JSON inválido como
    "lista vazia", fazendo as conversas sumirem da barra lateral.

    Aqui a gravação é atômica (escreve num arquivo temporário e só
    depois troca pelo definitivo com os.replace) e protegida por
    uma trava por caminho, compartilhada por todas as instâncias
    do processo (todas as janelas da Shaula vivem no mesmo
    processo).
    """

    TENTATIVAS_DE_TROCA = 5
    ESPERA_ENTRE_TENTATIVAS_S = 0.05

    _travas_por_caminho = {}
    _trava_das_travas = threading.Lock()

    def __init__(self, caminho):

        self.caminho = os.path.abspath(caminho)

    @property
    def trava(self):
        """
        Trava reentrante deste arquivo. Quem precisa de um
        "ler, alterar e gravar" sem que outra thread se intrometa
        no meio faz `with armazenamento.trava:` em volta.
        """

        with self._trava_das_travas:

            if self.caminho not in self._travas_por_caminho:

                self._travas_por_caminho[self.caminho] = (
                    threading.RLock()
                )

            return self._travas_por_caminho[self.caminho]

    def existe(self):

        return os.path.isfile(self.caminho)

    def ler(self, padrao=None):
        """
        Devolve o conteúdo do JSON, ou `padrao` se o arquivo não
        existir, estiver ilegível ou corrompido (inclusive com
        bytes que não são UTF-8 válido — UnicodeDecodeError não é
        um JSONDecodeError e antes escapava dos except).
        """

        with self.trava:

            if not self.existe():
                return padrao

            try:

                with open(
                    self.caminho,
                    "r",
                    encoding="utf-8"
                ) as arquivo:

                    return json.load(arquivo)

            except (OSError, ValueError):

                return padrao

    def gravar(self, dados):
        """Grava de forma atômica. Devolve True se gravou."""

        with self.trava:

            caminho_temporario = (
                f"{self.caminho}.{os.getpid()}."
                f"{threading.get_ident()}.tmp"
            )

            try:

                os.makedirs(
                    os.path.dirname(self.caminho),
                    exist_ok=True
                )

                with open(
                    caminho_temporario,
                    "w",
                    encoding="utf-8"
                ) as arquivo:

                    json.dump(
                        dados,
                        arquivo,
                        ensure_ascii=False,
                        indent=2
                    )

                    arquivo.flush()

                    os.fsync(arquivo.fileno())

                return self._trocar(caminho_temporario)

            except (OSError, TypeError, ValueError):

                self._remover_se_existir(caminho_temporario)

                return False

    def remover(self):

        with self.trava:

            try:

                if self.existe():
                    os.remove(self.caminho)

                return True

            except OSError:

                return False

    def _trocar(self, caminho_temporario):
        """
        No Windows, os.replace falha com PermissionError se um
        antivírus/indexador estiver com o arquivo aberto naquele
        instante. Algumas tentativas curtas resolvem na prática.
        """

        for tentativa in range(self.TENTATIVAS_DE_TROCA):

            try:

                os.replace(
                    caminho_temporario,
                    self.caminho
                )

                return True

            except PermissionError:

                time.sleep(self.ESPERA_ENTRE_TENTATIVAS_S)

            except OSError:

                break

        self._remover_se_existir(caminho_temporario)

        return False

    @staticmethod
    def _remover_se_existir(caminho):

        try:

            if os.path.exists(caminho):
                os.remove(caminho)

        except OSError:
            pass
