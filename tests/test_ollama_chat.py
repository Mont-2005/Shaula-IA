import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from tools.ollama_chat import ChamadaCancelada, ChatInterrompivel


class ClienteFalso:
    """Imita ollama.Client: chat() bloqueia até ser liberado."""

    def __init__(self, resposta="ok", erro=None):

        self.resposta = resposta
        self.erro = erro
        self.liberar = threading.Event()
        self.chamadas = []
        self.iniciou = threading.Event()
        self.fechado = False

        class _Http:

            def close(inner):
                self.fechado = True

        self._client = _Http()

    def chat(self, **parametros):

        self.chamadas.append(parametros)
        self.iniciou.set()

        self.liberar.wait(10)

        if self.erro is not None:
            raise self.erro

        return self.resposta


class TestChatInterrompivel:

    def test_devolve_a_resposta_normalmente(self):

        cliente = ClienteFalso("resposta pronta")
        cliente.liberar.set()

        chat = ChatInterrompivel(lambda: cliente)

        resposta = chat.conversar(
            model="m",
            messages=[{"role": "user", "content": "oi"}]
        )

        assert resposta == "resposta pronta"
        assert cliente.chamadas[0]["model"] == "m"

    def test_propaga_erro_do_cliente(self):

        cliente = ClienteFalso(erro=ConnectionError("recusada"))
        cliente.liberar.set()

        chat = ChatInterrompivel(lambda: cliente)

        with pytest.raises(ConnectionError):
            chat.conversar(model="m", messages=[])

    def test_cancelar_libera_na_hora_com_a_chamada_ainda_bloqueada(self):

        cliente = ClienteFalso()

        chat = ChatInterrompivel(lambda: cliente)

        threading.Timer(0.2, chat.cancelar).start()

        inicio = time.time()

        with pytest.raises(ChamadaCancelada):
            chat.conversar(model="m", messages=[])

        assert time.time() - inicio < 1.0
        assert not cliente.liberar.is_set()

        cliente.liberar.set()

    def test_cancelar_fecha_a_conexao_http(self):

        cliente = ClienteFalso()

        chat = ChatInterrompivel(lambda: cliente)

        threading.Timer(0.1, chat.cancelar).start()

        with pytest.raises(ChamadaCancelada):
            chat.conversar(model="m", messages=[])

        assert cliente.fechado

        cliente.liberar.set()

    def test_cancelado_antes_de_comecar_nem_chama_o_cliente(self):

        cliente = ClienteFalso()
        cliente.liberar.set()

        chat = ChatInterrompivel(lambda: cliente)

        chat.cancelar()

        with pytest.raises(ChamadaCancelada):
            chat.conversar(model="m", messages=[])

        assert cliente.chamadas == []

    def test_cancelar_sem_nenhuma_chamada_feita_nao_quebra(self):

        ChatInterrompivel(lambda: ClienteFalso()).cancelar()

    def test_resposta_que_chegou_junto_do_cancelamento_e_descartada(self):

        cliente = ClienteFalso("tarde demais")

        chat = ChatInterrompivel(lambda: cliente)

        def liberar_e_cancelar():

            cliente.iniciou.wait(2)
            chat._cancelado.set()   # pedido de parar chega...
            cliente.liberar.set()   # ...junto com a resposta

        threading.Thread(target=liberar_e_cancelar).start()

        with pytest.raises(ChamadaCancelada):
            chat.conversar(model="m", messages=[])

    def test_reusa_o_mesmo_cliente_entre_chamadas(self):

        criados = []

        def fabrica():

            cliente = ClienteFalso("ok")
            cliente.liberar.set()
            criados.append(cliente)

            return cliente

        chat = ChatInterrompivel(fabrica)

        chat.conversar(model="m", messages=[])
        chat.conversar(model="m", messages=[])

        assert len(criados) == 1
        assert len(criados[0].chamadas) == 2


class _ServidorLento:
    """
    Servidor HTTP local que imita o /api/chat do Ollama mas
    demora para responder — para testar o ChatInterrompivel com o
    ollama.Client de verdade, sem Ollama instalado.
    """

    def __init__(self, atraso_s):

        self.atraso_s = atraso_s
        self.requisicoes = 0

        servidor = self

        class Manipulador(BaseHTTPRequestHandler):

            def do_POST(self):

                servidor.requisicoes += 1

                tamanho = int(
                    self.headers.get("Content-Length", 0)
                )

                self.rfile.read(tamanho)

                time.sleep(servidor.atraso_s)

                corpo = json.dumps({
                    "model": "m",
                    "created_at": "2026-01-01T00:00:00Z",
                    "message": {
                        "role": "assistant",
                        "content": "resposta lenta"
                    },
                    "done": True
                }).encode()

                try:

                    self.send_response(200)
                    self.send_header(
                        "Content-Type",
                        "application/json"
                    )
                    self.send_header(
                        "Content-Length",
                        str(len(corpo))
                    )
                    self.end_headers()
                    self.wfile.write(corpo)

                except OSError:
                    pass

            def log_message(self, *args):
                pass

        self.http = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            Manipulador
        )

        self.http.daemon_threads = True

        self.url = (
            f"http://127.0.0.1:{self.http.server_address[1]}"
        )

        threading.Thread(
            target=self.http.serve_forever,
            daemon=True
        ).start()

    def parar(self):

        self.http.shutdown()
        self.http.server_close()


class TestComOllamaClientReal:

    def test_resposta_normal_via_cliente_real(self):

        pytest.importorskip("ollama")

        from ollama import Client

        servidor = _ServidorLento(atraso_s=0.1)

        try:

            chat = ChatInterrompivel(
                lambda: Client(host=servidor.url)
            )

            resposta = chat.conversar(
                model="m",
                messages=[{"role": "user", "content": "oi"}]
            )

            assert resposta.message.content == "resposta lenta"

        finally:

            servidor.parar()

    def test_cancelar_libera_rapido_mesmo_com_servidor_lento(self):

        pytest.importorskip("ollama")

        from ollama import Client

        servidor = _ServidorLento(atraso_s=5)

        try:

            chat = ChatInterrompivel(
                lambda: Client(host=servidor.url)
            )

            threading.Timer(0.3, chat.cancelar).start()

            inicio = time.time()

            with pytest.raises(ChamadaCancelada):
                chat.conversar(
                    model="m",
                    messages=[{"role": "user", "content": "oi"}]
                )

            assert time.time() - inicio < 2.0
            assert servidor.requisicoes == 1

        finally:

            servidor.parar()
