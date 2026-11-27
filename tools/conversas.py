import os
import uuid

from .banco_dados import BancoSqlite
from .memoria import HistoricoConversa
from .repositorio_conversas import RepositorioConversas


class GerenciadorConversas:
    """
    Gerencia múltiplas conversas independentes. As conversas e as
    mensagens ficam num banco SQLite (um único arquivo,
    ~/.shaula/conversas/shaula.db) acessado pelo RepositorioConversas;
    este gerenciador guarda só as REGRAS: título padrão e automático,
    quando uma conversa conta como atualizada, qual histórico entregar
    para cada janela.

    Nada é cacheado em memória entre chamadas — toda consulta vai ao
    banco na hora. É isso que permite várias janelas abertas ao mesmo
    tempo (a principal e as abertas via "Abrir em nova janela")
    verem a mesma lista de conversas: todas leem e escrevem o mesmo
    banco, e as transações dele impedem que uma janela atropele a
    alteração da outra.
    """

    TITULO_PADRAO = "Nova conversa"
    TAMANHO_TITULO_AUTOMATICO = 40
    NOME_ARQUIVO_BANCO = "shaula.db"

    def __init__(
        self,
        mensagem_sistema,
        pasta_base=None,
        repositorio=None
    ):

        self.mensagem_sistema = mensagem_sistema

        self._pasta_base = pasta_base or os.path.join(
            os.path.expanduser("~"), ".shaula", "conversas"
        )

        # `repositorio` existe para testes (e para trocar o banco
        # sem mexer aqui); no uso normal é criado a partir da pasta.
        self.repositorio = repositorio or RepositorioConversas(
            BancoSqlite(
                os.path.join(
                    self._pasta_base,
                    self.NOME_ARQUIVO_BANCO
                )
            )
        )

    def listar_conversas(self):
        """
        Devolve as conversas ordenadas para exibição: fixadas
        primeiro (mais recentes primeiro entre si), depois as
        demais, também por atualização mais recente.
        """

        return self.repositorio.listar()

    # --------------------------------------------------------
    # CRIAR / OBTER
    # --------------------------------------------------------

    def criar_conversa(self):
        """Cria uma conversa nova vazia e devolve o id dela."""

        id_conversa = uuid.uuid4().hex[:12]

        self.repositorio.inserir(
            id_conversa,
            self.TITULO_PADRAO
        )

        return id_conversa

    def obter_entrada(self, id_conversa):

        return self.repositorio.obter(id_conversa)

    def obter_historico(self, id_conversa):
        """Devolve um HistoricoConversa ligado às mensagens dessa conversa no banco."""

        return HistoricoConversa(
            self.mensagem_sistema,
            armazenamento=self.repositorio.mensagens_da(
                id_conversa
            )
        )

    # --------------------------------------------------------
    # RENOMEAR / FIXAR / APAGAR
    # --------------------------------------------------------

    def renomear_conversa(self, id_conversa, novo_titulo):

        novo_titulo = str(novo_titulo).strip()

        if not novo_titulo:
            return False

        return self.repositorio.renomear(
            id_conversa,
            novo_titulo
        )

    def alternar_fixado(self, id_conversa):
        """Fixa/desafixa a conversa. Devolve o novo estado (True/False), ou None se não achou."""

        return self.repositorio.alternar_fixado(
            id_conversa
        )

    def apagar_conversa(self, id_conversa):
        """Remove a conversa inteira: a entrada e todas as mensagens dela."""

        self.repositorio.apagar(id_conversa)

    def resetar_titulo(self, id_conversa):
        """
        Volta o título para o padrão e destrava a geração
        automática — usado quando o conteúdo da conversa é
        apagado (comando "excluir memória"), para o próximo
        título gerado refletir o novo conteúdo, não o antigo.
        """

        self.repositorio.redefinir_titulo(
            id_conversa,
            self.TITULO_PADRAO
        )

    def marcar_atualizada(self, id_conversa):
        """Atualiza o timestamp de atualização — afeta a ordenação da lista."""

        self.repositorio.marcar_atualizada(
            id_conversa
        )

    def atualizar_titulo_automatico(self, id_conversa, primeira_mensagem):
        """
        Se a conversa ainda tem o título padrão (nunca foi
        renomeada manualmente pelo usuário), gera um título a
        partir da primeira mensagem do usuário.
        """

        texto = str(primeira_mensagem).strip().replace("\n", " ")

        if len(texto) > self.TAMANHO_TITULO_AUTOMATICO:
            texto = texto[:self.TAMANHO_TITULO_AUTOMATICO].rstrip() + "..."

        self.repositorio.definir_titulo_automatico(
            id_conversa,
            texto or self.TITULO_PADRAO
        )
