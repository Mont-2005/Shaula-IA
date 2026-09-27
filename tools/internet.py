class EstadoInternet:
    """
    Substitui a variável global `internet_ativa` que existia
    antes. Encapsular esse estado numa classe evita depender de
    uma variável de módulo mutável compartilhada — qualquer
    parte do código que precisar saber ou mudar o estado da
    internet recebe uma referência a este objeto, em vez de
    importar e mexer numa global.
    """

    def __init__(self):

        self._ativa = False

    @property
    def ativa(self):

        return self._ativa

    def ativar(self):

        self._ativa = True

        return (
            "Internet ativada. Agora posso realizar pesquisas "
            "na internet e consultar fontes quando necessário."
        )

    def desativar(self):

        self._ativa = False

        return (
            "Internet desativada. Voltarei a funcionar "
            "somente com os recursos locais."
        )
