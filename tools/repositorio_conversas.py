import sqlite3
from datetime import datetime


def _agora():

    return datetime.now().isoformat(
        timespec="microseconds"
    )


class MensagensSqlite:
    """
    As mensagens de UMA conversa, com a mesma interface do
    ArmazenamentoJson (ler / gravar / remover / existe). É isso que
    deixa o HistoricoConversa trocar o arquivo JSON pelo banco sem
    mudar uma linha da lógica dele.
    """

    def __init__(
        self,
        repositorio,
        id_conversa
    ):

        self._repositorio = repositorio

        self.id_conversa = id_conversa

    def existe(self):

        return self._repositorio.obter(
            self.id_conversa
        ) is not None

    def ler(
        self,
        padrao=None
    ):

        try:

            return self._repositorio.carregar_mensagens(
                self.id_conversa
            )

        except sqlite3.Error:

            return padrao

    def gravar(
        self,
        dados
    ):
        """Devolve True se gravou (False se a conversa não existe mais)."""

        try:

            return self._repositorio.gravar_mensagens(
                self.id_conversa,
                dados
            )

        except (sqlite3.Error, KeyError, TypeError):

            return False

    def remover(self):

        try:

            self._repositorio.apagar_mensagens(
                self.id_conversa
            )

            return True

        except sqlite3.Error:

            return False


class RepositorioConversas:
    """
    Todo o SQL das conversas e das mensagens fica aqui — o
    GerenciadorConversas decide O QUE fazer (regras de título,
    ordenação da barra lateral) e este repositório sabe COMO guardar.

    Os valores sempre vão como parâmetros (?), nunca montados dentro
    do texto do comando: um título como  '); DROP TABLE conversas;--
    é só um título.
    """

    def __init__(
        self,
        banco
    ):

        self.banco = banco

    # ========================================================
    # CONVERSAS
    # ========================================================

    @staticmethod
    def _entrada(linha):
        """Linha do banco -> dicionário no formato que a interface usa."""

        return {
            "id": linha["id"],
            "titulo": linha["titulo"],
            "titulo_automatico": bool(linha["titulo_automatico"]),
            "fixado": bool(linha["fixado"]),
            "criado_em": linha["criado_em"],
            "atualizado_em": linha["atualizado_em"],
        }

    def inserir(
        self,
        id_conversa,
        titulo
    ):

        agora = _agora()

        with self.banco.transacao() as conexao:

            conexao.execute(
                "INSERT INTO conversas "
                "(id, titulo, titulo_automatico, fixado, "
                "criado_em, atualizado_em) "
                "VALUES (?, ?, 1, 0, ?, ?)",
                (id_conversa, titulo, agora, agora)
            )

    def listar(self):
        """Fixadas primeiro; dentro de cada grupo, as mais recentes antes."""

        with self.banco.leitura() as conexao:

            linhas = conexao.execute(
                "SELECT * FROM conversas "
                "ORDER BY fixado DESC, atualizado_em DESC, rowid ASC"
            ).fetchall()

        return [
            self._entrada(linha)
            for linha in linhas
        ]

    def obter(
        self,
        id_conversa
    ):

        with self.banco.leitura() as conexao:

            linha = conexao.execute(
                "SELECT * FROM conversas WHERE id = ?",
                (id_conversa,)
            ).fetchone()

        return (
            self._entrada(linha)
            if linha is not None
            else None
        )

    def renomear(
        self,
        id_conversa,
        titulo
    ):
        """Título escolhido pelo usuário: deixa de ser automático."""

        with self.banco.transacao() as conexao:

            return conexao.execute(
                "UPDATE conversas "
                "SET titulo = ?, titulo_automatico = 0 "
                "WHERE id = ?",
                (titulo, id_conversa)
            ).rowcount > 0

    def alternar_fixado(
        self,
        id_conversa
    ):
        """Novo estado (True/False), ou None se a conversa não existe."""

        with self.banco.transacao() as conexao:

            conexao.execute(
                "UPDATE conversas SET fixado = 1 - fixado "
                "WHERE id = ?",
                (id_conversa,)
            )

            linha = conexao.execute(
                "SELECT fixado FROM conversas WHERE id = ?",
                (id_conversa,)
            ).fetchone()

        return (
            bool(linha["fixado"])
            if linha is not None
            else None
        )

    def apagar(
        self,
        id_conversa
    ):
        """Apaga a conversa; as mensagens vão junto (ON DELETE CASCADE)."""

        with self.banco.transacao() as conexao:

            conexao.execute(
                "DELETE FROM conversas WHERE id = ?",
                (id_conversa,)
            )

    def redefinir_titulo(
        self,
        id_conversa,
        titulo
    ):
        """Volta ao título padrão e libera a geração automática."""

        with self.banco.transacao() as conexao:

            conexao.execute(
                "UPDATE conversas "
                "SET titulo = ?, titulo_automatico = 1 "
                "WHERE id = ?",
                (titulo, id_conversa)
            )

    def definir_titulo_automatico(
        self,
        id_conversa,
        titulo
    ):
        """Só mexe se a conversa nunca foi renomeada pelo usuário."""

        with self.banco.transacao() as conexao:

            conexao.execute(
                "UPDATE conversas SET titulo = ? "
                "WHERE id = ? AND titulo_automatico = 1",
                (titulo, id_conversa)
            )

    def marcar_atualizada(
        self,
        id_conversa
    ):

        with self.banco.transacao() as conexao:

            conexao.execute(
                "UPDATE conversas SET atualizado_em = ? "
                "WHERE id = ?",
                (_agora(), id_conversa)
            )

    # ========================================================
    # MENSAGENS
    # ========================================================

    def mensagens_da(
        self,
        id_conversa
    ):
        """Armazenamento (interface do ArmazenamentoJson) de uma conversa."""

        return MensagensSqlite(
            self,
            id_conversa
        )

    def carregar_mensagens(
        self,
        id_conversa
    ):

        with self.banco.leitura() as conexao:

            linhas = conexao.execute(
                "SELECT papel, conteudo FROM mensagens "
                "WHERE conversa_id = ? ORDER BY id",
                (id_conversa,)
            ).fetchall()

        return [
            {
                "role": linha["papel"],
                "content": linha["conteudo"]
            }
            for linha in linhas
        ]

    def gravar_mensagens(
        self,
        id_conversa,
        mensagens
    ):
        """
        Faz o banco ficar igual à lista `mensagens` (dicionários com
        role/content), numa única transação.

        No caso comum — a lista só ganhou mensagens no final desde a
        última vez — insere apenas as novas, e as antigas mantêm o
        mesmo id e a mesma data. Se a lista mudou de outro jeito (o
        limite de 60 mensagens descartou as mais antigas, por
        exemplo), reescreve a conversa inteira.

        Devolve False se a conversa não existe mais (apagada em
        outra janela) — nesse caso nada é gravado.
        """

        novas = [
            (mensagem["role"], mensagem["content"])
            for mensagem in mensagens
        ]

        with self.banco.transacao() as conexao:

            existe = conexao.execute(
                "SELECT 1 FROM conversas WHERE id = ?",
                (id_conversa,)
            ).fetchone()

            if existe is None:

                return False

            atuais = [
                (linha["papel"], linha["conteudo"])
                for linha in conexao.execute(
                    "SELECT papel, conteudo FROM mensagens "
                    "WHERE conversa_id = ? ORDER BY id",
                    (id_conversa,)
                )
            ]

            if novas[:len(atuais)] == atuais:

                a_inserir = novas[len(atuais):]

            else:

                conexao.execute(
                    "DELETE FROM mensagens WHERE conversa_id = ?",
                    (id_conversa,)
                )

                a_inserir = novas

            agora = _agora()

            conexao.executemany(
                "INSERT INTO mensagens "
                "(conversa_id, papel, conteudo, criado_em) "
                "VALUES (?, ?, ?, ?)",
                [
                    (id_conversa, papel, conteudo, agora)
                    for papel, conteudo in a_inserir
                ]
            )

        return True

    def apagar_mensagens(
        self,
        id_conversa
    ):

        with self.banco.transacao() as conexao:

            conexao.execute(
                "DELETE FROM mensagens WHERE conversa_id = ?",
                (id_conversa,)
            )
