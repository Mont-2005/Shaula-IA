import functools
import os
import uuid
from datetime import datetime

from .armazenamento import ArmazenamentoJson
from .memoria import HistoricoConversa


def _transacional(metodo):
    """
    Decorador: executa o método inteiro dentro da trava do
    índice, para que "ler, alterar, gravar" seja uma operação
    única mesmo com várias janelas/threads mexendo nas conversas.
    """

    @functools.wraps(metodo)
    def envolvido(self, *args, **kwargs):

        with self._transacao():

            return metodo(self, *args, **kwargs)

    return envolvido


class GerenciadorConversas:
    """
    Gerencia múltiplas conversas independentes — cada uma com
    seu próprio arquivo de histórico (reaproveita
    HistoricoConversa sem modificá-la, só aponta para um
    arquivo diferente por conversa), mais um índice
    compartilhado (título, fixado, datas) usado para montar a
    barra lateral.

    O índice é sempre lido do disco na hora, nunca cacheado em
    memória entre chamadas — isso é o que permite múltiplas
    janelas abertas ao mesmo tempo (uma "instância principal" e
    outras abertas via "Abrir em nova janela") verem a mesma
    lista de conversas: todas leem/escrevem o mesmo arquivo de
    índice.
    """

    TITULO_PADRAO = "Nova conversa"
    TAMANHO_TITULO_AUTOMATICO = 40

    def __init__(self, mensagem_sistema, pasta_base=None):

        self.mensagem_sistema = mensagem_sistema

        self._pasta_base = pasta_base or os.path.join(
            os.path.expanduser("~"), ".shaula", "conversas"
        )

        os.makedirs(self._pasta_base, exist_ok=True)

        self._caminho_indice = os.path.join(
            self._pasta_base, "indice.json"
        )

        self._armazenamento_indice = ArmazenamentoJson(
            self._caminho_indice
        )

        self._migrar_conversa_legada()

    def _migrar_conversa_legada(self):
        """
        Antes de existirem múltiplas conversas, havia um único
        arquivo fixo (~/.shaula/historico_conversa.json). Se
        esse arquivo existir e ainda não tiver sido migrado
        (índice novo ainda não existe), importa ele como a
        primeira conversa — sem isso, quem já usava a Shaula
        veria a conversa antiga simplesmente desaparecer na
        primeira atualização.
        """

        if os.path.isfile(self._caminho_indice):
            # Já existe um índice novo — ou não há nada pra
            # migrar, ou a migração já aconteceu antes.
            return

        caminho_legado = os.path.join(
            os.path.expanduser("~"), ".shaula", "historico_conversa.json"
        )

        if not os.path.isfile(caminho_legado):
            self._salvar_indice([])
            return

        agora = datetime.now().isoformat()
        id_conversa = uuid.uuid4().hex[:12]

        try:
            os.replace(
                caminho_legado,
                self._caminho_arquivo(id_conversa)
            )
        except OSError:
            self._salvar_indice([])
            return

        self._salvar_indice([{
            "id": id_conversa,
            "titulo": "Conversa anterior",
            "titulo_automatico": False,
            "fixado": False,
            "criado_em": agora,
            "atualizado_em": agora,
        }])

    # --------------------------------------------------------
    # ÍNDICE (metadados compartilhados entre janelas)
    # --------------------------------------------------------

    def _carregar_indice(self):

        dados = self._armazenamento_indice.ler(padrao=[])

        if not isinstance(dados, list):
            return []

        return [
            entrada for entrada in dados
            if isinstance(entrada, dict) and "id" in entrada
        ]

    def _salvar_indice(self, entradas):

        return self._armazenamento_indice.gravar(entradas)

    def _transacao(self):
        """
        Trava do índice. Todo "ler, alterar, gravar" roda dentro
        dela (`with self._transacao():`), senão duas janelas
        alterando o índice ao mesmo tempo perdiam uma das
        alterações (a última gravação vencia).
        """

        return self._armazenamento_indice.trava

    def listar_conversas(self):
        """
        Devolve as conversas ordenadas para exibição: fixadas
        primeiro (mais recentes primeiro entre si), depois as
        demais, também por atualização mais recente.
        """

        entradas = self._carregar_indice()

        return sorted(
            entradas,
            key=lambda e: (
                not e.get("fixado", False),
                -self._timestamp_ordenavel(e.get("atualizado_em"))
            )
        )

    def _timestamp_ordenavel(self, valor):

        if not valor:
            return 0

        try:
            return datetime.fromisoformat(valor).timestamp()
        except (TypeError, ValueError):
            return 0

    # --------------------------------------------------------
    # CRIAR / OBTER
    # --------------------------------------------------------

    @_transacional
    def criar_conversa(self):
        """Cria uma conversa nova vazia e devolve o id dela."""

        agora = datetime.now().isoformat()

        id_conversa = uuid.uuid4().hex[:12]

        entradas = self._carregar_indice()

        entradas.append({
            "id": id_conversa,
            "titulo": self.TITULO_PADRAO,
            "titulo_automatico": True,
            "fixado": False,
            "criado_em": agora,
            "atualizado_em": agora,
        })

        self._salvar_indice(entradas)

        return id_conversa

    def obter_entrada(self, id_conversa):

        for entrada in self._carregar_indice():

            if entrada["id"] == id_conversa:
                return entrada

        return None

    def obter_historico(self, id_conversa):
        """Devolve um HistoricoConversa carregado para o arquivo dessa conversa."""

        return HistoricoConversa(
            self.mensagem_sistema,
            caminho_arquivo=self._caminho_arquivo(id_conversa)
        )

    def _caminho_arquivo(self, id_conversa):

        return os.path.join(self._pasta_base, f"{id_conversa}.json")

    # --------------------------------------------------------
    # RENOMEAR / FIXAR / APAGAR
    # --------------------------------------------------------

    @_transacional
    def renomear_conversa(self, id_conversa, novo_titulo):

        novo_titulo = str(novo_titulo).strip()

        if not novo_titulo:
            return False

        entradas = self._carregar_indice()

        for entrada in entradas:

            if entrada["id"] == id_conversa:

                entrada["titulo"] = novo_titulo
                entrada["titulo_automatico"] = False

                self._salvar_indice(entradas)

                return True

        return False

    @_transacional
    def alternar_fixado(self, id_conversa):
        """Fixa/desafixa a conversa. Devolve o novo estado (True/False), ou None se não achou."""

        entradas = self._carregar_indice()

        for entrada in entradas:

            if entrada["id"] == id_conversa:

                entrada["fixado"] = not entrada.get("fixado", False)

                self._salvar_indice(entradas)

                return entrada["fixado"]

        return None

    @_transacional
    def apagar_conversa(self, id_conversa):
        """Remove a conversa inteira: arquivo de histórico + entrada no índice."""

        entradas = self._carregar_indice()

        entradas = [e for e in entradas if e["id"] != id_conversa]

        self._salvar_indice(entradas)

        caminho = self._caminho_arquivo(id_conversa)

        try:

            if os.path.isfile(caminho):
                os.remove(caminho)

        except OSError:

            pass

    @_transacional
    def resetar_titulo(self, id_conversa):
        """
        Volta o título para o padrão e destrava a geração
        automática — usado quando o conteúdo da conversa é
        apagado (comando "excluir memória"), para o próximo
        título gerado refletir o novo conteúdo, não o antigo.
        """

        entradas = self._carregar_indice()

        for entrada in entradas:

            if entrada["id"] == id_conversa:

                entrada["titulo"] = self.TITULO_PADRAO
                entrada["titulo_automatico"] = True

                self._salvar_indice(entradas)

                return

    @_transacional
    def marcar_atualizada(self, id_conversa):
        """Atualiza o timestamp de atualização — afeta a ordenação da lista."""

        entradas = self._carregar_indice()

        for entrada in entradas:

            if entrada["id"] == id_conversa:

                entrada["atualizado_em"] = datetime.now().isoformat()

                self._salvar_indice(entradas)

                return

    @_transacional
    def atualizar_titulo_automatico(self, id_conversa, primeira_mensagem):
        """
        Se a conversa ainda tem o título padrão (nunca foi
        renomeada manualmente pelo usuário), gera um título a
        partir da primeira mensagem do usuário.
        """

        entradas = self._carregar_indice()

        for entrada in entradas:

            if entrada["id"] != id_conversa:
                continue

            if not entrada.get("titulo_automatico", True):
                return

            texto = str(primeira_mensagem).strip().replace("\n", " ")

            if len(texto) > self.TAMANHO_TITULO_AUTOMATICO:
                texto = texto[:self.TAMANHO_TITULO_AUTOMATICO].rstrip() + "..."

            entrada["titulo"] = texto or self.TITULO_PADRAO

            self._salvar_indice(entradas)

            return
