from .calculadora import Calculadora
from .cache import CacheComandos
from .arquivos import BuscadorArquivos
from .janelas import GerenciadorJanelas
from .programas import GerenciadorProgramas
from .sistema import InformacoesSistema
from .internet import EstadoInternet
from .pesquisa import PesquisaInternet
from .captura_tela import CapturadorTela
from .lembretes import GerenciadorLembretes
from .notificacoes import NotificadorToast
from .processos import GerenciadorProcessos
from .clipboard import GerenciadorClipboard
from .rede import InformacoesRede

from .ferramentas_calculo import (
    CalcularFerramenta,
    MatrizSomaFerramenta,
    MatrizSubtracaoFerramenta,
    MatrizMultiplicacaoFerramenta,
    MatrizEscalarFerramenta,
    MatrizTranspostaFerramenta,
    MatrizDeterminanteFerramenta,
    MatrizInversaFerramenta,
    MatrizPotenciaFerramenta,
    ConverterBaseFerramenta,
)

from .ferramentas_sistema import (
    AbrirProgramaFerramenta,
    FecharProgramaFerramenta,
    BuscarArquivoFerramenta,
    AbrirArquivoFerramenta,
    DesligarComputadorFerramenta,
    CancelarDesligamentoFerramenta,
    BloquearTelaFerramenta,
    TestarPingFerramenta,
    InformacoesHardwareFerramenta,
    AbrirMenuIniciarFerramenta,
    AtivarInternetFerramenta,
    DesativarInternetFerramenta,
    PesquisarInternetFerramenta,
    ListarMonitoresFerramenta,
    ListarJanelasAbertasFerramenta,
    MoverProgramaMonitorFerramenta,
    MoverParaOutroMonitorFerramenta,
    TirarPrintFerramenta,
    ControlarJanelaFerramenta,
    CriarLembreteFerramenta,
    ListarLembretesFerramenta,
    CancelarLembreteFerramenta,
    ListarProcessosFerramenta,
    ListarProcessosProtegidosFerramenta,
    FinalizarProcessoFerramenta,
    CopiarTextoFerramenta,
    ColarTextoFerramenta,
    ObterIpLocalFerramenta,
    VerificarWifiFerramenta,
)


class RegistroFerramentas:
    """
    Monta e guarda uma instância de cada ferramenta disponível
    para a Chelsea, cuidando de conectar cada uma ao serviço
    certo (cache, buscador de arquivos, gerenciador de janelas
    etc.). Substitui o antigo dicionário `_DISPATCH_FERRAMENTAS`
    de nome -> lambda.

    Uso:

        registro = RegistroFerramentas(estado_internet)
        registro.executar("abrir_programa", {"nome": "firefox"})
        registro.schemas_openai()  # lista para enviar ao Ollama
    """

    def __init__(
        self,
        estado_internet=None,
        cache=None,
        ferramentas_permitidas=None
    ):
        """
        ferramentas_permitidas: se fornecido (um conjunto de
        nomes), restringe o registro a só essas ferramentas —
        usado pelo main.py (versão de linha de comando), que
        originalmente só tinha acesso a um subconjunto (sem
        internet, sem controle de janelas/sistema). Se None
        (padrão), registra todas as ferramentas disponíveis.
        """

        self.estado_internet = estado_internet or EstadoInternet()

        cache = cache or CacheComandos()

        calculadora = Calculadora()
        buscador_arquivos = BuscadorArquivos(cache=cache)
        gerenciador_janelas = GerenciadorJanelas(cache=cache)
        gerenciador_processos = GerenciadorProcessos()
        gerenciador_programas = GerenciadorProgramas(gerenciador_processos)
        gerenciador_clipboard = GerenciadorClipboard()
        informacoes_rede = InformacoesRede()
        informacoes_sistema = InformacoesSistema()
        pesquisa_internet = PesquisaInternet(self.estado_internet)
        capturador_tela = CapturadorTela(gerenciador_janelas)
        notificador_toast = NotificadorToast()
        gerenciador_lembretes = GerenciadorLembretes(notificador_toast)

        ferramentas = [
            AbrirProgramaFerramenta(gerenciador_programas),
            FecharProgramaFerramenta(gerenciador_programas),
            BuscarArquivoFerramenta(buscador_arquivos),
            AbrirArquivoFerramenta(buscador_arquivos),
            CalcularFerramenta(calculadora),
            MatrizSomaFerramenta(calculadora),
            MatrizSubtracaoFerramenta(calculadora),
            MatrizMultiplicacaoFerramenta(calculadora),
            MatrizEscalarFerramenta(calculadora),
            MatrizTranspostaFerramenta(calculadora),
            MatrizDeterminanteFerramenta(calculadora),
            MatrizInversaFerramenta(calculadora),
            MatrizPotenciaFerramenta(calculadora),
            ConverterBaseFerramenta(calculadora),
            DesligarComputadorFerramenta(informacoes_sistema),
            CancelarDesligamentoFerramenta(informacoes_sistema),
            BloquearTelaFerramenta(informacoes_sistema),
            TestarPingFerramenta(informacoes_sistema),
            InformacoesHardwareFerramenta(informacoes_sistema),
            AbrirMenuIniciarFerramenta(gerenciador_janelas),
            AtivarInternetFerramenta(self.estado_internet),
            DesativarInternetFerramenta(self.estado_internet),
            PesquisarInternetFerramenta(pesquisa_internet),
            ListarMonitoresFerramenta(gerenciador_janelas),
            ListarJanelasAbertasFerramenta(gerenciador_janelas),
            MoverProgramaMonitorFerramenta(gerenciador_janelas),
            MoverParaOutroMonitorFerramenta(gerenciador_janelas),
            TirarPrintFerramenta(capturador_tela),
            ControlarJanelaFerramenta(gerenciador_janelas),
            CriarLembreteFerramenta(gerenciador_lembretes),
            ListarLembretesFerramenta(gerenciador_lembretes),
            CancelarLembreteFerramenta(gerenciador_lembretes),
            ListarProcessosFerramenta(gerenciador_processos),
            ListarProcessosProtegidosFerramenta(gerenciador_processos),
            FinalizarProcessoFerramenta(gerenciador_processos),
            CopiarTextoFerramenta(gerenciador_clipboard),
            ColarTextoFerramenta(gerenciador_clipboard),
            ObterIpLocalFerramenta(informacoes_rede),
            VerificarWifiFerramenta(informacoes_rede),
        ]

        if ferramentas_permitidas is not None:

            ferramentas = [
                ferramenta
                for ferramenta in ferramentas
                if ferramenta.nome in ferramentas_permitidas
            ]

        self._ferramentas = {
            ferramenta.nome: ferramenta
            for ferramenta in ferramentas
        }

        # Guardamos referências aos serviços também, para casos
        # em que o resto do código precisa acessá-los
        # diretamente (ex.: TrabalhadorIA quer saber quais URLs
        # uma pesquisa retornou, ou disparar uma busca forçada).
        self.pesquisa_internet = pesquisa_internet
        self.buscador_arquivos = buscador_arquivos
        self.gerenciador_janelas = gerenciador_janelas
        self.capturador_tela = capturador_tela
        self.gerenciador_lembretes = gerenciador_lembretes
        self.cache = cache

    def obter(self, nome):
        """Devolve a instância de Ferramenta pelo nome, ou None."""

        return self._ferramentas.get(nome)

    def executar(self, nome, argumentos):
        """
        Executa a ferramenta pelo nome. Devolve uma mensagem de
        erro amigável se o nome não corresponder a nenhuma
        ferramenta conhecida (em vez de lançar exceção) — mesmo
        comportamento do dispatch table antigo.
        """

        ferramenta = self.obter(nome)

        if ferramenta is None:

            return f"Ferramenta desconhecida: {nome}"

        return ferramenta.executar(argumentos)

    def schemas_openai(self):
        """
        Lista de definições de ferramentas no formato que o
        Ollama espera — substitui a lista `tools = [...]` que
        antes era escrita manualmente.
        """

        return [
            ferramenta.schema_openai()
            for ferramenta in self._ferramentas.values()
        ]

    def __contains__(self, nome):

        return nome in self._ferramentas

    def __iter__(self):

        return iter(self._ferramentas.values())
