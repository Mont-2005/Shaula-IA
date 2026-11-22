import ctypes
import math
import os
import threading
from datetime import datetime, timedelta

from .armazenamento import ArmazenamentoJson
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

    PERSISTÊNCIA. Os lembretes pendentes ficam gravados em
    ~/.shaula/lembretes.json (via ArmazenamentoJson). O ARQUIVO é a
    fonte da verdade; os Timers são só "despertadores":

    - ao abrir a Shaula, os lembretes que ainda vão acontecer são
      reagendados, e os que venceram enquanto ela estava fechada
      são entregues uma vez, marcados como atrasados;
    - listar e cancelar leem e alteram o arquivo, então valem para
      todas as janelas (cada janela tem seu próprio gerenciador);
    - na hora de disparar, o lembrete é removido do arquivo ANTES de
      ser entregue, dentro de uma trava: se duas janelas tiverem um
      Timer para o mesmo lembrete, só a primeira entrega, e um
      lembrete cancelado em outra janela não dispara.

    Se a Shaula estiver fechada na hora marcada, nada é avisado
    naquele momento: o aviso (atrasado) aparece quando ela abrir.
    """

    UNIDADES_EM_SEGUNDOS = {
        "segundos": 1,
        "minutos": 60,
        "horas": 3600,
    }

    # Teto de um ano. Sem limite, valores absurdos (ou "inf" e
    # "nan", que float() aceita) quebravam timedelta/Timer com
    # OverflowError ou passavam pela checagem "tempo <= 0".
    LIMITE_SEGUNDOS = 365 * 24 * 3600

    # Entrega dos lembretes atrasados ao abrir: escalonada e depois
    # de a interface subir, para não competir com a abertura da
    # janela nem empilhar várias notificações no mesmo instante.
    ATRASO_INICIAL_ENTREGA_S = 2.0

    INTERVALO_ENTRE_ATRASADOS_S = 1.5

    # Um despertador pode disparar com pequena folga em relação ao
    # horário gravado; acima disso, o lembrete ainda não venceu.
    TOLERANCIA_ANTECIPACAO_S = 2.0

    def __init__(
        self,
        notificador=None,
        armazenamento=None,
        relogio=None,
        restaurar=True
    ):

        self._notificador = notificador or NotificadorToast()

        self._armazenamento = armazenamento or ArmazenamentoJson(
            os.path.join(
                os.path.expanduser("~"),
                ".shaula",
                "lembretes.json"
            )
        )

        self._agora = relogio or datetime.now

        # Despertadores desta instância: id -> threading.Timer.
        self._timers = {}

        self._trava = threading.Lock()

        if restaurar:
            self.restaurar()

    # --------------------------------------------------------
    # ARQUIVO (fonte da verdade)
    # --------------------------------------------------------

    def _ler_lembretes(self):
        """Lista de lembretes válidos gravados, ordenada por id."""

        dados = self._armazenamento.ler(padrao=[])

        if not isinstance(dados, list):
            return []

        validos = []

        for entrada in dados:

            try:

                validos.append({
                    "id": int(entrada["id"]),
                    "texto": str(entrada["texto"]),
                    "disparo_em": datetime.fromisoformat(
                        entrada["disparo_em"]
                    ),
                })

            except (KeyError, TypeError, ValueError):
                continue

        return sorted(validos, key=lambda item: item["id"])

    def _gravar_lembretes(self, lembretes):

        return self._armazenamento.gravar([
            {
                "id": item["id"],
                "texto": item["texto"],
                # Sem timespec: guardar só os segundos truncava o
                # horário para baixo e um lembrete de poucos
                # segundos já nascia "atrasado" ao ser restaurado.
                "disparo_em": item["disparo_em"].isoformat(),
            }
            for item in lembretes
        ])

    # --------------------------------------------------------
    # RESTAURAR (ao abrir)
    # --------------------------------------------------------

    def restaurar(self):
        """
        Reagenda os lembretes gravados. Os que ainda vão acontecer
        voltam a contar; os que venceram com a Shaula fechada são
        entregues uma vez (atrasados) e removidos.
        """

        agora = self._agora()

        atrasados = 0

        for item in self._ler_lembretes():

            restante = (item["disparo_em"] - agora).total_seconds()

            if restante > 0:

                self._agendar(item["id"], restante)

                continue

            self._agendar(
                item["id"],
                self.ATRASO_INICIAL_ENTREGA_S
                + atrasados * self.INTERVALO_ENTRE_ATRASADOS_S,
                atrasado=True
            )

            atrasados += 1

    # --------------------------------------------------------
    # DESPERTADORES
    # --------------------------------------------------------

    def _agendar(self, id_lembrete, segundos, atrasado=False):

        with self._trava:

            antigo = self._timers.pop(id_lembrete, None)

            if antigo is not None:
                antigo.cancel()

            timer = threading.Timer(
                max(0.0, segundos),
                self._disparar,
                args=(id_lembrete, atrasado)
            )

            # daemon=True: um lembrete pendente nunca deve
            # impedir o programa de fechar.
            timer.daemon = True

            self._timers[id_lembrete] = timer

            timer.start()

    def _cancelar_despertador(self, id_lembrete):

        with self._trava:

            timer = self._timers.pop(id_lembrete, None)

        if timer is not None:
            timer.cancel()

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

        if not math.isfinite(tempo) or tempo <= 0:
            return "O tempo precisa ser um número maior que zero."

        segundos_totais = tempo * segundos_por_unidade

        if segundos_totais > self.LIMITE_SEGUNDOS:
            return "O lembrete pode ser programado para no máximo 1 ano."

        with self._armazenamento.trava:

            lembretes = self._ler_lembretes()

            # O id continua de onde o arquivo parou, para não repetir
            # números entre sessões nem entre janelas.
            id_lembrete = max(
                (item["id"] for item in lembretes),
                default=0
            ) + 1

            disparo_em = self._agora() + timedelta(
                seconds=segundos_totais
            )

            lembretes.append({
                "id": id_lembrete,
                "texto": texto,
                "disparo_em": disparo_em,
            })

            gravou = self._gravar_lembretes(lembretes)

        self._agendar(id_lembrete, segundos_totais)

        aviso_disco = (
            ""
            if gravou
            else (
                " (Atenção: não consegui gravá-lo em disco; ele só "
                "vale enquanto a Shaula estiver aberta.)"
            )
        )

        return (
            f"Lembrete #{id_lembrete} criado: vou avisar sobre "
            f"'{texto}' {self._formatar_tempo(tempo, unidade)}."
            + aviso_disco
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

    def _disparar(self, id_lembrete, atrasado=False):

        reagendar_em = None

        with self._armazenamento.trava:

            lembretes = self._ler_lembretes()

            alvo = next(
                (
                    item for item in lembretes
                    if item["id"] == id_lembrete
                ),
                None
            )

            if alvo is not None:

                faltam = (
                    alvo["disparo_em"] - self._agora()
                ).total_seconds()

                # O id pode ter sido REUSADO: cancelar o lembrete de
                # maior número e criar outro dá a ele o mesmo id, e o
                # despertador antigo de OUTRA janela (que não ficou
                # sabendo do cancelamento) ainda dispara na hora do
                # lembrete velho. Se o que está no arquivo ainda não
                # venceu, não é ele que esse despertador veio entregar.
                if (
                    not atrasado
                    and faltam > self.TOLERANCIA_ANTECIPACAO_S
                ):

                    reagendar_em = faltam

                else:

                    self._gravar_lembretes([
                        item for item in lembretes
                        if item["id"] != id_lembrete
                    ])

        if reagendar_em is not None:

            self._agendar(id_lembrete, reagendar_em)

            return

        with self._trava:

            self._timers.pop(id_lembrete, None)

        # Já entregue por outra janela, ou cancelado: nada a fazer.
        if alvo is None:
            return

        titulo = "Shaula — Lembrete"

        texto = alvo["texto"]

        if atrasado:

            titulo += " (atrasado)"

            texto += (
                " — era para "
                + alvo["disparo_em"].strftime("%d/%m às %H:%M")
            )

        sucesso = self._notificador.notificar(titulo, texto)

        if not sucesso:

            user32.MessageBoxW(
                0,
                texto,
                titulo,
                MB_OK | MB_ICONINFORMATION | MB_SETFOREGROUND | MB_TOPMOST
            )

    # --------------------------------------------------------
    # LISTAR / CANCELAR
    # --------------------------------------------------------

    def listar_lembretes(self):

        lembretes = self._ler_lembretes()

        if not lembretes:
            return "Não há nenhum lembrete programado."

        agora = self._agora()

        linhas = ["Lembretes programados:"]

        for item in lembretes:

            restante = (item["disparo_em"] - agora).total_seconds()
            restante = max(0, int(restante))

            minutos_restantes, segundos_restantes = divmod(restante, 60)

            linhas.append(
                f"#{item['id']}: '{item['texto']}' "
                f"— dispara em {minutos_restantes}min {segundos_restantes}s"
            )

        return "\n".join(linhas)

    def cancelar_lembrete(self, id_lembrete):

        try:
            id_lembrete = int(id_lembrete)
        except (TypeError, ValueError):
            return "O número do lembrete precisa ser um número inteiro."

        with self._armazenamento.trava:

            lembretes = self._ler_lembretes()

            alvo = next(
                (
                    item for item in lembretes
                    if item["id"] == id_lembrete
                ),
                None
            )

            if alvo is None:
                return f"Não existe nenhum lembrete #{id_lembrete} pendente."

            self._gravar_lembretes([
                item for item in lembretes
                if item["id"] != id_lembrete
            ])

        self._cancelar_despertador(id_lembrete)

        return f"Lembrete #{id_lembrete} ('{alvo['texto']}') cancelado."
