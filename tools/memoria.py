import os
import json


class HistoricoConversa:
    """
    Histórico de conversa persistente entre sessões.

    Diferente do módulo original (funções soltas operando sobre
    uma lista que o chamador tinha que gerenciar por conta
    própria), esta classe É DONA da lista de mensagens — quem
    usa chama métodos (.adicionar(), .salvar(), .apagar()) em
    vez de manipular uma lista solta e lembrar de chamar
    salvar_historico() toda vez.
    """

    MAX_MENSAGENS_HISTORICO = 60

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

        self.mensagens = self._carregar()

    def _carregar(self):
        """
        Carrega o histórico salvo em disco e devolve a lista de
        mensagens pronta para uso:
        [mensagem_sistema, ...histórico].

        Se não houver nada salvo, ou o arquivo estiver
        corrompido, devolve só a mensagem de sistema (conversa
        nova).
        """

        if not os.path.isfile(self.caminho_arquivo):
            return [self.mensagem_sistema]

        try:

            with open(
                self.caminho_arquivo,
                "r",
                encoding="utf-8"
            ) as arquivo:

                salvas = json.load(arquivo)

            if not isinstance(salvas, list):
                return [self.mensagem_sistema]

            mensagens_validas = [
                mensagem
                for mensagem in salvas
                if (
                    isinstance(mensagem, dict)
                    and "role" in mensagem
                    and "content" in mensagem
                )
            ]

            return (
                [self.mensagem_sistema]
                + mensagens_validas[
                    -self.MAX_MENSAGENS_HISTORICO:
                ]
            )

        except (
            json.JSONDecodeError,
            OSError
        ):

            # Histórico corrompido ou ilegível — em vez de
            # travar a Shaula na inicialização, começamos uma
            # conversa nova.
            return [self.mensagem_sistema]

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
        Salva o histórico atual em disco.

        A primeira mensagem (a de sistema) nunca é salva — ela
        é definida no código e pode mudar entre versões da
        Shaula, então recarregá-la do disco poderia travar a
        personalidade numa versão antiga.
        """

        sem_sistema = self.mensagens[1:]

        # Só guardamos entradas que são realmente um dicionário
        # simples, com "role" e "content" em texto. Isso evita
        # que um objeto não serializável quebre o salvamento
        # inteiro silenciosamente.
        serializaveis = [
            mensagem
            for mensagem in sem_sistema
            if (
                isinstance(mensagem, dict)
                and isinstance(
                    mensagem.get("role"),
                    str
                )
                and isinstance(
                    mensagem.get("content"),
                    str
                )
            )
        ]

        limitado = serializaveis[
            -self.MAX_MENSAGENS_HISTORICO:
        ]

        try:

            os.makedirs(
                os.path.dirname(
                    self.caminho_arquivo
                ),
                exist_ok=True
            )

            with open(
                self.caminho_arquivo,
                "w",
                encoding="utf-8"
            ) as arquivo:

                json.dump(
                    limitado,
                    arquivo,
                    ensure_ascii=False,
                    indent=2
                )

        except (
            OSError,
            TypeError
        ):

            # Se não der para salvar, a conversa simplesmente
            # não é memorizada desta vez — não é motivo para
            # travar a Shaula.
            pass

    def apagar(self):
        """
        Apaga a conversa memorizada em disco E reseta o
        histórico em memória de volta para só a mensagem de
        sistema. Usado pelo comando "excluir conversa".
        """

        try:

            if os.path.isfile(self.caminho_arquivo):

                os.remove(self.caminho_arquivo)

        except OSError:

            pass

        self.mensagens = [self.mensagem_sistema]

    def __iter__(self):
        """Permite iterar direto sobre o histórico: for m in historico"""

        return iter(self.mensagens)

    def __len__(self):

        return len(self.mensagens)
