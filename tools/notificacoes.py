import os
import subprocess
import tempfile
import threading
import traceback
from datetime import datetime


class NotificadorToast:
    """
    Mostra notificações que aparecem de verdade na Central de
    Notificações do Windows 10/11 (o painel que abre clicando
    no relógio/data na barra de tarefas) — diferente da caixa
    de mensagem simples (MessageBoxW) e do balão antigo da
    bandeja (Shell_NotifyIcon), nenhum dos dois fica registrado
    ali.

    A API "de verdade" pra isso é o WinRT
    (Windows.UI.Notifications), que não é Win32 clássico — não
    dá pra chamar com uma simples ctypes.windll.alguma_coisa()
    como o resto do projeto faz. Em vez de implementar a
    ativação COM/WinRT manualmente em ctypes (superfície de bug
    grande, e sem Windows aqui pra testar cada detalhe), quem
    faz esse trabalho é um script PowerShell pequeno, chamado
    via subprocess — o PowerShell já sabe conversar com WinRT
    nativamente, então o script em si fica simples e pequeno.

    EXIGE UM AUMID (AppUserModelID): um app Win32 "cru" (tipo
    um python.exe rodando um script) não tem um por padrão, e
    o Windows recusa mostrar o toast sem isso. Usamos o AUMID
    do próprio PowerShell do Windows, que já vem registrado em
    qualquer instalação — por isso a notificação aparece com
    "Windows PowerShell" como remetente, não "Shaula". Dá pra
    personalizar isso registrando um AUMID próprio, mas é bem
    mais trabalho (envolve criar um atalho no Menu Iniciar com
    esse AUMID) — deixado de fora por ora.

    Se o PowerShell falhar por qualquer motivo (política de
    execução bloqueada, versão do Windows sem suporte, etc.),
    notificar() devolve False e quem chamou pode cair para
    outro tipo de aviso — é isso que GerenciadorLembretes faz,
    caindo de volta pro MessageBoxW.
    """

    AUMID_POWERSHELL = (
        r"{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}"
        r"\WindowsPowerShell\v1.0\powershell.exe"
    )

    TIMEOUT_SEGUNDOS = 10

    # Texto/título chegam como parâmetros nomeados do script
    # (-Titulo/-Texto), nunca interpolados diretamente na
    # string do script — evita qualquer problema de
    # injeção/quebra de sintaxe por causa do conteúdo do
    # lembrete. Dentro do script, ainda escapamos pra XML por
    # segurança extra (Escape trata <, >, &, aspas).
    _SCRIPT_PS1 = (
        "param(\n"
        "    [string]$Titulo,\n"
        "    [string]$Texto,\n"
        "    [string]$AppId\n"
        ")\n"
        "\n"
        "$ErrorActionPreference = \"Stop\"\n"
        "\n"
        "[Windows.UI.Notifications.ToastNotificationManager, "
        "Windows.UI.Notifications, ContentType = WindowsRuntime] "
        "| Out-Null\n"
        "[Windows.Data.Xml.Dom.XmlDocument, "
        "Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] "
        "| Out-Null\n"
        "\n"
        "$TituloEscapado = [System.Security.SecurityElement]::Escape($Titulo)\n"
        "$TextoEscapado = [System.Security.SecurityElement]::Escape($Texto)\n"
        "\n"
        "$TemplateXml = @\"\n"
        "<toast>\n"
        "  <visual>\n"
        "    <binding template=\"ToastGeneric\">\n"
        "      <text>$TituloEscapado</text>\n"
        "      <text>$TextoEscapado</text>\n"
        "    </binding>\n"
        "  </visual>\n"
        "</toast>\n"
        "\"@\n"
        "\n"
        "$XmlDoc = New-Object Windows.Data.Xml.Dom.XmlDocument\n"
        "$XmlDoc.LoadXml($TemplateXml)\n"
        "\n"
        "$Toast = New-Object Windows.UI.Notifications.ToastNotification $XmlDoc\n"
        "\n"
        "[Windows.UI.Notifications.ToastNotificationManager]::"
        "CreateToastNotifier($AppId).Show($Toast)\n"
    )

    def __init__(self):

        self._trava = threading.Lock()
        self._caminho_script = None

    def notificar(self, titulo, texto):
        """Mostra o toast. Devolve True em caso de sucesso, False se algo falhou."""

        try:

            with self._trava:
                caminho_script = self._obter_script()

            resultado = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy", "Bypass",
                    "-File", caminho_script,
                    "-Titulo", str(titulo),
                    "-Texto", str(texto),
                    "-AppId", self.AUMID_POWERSHELL,
                ],
                capture_output=True,
                text=True,
                timeout=self.TIMEOUT_SEGUNDOS,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

            if resultado.returncode != 0:

                self._registrar_log(
                    "notificar(): PowerShell retornou código "
                    f"{resultado.returncode}.\n"
                    f"stdout: {resultado.stdout}\n"
                    f"stderr: {resultado.stderr}"
                )

                return False

            self._registrar_log("notificar(): toast exibido com sucesso.")

            return True

        except Exception:

            self._registrar_log(
                "notificar(): exceção capturada:\n" + traceback.format_exc()
            )

            return False

    def _obter_script(self):
        """Escreve o script .ps1 em disco uma vez só e reaproveita nas chamadas seguintes."""

        if self._caminho_script and os.path.exists(self._caminho_script):
            return self._caminho_script

        pasta = os.path.join(tempfile.gettempdir(), "shaula")
        os.makedirs(pasta, exist_ok=True)

        caminho = os.path.join(pasta, "toast.ps1")

        # utf-8-sig (com BOM): o Windows PowerShell 5.1 (não o
        # PowerShell 7+) só interpreta corretamente um .ps1 com
        # caracteres não-ASCII se o arquivo tiver um BOM UTF-8.
        # O corpo do script aqui é todo ASCII, mas escrever com
        # BOM já deixa isso à prova de futuro sem custo nenhum.
        with open(caminho, "w", encoding="utf-8-sig") as arquivo:
            arquivo.write(self._SCRIPT_PS1)

        self._caminho_script = caminho

        return caminho

    # --------------------------------------------------------
    # DIAGNÓSTICO
    # --------------------------------------------------------

    def _registrar_log(self, mensagem):

        try:

            pasta_log = os.path.join(os.path.expanduser("~"), ".shaula")
            os.makedirs(pasta_log, exist_ok=True)

            caminho_log = os.path.join(pasta_log, "notificacoes.log")

            carimbo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with open(caminho_log, "a", encoding="utf-8") as arquivo:
                arquivo.write(f"[{carimbo}] {mensagem}\n")

        except Exception:

            pass
