import threading


class ChamadaCancelada(Exception):
    """
    Levantada por ChatInterrompivel quando o usuário mandou parar
    a resposta. Não é um erro: é o caminho normal de "parar".
    """


class ChatInterrompivel:
    """
    Faz chamadas `chat()` ao Ollama que podem ser interrompidas
    de outra thread.

    Por que existe: a Shaula usa chat() sem streaming (ver
    limitações no README), e uma chamada assim bloqueia a thread
    até o modelo terminar a resposta inteira — não há ponto
    intermediário onde olhar "o usuário pediu pra parar?". Aqui a
    chamada de verdade roda numa thread auxiliar, e quem chamou
    espera por ela em intervalos curtos, conferindo o pedido de
    cancelamento. Ao cancelar:

    1. quem chamou é liberado na hora (levanta ChamadaCancelada),
       sem esperar o modelo terminar;
    2. a conexão HTTP com o Ollama é fechada. O servidor percebe
       que o cliente foi embora e deixa de gerar (no Windows o
       fechamento do socket interrompe a leitura pendente) —
       melhor esforço: o que é garantido é o item 1.
    """

    INTERVALO_DE_CONFERENCIA_S = 0.05

    def __init__(
        self,
        fabrica_cliente=None
    ):

        self._fabrica_cliente = (
            fabrica_cliente
            or self._criar_cliente_padrao
        )

        self._cancelado = threading.Event()

        self._cliente = None

    @staticmethod
    def _criar_cliente_padrao():

        from ollama import Client

        return Client()

    @property
    def foi_cancelado(self):

        return self._cancelado.is_set()

    def cancelar(self):
        """
        Pode ser chamado de qualquer thread, a qualquer momento
        (inclusive antes da primeira chamada ou depois da última).
        """

        self._cancelado.set()

        self._fechar_conexao()

    def conversar(
        self,
        **parametros
    ):
        """
        Mesmos parâmetros de ollama.chat (model, messages, tools,
        options...). Devolve a resposta, ou levanta
        ChamadaCancelada se o usuário mandou parar — mesmo que a
        resposta tenha chegado um instante antes: quem pediu pra
        parar não quer mais vê-la.
        """

        if self._cancelado.is_set():
            raise ChamadaCancelada()

        if self._cliente is None:
            self._cliente = self._fabrica_cliente()

        cliente = self._cliente

        resultado = {}

        terminou = threading.Event()

        def executar():

            try:

                resultado["resposta"] = cliente.chat(
                    **parametros
                )

            except BaseException as erro:

                resultado["erro"] = erro

            finally:

                terminou.set()

        threading.Thread(
            target=executar,
            daemon=True
        ).start()

        while not terminou.wait(
            self.INTERVALO_DE_CONFERENCIA_S
        ):

            if self._cancelado.is_set():
                raise ChamadaCancelada()

        if self._cancelado.is_set():
            raise ChamadaCancelada()

        if "erro" in resultado:
            raise resultado["erro"]

        return resultado["resposta"]

    def _fechar_conexao(self):

        cliente = self._cliente

        if cliente is None:
            return

        # ollama.Client guarda o httpx.Client em `_client`.
        http = getattr(
            cliente,
            "_client",
            None
        )

        if http is None:
            return

        try:

            http.close()

        except Exception:
            pass
