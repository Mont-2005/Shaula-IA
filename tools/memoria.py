import os

from .armazenamento import ArmazenamentoJson


class HistoricoConversa:
    """
    Histórico de conversa persistente entre sessões.

    Diferente do módulo original (funções soltas operando sobre
    uma lista que o chamador tinha que gerenciar por conta
    própria), esta classe É DONA da lista de mensagens — quem
    usa chama métodos (.adicionar(), .salvar(), .apagar()) em
    vez de manipular uma lista solta e lembrar de chamar
    salvar_historico() toda vez.

    Só mensagens de conversa de verdade (usuário e assistente)
    são persistidas. Mensagens de ferramenta ("tool") ficam de
    fora: sem a mensagem do assistente que pediu a chamada elas
    ficam "órfãs" quando recarregadas e confundem o modelo, e o
    resultado útil delas já aparece na resposta final.
    """

    MAX_MENSAGENS_HISTORICO = 60

    PAPEIS_PERSISTIDOS = frozenset({"user", "assistant"})

    def __init__(
        self,
        mensagem_sistema,
        caminho_arquivo=None
    ):

        self.mensagem_sistema = mensagem_sistema

        if caminho_arquivo is None:

            pasta_padrao = os.path.join(
                os.path.expanduser("~"),
                ".shaula"
            )

            caminho_arquivo = os.path.join(
                pasta_padrao,
                "historico_conversa.json"
            )

        self.caminho_arquivo = caminho_arquivo

        self._armazenamento = ArmazenamentoJson(
            caminho_arquivo
        )

        self.mensagens = self._carregar()

    @classmethod
    def _eh_persistivel(cls, mensagem):

        return (
            isinstance(mensagem, dict)
            and mensagem.get("role") in cls.PAPEIS_PERSISTIDOS
            and isinstance(mensagem.get("content"), str)
        )

    def _carregar(self):
        """
        Carrega o histórico salvo em disco e devolve a lista de
        mensagens pronta para uso:
        [mensagem_sistema, ...histórico].

        Se não houver nada salvo, ou o arquivo estiver
        corrompido, devolve só a mensagem de sistema (conversa
        nova). Mensagens de ferramenta gravadas por versões
        anteriores são descartadas aqui.
        """

        salvas = self._armazenamento.ler(padrao=[])

        if not isinstance(salvas, list):
            return [self.mensagem_sistema]

        mensagens_validas = [
            mensagem
            for mensagem in salvas
            if self._eh_persistivel(mensagem)
        ]

        return (
            [self.mensagem_sistema]
            + mensagens_validas[
                -self.MAX_MENSAGENS_HISTORICO:
            ]
        )

    def adicionar(self, papel, conteudo):
        """
        Adiciona uma mensagem ao histórico em memória. Não
        salva em disco sozinho — chame .salvar() quando quiser
        persistir (normalmente depois de cada resposta
        completa).
        """

        self.mensagens.append({
            "role": papel,
            "content": conteudo
        })

    def salvar(self):
        """
        Salva o histórico atual em disco (de forma atômica).

        A primeira mensagem (a de sistema) nunca é salva — ela
        é definida no código e pode mudar entre versões da
        Shaula, então recarregá-la do disco poderia travar a
        personalidade numa versão antiga.
        """

        persistiveis = [
            mensagem
            for mensagem in self.mensagens[1:]
            if self._eh_persistivel(mensagem)
        ]

        limitado = persistiveis[
            -self.MAX_MENSAGENS_HISTORICO:
        ]

        return self._armazenamento.gravar(limitado)

    def apagar(self):
        """
        Apaga a conversa memorizada em disco E reseta o
        histórico em memória de volta para só a mensagem de
        sistema. Usado pelo comando "excluir conversa".
        """

        self._armazenamento.remover()

        self.mensagens = [self.mensagem_sistema]

    def __iter__(self):
        """Permite iterar direto sobre o histórico: for m in historico"""

        return iter(self.mensagens)

    def __len__(self):

        return len(self.mensagens)
