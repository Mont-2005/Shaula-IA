import ctypes
import ctypes.wintypes as wintypes
import os
import time
from contextlib import contextmanager


class ApiJanelasWin32:
    """
    As poucas chamadas do Windows necessárias para esconder e
    mostrar as janelas desta própria aplicação.

    Usa uma instância PRÓPRIA da user32 (WinDLL, e não o
    ctypes.windll.user32 compartilhado) com `argtypes`/`restype`
    declarados: sem isso, handles de janela são passados como
    inteiros de 32 bits e podem ser truncados ou mal interpretados
    (a mesma classe de bug que já apareceu no LoadIconW).

    Só existe no Windows. A criação é adiada até o primeiro uso.
    """

    SW_MINIMIZE = 6

    SW_RESTORE = 9

    GW_OWNER = 4

    def __init__(self):

        user32 = ctypes.WinDLL("user32", use_last_error=True)

        self._tipo_callback = ctypes.WINFUNCTYPE(
            wintypes.BOOL,
            wintypes.HWND,
            wintypes.LPARAM
        )

        user32.EnumWindows.argtypes = [
            self._tipo_callback,
            wintypes.LPARAM
        ]
        user32.EnumWindows.restype = wintypes.BOOL

        user32.IsWindowVisible.argtypes = [wintypes.HWND]
        user32.IsWindowVisible.restype = wintypes.BOOL

        user32.IsIconic.argtypes = [wintypes.HWND]
        user32.IsIconic.restype = wintypes.BOOL

        user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
        user32.GetWindow.restype = wintypes.HWND

        user32.GetWindowThreadProcessId.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(wintypes.DWORD)
        ]
        user32.GetWindowThreadProcessId.restype = wintypes.DWORD

        user32.GetWindowRect.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(wintypes.RECT)
        ]
        user32.GetWindowRect.restype = wintypes.BOOL

        user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.ShowWindow.restype = wintypes.BOOL

        self._user32 = user32

    def janelas_visiveis_do_processo(self, pid):
        """Handles das janelas de topo visíveis e não minimizadas."""

        encontradas = []

        def callback(hwnd, _lparam):

            if (
                self._user32.IsWindowVisible(hwnd)
                and not self._user32.IsIconic(hwnd)
                and not self._user32.GetWindow(hwnd, self.GW_OWNER)
            ):

                dono = wintypes.DWORD(0)

                self._user32.GetWindowThreadProcessId(
                    hwnd,
                    ctypes.byref(dono)
                )

                if dono.value == pid:
                    encontradas.append(hwnd)

            return True

        self._user32.EnumWindows(
            self._tipo_callback(callback),
            0
        )

        return encontradas

    def retangulo(self, hwnd):
        """(esquerda, topo, direita, base) da janela."""

        retangulo = wintypes.RECT()

        if not self._user32.GetWindowRect(
            hwnd,
            ctypes.byref(retangulo)
        ):
            return None

        return (
            retangulo.left,
            retangulo.top,
            retangulo.right,
            retangulo.bottom
        )

    def minimizar(self, hwnd):

        self._user32.ShowWindow(hwnd, self.SW_MINIMIZE)

    def restaurar(self, hwnd):

        self._user32.ShowWindow(hwnd, self.SW_RESTORE)


class OcultadorJanelasProprias:
    """
    Minimiza por um instante as janelas da Shaula que cobrem uma
    região da tela e as restaura depois.

    Serve para "perguntar sobre a tela": sem isso, o print mostraria
    a própria conversa da Shaula por cima do que a pessoa quer
    mostrar. Só as janelas que INTERSECTAM a região capturada são
    minimizadas — se a Shaula está num monitor e o print é do outro,
    nada se mexe.

    A restauração acontece num `finally`: mesmo que a captura falhe,
    a janela volta.
    """

    ESPERA_PADRAO_S = 0.4

    def __init__(
        self,
        api=None,
        pid=None,
        espera_s=ESPERA_PADRAO_S,
        dormir=time.sleep
    ):

        self._api = api

        self._pid = os.getpid() if pid is None else pid

        self._espera_s = espera_s

        self._dormir = dormir

    @staticmethod
    def intersecta(retangulo_a, retangulo_b):
        """Há área em comum entre dois retângulos (l, t, r, b)?"""

        return (
            retangulo_a[0] < retangulo_b[2]
            and retangulo_a[2] > retangulo_b[0]
            and retangulo_a[1] < retangulo_b[3]
            and retangulo_a[3] > retangulo_b[1]
        )

    def _obter_api(self):

        if self._api is None:

            self._api = ApiJanelasWin32()

        return self._api

    def _janelas_a_ocultar(self, regiao):

        try:

            api = self._obter_api()

            alvo = []

            for hwnd in api.janelas_visiveis_do_processo(self._pid):

                retangulo = api.retangulo(hwnd)

                if (
                    regiao is None
                    or (
                        retangulo is not None
                        and self.intersecta(retangulo, regiao)
                    )
                ):
                    alvo.append(hwnd)

            return alvo

        except Exception:

            # Fora do Windows (ou se a API falhar), segue sem
            # esconder nada: a captura ainda funciona.
            return []

    @contextmanager
    def ocultar(self, regiao=None):
        """
        `with ocultador.ocultar(regiao) as quantas:` — dentro do bloco
        as janelas estão minimizadas; `quantas` é quantas foram.
        """

        minimizadas = []

        try:

            for hwnd in self._janelas_a_ocultar(regiao):

                try:

                    self._api.minimizar(hwnd)

                    minimizadas.append(hwnd)

                except Exception:
                    continue

            if minimizadas:

                # A animação de minimizar leva uns 250 ms; sem
                # esperar, o print pegaria a janela "encolhendo".
                self._dormir(self._espera_s)

            yield len(minimizadas)

        finally:

            for hwnd in reversed(minimizadas):

                try:

                    self._api.restaurar(hwnd)

                except Exception:
                    pass
