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

    def _resolver_janela(self, nome):
        """
        Encontra a janela certa a partir de um nome digitado
        pelo usuário. Se houver várias janelas com títulos
        parecidos, aceita o mesmo truque de "nome N" (ex.:
        'chrome 2') já usado em mover_programa_monitor para
        desambiguar. Devolve (janela, None) em caso de sucesso,
        ou (None, mensagem) se não achou nada ou ficou ambíguo.
        """

        janelas = self.encontrar_janelas_por_nome(nome)

        if not janelas:

            return None, (
                f"Não encontrei uma janela aberta "
                f"correspondente a '{nome}'."
            )

        if len(janelas) == 1:

            return janelas[0], None

        partes = nome.rsplit(" ", 1)

        if len(partes) == 2:

            try:

                indice = int(partes[1])

                if 1 <= indice <= len(janelas):

                    return janelas[indice - 1], None

            except ValueError:

                pass

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

        janela = RECT()

        user32.GetWindowRect(
            hwnd,
            ctypes.byref(janela)
        )

        largura = janela.right - janela.left
        altura = janela.bottom - janela.top

        SW_RESTORE = 9

        estava_maximizada = bool(
            user32.IsZoomed(hwnd)
        )

        if estava_maximizada:

            user32.ShowWindow(
                hwnd,
                SW_RESTORE
            )

            time.sleep(0.15)

            user32.GetWindowRect(
                hwnd,
                ctypes.byref(janela)
            )

            largura = janela.right - janela.left
            altura = janela.bottom - janela.top

        monitor_largura = destino["right"] - destino["left"]
        monitor_altura = destino["bottom"] - destino["top"]

        x = destino["left"] + (monitor_largura - largura) // 2
        y = destino["top"] + (monitor_altura - altura) // 2

        SWP_NOZORDER = 0x0004
        SWP_SHOWWINDOW = 0x0040

        user32.SetWindowPos(
            hwnd,
            0,
            x,
            y,
            largura,
            altura,
            SWP_NOZORDER | SWP_SHOWWINDOW
        )

        if estava_maximizada:

            # Esta pausa só é necessária aqui: o Windows precisa
            # "assentar" a nova posição da janela antes de
            # maximizá-la de novo, senão ela pode maximizar no
            # monitor errado. Ao contrário do resto do método,
            # não há como evitar essa espera quando a janela
            # estava maximizada.
            time.sleep(0.15)

            SW_MAXIMIZE = 3

            user32.ShowWindow(
                hwnd,
                SW_MAXIMIZE
            )

        return f"Janela movida para o monitor {numero_monitor}."

    def mover_programa_monitor(self, nome, numero_monitor=None):

        janelas = self.encontrar_janelas_por_nome(nome)

        if not janelas:

            return (
                f"Não encontrei uma janela aberta "
                f"correspondente a '{nome}'."
            )

        if (
            len(janelas) > 1
            and numero_monitor is None
        ):

            # Uma única enumeração aqui fora, reaproveitada no
            # loop abaixo — evita repetir EnumDisplayMonitors
            # uma vez por janela.
            monitores_disponiveis = self.obter_monitores()

            lista = []

            for i, janela in enumerate(janelas, start=1):

                monitor = None

                try:

                    monitor_handle = user32.MonitorFromWindow(
                        janela["hwnd"],
                        2
                    )

                    monitor = self._numero_monitor_em_lista(
                        monitores_disponiveis,
                        monitor_handle
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

        if len(janelas) == 1:

            janela = janelas[0]

        else:

            janela = janelas[0]

            partes = nome.rsplit(" ", 1)

            if len(partes) == 2:

                try:

                    indice = int(partes[1])

                    if 1 <= indice <= len(janelas):

                        janela = janelas[indice - 1]

                except ValueError:

                    pass

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

        janelas = self.encontrar_janelas_por_nome(nome)

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

                    monitor_handle = user32.MonitorFromWindow(
                        janela["hwnd"],
                        2
                    )

                    monitor = self._numero_monitor_em_lista(
                        monitores,
                        monitor_handle
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

        monitor_atual_handle = user32.MonitorFromWindow(
            hwnd,
            2
        )

        monitor_atual = self._numero_monitor_em_lista(
            monitores,
            monitor_atual_handle
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

        return (
            f"{resultado} "
            f"O aplicativo estava no monitor "
            f"{monitor_atual} e foi colocado no "
            f"monitor {destino}."
        )
