import ctypes
import itertools
import threading
from datetime import datetime, timedelta

from .notificacoes import NotificadorToast


user32 = ctypes.windll.user32

MB_OK = 0x00000000
MB_ICONINFORMATION = 0x00000040
MB_SETFOREGROUND = 0x00010000
MB_TOPMOST = 0x00040000


class GerenciadorLembretes:
    """
    Lembretes com temporizador: agenda um aviso para daqui a X
    segundos/minutos/horas.

    Por que threading.Timer e não o mesmo esquema de 'atraso'
    usado em tirar_print (time.sleep bloqueante)?

    Porque um lembrete de "daqui a 10 minutos" não pode travar
    a thread do TrabalhadorIA por 10 minutos — o usuário
    precisa continuar conversando com a Shaula nesse meio
    tempo. threading.Timer agenda a execução numa thread própria
    e devolve o controle na hora; o lembrete continua contando
    em segundo plano depois que a ferramenta já retornou.

    O aviso em si é entregue pelo NotificadorToast (injeção de
    dependência) — um toast de verdade, que aparece na Central
    de Notificações do Windows. Se o PowerShell usado por trás
    disso falhar por qualquer motivo, cai de volta para
    MessageBoxW — API Win32 pura, sem relação com o laço de
    eventos do Qt (mesmo raciocínio já usado para as chamadas
    GDI em captura_tela.py), então é seguro chamar de qualquer
    thread. Uma versão anterior usava um balão na bandeja do
    sistema (Shell_NotifyIcon), mas essa API se mostrou
    inconsistente nos testes reais — às vezes aparecia, às
    vezes não, sem erro nenhum pra explicar por quê, e nunca
    ficava registrada na Central de Notificações de qualquer
    forma.
    """

    UNIDADES_EM_SEGUNDOS = {
        "segundos": 1,
        "minutos": 60,
        "horas": 3600,
    }

    def __init__(self, notificador=None):

        self._notificador = notificador or NotificadorToast()

        self._lembretes = {}
        self._proximo_id = itertools.count(1)
        self._trava = threading.Lock()

    # --------------------------------------------------------
    # CRIAR
    # --------------------------------------------------------

    def criar_lembrete(self, texto, tempo, unidade="minutos"):

        texto = str(texto).strip()

        if not texto:
            return "Preciso saber o que o lembrete deve dizer."

        unidade = str(unidade or "minutos").strip().lower()

        segundos_por_unidade = self.UNIDADES_EM_SEGUNDOS.get(unidade)

        if segundos_por_unidade is None:
            return (
                "Unidade de tempo inválida. Use segundos, "
                "minutos ou horas."
            )

        try:
            tempo = float(tempo)
        except (TypeError, ValueError):
            return "O tempo precisa ser um número."

        if tempo <= 0:
            return "O tempo precisa ser maior que zero."

        segundos_totais = tempo * segundos_por_unidade

        with self._trava:

            id_lembrete = next(self._proximo_id)

            timer = threading.Timer(
                segundos_totais,
                self._disparar,
                args=(id_lembrete, texto)
            )

            # daemon=True: um lembrete pendente nunca deve
            # impedir o programa de fechar.
            timer.daemon = True

            self._lembretes[id_lembrete] = {
                "texto": texto,
                "disparo_em": datetime.now() + timedelta(seconds=segundos_totais),
                "timer": timer,
            }

            timer.start()

        return (
            f"Lembrete #{id_lembrete} criado: vou avisar sobre "
            f"'{texto}' {self._formatar_tempo(tempo, unidade)}."
        )

    def _formatar_tempo(self, tempo, unidade):

        tempo_texto = (
            str(int(tempo))
            if tempo == int(tempo)
            else str(tempo)
        )

        return f"em {tempo_texto} {unidade}"

    # --------------------------------------------------------
    # DISPARO
    # --------------------------------------------------------

    def _disparar(self, id_lembrete, texto):

        with self._trava:
            self._lembretes.pop(id_lembrete, None)

        sucesso = self._notificador.notificar("Shaula — Lembrete", texto)

        if not sucesso:

            user32.MessageBoxW(
                0,
                texto,
                "Shaula — Lembrete",
                MB_OK | MB_ICONINFORMATION | MB_SETFOREGROUND | MB_TOPMOST
            )

    # --------------------------------------------------------
    # LISTAR / CANCELAR
    # --------------------------------------------------------

    def listar_lembretes(self):

        with self._trava:
            lembretes = list(self._lembretes.items())

        if not lembretes:
            return "Não há nenhum lembrete programado."

        agora = datetime.now()

        linhas = ["Lembretes programados:"]

        for id_lembrete, dados in sorted(lembretes):

            restante = (dados["disparo_em"] - agora).total_seconds()
            restante = max(0, int(restante))

            minutos_restantes, segundos_restantes = divmod(restante, 60)

            linhas.append(
                f"#{id_lembrete}: '{dados['texto']}' "
                f"— dispara em {minutos_restantes}min {segundos_restantes}s"
            )

        return "\n".join(linhas)

    def cancelar_lembrete(self, id_lembrete):

        try:
            id_lembrete = int(id_lembrete)
        except (TypeError, ValueError):
            return "O número do lembrete precisa ser um número inteiro."

        with self._trava:

            dados = self._lembretes.pop(id_lembrete, None)

            if dados is None:
                return f"Não existe nenhum lembrete #{id_lembrete} pendente."

            dados["timer"].cancel()

        return f"Lembrete #{id_lembrete} ('{dados['texto']}') cancelado."
