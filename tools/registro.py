from .confirmacao import PoliticaConfirmacao
from .janelas_proprias import OcultadorJanelasProprias
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
    AnalisarTelaFerramenta,
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
        ferramentas_permitidas=None,
        politica_confirmacao=None,
        confirmador=None
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

        # Ações destrutivas (desligar, finalizar processo, fechar
        # programa/janela, executar arquivo) só rodam depois que o
        # `confirmador` autorizar. Sem confirmador configurado,
        # essas ações são RECUSADAS (seguro por padrão); a interface
        # gráfica e o terminal configuram o seu.
        self.politica_confirmacao = (
            politica_confirmacao or PoliticaConfirmacao.padrao()
        )

        self.confirmador = confirmador

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
        capturador_tela = CapturadorTela(
            gerenciador_janelas,
            ocultador=OcultadorJanelasProprias()
        )
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
            AnalisarTelaFerramenta(capturador_tela),
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

        if not isinstance(argumentos, dict):
            argumentos = dict(argumentos or {})

        # Confere os parâmetros obrigatórios ANTES: assim não se pede
        # confirmação para uma chamada que vai falhar, e um KeyError de
        # dentro da ferramenta (um defeito dela, não do modelo) não é
        # confundido com "faltou parâmetro" — aparece como erro de
        # execução, com a causa verdadeira.
        faltando = [
            parametro
            for parametro in ferramenta.parametros.get("required", [])
            if parametro not in argumentos
        ]

        if faltando:

            nomes = ", ".join(f"'{p}'" for p in faltando)

            return (
                f"Faltou o parâmetro obrigatório {nomes} "
                f"para '{nome}'. Tente de novo informando-o."
            )

        negada = self._conferir_confirmacao(nome, argumentos)

        if negada is not None:
            return negada

        return ferramenta.executar(argumentos)

    def _conferir_confirmacao(self, nome, argumentos):
        """
        Devolve None se a ação pode seguir, ou o texto de recusa se
        ela exigir confirmação e o usuário não a deu.
        """

        pedido = self.politica_confirmacao.avaliar(nome, argumentos)

        if pedido is None:
            return None

        if self.confirmador is None:

            return (
                f"Ação não executada: {pedido.descricao} exige a "
                "confirmação do usuário, e não há como perguntar "
                "neste modo."
            )

        try:

            autorizado = self.confirmador.confirmar(pedido)

        except Exception:

            autorizado = False

        return None if autorizado else pedido.mensagem_negada

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
