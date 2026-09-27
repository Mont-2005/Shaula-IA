import subprocess
import time


class GerenciadorOllama:
    """
    Controle do processo do Ollama no Windows: verificar se
    está rodando, encerrar o app e o servidor.
    """

    NOMES_PROCESSOS = (
        "ollama app.exe",
        "ollama.exe",
    )

    def processo_existe(self, nome_processo):

        try:

            resultado = subprocess.run(
                [
                    "tasklist",
                    "/FI",
                    f"IMAGENAME eq {nome_processo}",
                ],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            return nome_processo.lower() in resultado.stdout.lower()

        except Exception:

            return False

    def encerrar_processo(self, nome_processo):

        try:

            subprocess.run(
                [
                    "taskkill",
                    "/F",
                    "/T",
                    "/IM",
                    nome_processo,
                ],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

        except Exception:

            pass

    def encerrar_tudo(self):
        """
        Encerra completamente o Ollama no Windows.

        A ordem é importante:

        1. encerra o aplicativo do Ollama;
        2. encerra o servidor ollama.exe;
        3. verifica se algum deles voltou;
        4. repete algumas vezes.

        Isso evita que o "ollama app.exe" recrie o "ollama.exe"
        depois que o servidor for encerrado.
        """

        self.encerrar_processo("ollama app.exe")
        self.encerrar_processo("ollama.exe")

        # Polling curto (0.1s), com um teto de ~4s como rede de
        # segurança, em vez de esperas fixas mais longas.
        intervalo_poll = 0.1
        tempo_maximo = 4.0
        tempo_decorrido = 0.0

        while tempo_decorrido < tempo_maximo:

            time.sleep(intervalo_poll)

            tempo_decorrido += intervalo_poll

            app_existe = self.processo_existe("ollama app.exe")
            servidor_existe = self.processo_existe("ollama.exe")

            if not app_existe and not servidor_existe:

                return True

            if app_existe:

                self.encerrar_processo("ollama app.exe")

            if servidor_existe:

                self.encerrar_processo("ollama.exe")

        # Última tentativa
        if self.processo_existe("ollama app.exe"):

            self.encerrar_processo("ollama app.exe")

        if self.processo_existe("ollama.exe"):

            self.encerrar_processo("ollama.exe")

        time.sleep(0.3)

        return not (
            self.processo_existe("ollama app.exe")
            or self.processo_existe("ollama.exe")
        )
