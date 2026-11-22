import os


class CodificacaoConsole:
    """
    Codificação em que os programas de console do Windows (netsh,
    tasklist, taskkill...) imprimem: a página OEM (cp850 no Brasil),
    que NÃO é a padrão do Python no Windows (cp1252). Com
    `text=True` e sem informar a codificação, um SSID como "Casa da
    Vovó" virava "Casa da Vov¢" e bytes sem equivalente em cp1252
    (como o "É" maiúsculo da OEM) lançavam UnicodeDecodeError.

    Use sempre com errors="replace": uma saída ilegível não deve
    derrubar a ferramenta.
    """

    NOME = "oem" if os.name == "nt" else "utf-8"

    ERROS = "replace"

    @classmethod
    def opcoes(cls):
        """Argumentos para subprocess.run(...): encoding e errors."""

        return {"encoding": cls.NOME, "errors": cls.ERROS}
