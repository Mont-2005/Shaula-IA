import os
import re
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass


class AtrasoDesligamento:
    """
    Atraso do desligamento, já saneado. O modelo às vezes omite
    `segundos`, manda texto ("30") ou null: ausente/inválido vira o
    PADRAO (60 s); 0 continua significando "agora". A regra de
    confirmação e a ferramenta usam esta mesma classe, para a pergunta
    nunca divergir do que realmente acontece.
    """

    PADRAO = 60

    def __init__(self, valor=None):

        self._segundos = self._interpretar(valor)

    @classmethod
    def _interpretar(cls, valor):

        if valor is None or isinstance(valor, bool):
            return cls.PADRAO

        try:
            return int(float(str(valor).strip().replace(",", ".")))
        except (ValueError, OverflowError):
            return cls.PADRAO

    @property
    def segundos(self):
        return self._segundos

    @property
    def imediato(self):
        return self._segundos == 0

    @property
    def descricao(self):
        return (
            "agora"
            if self.imediato
            else f"em {self._segundos} segundo(s)"
        )


@dataclass(frozen=True)
class PedidoConfirmacao:
    """O que será perguntado ao usuário antes de uma ação sensível."""

    ferramenta: str
    titulo: str
    descricao: str

    @property
    def mensagem_negada(self):
        """Resposta da ferramenta quando o usuário diz não."""

        return (
            "Ação cancelada: você não autorizou "
            f"{self.descricao}."
        )


# ============================================================
# REGRAS (uma por ferramenta sensível)
# ============================================================

class RegraConfirmacao(ABC):
    """
    Decide, para UMA ferramenta, se uma chamada específica precisa
    de confirmação e como descrevê-la. Devolve None quando a
    chamada é inofensiva (ex.: controlar_janela com "minimizar").
    """

    @property
    @abstractmethod
    def ferramenta(self):
        """Nome da ferramenta que esta regra cobre."""

    @abstractmethod
    def avaliar(self, argumentos):
        """Devolve um PedidoConfirmacao ou None."""


class RegraDesligarComputador(RegraConfirmacao):

    ferramenta = "desligar_computador"

    def avaliar(self, argumentos):

        atraso = AtrasoDesligamento(argumentos.get("segundos"))

        return PedidoConfirmacao(
            self.ferramenta,
            "Desligar o computador?",
            f"desligar o computador {atraso.descricao}",
        )


class RegraFinalizarProcesso(RegraConfirmacao):

    ferramenta = "finalizar_processo"

    def avaliar(self, argumentos):

        alvo = str(argumentos.get("alvo", "")).strip() or "?"

        return PedidoConfirmacao(
            self.ferramenta,
            "Finalizar processo?",
            f"finalizar o(s) processo(s) '{alvo}' "
            "(o que estiver aberto nele pode perder dados "
            "não salvos)",
        )


class RegraFecharPrograma(RegraConfirmacao):

    ferramenta = "fechar_programa"

    def avaliar(self, argumentos):

        nome = str(argumentos.get("nome", "")).strip() or "?"

        return PedidoConfirmacao(
            self.ferramenta,
            "Fechar programa?",
            f"fechar o programa '{nome}' (trabalho não salvo "
            "pode ser perdido)",
        )


class RegraFecharJanela(RegraConfirmacao):

    ferramenta = "controlar_janela"

    def avaliar(self, argumentos):

        if str(argumentos.get("acao", "")).strip().lower() != "fechar":
            return None

        nome = str(argumentos.get("nome", "")).strip() or "?"

        return PedidoConfirmacao(
            self.ferramenta,
            "Fechar janela?",
            f"fechar a janela '{nome}' (trabalho não salvo "
            "pode ser perdido)",
        )


class CaminhoExecutavel:
    """
    Um nome de arquivo do jeito que o Windows o enxerga, para decidir
    se abri-lo é executar um programa ou script.

    O Windows ignora pontos e espaços no fim do nome ("run.bat." abre
    run.bat) e aceita um fluxo alternativo depois de dois-pontos
    ("run.exe:fluxo"); olhar só os últimos caracteres do texto
    recebido deixava essas formas passarem sem confirmação.
    """

    EXTENSOES = frozenset({
        ".exe", ".com", ".scr", ".msi", ".msp", ".bat", ".cmd",
        ".ps1", ".vbs", ".vbe", ".vb", ".js", ".jse", ".wsf", ".ws",
        ".wsh", ".sct", ".hta", ".reg", ".inf", ".lnk", ".url",
        ".pif", ".scf", ".cpl", ".msc", ".jar", ".py", ".pyw",
        ".application", ".gadget", ".appref-ms",
        ".docm", ".xlsm", ".pptm",
    })

    _FLUXO_ALTERNATIVO = re.compile(r"(?<=[^\\/:]):[^\\/:]*$")

    def __init__(self, texto):

        self._texto = str(texto or "").strip()

    @property
    def texto(self):
        """O texto como veio, sem espaços nas pontas."""

        return self._texto

    @property
    def normalizado(self):

        sem_pontos = self._texto.rstrip(" .")

        sem_fluxo = self._FLUXO_ALTERNATIVO.sub("", sem_pontos)

        return sem_fluxo.rstrip(" .")

    @property
    def extensao(self):

        return os.path.splitext(self.normalizado)[1].lower()

    @property
    def eh_executavel(self):

        return self.extensao in self.EXTENSOES


class RegraAbrirExecutavel(RegraConfirmacao):
    """
    Abrir um documento é seguro; abrir um programa ou script é
    executá-lo. Se o caminho veio de uma página pesquisada ou de
    uma frase mal reconhecida, vale perguntar.
    """

    ferramenta = "abrir_arquivo"

    EXTENSOES_EXECUTAVEIS = CaminhoExecutavel.EXTENSOES

    def avaliar(self, argumentos):

        caminho = CaminhoExecutavel(argumentos.get("caminho", ""))

        if not caminho.eh_executavel:
            return None

        return PedidoConfirmacao(
            self.ferramenta,
            "Executar arquivo?",
            f"abrir/executar o arquivo '{caminho.texto}' (é um "
            f"programa ou script, tipo {caminho.extensao})",
        )


class RegraAbrirPrograma(RegraConfirmacao):
    """
    abrir_programa("notepad") é o uso normal e não pergunta. Mas a
    ferramenta também aceita caminhos completos, caminhos de rede,
    endereços e scripts — e isso é executar um arquivo qualquer, o
    mesmo que RegraAbrirExecutavel já pergunta para abrir_arquivo.
    Sem esta regra, bastava chamar abrir_programa para contornar a
    confirmação.
    """

    ferramenta = "abrir_programa"

    SEPARADORES = ("\\", "/", ":")

    def avaliar(self, argumentos):

        nome = CaminhoExecutavel(argumentos.get("nome", ""))

        if any(c in nome.texto for c in self.SEPARADORES):

            motivo = "é um caminho ou endereço, não só o nome de um programa"

        elif nome.eh_executavel and nome.extensao != ".exe":

            motivo = f"é um script ou atalho, tipo {nome.extensao}"

        else:

            return None

        return PedidoConfirmacao(
            self.ferramenta,
            "Abrir programa?",
            f"abrir '{nome.texto}' ({motivo})",
        )


# ============================================================
# POLÍTICA
# ============================================================

class PoliticaConfirmacao:
    """
    Conjunto de regras que decide quais chamadas de ferramenta
    exigem a confirmação do usuário.

    Desligue com a variável de ambiente SHAULA_CONFIRMAR=0 (não
    recomendado: sem ela, um comando de voz mal reconhecido ou um
    texto malicioso numa página pesquisada pode fechar programas
    ou desligar o computador sem ninguém ver).
    """

    VARIAVEL_AMBIENTE = "SHAULA_CONFIRMAR"

    def __init__(self, regras=None, ativa=True):

        regras = (
            regras
            if regras is not None
            else self.regras_padrao()
        )

        self._regras = {
            regra.ferramenta: regra
            for regra in regras
        }

        self.ativa = ativa

    @staticmethod
    def regras_padrao():

        return [
            RegraDesligarComputador(),
            RegraFinalizarProcesso(),
            RegraFecharPrograma(),
            RegraFecharJanela(),
            RegraAbrirExecutavel(),
            RegraAbrirPrograma(),
        ]

    @classmethod
    def padrao(cls, ambiente=None):

        ambiente = os.environ if ambiente is None else ambiente

        desativada = (
            str(ambiente.get(cls.VARIAVEL_AMBIENTE, "1")).strip()
            == "0"
        )

        return cls(ativa=not desativada)

    @property
    def ferramentas_cobertas(self):

        return sorted(self._regras)

    def avaliar(self, ferramenta, argumentos):
        """PedidoConfirmacao se a chamada precisa de confirmação."""

        if not self.ativa:
            return None

        regra = self._regras.get(ferramenta)

        if regra is None:
            return None

        return regra.avaliar(argumentos or {})


# ============================================================
# CONFIRMADORES (quem pergunta)
# ============================================================

class Confirmador(ABC):
    """Pergunta ao usuário e devolve True (autorizou) ou False."""

    @abstractmethod
    def confirmar(self, pedido):
        """Pode ser chamado de qualquer thread."""


class ConfirmadorTerminal(Confirmador):
    """Versão de linha de comando (main.py): pergunta com [s/N]."""

    RESPOSTAS_SIM = frozenset({"s", "sim", "y", "yes"})

    def __init__(self, entrada=input, saida=print):

        self._entrada = entrada

        self._saida = saida

        self._trava = threading.Lock()

    def confirmar(self, pedido):

        with self._trava:

            self._saida(f"\n⚠ {pedido.titulo}")

            self._saida(f"A Shaula quer {pedido.descricao}.")

            try:

                resposta = self._entrada("Autorizar? [s/N]: ")

            except (EOFError, KeyboardInterrupt):

                return False

            return resposta.strip().lower() in self.RESPOSTAS_SIM


class ConfirmadorFixo(Confirmador):
    """Responde sempre igual. Útil em testes e automações."""

    def __init__(self, resposta):

        self.resposta = bool(resposta)

        self.pedidos = []

    def confirmar(self, pedido):

        self.pedidos.append(pedido)

        return self.resposta
