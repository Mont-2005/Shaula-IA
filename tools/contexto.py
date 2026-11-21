import json


class CompactadorHistorico:
    """
    Encurta respostas ANTIGAS e longas da Shaula (código, resultado
    de pesquisa, explicações) antes de o orçamento ter de descartar
    mensagens inteiras. As falas do usuário nunca são encurtadas: são
    curtas e é nelas que estão os fatos que ele costuma retomar
    ("como eu disse antes...").
    """

    LIMITE_CARACTERES = 600

    SUFIXO = "\n[... resposta antiga encurtada ...]"

    def compactar(self, mensagem):
        """Devolve a própria mensagem ou uma cópia encurtada."""

        if not isinstance(mensagem, dict):
            return mensagem

        conteudo = mensagem.get("content")

        if (
            mensagem.get("role") != "assistant"
            or not isinstance(conteudo, str)
            or len(conteudo) <= self.LIMITE_CARACTERES
        ):
            return mensagem

        copia = dict(mensagem)

        copia["content"] = (
            conteudo[:self.LIMITE_CARACTERES] + self.SUFIXO
        )

        return copia


class ResumidorHistorico:
    """
    Transforma as mensagens que não couberam no contexto num resumo
    curto e determinístico (sem chamar o modelo), para que a conversa
    antiga não desapareça por completo: o modelo ainda enxerga o
    começo de cada fala e consegue responder "o que eu disse sobre X?".

    O resumo cabe em LIMITE_TOKENS e privilegia as mensagens mais
    recentes entre as descartadas.
    """

    LIMITE_TOKENS = 600

    CARACTERES_POR_TOKEN = 3

    CARACTERES_USUARIO = 180

    CARACTERES_ASSISTENTE = 110

    CABECALHO = (
        "RESUMO DAS MENSAGENS MAIS ANTIGAS DESTA CONVERSA (ficaram "
        "de fora do contexto por falta de espaço; use como memória "
        "do que já foi dito):"
    )

    @staticmethod
    def _campo(mensagem, campo):

        if isinstance(mensagem, dict):
            return mensagem.get(campo)

        return getattr(mensagem, campo, None)

    @staticmethod
    def _trecho(texto, limite):

        linha = " ".join(texto.split())

        if len(linha) <= limite:
            return linha

        return linha[:limite].rstrip() + "…"

    def resumir(self, removidas, limite_tokens=None):
        """
        Mensagem de sistema com o resumo, ou None se não houver nada.
        `limite_tokens` (padrão LIMITE_TOKENS) deixa o orçamento apertar
        o resumo quando o contexto está quase cheio.
        """

        limite = (
            self.LIMITE_TOKENS
            if limite_tokens is None
            else limite_tokens
        )

        capacidade = (
            limite * self.CARACTERES_POR_TOKEN
            - len(self.CABECALHO)
        )

        linhas = []

        for mensagem in reversed(removidas):

            papel = self._campo(mensagem, "role")

            conteudo = self._campo(mensagem, "content")

            if papel not in ("user", "assistant"):
                continue

            if not isinstance(conteudo, str) or not conteudo.strip():
                continue

            if papel == "user":
                linha = "- Usuário: " + self._trecho(
                    conteudo, self.CARACTERES_USUARIO
                )
            else:
                linha = "- Shaula: " + self._trecho(
                    conteudo, self.CARACTERES_ASSISTENTE
                )

            capacidade -= len(linha) + 1

            if capacidade < 0:
                break

            linhas.append(linha)

        if not linhas:
            return None

        linhas.reverse()

        return {
            "role": "system",
            "content": self.CABECALHO + "\n" + "\n".join(linhas)
        }


class OrcamentoContexto:
    """
    Garante que o que vai para o Ollama cabe no `num_ctx`.

    Por que existe: com num_ctx = 8192, o prompt de sistema
    (~1.700 tokens) e os schemas das 39 ferramentas (~3.700
    tokens) já ocupam cerca de 5.400 tokens ANTES de qualquer
    histórico, anexo ou resultado de pesquisa. Quando o total
    passa do num_ctx o Ollama não dá erro: ele descarta o começo
    do prompt em silêncio — justamente a mensagem de sistema e as
    ferramentas. O resultado são respostas vazias, ferramentas
    ignoradas e comportamento "esquecido" que parecem bug do
    modelo, mas são só contexto estourado.

    A estimativa é por caracteres (não há tokenizador do Qwen
    disponível offline de forma leve) e propositalmente
    conservadora.
    """

    CARACTERES_POR_TOKEN = 3

    TOKENS_POR_IMAGEM = 800

    SUFIXO_TRUNCADO = "\n[... truncado para caber no contexto ...]"

    # Nenhuma mensagem "de apoio" (resultado de pesquisa, texto
    # de anexo, saída de ferramenta) pode ocupar mais que essa
    # fração do orçamento. Sem esse teto, um resultado de busca
    # grande expulsava a conversa inteira do contexto.
    FRACAO_MAXIMA_APOIO = 0.35

    # O resumo do histórico descartado nunca toma mais que essa fração
    # do espaço livre (senão, em orçamento apertado, ele expulsaria as
    # mensagens recentes, que valem mais), e só vale a pena se couberem
    # pelo menos MINIMO_RESUMO_TOKENS.
    FRACAO_MAXIMA_RESUMO = 0.30

    MINIMO_RESUMO_TOKENS = 120

    def __init__(
        self,
        num_ctx=8192,
        reserva_resposta=1024,
        compactador=None,
        resumidor=None
    ):

        self.num_ctx = num_ctx

        self.reserva_resposta = reserva_resposta

        # Colaboradores injetáveis (trocáveis em testes).
        self._compactador = compactador or CompactadorHistorico()

        self._resumidor = resumidor or ResumidorHistorico()

        # Quantas mensagens antigas foram descartadas, quantas foram
        # encurtadas e quantas respostas antigas foram compactadas
        # no último ajuste (para log/diagnóstico).
        self.descartadas = 0

        self.encurtadas = 0

        self.compactadas = 0

        self.resumiu = False

    @property
    def tokens_disponiveis(self):

        return max(
            self.num_ctx - self.reserva_resposta,
            0
        )

    # --------------------------------------------------------
    # ESTIMATIVAS
    # --------------------------------------------------------

    def estimar_texto(self, texto):

        if not texto:
            return 0

        return -(-len(texto) // self.CARACTERES_POR_TOKEN)

    def estimar_schemas(self, schemas):

        if not schemas:
            return 0

        return self.estimar_texto(
            json.dumps(schemas, ensure_ascii=False)
        )

    def estimar_mensagem(self, mensagem):

        conteudo = self._ler_campo(mensagem, "content")

        imagens = self._ler_campo(mensagem, "images") or []

        # +4: custo fixo de papel/delimitadores por mensagem.
        return (
            self.estimar_texto(
                conteudo if isinstance(conteudo, str) else ""
            )
            + len(imagens) * self.TOKENS_POR_IMAGEM
            + 4
        )

    def estimar_mensagens(self, mensagens):

        return sum(
            self.estimar_mensagem(mensagem)
            for mensagem in mensagens
        )

    # --------------------------------------------------------
    # AJUSTE
    # --------------------------------------------------------

    def ajustar(
        self,
        mensagens,
        tokens_ferramentas=0
    ):
        """
        Devolve uma NOVA lista de mensagens que cabe no
        orçamento (a original não é alterada).

        Ordem de sacrifício:
        1. encurta respostas antigas e longas da Shaula (as mais
           velhas primeiro): as falas do usuário ficam intactas;
        2. descarta mensagens antigas do histórico (as mais velhas
           primeiro) — nunca a de sistema do topo nem nada a
           partir da última mensagem do usuário — e deixa no lugar
           um RESUMO curto do que saiu, para a conversa antiga não
           sumir por completo;
        3. se ainda assim não couber, encurta a maior mensagem
           de texto "de apoio" (resultado de pesquisa, texto de
           anexo, saída de ferramenta) da parte final.
        """

        self.descartadas = 0

        self.encurtadas = 0

        self.compactadas = 0

        self.resumiu = False

        orcamento = (
            self.tokens_disponiveis - tokens_ferramentas
        )

        indice_ultimo_usuario = self._indice_ultimo_usuario(
            mensagens
        )

        inicio = 1 if self._eh_sistema_do_topo(mensagens) else 0

        topo = list(mensagens[:inicio])

        historico = list(mensagens[inicio:indice_ultimo_usuario])

        cauda = list(mensagens[indice_ultimo_usuario:])

        cauda = self._limitar_mensagens_de_apoio(
            cauda,
            int(orcamento * self.FRACAO_MAXIMA_APOIO)
        )

        fixo = (
            self.estimar_mensagens(topo)
            + self.estimar_mensagens(cauda)
        )

        total_historico = self.estimar_mensagens(historico)

        # 1) Encurta respostas antigas longas antes de descartar.
        for posicao in range(len(historico)):

            if fixo + total_historico <= orcamento:
                break

            original = historico[posicao]

            compacta = self._compactador.compactar(original)

            if compacta is not original:

                total_historico += (
                    self.estimar_mensagem(compacta)
                    - self.estimar_mensagem(original)
                )

                historico[posicao] = compacta

                self.compactadas += 1

        # 2) Descarta as mais antigas, já reservando espaço para o
        # resumo do que sair.
        limite_resumo = min(
            self._resumidor.LIMITE_TOKENS,
            int(max(orcamento - fixo, 0) * self.FRACAO_MAXIMA_RESUMO)
        )

        if limite_resumo < self.MINIMO_RESUMO_TOKENS:
            limite_resumo = 0

        precisa_resumo = fixo + total_historico > orcamento

        reserva_resumo = limite_resumo if precisa_resumo else 0

        removidas = []

        while (
            historico
            and fixo + total_historico + reserva_resumo > orcamento
        ):

            removida = historico.pop(0)

            removidas.append(removida)

            total_historico -= self.estimar_mensagem(removida)

            self.descartadas += 1

        if removidas and limite_resumo:

            resumo = self._resumidor.resumir(
                removidas,
                limite_tokens=limite_resumo
            )

            if (
                resumo is not None
                and fixo
                + total_historico
                + self.estimar_mensagem(resumo)
                <= orcamento
            ):

                historico.insert(0, resumo)

                total_historico += self.estimar_mensagem(resumo)

                self.resumiu = True

        cauda = self._encurtar_cauda(
            cauda,
            excesso=(
                fixo + total_historico - orcamento
            )
        )

        return topo + historico + cauda

    # --------------------------------------------------------
    # INTERNOS
    # --------------------------------------------------------

    def _limitar_mensagens_de_apoio(self, cauda, limite_tokens):

        if limite_tokens <= 0:
            return cauda

        resultado = []

        for mensagem in cauda:

            if (
                isinstance(mensagem, dict)
                and mensagem.get("role") in ("system", "tool")
                and isinstance(mensagem.get("content"), str)
                and self.estimar_mensagem(mensagem) > limite_tokens
            ):

                mensagem = dict(mensagem)

                mensagem["content"] = (
                    mensagem["content"][
                        :limite_tokens * self.CARACTERES_POR_TOKEN
                    ]
                    + self.SUFIXO_TRUNCADO
                )

                self.encurtadas += 1

            resultado.append(mensagem)

        return resultado

    def _encurtar_cauda(self, cauda, excesso):

        if excesso <= 0:
            return cauda

        cauda = list(cauda)

        while excesso > 0:

            candidatos = [
                (posicao, self.estimar_mensagem(mensagem))
                for posicao, mensagem in enumerate(cauda)
                if isinstance(mensagem, dict)
                and mensagem.get("role") in ("system", "tool")
                and isinstance(mensagem.get("content"), str)
                and len(mensagem["content"]) > 400
            ]

            if not candidatos:
                break

            posicao, tokens = max(
                candidatos,
                key=lambda item: item[1]
            )

            mensagem = dict(cauda[posicao])

            conteudo = mensagem["content"]

            reducao = min(excesso + 50, tokens - 100)

            if reducao <= 0:
                break

            novo_tamanho = max(
                len(conteudo)
                - reducao * self.CARACTERES_POR_TOKEN,
                200
            )

            mensagem["content"] = (
                conteudo[:novo_tamanho] + self.SUFIXO_TRUNCADO
            )

            cauda[posicao] = mensagem

            self.encurtadas += 1

            excesso -= (
                tokens - self.estimar_mensagem(mensagem)
            )

        return cauda

    @staticmethod
    def _ler_campo(mensagem, campo):

        if isinstance(mensagem, dict):
            return mensagem.get(campo)

        return getattr(mensagem, campo, None)

    def _eh_sistema_do_topo(self, mensagens):

        return (
            bool(mensagens)
            and self._ler_campo(mensagens[0], "role") == "system"
        )

    def _indice_ultimo_usuario(self, mensagens):

        for indice in range(len(mensagens) - 1, -1, -1):

            if self._ler_campo(mensagens[indice], "role") == "user":
                return indice

        return len(mensagens)
