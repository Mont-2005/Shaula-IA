import ctypes
import ctypes.wintypes


user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002

# Assinaturas explícitas — mesmo motivo já documentado em
# captura_tela.py: sem argtypes/restype corretos, handles de 64
# bits (HGLOBAL, HANDLE) podem ser truncados pelo ctypes, que
# assume "int" de 32 bits por padrão.

user32.OpenClipboard.argtypes = [ctypes.wintypes.HWND]
user32.OpenClipboard.restype = ctypes.wintypes.BOOL

user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = ctypes.wintypes.BOOL

user32.EmptyClipboard.argtypes = []
user32.EmptyClipboard.restype = ctypes.wintypes.BOOL

user32.IsClipboardFormatAvailable.argtypes = [ctypes.wintypes.UINT]
user32.IsClipboardFormatAvailable.restype = ctypes.wintypes.BOOL

user32.GetClipboardData.argtypes = [ctypes.wintypes.UINT]
user32.GetClipboardData.restype = ctypes.wintypes.HANDLE

user32.SetClipboardData.argtypes = [
    ctypes.wintypes.UINT,
    ctypes.wintypes.HANDLE
]
user32.SetClipboardData.restype = ctypes.wintypes.HANDLE

kernel32.GlobalAlloc.argtypes = [ctypes.wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = ctypes.wintypes.HGLOBAL

kernel32.GlobalLock.argtypes = [ctypes.wintypes.HGLOBAL]
kernel32.GlobalLock.restype = ctypes.c_void_p

kernel32.GlobalUnlock.argtypes = [ctypes.wintypes.HGLOBAL]
kernel32.GlobalUnlock.restype = ctypes.wintypes.BOOL

kernel32.GlobalFree.argtypes = [ctypes.wintypes.HGLOBAL]
kernel32.GlobalFree.restype = ctypes.wintypes.HGLOBAL


class GerenciadorClipboard:
    """
    Lê e escreve TEXTO na área de transferência do Windows
    (formato CF_UNICODETEXT).

    Bem mais simples que o clipboard de imagem em
    captura_tela.py: não precisa de GDI, BitBlt, nem coordenadas
    de tela — só o mesmo protocolo de memória compartilhada
    (GlobalAlloc/GlobalLock/SetClipboardData) já testado e
    funcionando lá, com um payload mais simples (uma string, em
    vez de um bitmap inteiro).
    """

    def copiar_texto(self, texto):
        """Coloca um texto na área de transferência do Windows."""

        texto = str(texto) if texto is not None else ""

        if not texto.strip():
            return "Preciso de um texto para copiar."

        buffer = ctypes.create_unicode_buffer(texto)
        tamanho = ctypes.sizeof(buffer)

        h_global = kernel32.GlobalAlloc(GMEM_MOVEABLE, tamanho)

        if not h_global:
            return "Não foi possível alocar memória para a área de transferência."

        ponteiro = kernel32.GlobalLock(h_global)

        if not ponteiro:
            kernel32.GlobalFree(h_global)
            return "Não foi possível preparar a memória da área de transferência."

        ctypes.memmove(ponteiro, buffer, tamanho)
        kernel32.GlobalUnlock(h_global)

        if not user32.OpenClipboard(0):
            kernel32.GlobalFree(h_global)
            return (
                "Não consegui abrir a área de transferência "
                "(outro programa pode estar usando)."
            )

        try:

            user32.EmptyClipboard()

            if not user32.SetClipboardData(CF_UNICODETEXT, h_global):
                kernel32.GlobalFree(h_global)
                return (
                    "O Windows recusou colocar o texto na "
                    "área de transferência."
                )

            # A partir daqui a memória pertence ao Windows —
            # não liberar, mesmo raciocínio já usado no
            # clipboard de imagem em captura_tela.py.

        finally:
            user32.CloseClipboard()

        preview = texto if len(texto) <= 60 else texto[:57] + "..."

        return f'Copiado para a área de transferência: "{preview}"'

    def colar_texto(self):
        """Lê o texto atual da área de transferência do Windows."""

        if not user32.OpenClipboard(0):
            return (
                "Não consegui abrir a área de transferência "
                "(outro programa pode estar usando)."
            )

        try:

            if not user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
                return "Não há texto na área de transferência."

            h_global = user32.GetClipboardData(CF_UNICODETEXT)

            if not h_global:
                return "Não consegui ler o conteúdo da área de transferência."

            ponteiro = kernel32.GlobalLock(h_global)

            if not ponteiro:
                return "Não consegui acessar o conteúdo da área de transferência."

            try:
                texto = ctypes.wstring_at(ponteiro)
            finally:
                kernel32.GlobalUnlock(h_global)

        finally:
            user32.CloseClipboard()

        if not texto:
            return "A área de transferência está vazia."

        return f"Conteúdo da área de transferência:\n{texto}"
