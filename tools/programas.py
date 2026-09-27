import subprocess

from .processos import GerenciadorProcessos


class GerenciadorProgramas:
    """
    Abertura de programas via o comando "start" do Windows
    (deixa o próprio Windows resolver o caminho/associação do
    programa pelo nome, como se tivesse sido digitado no menu
    Executar).

    Recebe um GerenciadorProcessos por injeção de dependência
    para fechar_programa — em vez de duplicar a lógica de
    terminar processos (e a lista de processos protegidos) que
    já vive em processos.py, só delega pra lá com um nome mais
    natural de pedir a mesma coisa.
    """

    def __init__(self, gerenciador_processos=None):

        self._processos = gerenciador_processos or GerenciadorProcessos()

    def abrir_programa(self, nome):

        nome = str(nome).strip()

        if not nome:

            return "Nenhum programa foi informado."

        try:

            subprocess.Popen(
                [
                    "cmd",
                    "/c",
                    "start",
                    "",
                    nome
                ],
                shell=False
            )

            return f"Comando enviado para abrir '{nome}'."

        except Exception as erro:

            return f"Não foi possível abrir '{nome}': {erro}"

    def fechar_programa(self, nome):
        """Fecha um programa pelo nome (delega para finalizar_processo)."""

        return self._processos.finalizar_processo(nome)
