import os
import threading
import unicodedata
from dataclasses import dataclass

from .armazenamento import ArmazenamentoJson


@dataclass(frozen=True)
class PerfilEsforco:
    """
    Um nível de esforço: um pacote de parâmetros que, juntos,
    decidem quanto a Shaula "pensa" e quanto contexto usa.

    - pensar:       o modelo raciocina antes de responder
                    (think=True). Melhora a escolha de ferramentas
                    e pedidos ambíguos, mas é mais lento.
    - num_ctx:      tamanho da memória de trabalho do modelo, em
                    tokens. Mais contexto = cabem mais histórico e
                    anexos, ao custo de mais VRAM. Mudar o num_ctx
                    faz o Ollama recarregar o modelo.
    - num_predict:  teto de tokens gerados por chamada (raciocínio
                    + resposta). É também a reserva que o
                    OrcamentoContexto separa para a resposta.
    - max_rodadas:  idas e vindas modelo <-> ferramentas por
                    mensagem.
    """

    chave: str
    nome: str
    descricao: str
    pensar: bool
    num_ctx: int
    num_predict: int
    max_rodadas: int
    recomendado: bool = False
    aviso: str = ""

    @property
    def tokens_para_prompt(self):

        return max(self.num_ctx - self.num_predict, 0)

    @property
    def resumo(self):

        raciocinio = "com raciocínio" if self.pensar else "sem raciocínio"

        return (
            f"{raciocinio} · contexto {self.num_ctx} · "
            f"resposta até {self.num_predict} tokens · "
            f"até {self.max_rodadas} rodadas de ferramentas"
        )


class CatalogoEsforco:
    """
    Lista fixa dos níveis disponíveis, do mais leve ao mais pesado.

    Os valores foram escolhidos para uma GPU de 8 GB rodando o
    qwen3.5:9b. O prompt de sistema (~1.700 tokens) e os 40 schemas
    de ferramentas (~4.100) ocupam cerca de 5.900 tokens ANTES de
    qualquer conversa, e a reserva de resposta (num_predict) sai do
    mesmo num_ctx; com 8192 sobravam só ~180 tokens de histórico no
    Médio, e a Shaula "esquecia" tudo logo na segunda mensagem. Cada
    nível agora deixa espaço real para o histórico (de ~3.200 tokens
    no Baixo/Médio a ~6.300 no Máx). Como o qwen3.5 usa atenção
    completa em apenas 8 de 32 camadas, cada token de contexto custa
    ~32 KB de VRAM: os aumentos abaixo somam de 64 a 96 MB por nível.
    Extra e Máx continuam com aviso: em placas de 8 GB parte do
    modelo ainda pode ir para a CPU.
    """

    PADRAO = "medio"

    PERFIS = (
        PerfilEsforco(
            chave="baixo",
            nome="Baixo",
            descricao="Respostas rápidas, sem raciocínio.",
            pensar=False,
            num_ctx=10240,
            num_predict=1024,
            max_rodadas=4,
        ),
        PerfilEsforco(
            chave="medio",
            nome="Médio",
            descricao="Equilíbrio entre velocidade e qualidade.",
            pensar=True,
            num_ctx=11264,
            num_predict=2048,
            max_rodadas=8,
            recomendado=True,
        ),
        PerfilEsforco(
            chave="alto",
            nome="Alto",
            descricao="Raciocina mais e lembra mais da conversa.",
            pensar=True,
            num_ctx=13312,
            num_predict=3072,
            max_rodadas=8,
        ),
        PerfilEsforco(
            chave="extra",
            nome="Extra",
            descricao="Raciocínio longo e bastante contexto.",
            pensar=True,
            num_ctx=15360,
            num_predict=4096,
            max_rodadas=10,
            aviso=(
                "Usa mais VRAM: em placas de 8 GB parte do modelo "
                "pode ir para a CPU e a resposta ficar mais lenta."
            ),
        ),
        PerfilEsforco(
            chave="max",
            nome="Máx",
            descricao="O máximo de raciocínio e de contexto.",
            pensar=True,
            num_ctx=18432,
            num_predict=6144,
            max_rodadas=12,
            aviso=(
                "Muito mais lento e pesado. Em placas de 8 GB é "
                "provável que parte do modelo vá para a CPU."
            ),
        ),
    )

    @staticmethod
    def _normalizar(texto):
        """'Médio', ' MEDIO ' e 'medio' são o mesmo nível."""

        sem_acento = unicodedata.normalize(
            "NFD",
            str(texto)
        )

        return "".join(
            letra
            for letra in sem_acento
            if unicodedata.category(letra) != "Mn"
        ).strip().lower()

    @classmethod
    def listar(cls):

        return list(cls.PERFIS)

    @classmethod
    def obter(cls, chave):
        """Devolve o perfil pelo nome/chave, ou None se não existir."""

        procurada = cls._normalizar(chave)

        for perfil in cls.PERFIS:

            if procurada in (
                perfil.chave,
                cls._normalizar(perfil.nome)
            ):
                return perfil

        return None

    @classmethod
    def padrao(cls):

        return cls.obter(cls.PADRAO)


class EstadoEsforco:
    """
    Nível de esforço em uso, compartilhado por todas as janelas
    (como o EstadoInternet) e lembrado entre uma sessão e outra.

    Ordem de prioridade ao abrir a Shaula:
    1. o nível que a pessoa escolheu na última vez (salvo em
       ~/.shaula/configuracoes.json);
    2. a variável de ambiente SHAULA_ESFORCO (baixo, medio, alto,
       extra ou max);
    3. o nível padrão (Médio).
    """

    VARIAVEL_AMBIENTE = "SHAULA_ESFORCO"

    CHAVE_NO_ARQUIVO = "esforco"

    def __init__(
        self,
        armazenamento=None,
        ambiente=None
    ):

        if armazenamento is None:

            armazenamento = ArmazenamentoJson(
                os.path.join(
                    os.path.expanduser("~"),
                    ".shaula",
                    "configuracoes.json"
                )
            )

        self._armazenamento = armazenamento

        self._trava = threading.Lock()

        ambiente = (
            os.environ
            if ambiente is None
            else ambiente
        )

        self._perfil = (
            self._perfil_salvo()
            or CatalogoEsforco.obter(
                ambiente.get(self.VARIAVEL_AMBIENTE, "")
            )
            or CatalogoEsforco.padrao()
        )

    @property
    def perfil(self):

        with self._trava:

            return self._perfil

    def definir(self, chave):
        """
        Troca o nível e guarda a escolha. Devolve o perfil novo,
        ou None se o nome não for um nível válido (nada muda).
        """

        novo = CatalogoEsforco.obter(chave)

        if novo is None:
            return None

        with self._trava:

            self._perfil = novo

            self._salvar(novo)

        return novo

    # --------------------------------------------------------

    def _perfil_salvo(self):

        dados = self._armazenamento.ler(padrao={})

        if not isinstance(dados, dict):
            return None

        return CatalogoEsforco.obter(
            dados.get(self.CHAVE_NO_ARQUIVO, "")
        )

    def _salvar(self, perfil):

        with self._armazenamento.trava:

            dados = self._armazenamento.ler(padrao={})

            if not isinstance(dados, dict):
                dados = {}

            dados[self.CHAVE_NO_ARQUIVO] = perfil.chave

            self._armazenamento.gravar(dados)
