from .ferramenta import Ferramenta


class AbrirProgramaFerramenta(Ferramenta):

    def __init__(self, gerenciador_programas):
        self._gerenciador = gerenciador_programas

    @property
    def nome(self):
        return "abrir_programa"

    @property
    def descricao(self):
        return "Localiza e abre um programa instalado no Windows."

    @property
    def parametros(self):
        return {
            "type": "object",
            "properties": {"nome": {"type": "string"}},
            "required": ["nome"]
        }

    def executar(self, argumentos):
        return self._gerenciador.abrir_programa(argumentos["nome"])


class FecharProgramaFerramenta(Ferramenta):

    def __init__(self, gerenciador_programas):
        self._gerenciador = gerenciador_programas

    @property
    def nome(self):
        return "fechar_programa"

    @property
    def descricao(self):
        return (
            "Fecha um programa pelo nome (ex.: 'spotify', "
            "'chrome') — fecha todas as janelas/processos "
            "associados a ele."
        )

    @property
    def parametros(self):
        return {
            "type": "object",
            "properties": {"nome": {"type": "string"}},
            "required": ["nome"]
        }

    def executar(self, argumentos):
        return self._gerenciador.fechar_programa(argumentos["nome"])


class BuscarArquivoFerramenta(Ferramenta):

    def __init__(self, buscador_arquivos):
        self._buscador = buscador_arquivos

    @property
    def nome(self):
        return "buscar_arquivo"

    @property
    def descricao(self):
        return (
            "Procura um arquivo pelo nome em uma unidade "
            "ou em todos os discos."
        )

    @property
    def parametros(self):
        return {
            "type": "object",
            "properties": {
                "nome": {"type": "string"},
                "unidade": {"type": "string"}
            },
            "required": ["nome"]
        }

    def executar(self, argumentos):
        return self._buscador.buscar_arquivo(
            argumentos["nome"],
            argumentos.get("unidade")
        )


class AbrirArquivoFerramenta(Ferramenta):

    def __init__(self, buscador_arquivos):
        self._buscador = buscador_arquivos

    @property
    def nome(self):
        return "abrir_arquivo"

    @property
    def descricao(self):
        return "Abre um arquivo pelo caminho completo."

    @property
    def parametros(self):
        return {
            "type": "object",
            "properties": {"caminho": {"type": "string"}},
            "required": ["caminho"]
        }

    def executar(self, argumentos):
        return self._buscador.abrir_arquivo(argumentos["caminho"])


class DesligarComputadorFerramenta(Ferramenta):

    def __init__(self, informacoes_sistema):
        self._sistema = informacoes_sistema

    @property
    def nome(self):
        return "desligar_computador"

    @property
    def descricao(self):
        return (
            "Agenda o desligamento do computador Windows. "
            "Use somente quando solicitado."
        )

    @property
    def parametros(self):
        return {
            "type": "object",
            "properties": {"segundos": {"type": "integer"}},
            "required": ["segundos"]
        }

    def executar(self, argumentos):
        return self._sistema.desligar_computador(argumentos["segundos"])


class CancelarDesligamentoFerramenta(Ferramenta):

    def __init__(self, informacoes_sistema):
        self._sistema = informacoes_sistema

    @property
    def nome(self):
        return "cancelar_desligamento"

    @property
    def descricao(self):
        return "Cancela um desligamento agendado."

    def executar(self, argumentos):
        return self._sistema.cancelar_desligamento()


class BloquearTelaFerramenta(Ferramenta):

    def __init__(self, informacoes_sistema):
        self._sistema = informacoes_sistema

    @property
    def nome(self):
        return "bloquear_tela"

    @property
    def descricao(self):
        return (
            "Bloqueia a tela do Windows (equivalente a Win+L). "
            "Instantâneo por padrão, ou com um atraso em segundos."
        )

    @property
    def parametros(self):
        return {
            "type": "object",
            "properties": {
                "atraso": {
                    "type": "number",
                    "description": (
                        "Segundos de espera antes de bloquear. "
                        "0 ou omitido = instantâneo."
                    )
                }
            },
            "required": []
        }

    def executar(self, argumentos):
        return self._sistema.bloquear_tela(argumentos.get("atraso", 0))


class TestarPingFerramenta(Ferramenta):

    def __init__(self, informacoes_sistema):
        self._sistema = informacoes_sistema

    @property
    def nome(self):
        return "testar_ping"

    @property
    def descricao(self):
        return "Testa a conectividade usando ping."

    @property
    def parametros(self):
        return {
            "type": "object",
            "properties": {"host": {"type": "string"}},
            "required": []
        }

    def executar(self, argumentos):
        return self._sistema.testar_ping(
            argumentos.get("host", "google.com")
        )


class InformacoesHardwareFerramenta(Ferramenta):

    def __init__(self, informacoes_sistema):
        self._sistema = informacoes_sistema

    @property
    def nome(self):
        return "informacoes_hardware"

    @property
    def descricao(self):
        return "Obtém informações do hardware e sistema."

    def executar(self, argumentos):
        return self._sistema.informacoes_hardware()


class AbrirMenuIniciarFerramenta(Ferramenta):

    def __init__(self, gerenciador_janelas):
        self._janelas = gerenciador_janelas

    @property
    def nome(self):
        return "abrir_menu_iniciar"

    @property
    def descricao(self):
        return "Abre o menu Iniciar."

    def executar(self, argumentos):
        return self._janelas.abrir_menu_iniciar()


class AtivarInternetFerramenta(Ferramenta):

    def __init__(self, estado_internet):
        self._estado = estado_internet

    @property
    def nome(self):
        return "ativar_internet"

    @property
    def descricao(self):
        return "Ativa o modo de internet da Shaula."

    def executar(self, argumentos):
        return self._estado.ativar()


class DesativarInternetFerramenta(Ferramenta):

    def __init__(self, estado_internet):
        self._estado = estado_internet

    @property
    def nome(self):
        return "desativar_internet"

    @property
    def descricao(self):
        return "Desativa o modo de internet da Shaula."

    def executar(self, argumentos):
        return self._estado.desativar()


class ObterIpLocalFerramenta(Ferramenta):

    def __init__(self, informacoes_rede):
        self._rede = informacoes_rede

    @property
    def nome(self):
        return "obter_ip_local"

    @property
    def descricao(self):
        return "Mostra o(s) endereço(s) IP local(is) das interfaces de rede ativas."

    def executar(self, argumentos):
        return self._rede.obter_ip_local()


class VerificarWifiFerramenta(Ferramenta):

    def __init__(self, informacoes_rede):
        self._rede = informacoes_rede

    @property
    def nome(self):
        return "verificar_wifi"

    @property
    def descricao(self):
        return "Verifica se há uma rede Wi-Fi conectada e mostra o nome dela e a força do sinal."

    def executar(self, argumentos):
        return self._rede.verificar_wifi()


class PesquisarInternetFerramenta(Ferramenta):

    def __init__(self, pesquisa_internet):
        self._pesquisa = pesquisa_internet

    @property
    def nome(self):
        return "pesquisar_internet"

    @property
    def descricao(self):
        return "Pesquisa informações na internet."

    @property
    def parametros(self):
        return {
            "type": "object",
            "properties": {"consulta": {"type": "string"}},
            "required": ["consulta"]
        }

    @property
    def precisa_de_sintese(self):
        return True

    def executar(self, argumentos):
        return self._pesquisa.buscar(argumentos["consulta"])


class ListarMonitoresFerramenta(Ferramenta):

    def __init__(self, gerenciador_janelas):
        self._janelas = gerenciador_janelas

    @property
    def nome(self):
        return "listar_monitores"

    @property
    def descricao(self):
        return "Lista os monitores."

    def executar(self, argumentos):
        return self._janelas.listar_monitores()


class ListarJanelasAbertasFerramenta(Ferramenta):

    def __init__(self, gerenciador_janelas):
        self._janelas = gerenciador_janelas

    @property
    def nome(self):
        return "listar_janelas_abertas"

    @property
    def descricao(self):
        return "Lista os títulos de todas as janelas abertas no momento."

    def executar(self, argumentos):
        return self._janelas.listar_janelas_abertas()


class MoverProgramaMonitorFerramenta(Ferramenta):

    def __init__(self, gerenciador_janelas):
        self._janelas = gerenciador_janelas

    @property
    def nome(self):
        return "mover_programa_monitor"

    @property
    def descricao(self):
        return "Move uma janela de aplicativo para um monitor específico."

    @property
    def parametros(self):
        return {
            "type": "object",
            "properties": {
                "nome": {"type": "string"},
                "monitor": {"type": "integer"}
            },
            "required": ["nome"]
        }

    def executar(self, argumentos):
        return self._janelas.mover_programa_monitor(
            argumentos["nome"],
            argumentos.get("monitor")
        )


class MoverParaOutroMonitorFerramenta(Ferramenta):

    def __init__(self, gerenciador_janelas):
        self._janelas = gerenciador_janelas

    @property
    def nome(self):
        return "mover_para_outro_monitor"

    @property
    def descricao(self):
        return "Move um aplicativo para outro monitor."

    @property
    def parametros(self):
        return {
            "type": "object",
            "properties": {"nome": {"type": "string"}},
            "required": ["nome"]
        }

    def executar(self, argumentos):
        return self._janelas.mover_para_outro_monitor(argumentos["nome"])


class ControlarJanelaFerramenta(Ferramenta):

    def __init__(self, gerenciador_janelas):
        self._janelas = gerenciador_janelas

    @property
    def nome(self):
        return "controlar_janela"

    @property
    def descricao(self):
        return (
            "Minimiza, maximiza, restaura, fecha ou traz para "
            "frente (foca) uma janela aberta, identificada pelo "
            "nome ou parte do título."
        )

    @property
    def parametros(self):
        return {
            "type": "object",
            "properties": {
                "nome": {
                    "type": "string",
                    "description": (
                        "Nome ou parte do título da janela "
                        "(ex.: 'discord', 'chrome')."
                    )
                },
                "acao": {
                    "type": "string",
                    "enum": [
                        "minimizar",
                        "maximizar",
                        "restaurar",
                        "fechar",
                        "focar"
                    ],
                    "description": "Ação a realizar na janela."
                }
            },
            "required": ["nome", "acao"]
        }

    def executar(self, argumentos):
        return self._janelas.controlar_janela(
            argumentos["nome"],
            argumentos["acao"]
        )


class TirarPrintFerramenta(Ferramenta):

    def __init__(self, capturador_tela):
        self._capturador = capturador_tela

    @property
    def nome(self):
        return "tirar_print"

    @property
    def descricao(self):
        return (
            "Tira uma captura de tela (print/screenshot) de um "
            "monitor específico ou de todos os monitores ao "
            "mesmo tempo. Pode ser instantânea ou com um atraso "
            "em segundos antes de capturar (ex.: para dar tempo "
            "de trocar de janela)."
        )

    @property
    def parametros(self):
        return {
            "type": "object",
            "properties": {
                "monitor": {
                    "type": "integer",
                    "description": (
                        "Número do monitor a capturar (1, 2, "
                        "...). Ignorado se 'todos' for "
                        "verdadeiro. Se omitido, captura o "
                        "monitor principal."
                    )
                },
                "todos": {
                    "type": "boolean",
                    "description": (
                        "Se verdadeiro, captura todos os "
                        "monitores de uma vez, um arquivo por "
                        "monitor."
                    )
                },
                "atraso": {
                    "type": "number",
                    "description": (
                        "Segundos de espera antes de capturar. "
                        "0 ou omitido = instantâneo."
                    )
                },
                "destino": {
                    "type": "string",
                    "enum": ["arquivo", "area_transferencia", "ambos"],
                    "description": (
                        "Para onde vai o print: 'arquivo' salva "
                        "em disco (padrão), 'area_transferencia' "
                        "copia para a área de transferência "
                        "(colar com Ctrl+V), 'ambos' faz as duas "
                        "coisas. Não se aplica quando 'todos' é "
                        "verdadeiro — nesse caso sempre vira "
                        "arquivo, já que a área de transferência "
                        "só guarda uma imagem por vez."
                    )
                }
            },
            "required": []
        }

    def executar(self, argumentos):
        return self._capturador.tirar_print(
            monitor=argumentos.get("monitor"),
            todos=bool(argumentos.get("todos", False)),
            atraso=argumentos.get("atraso", 0),
            destino=argumentos.get("destino")
        )


class CriarLembreteFerramenta(Ferramenta):

    def __init__(self, gerenciador_lembretes):
        self._lembretes = gerenciador_lembretes

    @property
    def nome(self):
        return "criar_lembrete"

    @property
    def descricao(self):
        return (
            "Cria um lembrete com temporizador: avisa o "
            "usuário depois de um tempo determinado, com uma "
            "janela de aviso na tela."
        )

    @property
    def parametros(self):
        return {
            "type": "object",
            "properties": {
                "texto": {
                    "type": "string",
                    "description": (
                        "O que o lembrete deve dizer "
                        "(ex.: 'reunião com o cliente')."
                    )
                },
                "tempo": {
                    "type": "number",
                    "description": "Quantidade de tempo até o lembrete disparar."
                },
                "unidade": {
                    "type": "string",
                    "enum": ["segundos", "minutos", "horas"],
                    "description": "Unidade do tempo informado. Padrão: minutos."
                }
            },
            "required": ["texto", "tempo"]
        }

    def executar(self, argumentos):
        return self._lembretes.criar_lembrete(
            argumentos["texto"],
            argumentos["tempo"],
            argumentos.get("unidade", "minutos")
        )


class ListarLembretesFerramenta(Ferramenta):

    def __init__(self, gerenciador_lembretes):
        self._lembretes = gerenciador_lembretes

    @property
    def nome(self):
        return "listar_lembretes"

    @property
    def descricao(self):
        return "Lista os lembretes programados que ainda não dispararam."

    def executar(self, argumentos):
        return self._lembretes.listar_lembretes()


class CancelarLembreteFerramenta(Ferramenta):

    def __init__(self, gerenciador_lembretes):
        self._lembretes = gerenciador_lembretes

    @property
    def nome(self):
        return "cancelar_lembrete"

    @property
    def descricao(self):
        return (
            "Cancela um lembrete programado, pelo número dele "
            "(use listar_lembretes para ver os números)."
        )

    @property
    def parametros(self):
        return {
            "type": "object",
            "properties": {
                "id_lembrete": {
                    "type": "integer",
                    "description": "Número do lembrete a cancelar."
                }
            },
            "required": ["id_lembrete"]
        }

    def executar(self, argumentos):
        return self._lembretes.cancelar_lembrete(argumentos["id_lembrete"])


class ListarProcessosProtegidosFerramenta(Ferramenta):

    def __init__(self, gerenciador_processos):
        self._processos = gerenciador_processos

    @property
    def nome(self):
        return "listar_processos_protegidos"

    @property
    def descricao(self):
        return (
            "Lista os processos que nunca são finalizados por "
            "segurança, mesmo se solicitado."
        )

    def executar(self, argumentos):
        return self._processos.listar_processos_protegidos()


class ListarProcessosFerramenta(Ferramenta):

    def __init__(self, gerenciador_processos):
        self._processos = gerenciador_processos

    @property
    def nome(self):
        return "listar_processos"

    @property
    def descricao(self):
        return (
            "Lista os processos que mais consomem CPU ou "
            "memória no momento."
        )

    @property
    def parametros(self):
        return {
            "type": "object",
            "properties": {
                "ordenar_por": {
                    "type": "string",
                    "enum": ["cpu", "memoria"],
                    "description": "Critério de ordenação. Padrão: cpu."
                },
                "limite": {
                    "type": "integer",
                    "description": "Quantos processos mostrar. Padrão: 10."
                }
            },
            "required": []
        }

    def executar(self, argumentos):
        return self._processos.listar_processos(
            ordenar_por=argumentos.get("ordenar_por", "cpu"),
            limite=argumentos.get("limite", 10)
        )


class FinalizarProcessoFerramenta(Ferramenta):

    def __init__(self, gerenciador_processos):
        self._processos = gerenciador_processos

    @property
    def nome(self):
        return "finalizar_processo"

    @property
    def descricao(self):
        return (
            "Finaliza um processo pelo nome (mata todos os "
            "processos com esse nome, ex.: várias instâncias "
            "abertas do Chrome) ou por um PID exato."
        )

    @property
    def parametros(self):
        return {
            "type": "object",
            "properties": {
                "alvo": {
                    "type": "string",
                    "description": (
                        "Nome do processo (ex.: 'chrome.exe') "
                        "ou PID (ex.: '1234')."
                    )
                }
            },
            "required": ["alvo"]
        }

    def executar(self, argumentos):
        return self._processos.finalizar_processo(argumentos["alvo"])


class CopiarTextoFerramenta(Ferramenta):

    def __init__(self, gerenciador_clipboard):
        self._clipboard = gerenciador_clipboard

    @property
    def nome(self):
        return "copiar_texto"

    @property
    def descricao(self):
        return "Copia um texto para a área de transferência do Windows."

    @property
    def parametros(self):
        return {
            "type": "object",
            "properties": {"texto": {"type": "string"}},
            "required": ["texto"]
        }

    def executar(self, argumentos):
        return self._clipboard.copiar_texto(argumentos["texto"])


class ColarTextoFerramenta(Ferramenta):

    def __init__(self, gerenciador_clipboard):
        self._clipboard = gerenciador_clipboard

    @property
    def nome(self):
        return "colar_texto"

    @property
    def descricao(self):
        return "Lê o texto atual da área de transferência do Windows."

    def executar(self, argumentos):
        return self._clipboard.colar_texto()
