import ctypes
import ctypes.wintypes
import time

from .cache import CacheComandos


# ============================================================
# ESTRUTURAS DO WINDOWS
# ============================================================
#
# Precisam ser classes ctypes.Structure de verdade — não dá
# para aninhar dentro de GerenciadorJanelas de forma limpa,
# então ficam no nível do módulo, como já eram.

user32 = ctypes.windll.user32


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.wintypes.LONG),
        ("top", ctypes.wintypes.LONG),
        ("right", ctypes.wintypes.LONG),
        ("bottom", ctypes.wintypes.LONG),
    ]


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", ctypes.wintypes.DWORD),
    ]


MonitorEnumProc = ctypes.WINFUNCTYPE(
    ctypes.wintypes.BOOL,
    ctypes.wintypes.HMONITOR,
    ctypes.wintypes.HDC,
    ctypes.POINTER(RECT),
    ctypes.wintypes.LPARAM
)


class GerenciadorJanelas:
    """
    Controle de janelas e monitores do Windows: encontrar
    janelas abertas, mover entre monitores, abrir o menu
    Iniciar. Encapsula as chamadas ctypes que antes viviam
    soltas dentro de interface.py.

    Recebe um CacheComandos (injeção de dependência) para
    lembrar em qual monitor cada programa costuma ser colocado
    — assim não depende de nenhuma variável global de cache.
    """

    def __init__(self, cache=None):

        self._cache = cache or CacheComandos()

    # --------------------------------------------------------
    # TECLADO
    # --------------------------------------------------------

    def pressionar_tecla(self, vk):

        KEYEVENTF_KEYUP = 0x0002

        user32.keybd_event(
            vk,
            0,
            0,
            0
        )

        user32.keybd_event(
            vk,
            0,
            KEYEVENTF_KEYUP,
            0
        )

    def pressionar_combinacao(self, teclas):

        KEYEVENTF_KEYUP = 0x0002

        for tecla in teclas:

            user32.keybd_event(
                tecla,
                0,
                0,
                0
            )

        time.sleep(0.05)

        for tecla in reversed(teclas):

            user32.keybd_event(
                tecla,
                0,
                KEYEVENTF_KEYUP,
                0
            )

    def abrir_menu_iniciar(self):

        VK_LWIN = 0x5B

        self.pressionar_tecla(VK_LWIN)

        return "Menu Iniciar aberto."

    # --------------------------------------------------------
    # MONITORES
    # --------------------------------------------------------

    def obter_monitores(self):

        monitores = []

        def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):

            info = MONITORINFO()

            info.cbSize = ctypes.sizeof(MONITORINFO)

            user32.GetMonitorInfoW(
                hMonitor,
                ctypes.byref(info)
            )

            monitores.append({
                "handle": hMonitor,
                "left": info.rcMonitor.left,
                "top": info.rcMonitor.top,
                "right": info.rcMonitor.right,
                "bottom": info.rcMonitor.bottom,
                "primary": bool(info.dwFlags & 1)
            })

            return True

        callback_func = MonitorEnumProc(callback)

        user32.EnumDisplayMonitors(
            0,
            0,
            callback_func,
            0
        )

        return monitores

    def _numero_monitor_em_lista(self, monitores, hmonitor):
        """
        Lookup puro em uma lista já obtida, sem chamar o
        Windows de novo. Usado quando várias janelas precisam
        ser resolvidas na mesma operação.
        """

        for numero, monitor in enumerate(monitores, start=1):

            if monitor["handle"] == hmonitor:

                return numero

        return None

    def _retangulo_da_janela(self, hwnd):

        retangulo = RECT()

        user32.GetWindowRect(
            hwnd,
            ctypes.byref(retangulo)
        )

        return retangulo

    def numero_monitor_da_janela(self, hwnd, monitores=None):
        """
        Número (1, 2...) do monitor onde a janela está de verdade, ou
        None se não der para saber.

        Decide pela GEOMETRIA — o monitor que cobre a maior parte do
        retângulo da janela — e só cai no handle de MonitorFromWindow
        se a janela estiver fora de todos (minimizada). Comparar
        handles sozinho é frágil: MonitorFromWindow devolve um int de
        32 bits com sinal e a enumeração devolve um HMONITOR sem sinal,
        então os dois podem não bater mesmo sendo o mesmo monitor — e
        aí "mover para o outro monitor" escolhia o destino errado.
        """

        monitores = monitores or self.obter_monitores()

        janela = self._retangulo_da_janela(hwnd)

        melhor = None

        maior_area = 0

        for numero, monitor in enumerate(monitores, start=1):

            largura = (
                min(janela.right, monitor["right"])
                - max(janela.left, monitor["left"])
            )

            altura = (
                min(janela.bottom, monitor["bottom"])
                - max(janela.top, monitor["top"])
            )

            if largura > 0 and altura > 0 and largura * altura > maior_area:

                maior_area = largura * altura

                melhor = numero

        if melhor is not None:

            return melhor

        return self._numero_monitor_em_lista(
            monitores,
            user32.MonitorFromWindow(
                hwnd,
                2
            )
        )

    def obter_numero_monitor(self, hmonitor):

        return self._numero_monitor_em_lista(
            self.obter_monitores(),
            hmonitor
        )

    def listar_monitores(self):

        monitores = self.obter_monitores()

        if not monitores:

            return "Não consegui detectar os monitores."

        linhas = [
            f"O Windows detectou "
            f"{len(monitores)} monitor(es):"
        ]

        for numero, monitor in enumerate(monitores, start=1):

            largura = monitor["right"] - monitor["left"]
            altura = monitor["bottom"] - monitor["top"]

            principal = (
                " — principal"
                if monitor["primary"]
                else ""
            )

            linhas.append(
                f"Monitor {numero}: "
                f"{largura}x{altura}"
                f"{principal}"
            )

        return "\n".join(linhas)

    # --------------------------------------------------------
    # JANELAS
    # --------------------------------------------------------

    def _enumerar_janelas_visiveis(self):
        """
        Enumera todas as janelas visíveis com título, sem
        filtro de nome — a mesma varredura via EnumWindows que
        encontrar_janelas_por_nome já fazia, só que devolvendo
        tudo. Fica num lugar só, reaproveitado tanto pela busca
        por nome quanto pela listagem completa.
        """

        resultados = []

        EnumWindowsProc = ctypes.WINFUNCTYPE(
            ctypes.wintypes.BOOL,
            ctypes.wintypes.HWND,
            ctypes.wintypes.LPARAM
        )

        def callback(hwnd, lParam):

            if not user32.IsWindowVisible(hwnd):

                return True

            tamanho = user32.GetWindowTextLengthW(hwnd)

            if tamanho == 0:

                return True

            buffer = ctypes.create_unicode_buffer(tamanho + 1)

            user32.GetWindowTextW(
                hwnd,
                buffer,
                tamanho + 1
            )

            resultados.append({
                "hwnd": hwnd,
                "titulo": buffer.value
            })

            return True

        callback_func = EnumWindowsProc(callback)

        user32.EnumWindows(
            callback_func,
            0
        )

        return resultados

    def encontrar_janelas_por_nome(self, nome):

        nome = str(nome).lower().strip()

        return [
            janela
            for janela in self._enumerar_janelas_visiveis()
            if nome in janela["titulo"].lower()
        ]

    def listar_janelas_abertas(self):
        """Lista os títulos de todas as janelas visíveis abertas no momento."""

        janelas = self._enumerar_janelas_visiveis()

        if not janelas:
            return "Não encontrei nenhuma janela aberta no momento."

        linhas = [f"{len(janelas)} janela(s) aberta(s):"]

        for janela in janelas:
            linhas.append(f"- {janela['titulo']}")

        return "\n".join(linhas)

    def _janelas_com_indice(self, nome):
        """
        Encontra janelas pelo nome, aceitando o sufixo " N" para
        escolher uma entre várias ("chrome 2").

        Antes, a busca usava o texto inteiro ("chrome 2") como
        trecho de título, não achava nada e respondia "não
        encontrei" — então a desambiguação que a própria mensagem
        de erro sugere ("mova o Discord 1 para o monitor 2")
        nunca funcionava.

        Devolve (janelas, indice, nome_base): `indice` é 1-based
        e só vem preenchido quando o sufixo foi usado e é válido.
        """

        nome = str(nome).strip()

        janelas = self.encontrar_janelas_por_nome(nome)

        if janelas:
            return janelas, None, nome

        partes = nome.rsplit(" ", 1)

        if len(partes) == 2 and partes[1].isdigit():

            base = partes[0].strip()

            janelas = self.encontrar_janelas_por_nome(base)

            indice = int(partes[1])

            if janelas and 1 <= indice <= len(janelas):
                return janelas, indice, base

            return janelas, None, base

        return [], None, nome

    def _resolver_janela(self, nome):
        """
        Encontra a janela certa a partir de um nome digitado
        pelo usuário. Se houver várias janelas com títulos
        parecidos, aceita o mesmo truque de "nome N" (ex.:
        'chrome 2') já usado em mover_programa_monitor para
        desambiguar. Devolve (janela, None) em caso de sucesso,
        ou (None, mensagem) se não achou nada ou ficou ambíguo.
        """

        janelas, indice, _base = self._janelas_com_indice(nome)

        if not janelas:

            return None, (
                f"Não encontrei uma janela aberta "
                f"correspondente a '{nome}'."
            )

        if indice is not None:

            return janelas[indice - 1], None

        if len(janelas) == 1:

            return janelas[0], None

        lista = "\n".join(
            f"{i}. {j['titulo']}"
            for i, j in enumerate(janelas, start=1)
        )

        return None, (
            "Encontrei várias janelas correspondentes. "
            "Especifique qual deseja controlar.\n"
            f"{lista}"
        )

    def controlar_janela(self, nome, acao):
        """
        Minimiza, maximiza, restaura, fecha ou foca uma janela
        pelo nome. 'fechar' envia WM_CLOSE (o mesmo que clicar
        no X) em vez de matar o processo — assim o programa
        ainda pode perguntar "salvar alterações?" se precisar,
        em vez de perder dados do usuário.
        """

        janela, erro = self._resolver_janela(nome)

        if erro:

            return erro

        acoes = {
            "minimizar": self._minimizar_janela,
            "maximizar": self._maximizar_janela,
            "restaurar": self._restaurar_janela,
            "fechar": self._fechar_janela,
            "focar": self._focar_janela,
        }

        acao = str(acao).strip().lower()

        funcao = acoes.get(acao)

        if funcao is None:

            return (
                f"Ação inválida: '{acao}'. Use minimizar, "
                "maximizar, restaurar, fechar ou focar."
            )

        return funcao(janela)

    def _minimizar_janela(self, janela):

        SW_MINIMIZE = 6

        user32.ShowWindow(
            janela["hwnd"],
            SW_MINIMIZE
        )

        return f"'{janela['titulo']}' minimizada."

    def _maximizar_janela(self, janela):

        SW_MAXIMIZE = 3

        user32.ShowWindow(
            janela["hwnd"],
            SW_MAXIMIZE
        )

        return f"'{janela['titulo']}' maximizada."

    def _restaurar_janela(self, janela):

        SW_RESTORE = 9

        user32.ShowWindow(
            janela["hwnd"],
            SW_RESTORE
        )

        return f"'{janela['titulo']}' restaurada."

    def _fechar_janela(self, janela):

        WM_CLOSE = 0x0010

        user32.PostMessageW(
            janela["hwnd"],
            WM_CLOSE,
            0,
            0
        )

        return f"Pedido de fechamento enviado para '{janela['titulo']}'."

    def _focar_janela(self, janela):

        SW_RESTORE = 9

        if user32.IsIconic(janela["hwnd"]):

            # Só restaura se estiver minimizada — se já estava
            # maximizada, focar não deveria "desmaximizar" a
            # janela.
            user32.ShowWindow(
                janela["hwnd"],
                SW_RESTORE
            )

        user32.SetForegroundWindow(janela["hwnd"])

        return f"'{janela['titulo']}' trazida para frente."

    # Quanto esperar (s) o Windows terminar de restaurar/maximizar/
    # mover uma janela antes de seguir. O Firefox e outros apps com
    # animação demoram mais que os 0,15 s fixos que havia antes.
    ESPERA_ESTADO_S = 1.0

    ESPERA_MOVER_S = 0.4

    TENTATIVAS_MOVER = 3

    def _aguardar(self, condicao, limite):
        """Repete `condicao()` até ficar verdadeira ou estourar o limite."""

        fim = time.monotonic() + limite

        while time.monotonic() < fim:

            if condicao():

                return True

            time.sleep(0.02)

        return bool(condicao())

    def _janela_dentro_do_monitor(self, hwnd, monitor):
        """O centro da janela cai dentro do retângulo do monitor?"""

        janela = self._retangulo_da_janela(hwnd)

        centro_x = (janela.left + janela.right) // 2

        centro_y = (janela.top + janela.bottom) // 2

        return (
            monitor["left"] <= centro_x < monitor["right"]
            and monitor["top"] <= centro_y < monitor["bottom"]
        )

    def _restaurar_ate_ficar_normal(self, hwnd):
        """
        Tira a janela de minimizada/maximizada e espera o Windows
        concluir. Devolve True se ela estava (ou voltou a ficar)
        maximizada — para maximizar de novo no fim. Uma janela
        minimizada que estava maximizada volta maximizada no primeiro
        SW_RESTORE, então pode precisar de um segundo.
        """

        SW_RESTORE = 9

        era_maximizada = bool(
            user32.IsZoomed(hwnd)
        )

        for _ in range(2):

            if not (
                user32.IsIconic(hwnd)
                or user32.IsZoomed(hwnd)
            ):

                break

            user32.ShowWindow(
                hwnd,
                SW_RESTORE
            )

            self._aguardar(
                lambda: not user32.IsIconic(hwnd),
                self.ESPERA_ESTADO_S
            )

            if user32.IsZoomed(hwnd):

                era_maximizada = True

        self._aguardar(
            lambda: not user32.IsZoomed(hwnd),
            self.ESPERA_ESTADO_S
        )

        return era_maximizada

    def _posicionar_no_monitor(
        self,
        hwnd,
        destino,
        largura,
        altura
    ):
        """
        SetWindowPos centralizado no monitor, conferindo depois que a
        janela realmente foi parar lá e repetindo se não foi (o
        Windows às vezes desfaz o movimento se a janela ainda está
        assentando). True se terminou dentro do monitor de destino.
        """

        SWP_NOZORDER = 0x0004
        SWP_SHOWWINDOW = 0x0040

        x = destino["left"] + (
            (destino["right"] - destino["left"]) - largura
        ) // 2

        y = destino["top"] + (
            (destino["bottom"] - destino["top"]) - altura
        ) // 2

        for _ in range(self.TENTATIVAS_MOVER):

            user32.SetWindowPos(
                hwnd,
                0,
                x,
                y,
                largura,
                altura,
                SWP_NOZORDER | SWP_SHOWWINDOW
            )

            if self._aguardar(
                lambda: self._janela_dentro_do_monitor(
                    hwnd,
                    destino
                ),
                self.ESPERA_MOVER_S
            ):

                return True

        return False

    def mover_janela_monitor(self, hwnd, numero_monitor):

        monitores = self.obter_monitores()

        if numero_monitor < 1:

            return "O número do monitor deve ser 1 ou maior."

        if numero_monitor > len(monitores):

            return (
                f"Não existe o monitor {numero_monitor}. "
                f"Foram detectados {len(monitores)} monitor(es)."
            )

        destino = monitores[numero_monitor - 1]

        # Minimizada: o retângulo dela fica em (-32000, -32000) e o
        # tamanho é o do botão na barra de tarefas. Sem restaurar
        # antes, a janela "movia" para lugar nenhum.
        voltar_a_maximizar = self._restaurar_ate_ficar_normal(
            hwnd
        )

        janela = self._retangulo_da_janela(
            hwnd
        )

        # Nunca maior que o monitor de destino (resolução diferente
        # da de origem deixava parte da janela fora da tela).
        largura = min(
            janela.right - janela.left,
            destino["right"] - destino["left"]
        )

        altura = min(
            janela.bottom - janela.top,
            destino["bottom"] - destino["top"]
        )

        if not self._posicionar_no_monitor(
            hwnd,
            destino,
            largura,
            altura
        ):

            return (
                f"Não consegui mover a janela para o monitor "
                f"{numero_monitor}."
            )

        if voltar_a_maximizar:

            SW_MAXIMIZE = 3

            user32.ShowWindow(
                hwnd,
                SW_MAXIMIZE
            )

            self._aguardar(
                lambda: user32.IsZoomed(hwnd),
                self.ESPERA_ESTADO_S
            )

            if not self._janela_dentro_do_monitor(
                hwnd,
                destino
            ):

                return (
                    f"A janela foi para o monitor {numero_monitor}, "
                    f"mas não consegui maximizá-la lá."
                )

        return f"Janela movida para o monitor {numero_monitor}."

    def mover_programa_monitor(self, nome, numero_monitor=None):

        janelas, indice, nome = self._janelas_com_indice(nome)

        if not janelas:

            return (
                f"Não encontrei uma janela aberta "
                f"correspondente a '{nome}'."
            )

        if (
            len(janelas) > 1
            and numero_monitor is None
            and indice is None
        ):

            # Uma única enumeração aqui fora, reaproveitada no
            # loop abaixo — evita repetir EnumDisplayMonitors
            # uma vez por janela.
            monitores_disponiveis = self.obter_monitores()

            lista = []

            for i, janela in enumerate(janelas, start=1):

                monitor = None

                try:

                    monitor = self.numero_monitor_da_janela(
                        janela["hwnd"],
                        monitores_disponiveis
                    )

                except Exception:

                    pass

                lista.append(
                    f"{i}. {janela['titulo']} "
                    f"(monitor {monitor})"
                )

            return (
                "Encontrei várias janelas correspondentes. "
                "Especifique qual deseja mover.\n"
                + "\n".join(lista)
                + "\n\n"
                "Por exemplo: "
                "'mova o Discord 1 para o monitor 2'."
            )

        if numero_monitor is None:

            # Se já sabemos, de uma vez anterior, em qual
            # monitor esse programa costuma ser colocado, usamos
            # essa preferência memorizada em vez de sempre cair
            # no monitor 1 por padrão.
            numero_monitor = (
                self._cache.obter(
                    "monitores",
                    nome.strip().lower()
                )
                or 1
            )

        if indice is not None:

            janela = janelas[indice - 1]

        elif len(janelas) == 1:

            janela = janelas[0]

        else:

            # Várias janelas e o monitor foi dado: sem índice não
            # dá para saber qual — usa a primeira, como antes.
            janela = janelas[0]

        resultado = self.mover_janela_monitor(
            janela["hwnd"],
            int(numero_monitor)
        )

        if resultado.startswith("Janela movida"):

            # Movimento bem-sucedido: memorizamos o monitor
            # usado para esse programa, para usarmos como padrão
            # da próxima vez.
            self._cache.definir(
                "monitores",
                nome.strip().lower(),
                int(numero_monitor)
            )

        return resultado

    def mover_para_outro_monitor(self, nome):

        janelas, indice, nome = self._janelas_com_indice(nome)

        if indice is not None:

            janelas = [janelas[indice - 1]]

        if not janelas:

            return (
                f"Não encontrei uma janela aberta "
                f"correspondente a '{nome}'."
            )

        monitores = self.obter_monitores()

        if len(janelas) > 1:

            lista = []

            for i, janela in enumerate(janelas, start=1):

                try:

                    monitor = self.numero_monitor_da_janela(
                        janela["hwnd"],
                        monitores
                    )

                except Exception:

                    monitor = "desconhecido"

                lista.append(
                    f"{i}. {janela['titulo']} "
                    f"(monitor {monitor})"
                )

            return (
                "Encontrei mais de uma janela. "
                "Qual delas deseja mover?\n"
                + "\n".join(lista)
            )

        hwnd = janelas[0]["hwnd"]

        monitor_atual = self.numero_monitor_da_janela(
            hwnd,
            monitores
        )

        if len(monitores) < 2:

            return "O Windows informou que existe apenas um monitor."

        destino = None

        for numero in range(1, len(monitores) + 1):

            if numero != monitor_atual:

                destino = numero

                break

        if destino is None:

            return "Não consegui determinar um monitor de destino."

        resultado = self.mover_janela_monitor(
            hwnd,
            destino
        )

        if not resultado.startswith("Janela movida"):

            return resultado

        return (
            f"{resultado} "
            f"O aplicativo estava no monitor "
            f"{monitor_atual} e foi colocado no "
            f"monitor {destino}."
        )
