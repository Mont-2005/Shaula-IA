import contextlib
import os
import sqlite3


class BancoSqlite:
    """
    Banco SQLite da Shaula (um único arquivo, sem servidor — roda
    100% offline). Cuida só da parte de infraestrutura: abrir
    conexões, transações e criar/versionar o esquema. Quem sabe o
    que gravar é o RepositorioConversas.

    Cada operação abre e fecha a sua própria conexão. Uma conexão
    SQLite não pode ser usada por threads diferentes, e a Shaula tem
    várias (a IA, a voz, a interface) e várias janelas no mesmo
    processo; conexões curtas resolvem isso sem travas manuais, e
    com o volume de dados daqui o custo de abrir uma é desprezível.

    O arquivo usa journal WAL: leituras e uma escrita andam ao mesmo
    tempo, e uma queda no meio de uma gravação nunca deixa o banco
    pela metade (ou a transação inteira vale, ou nada vale).
    """

    VERSAO_ESQUEMA = 1

    ESPERA_POR_TRAVA_S = 10

    ESQUEMA_V1 = """
        CREATE TABLE IF NOT EXISTS conversas (
            id                TEXT PRIMARY KEY,
            titulo            TEXT NOT NULL,
            titulo_automatico INTEGER NOT NULL DEFAULT 1,
            fixado            INTEGER NOT NULL DEFAULT 0,
            criado_em         TEXT NOT NULL,
            atualizado_em     TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS mensagens (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            conversa_id TEXT NOT NULL
                REFERENCES conversas(id) ON DELETE CASCADE,
            papel       TEXT NOT NULL
                CHECK (papel IN ('user', 'assistant')),
            conteudo    TEXT NOT NULL,
            criado_em   TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_mensagens_conversa
            ON mensagens (conversa_id, id);
    """

    def __init__(self, caminho):

        self.caminho = os.path.abspath(caminho)

        os.makedirs(
            os.path.dirname(self.caminho),
            exist_ok=True
        )

        self._preparar()

    def _abrir(self):

        # isolation_level=None: nós mesmos controlamos o BEGIN/COMMIT
        # (ver transacao()), em vez da abertura automática do módulo.
        conexao = sqlite3.connect(
            self.caminho,
            timeout=self.ESPERA_POR_TRAVA_S,
            isolation_level=None
        )

        conexao.row_factory = sqlite3.Row

        # Desligado por padrão no SQLite, e é ele que faz apagar uma
        # conversa apagar também as mensagens dela.
        conexao.execute(
            "PRAGMA foreign_keys = ON"
        )

        return conexao

    @contextlib.contextmanager
    def leitura(self):
        """Conexão para consultas (SELECT)."""

        conexao = self._abrir()

        try:

            yield conexao

        finally:

            conexao.close()

    @contextlib.contextmanager
    def transacao(self):
        """
        Conexão dentro de uma transação de escrita: tudo que for
        feito no `with` é confirmado junto no fim, ou desfeito se
        algo der erro. BEGIN IMMEDIATE já pega a trava de escrita
        no começo, então um "ler, decidir, gravar" não é
        atropelado por outra janela no meio do caminho.
        """

        conexao = self._abrir()

        try:

            conexao.execute(
                "BEGIN IMMEDIATE"
            )

            try:

                yield conexao

            except BaseException:

                conexao.execute(
                    "ROLLBACK"
                )

                raise

            conexao.execute(
                "COMMIT"
            )

        finally:

            conexao.close()

    def _preparar(self):
        """Cria o esquema na primeira vez e registra a versão dele."""

        with self.leitura() as conexao:

            conexao.execute(
                "PRAGMA journal_mode = WAL"
            )

            versao = conexao.execute(
                "PRAGMA user_version"
            ).fetchone()[0]

        if versao >= self.VERSAO_ESQUEMA:
            return

        with self.transacao() as conexao:

            for comando in self.ESQUEMA_V1.split(";"):

                if comando.strip():

                    conexao.execute(
                        comando
                    )

            conexao.execute(
                f"PRAGMA user_version = {int(self.VERSAO_ESQUEMA)}"
            )
