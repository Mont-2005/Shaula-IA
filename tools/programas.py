import re
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

    # O nome vira argumento de `cmd /c start`, e o cmd.exe
    # interpreta & | < > ^ % mesmo quando o Python passa o
    # comando como lista. Um nome como "calc & del ..." (vindo,
    # por exemplo, de um texto malicioso de página pesquisada
    # que o modelo repetiu) executaria o segundo comando também.
    # Só aceitamos o que um nome de programa ou caminho legítimo
    # realmente contém.
    PADRAO_NOME_VALIDO = re.compile(
        r"^[\w .\-+@:\\/()]+$",
        re.UNICODE
    )

    def __init__(self, gerenciador_processos=None):

        self._processos = gerenciador_processos or GerenciadorProcessos()

    def abrir_programa(self, nome):

        nome = str(nome).strip()

        if not nome:

            return "Nenhum programa foi informado."

        if not self.PADRAO_NOME_VALIDO.match(nome):

            return (
                f"Não vou abrir '{nome}': o nome contém "
                "caracteres que não fazem parte de um nome "
                "de programa."
            )

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
