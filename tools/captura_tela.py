import ctypes
import ctypes.wintypes
import os
import time
from datetime import datetime


# ============================================================
# GDI (Windows) — chamadas de baixo nível para captura de tela
# ============================================================
#
# Por que não usar QScreen.grabWindow() do PySide6, já que a
# interface é toda Qt?
#
# Porque a ferramenta roda dentro do TrabalhadorIA (QThread) —
# ver interface.py — e classes gráficas do Qt (QScreen incluso)
# só podem ser chamadas com segurança a partir da thread
# principal. Chamar QScreen de uma QThread secundária é um
# comportamento não suportado pelo Qt e pode travar a
# aplicação.
#
# As chamadas GDI abaixo (BitBlt/GetDIBits) são Win32 puro, sem
# relação nenhuma com o laço de eventos do Qt — podem ser
# chamadas de qualquer thread sem problema. Como bônus, não
# criam nenhuma dependência nova (nada de Pillow/mss): o próprio
# Windows entrega os pixels já prontos para virar um .bmp.

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
ole32 = ctypes.windll.ole32
shell32 = ctypes.windll.shell32
kernel32 = ctypes.windll.kernel32

SRCCOPY = 0x00CC0020
BI_RGB = 0
DIB_RGB_COLORS = 0
CF_DIB = 8
GMEM_MOVEABLE = 0x0002

# Assinaturas explícitas (argtypes/restype) são essenciais aqui:
# sem elas, o ctypes assume que toda função devolve um "int" de
# 32 bits. Em Windows 64 bits, handles (HDC, HBITMAP) podem
# passar de 32 bits — sem as assinaturas corretas, o valor é
# truncado e a captura falha de forma silenciosa e intermitente.

user32.GetDC.argtypes = [ctypes.wintypes.HWND]
user32.GetDC.restype = ctypes.wintypes.HDC

user32.ReleaseDC.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.HDC]
user32.ReleaseDC.restype = ctypes.c_int

gdi32.CreateCompatibleDC.argtypes = [ctypes.wintypes.HDC]
gdi32.CreateCompatibleDC.restype = ctypes.wintypes.HDC

gdi32.CreateCompatibleBitmap.argtypes = [
    ctypes.wintypes.HDC,
    ctypes.c_int,
    ctypes.c_int
]
gdi32.CreateCompatibleBitmap.restype = ctypes.wintypes.HBITMAP

gdi32.SelectObject.argtypes = [
    ctypes.wintypes.HDC,
    ctypes.wintypes.HGDIOBJ
]
gdi32.SelectObject.restype = ctypes.wintypes.HGDIOBJ

gdi32.BitBlt.argtypes = [
    ctypes.wintypes.HDC,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.wintypes.HDC,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.wintypes.DWORD
]
gdi32.BitBlt.restype = ctypes.wintypes.BOOL

gdi32.DeleteObject.argtypes = [ctypes.wintypes.HGDIOBJ]
gdi32.DeleteObject.restype = ctypes.wintypes.BOOL

gdi32.DeleteDC.argtypes = [ctypes.wintypes.HDC]
gdi32.DeleteDC.restype = ctypes.wintypes.BOOL

# --- Área de transferência (clipboard) ---
#
# Fluxo padrão do Windows para colocar uma imagem no clipboard:
# aloca um bloco de memória "movível" (GMEM_MOVEABLE) que o
# próprio sistema operacional vai gerenciar dali pra frente,
# copia os bytes do DIB (BITMAPINFOHEADER + pixels — o mesmo
# conteúdo do .bmp, só sem o cabeçalho de arquivo de 14 bytes)
# pra dentro desse bloco, e entrega o bloco pro clipboard via
# SetClipboardData. A partir do momento em que SetClipboardData
# funciona, a memória passa a ser responsabilidade do Windows —
# não devemos mais liberá-la manualmente.

kernel32.GlobalAlloc.argtypes = [ctypes.wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = ctypes.wintypes.HGLOBAL

kernel32.GlobalLock.argtypes = [ctypes.wintypes.HGLOBAL]
kernel32.GlobalLock.restype = ctypes.c_void_p

kernel32.GlobalUnlock.argtypes = [ctypes.wintypes.HGLOBAL]
kernel32.GlobalUnlock.restype = ctypes.wintypes.BOOL

kernel32.GlobalFree.argtypes = [ctypes.wintypes.HGLOBAL]
kernel32.GlobalFree.restype = ctypes.wintypes.HGLOBAL

user32.OpenClipboard.argtypes = [ctypes.wintypes.HWND]
user32.OpenClipboard.restype = ctypes.wintypes.BOOL

user32.EmptyClipboard.argtypes = []
user32.EmptyClipboard.restype = ctypes.wintypes.BOOL

user32.SetClipboardData.argtypes = [
    ctypes.wintypes.UINT,
    ctypes.wintypes.HANDLE
]
user32.SetClipboardData.restype = ctypes.wintypes.HANDLE

user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = ctypes.wintypes.BOOL


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", ctypes.wintypes.DWORD),
        ("biWidth", ctypes.wintypes.LONG),
        ("biHeight", ctypes.wintypes.LONG),
        ("biPlanes", ctypes.wintypes.WORD),
        ("biBitCount", ctypes.wintypes.WORD),
        ("biCompression", ctypes.wintypes.DWORD),
        ("biSizeImage", ctypes.wintypes.DWORD),
        ("biXPelsPerMeter", ctypes.wintypes.LONG),
        ("biYPelsPerMeter", ctypes.wintypes.LONG),
        ("biClrUsed", ctypes.wintypes.DWORD),
        ("biClrImportant", ctypes.wintypes.DWORD),
    ]


gdi32.GetDIBits.argtypes = [
    ctypes.wintypes.HDC,
    ctypes.wintypes.HBITMAP,
    ctypes.wintypes.UINT,
    ctypes.wintypes.UINT,
    ctypes.c_void_p,
    ctypes.POINTER(BITMAPINFOHEADER),
    ctypes.wintypes.UINT
]
gdi32.GetDIBits.restype = ctypes.c_int


# ============================================================
# Localização real da pasta "Imagens" do Windows
# ============================================================
#
# Por que não usar os.path.expanduser("~") + "Pictures"?
#
# Porque isso monta o caminho "chutando" que a pasta Imagens
# mora dentro do perfil do usuário (sempre em C:). Se o usuário
# moveu a pasta Imagens para outro disco (D:, por exemplo) —
# coisa que o próprio Windows permite pelas propriedades da
# pasta — esse chute erra, e o programa acaba criando uma pasta
# "Imagens" nova e errada dentro de C:\Users\<usuário> em vez de
# usar a pasta real.
#
# A forma correta de descobrir o caminho verdadeiro (com
# qualquer redirecionamento já aplicado) é perguntar para o
# próprio Windows através da API SHGetKnownFolderPath, usando o
# identificador conhecido FOLDERID_Pictures.

class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.wintypes.DWORD),
        ("Data2", ctypes.wintypes.WORD),
        ("Data3", ctypes.wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


ole32.CLSIDFromString.argtypes = [
    ctypes.c_wchar_p,
    ctypes.POINTER(GUID)
]
ole32.CLSIDFromString.restype = ctypes.c_long

shell32.SHGetKnownFolderPath.argtypes = [
    ctypes.POINTER(GUID),
    ctypes.wintypes.DWORD,
    ctypes.wintypes.HANDLE,
    ctypes.POINTER(ctypes.c_wchar_p)
]
shell32.SHGetKnownFolderPath.restype = ctypes.c_long

ole32.CoTaskMemFree.argtypes = [ctypes.c_wchar_p]
ole32.CoTaskMemFree.restype = None

# GUID oficial da pasta "Imagens" (FOLDERID_Pictures), definido
# pela própria Microsoft — é sempre o mesmo em qualquer Windows.
_FOLDERID_PICTURES = "{33E28130-4E1E-4676-835A-98395C3BC3BB}"


def obter_pasta_imagens_windows():
    """
    Devolve o caminho real da pasta "Imagens" do Windows,
    respeitando qualquer redirecionamento feito pelo usuário
    (inclusive para outro disco que não o C:). Levanta
    RuntimeError se, por algum motivo, o Windows não conseguir
    informar o caminho.
    """

    guid = GUID()

    resultado = ole32.CLSIDFromString(
        _FOLDERID_PICTURES, ctypes.byref(guid)
    )

    if resultado != 0:
        raise RuntimeError(
            "Não foi possível interpretar o identificador da pasta Imagens."
        )

    caminho_ptr = ctypes.c_wchar_p()

    resultado = shell32.SHGetKnownFolderPath(
        ctypes.byref(guid), 0, None, ctypes.byref(caminho_ptr)
    )

    if resultado != 0 or not caminho_ptr.value:
        raise RuntimeError(
            "Não foi possível localizar a pasta Imagens do Windows."
        )

    caminho = caminho_ptr.value

    # A memória do caminho devolvido é alocada pelo Windows e
    # precisa ser liberada manualmente por nós — o Python não
    # sabe que ela existe.
    ole32.CoTaskMemFree(caminho_ptr)

    return caminho


class CapturadorTela:
    """
    Captura de screenshots (prints) de um monitor específico ou
    de todos ao mesmo tempo, instantânea ou com atraso.

    Depende do GerenciadorJanelas (injeção de dependência) só
    para saber a geometria dos monitores — a mesma lista que
    listar_monitores()/mover_programa_monitor() já usam. Não
    duplica a enumeração de monitores, que já vive em
    janelas.py.

    Os arquivos são salvos em .bmp (formato nativo do Windows,
    sem precisar de nenhuma biblioteca de imagem extra) dentro
    de uma pasta própria da Shaula, criada dentro da pasta
    Imagens real do Windows — onde quer que ela esteja (inclusive
    se tiver sido movida para outro disco que não o C:).
    """

    def __init__(self, gerenciador_janelas, pasta_destino=None):

        self._janelas = gerenciador_janelas

        if pasta_destino:
            self._pasta_destino = pasta_destino
        else:
            try:
                pasta_imagens = obter_pasta_imagens_windows()
            except RuntimeError:
                # Se por algum motivo o Windows não responder,
                # cair para o caminho padrão como último recurso
                # em vez de travar a ferramenta inteira.
                pasta_imagens = os.path.join(
                    os.path.expanduser("~"), "Pictures"
                )

            self._pasta_destino = os.path.join(pasta_imagens, "Shaula")

    # --------------------------------------------------------
    # CAPTURA BRUTA (GDI)
    # --------------------------------------------------------

    def _capturar_pixels(self, left, top, right, bottom):
        """
        Captura a região [left, top, right, bottom) do desktop
        virtual (coordenadas absolutas, iguais às que
        obter_monitores() devolve) e retorna o cabeçalho
        BITMAPINFOHEADER junto com os bytes crus dos pixels —
        ou seja, o mesmo conteúdo que tanto o .bmp em disco
        quanto o clipboard precisam, só que ainda sem decidir
        pra onde vai. Captura uma vez só, mesmo que o destino
        final seja arquivo + clipboard ao mesmo tempo.
        """

        largura = right - left
        altura = bottom - top

        if largura <= 0 or altura <= 0:
            raise ValueError("Região de captura inválida.")

        hdc_tela = user32.GetDC(0)

        if not hdc_tela:
            raise RuntimeError(
                "Não foi possível obter o contexto de tela do Windows."
            )

        hdc_memoria = gdi32.CreateCompatibleDC(hdc_tela)
        bitmap = gdi32.CreateCompatibleBitmap(hdc_tela, largura, altura)
        objeto_anterior = gdi32.SelectObject(hdc_memoria, bitmap)

        try:

            gdi32.BitBlt(
                hdc_memoria,
                0,
                0,
                largura,
                altura,
                hdc_tela,
                left,
                top,
                SRCCOPY
            )

            cabecalho = BITMAPINFOHEADER()
            cabecalho.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            cabecalho.biWidth = largura
            # biHeight positivo = ordem "bottom-up", que é
            # exatamente como o .bmp precisa dos pixels em
            # disco — evita ter que inverter linhas depois.
            cabecalho.biHeight = altura
            cabecalho.biPlanes = 1
            cabecalho.biBitCount = 32
            cabecalho.biCompression = BI_RGB

            buffer_pixels = ctypes.create_string_buffer(
                largura * altura * 4
            )

            linhas_copiadas = gdi32.GetDIBits(
                hdc_memoria,
                bitmap,
                0,
                altura,
                buffer_pixels,
                ctypes.byref(cabecalho),
                DIB_RGB_COLORS
            )

            if linhas_copiadas == 0:
                raise RuntimeError(
                    "O Windows não devolveu os pixels da captura."
                )

            return cabecalho, buffer_pixels.raw

        finally:

            gdi32.SelectObject(hdc_memoria, objeto_anterior)
            gdi32.DeleteObject(bitmap)
            gdi32.DeleteDC(hdc_memoria)
            user32.ReleaseDC(0, hdc_tela)

    def _montar_bmp(self, cabecalho_info, pixels):
        """Monta os bytes de um arquivo .bmp a partir do cabeçalho e dos pixels já capturados."""

        tamanho_cabecalho_arquivo = 14
        tamanho_cabecalho_info = ctypes.sizeof(BITMAPINFOHEADER)
        offset_pixels = tamanho_cabecalho_arquivo + tamanho_cabecalho_info
        tamanho_total = offset_pixels + len(pixels)

        cabecalho_arquivo = (
            b"BM"
            + tamanho_total.to_bytes(4, "little")
            + (0).to_bytes(2, "little")
            + (0).to_bytes(2, "little")
            + offset_pixels.to_bytes(4, "little")
        )

        return cabecalho_arquivo + bytes(cabecalho_info) + pixels

    # --------------------------------------------------------
    # SALVAR EM DISCO
    # --------------------------------------------------------

    def _gerar_caminho(self, sufixo):

        os.makedirs(self._pasta_destino, exist_ok=True)

        carimbo = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"print_{sufixo}_{carimbo}.bmp"

        return os.path.join(self._pasta_destino, nome_arquivo)

    def _salvar_bmp(self, cabecalho, pixels, sufixo):

        dados_bmp = self._montar_bmp(cabecalho, pixels)
        caminho = self._gerar_caminho(sufixo)

        with open(caminho, "wb") as arquivo:
            arquivo.write(dados_bmp)

        return caminho

    # --------------------------------------------------------
    # ÁREA DE TRANSFERÊNCIA (CLIPBOARD)
    # --------------------------------------------------------

    def _copiar_para_clipboard(self, cabecalho, pixels):
        """
        Coloca a captura na área de transferência do Windows,
        no formato CF_DIB — o mesmo formato que o Paint, o Word
        e qualquer outro programa esperam ao colar uma imagem
        (Ctrl+V). Levanta RuntimeError com uma mensagem amigável
        se qualquer etapa falhar.
        """

        dados_dib = bytes(cabecalho) + pixels
        tamanho = len(dados_dib)

        h_global = kernel32.GlobalAlloc(GMEM_MOVEABLE, tamanho)

        if not h_global:
            raise RuntimeError(
                "não foi possível alocar memória para a área de transferência"
            )

        ponteiro = kernel32.GlobalLock(h_global)

        if not ponteiro:
            kernel32.GlobalFree(h_global)
            raise RuntimeError(
                "não foi possível preparar a memória da área de transferência"
            )

        ctypes.memmove(ponteiro, dados_dib, tamanho)
        kernel32.GlobalUnlock(h_global)

        if not user32.OpenClipboard(0):
            kernel32.GlobalFree(h_global)
            raise RuntimeError(
                "não consegui abrir a área de transferência "
                "(outro programa pode estar usando)"
            )

        try:

            user32.EmptyClipboard()

            if not user32.SetClipboardData(CF_DIB, h_global):
                kernel32.GlobalFree(h_global)
                raise RuntimeError(
                    "o Windows recusou colocar a imagem na área de transferência"
                )

            # A partir daqui o bloco de memória passou a ser
            # responsabilidade do Windows — se déssemos
            # GlobalFree agora, invalidaríamos os dados que
            # acabamos de entregar pro clipboard.

        finally:
            user32.CloseClipboard()

    # --------------------------------------------------------
    # API PÚBLICA (usada pela Ferramenta)
    # --------------------------------------------------------

    DESTINOS_VALIDOS = {"arquivo", "area_transferencia", "ambos"}

    def tirar_print(self, monitor=None, todos=False, atraso=0, destino=None):
        """
        Tira um print instantâneo (atraso=0) ou com contagem
        regressiva (atraso em segundos), de um monitor
        específico, de todos ao mesmo tempo, ou — se nada for
        especificado — do monitor principal. 'destino' controla
        se o resultado vai para um arquivo, para a área de
        transferência, ou para os dois ('arquivo' é o padrão).
        Devolve uma mensagem de texto pronta para o usuário.
        """

        try:
            atraso = float(atraso or 0)
        except (TypeError, ValueError):
            return "O tempo de espera precisa ser um número, em segundos."

        if atraso < 0:
            return "O tempo de espera não pode ser negativo."

        destino = (destino or "arquivo").strip().lower()

        if destino not in self.DESTINOS_VALIDOS:
            return (
                "Destino inválido para o print. Use 'arquivo', "
                "'area_transferencia' ou 'ambos'."
            )

        if atraso > 0:
            time.sleep(atraso)

        monitores = self._janelas.obter_monitores()

        if not monitores:
            return "Não consegui detectar nenhum monitor."

        if todos:
            return self._tirar_print_todos(monitores, destino)

        if monitor is not None:

            try:
                numero_monitor = int(monitor)
            except (TypeError, ValueError):
                return "O número do monitor precisa ser um número inteiro."

            return self._tirar_print_monitor(monitores, numero_monitor, destino)

        # Nenhum monitor especificado e "todos" não foi pedido:
        # captura o monitor principal, o padrão mais previsível.
        numero_principal = next(
            (
                numero
                for numero, m in enumerate(monitores, start=1)
                if m["primary"]
            ),
            1
        )

        return self._tirar_print_monitor(monitores, numero_principal, destino)

    def _tirar_print_monitor(self, monitores, numero_monitor, destino):

        if numero_monitor < 1 or numero_monitor > len(monitores):
            return (
                f"Não existe o monitor {numero_monitor}. "
                f"Foram detectados {len(monitores)} monitor(es)."
            )

        alvo = monitores[numero_monitor - 1]

        try:
            cabecalho, pixels = self._capturar_pixels(
                alvo["left"],
                alvo["top"],
                alvo["right"],
                alvo["bottom"]
            )
        except Exception as erro:
            return f"Não consegui tirar o print: {erro}"

        resultados = []

        if destino in ("arquivo", "ambos"):

            try:
                caminho = self._salvar_bmp(
                    cabecalho, pixels, f"monitor{numero_monitor}"
                )
                resultados.append(f"salvo em: {caminho}")
            except Exception as erro:
                resultados.append(f"não consegui salvar o arquivo ({erro})")

        if destino in ("area_transferencia", "ambos"):

            try:
                self._copiar_para_clipboard(cabecalho, pixels)
                resultados.append("copiado para a área de transferência")
            except Exception as erro:
                resultados.append(str(erro))

        return f"Print do monitor {numero_monitor}: " + "; ".join(resultados)

    def _tirar_print_todos(self, monitores, destino):

        aviso_clipboard = ""

        if destino in ("area_transferencia", "ambos"):
            aviso_clipboard = (
                " (a área de transferência só guarda uma imagem por "
                "vez, então não foi usada aqui — todos os monitores "
                "foram salvos em arquivo)"
            )

        linhas = []

        for numero, monitor in enumerate(monitores, start=1):

            try:
                cabecalho, pixels = self._capturar_pixels(
                    monitor["left"],
                    monitor["top"],
                    monitor["right"],
                    monitor["bottom"]
                )
                caminho = self._salvar_bmp(cabecalho, pixels, f"monitor{numero}")
                linhas.append(f"Monitor {numero}: {caminho}")
            except Exception as erro:
                linhas.append(f"Monitor {numero}: falhou ({erro})")

        return (
            f"{len(monitores)} print(s) tirado(s){aviso_clipboard}:\n"
            + "\n".join(linhas)
        )