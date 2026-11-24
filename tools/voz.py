import os
import re
import threading

import numpy as np


TAXA_AMOSTRAGEM = 16000


# ================================================================
# EXCEÇÃO
# ================================================================

class VozIndisponivel(Exception):
    """
    Levantada quando o recurso de voz não pode funcionar agora:
    biblioteca opcional não instalada (faster-whisper,
    sounddevice), microfone inacessível, ou modelo de
    reconhecimento que não pôde ser carregado.

    Fica separada de "não entendi o que você disse" (que não é
    erro, é só um resultado None) porque o aviso para o usuário é
    diferente: aqui ele precisa fazer alguma coisa (instalar,
    conectar um microfone, ligar a internet uma vez).
    """

    def __init__(
        self,
        mensagem,
        pacote_pip=None
    ):

        super().__init__(
            mensagem
        )

        self.pacote_pip = pacote_pip


# ================================================================
# UTILITÁRIOS DE ÁUDIO
# ================================================================

def calcular_nivel(bloco_int16):
    """
    Volume (RMS) de um bloco int16, de 0.0 (silêncio) a 1.0
    (máximo possível). Usado pelo medidor da interface e pela
    checagem de "ninguém falou nada".
    """

    amostras = (
        np.asarray(bloco_int16, dtype=np.float32)
        / 32768.0
    )

    if amostras.size == 0:
        return 0.0

    return float(
        np.sqrt(
            np.mean(
                amostras * amostras
            )
        )
    )


def normalizar_volume(
    audio,
    pico_alvo=0.8,
    ganho_maximo=8.0
):
    """
    Sobe o volume de uma gravação baixa (microfone com pouco
    ganho, pessoa longe do microfone) até o pico ficar perto de
    `pico_alvo`. Só amplifica, nunca reduz, e limita o ganho para
    não transformar ruído de fundo em barulho. Reconhecimento de
    fala erra mais em áudio muito baixo.
    """

    if audio.size == 0:
        return audio

    pico = float(
        np.max(
            np.abs(audio)
        )
    )

    if pico <= 0.0:
        return audio

    ganho = min(
        pico_alvo / pico,
        ganho_maximo
    )

    # Ganho pequeno não compensa mexer no áudio.
    if ganho <= 1.2:
        return audio

    return np.clip(
        audio * ganho,
        -1.0,
        1.0
    ).astype(np.float32)


# ================================================================
# FONTE DE ÁUDIO (a "ponta" de hardware — fácil de trocar nos
# testes por uma fonte falsa)
# ================================================================

class FonteAudio:
    """
    Interface de uma fonte de áudio mono, 16 kHz, int16. Quem
    grava (Gravador) não sabe se os blocos vêm de um microfone de
    verdade ou de uma lista pronta num teste.
    """

    taxa = TAXA_AMOSTRAGEM

    def abrir(self):
        raise NotImplementedError

    def ler_bloco(self):
        """
        Devolve um np.ndarray 1-D int16 (bloqueia até haver
        áudio suficiente para um bloco).
        """
        raise NotImplementedError

    def fechar(self):
        raise NotImplementedError


class MicrofoneSounddevice(FonteAudio):
    """
    Microfone padrão do Windows via `sounddevice` (traz o
    PortAudio embutido no pacote para Windows, sem precisar
    instalar mais nada à parte).
    """

    def __init__(
        self,
        duracao_bloco_ms=30,
        dispositivo=None
    ):

        self.duracao_bloco_ms = duracao_bloco_ms
        self.dispositivo = dispositivo

        self._tamanho_bloco = int(
            self.taxa * duracao_bloco_ms / 1000
        )

        self._fluxo = None

    def abrir(self):

        try:

            import sounddevice as sd

        except (ImportError, OSError):

            raise VozIndisponivel(
                "Falta instalar a biblioteca de microfone:\n\n"
                "pip install sounddevice",
                "sounddevice"
            )

        try:

            self._fluxo = sd.InputStream(
                samplerate=self.taxa,
                channels=1,
                dtype="int16",
                blocksize=self._tamanho_bloco,
                device=self.dispositivo
            )

            self._fluxo.start()

        except Exception as erro:

            self._fluxo = None

            raise VozIndisponivel(
                "Não foi possível abrir o microfone.\n\n"
                "Confira se há um microfone conectado e se o "
                "Windows permite que aplicativos o usem "
                "(Configurações > Privacidade > Microfone).\n\n"
                f"Detalhe: {erro}"
            )

    def ler_bloco(self):

        dados, _ = self._fluxo.read(
            self._tamanho_bloco
        )

        return dados[:, 0].copy()

    def fechar(self):

        if self._fluxo is None:
            return

        try:

            self._fluxo.stop()
            self._fluxo.close()

        except Exception:
            pass

        finally:

            self._fluxo = None


# ================================================================
# GRAVADOR
# ================================================================

class Gravador:
    """
    Abre uma FonteAudio e grava TUDO até que a pessoa mande
    parar (um threading.Event) — não existe encerramento
    automático por silêncio: quem decide quando acabou é quem
    está falando, como num ditado. Devolve o áudio como float32
    entre -1 e 1, que é o formato que os reconhecedores esperam.

    A única parada automática é um teto de segurança de tempo
    (DURACAO_MAXIMA_S), para um microfone esquecido ligado não
    encher a memória.
    """

    DURACAO_MAXIMA_S = 600

    # Gravações mais curtas que isso são toques acidentais.
    DURACAO_MINIMA_S = 0.4

    # Se o volume NUNCA passou disso, não há fala nenhuma (mic
    # mudo, desconectado) — nem vale a pena transcrever, e
    # reconhecedores tendem a "inventar" texto em silêncio puro.
    NIVEL_MINIMO_DE_VOZ = 0.002

    def __init__(
        self,
        fonte,
        duracao_maxima_s=None
    ):

        self.fonte = fonte

        self.duracao_maxima_s = (
            duracao_maxima_s
            or self.DURACAO_MAXIMA_S
        )

    def gravar(
        self,
        parar=None,
        cancelado=None,
        ao_nivel=None
    ):
        """
        `parar`: threading.Event — ao ser acionado, termina a
        gravação e devolve o que foi captado.
        `cancelado`: threading.Event — ao ser acionado, descarta
        tudo e devolve None.
        `ao_nivel`: função chamada a cada bloco com o volume
        (0.0 a 1.0) — alimenta o medidor da interface.

        Devolve None se foi cancelado, se foi curto demais ou se
        ninguém falou.
        """

        blocos = []

        amostras_gravadas = 0

        nivel_maximo = 0.0

        limite_de_amostras = int(
            self.duracao_maxima_s
            * self.fonte.taxa
        )

        self.fonte.abrir()

        try:

            while True:

                if (
                    cancelado is not None
                    and cancelado.is_set()
                ):
                    return None

                if (
                    parar is not None
                    and parar.is_set()
                ):
                    break

                bloco = self.fonte.ler_bloco()

                blocos.append(
                    bloco
                )

                amostras_gravadas += len(
                    bloco
                )

                nivel = calcular_nivel(
                    bloco
                )

                nivel_maximo = max(
                    nivel_maximo,
                    nivel
                )

                if ao_nivel is not None:

                    ao_nivel(
                        nivel
                    )

                if amostras_gravadas >= limite_de_amostras:
                    break

        finally:

            self.fonte.fechar()

        if not blocos:
            return None

        audio = np.concatenate(
            blocos
        )

        if (
            len(audio)
            < self.DURACAO_MINIMA_S * self.fonte.taxa
        ):
            return None

        if nivel_maximo < self.NIVEL_MINIMO_DE_VOZ:
            return None

        return normalizar_volume(
            audio.astype(np.float32) / 32768.0
        )


# ================================================================
# RECONHECEDORES (Strategy — mesmo desenho de MecanismoBusca em
# pesquisa.py e EstrategiaAnexo em anexos.py)
# ================================================================

class ReconhecedorFala:
    """
    Interface de um motor de fala-para-texto. GerenciadorVoz não
    sabe qual motor está por baixo — adicionar outro (ex.: Vosk,
    mais leve em máquina fraca) é criar uma subclasse e passá-la
    no construtor.
    """

    # Texto que o motor recebe como "contexto" antes de ouvir;
    # usado pelo limpador pra detectar quando o motor, sem
    # entender nada, só devolve esse contexto de volta.
    prompt_inicial = ""

    @property
    def carregado(self):
        return True

    def carregar_modelo(
        self,
        somente_local=False
    ):
        pass

    def descarregar_modelo(self):
        pass

    def transcrever(
        self,
        audio,
        taxa=TAXA_AMOSTRAGEM
    ):
        raise NotImplementedError


class ReconhecedorFasterWhisper(ReconhecedorFala):
    """
    Whisper rodando 100% local via faster-whisper (CTranslate2),
    em CPU com quantização int8 — deixa a GPU livre pro modelo de
    linguagem (qwen3.5:9b) que já ocupa a maior parte dela.

    O modelo é baixado uma vez (precisa de internet nessa
    primeira vez) para ~/.shaula/modelos_voz e depois funciona
    offline. Tamanhos, do mais rápido ao mais preciso:
    "small" (~0,5 GB), "medium" (~1,5 GB, padrão),
    "large-v3-turbo" (~1,6 GB — quase a precisão do "large",
    mas pesado em CPU).
    """

    MODELO_PADRAO = "medium"

    prompt_inicial = (
        "Comandos para a assistente Shaula: abrir e fechar "
        "programas, pesquisar na internet, criar lembretes, "
        "tirar print, calcular, mover janelas entre monitores: "
        "monitor 1, monitor 2, monitor 3."
    )

    def __init__(
        self,
        modelo=None,
        dispositivo="cpu",
        tipo_computacao="int8",
        pasta_modelos=None,
        idioma="pt",
        beam_size=5,
        cpu_threads=None
    ):

        self.modelo = modelo or self.MODELO_PADRAO
        self.dispositivo = dispositivo
        self.tipo_computacao = tipo_computacao
        self.idioma = idioma

        # beam_size=1 (busca gulosa) é bem mais rápido, mas erra
        # mais; 5 é o padrão do Whisper original.
        self.beam_size = beam_size

        # O padrão do CTranslate2 é só 4 threads — em CPU com
        # mais núcleos isso deixa desempenho na mesa.
        self.cpu_threads = (
            cpu_threads
            or min(8, os.cpu_count() or 4)
        )

        self.pasta_modelos = pasta_modelos or os.path.join(
            os.path.expanduser("~"),
            ".shaula",
            "modelos_voz"
        )

        self._modelo = None
        self._trava = threading.Lock()

    @property
    def carregado(self):
        return self._modelo is not None

    def carregar_modelo(
        self,
        somente_local=False
    ):
        """
        `somente_local=True` só carrega se o modelo já estiver no
        disco (nunca baixa) — usado no pré-carregamento
        silencioso na abertura da Shaula.
        """

        with self._trava:

            if self._modelo is not None:
                return

            try:

                from faster_whisper import WhisperModel

            except ImportError:

                raise VozIndisponivel(
                    "Falta instalar a biblioteca de "
                    "reconhecimento de voz:\n\n"
                    "pip install faster-whisper",
                    "faster-whisper"
                )

            opcoes = {
                "device": self.dispositivo,
                "compute_type": self.tipo_computacao,
                "download_root": self.pasta_modelos,
                "local_files_only": somente_local,
            }

            if self.dispositivo == "cpu":
                opcoes["cpu_threads"] = self.cpu_threads

            try:

                self._modelo = WhisperModel(
                    self.modelo,
                    **opcoes
                )

            except Exception as erro:

                raise VozIndisponivel(
                    "Não foi possível carregar o modelo de voz "
                    f"'{self.modelo}'.\n\n"
                    "Na primeira vez ele precisa ser baixado, o "
                    "que exige internet.\n\n"
                    f"Detalhe: {erro}"
                )

    def descarregar_modelo(self):
        """
        Libera o modelo da memória (~1,5 GB de RAM no "medium" e
        as threads de CPU). Sem isso ele ficava carregado até
        fechar a Shaula, disputando RAM e CPU com o Ollama.
        """

        with self._trava:

            self._modelo = None

        import gc

        gc.collect()

    def transcrever(
        self,
        audio,
        taxa=TAXA_AMOSTRAGEM
    ):

        self.carregar_modelo()

        segmentos, _ = self._modelo.transcribe(
            audio,
            language=self.idioma,
            beam_size=self.beam_size,
            vad_filter=True,
            condition_on_previous_text=False,
            initial_prompt=self.prompt_inicial
        )

        return " ".join(
            segmento.text.strip()
            for segmento in segmentos
        ).strip()


# ================================================================
# LIMPEZA DO TEXTO RECONHECIDO
# ================================================================

class LimpadorTranscricao:
    """
    Whisper tem um vício conhecido: diante de silêncio ou ruído,
    "alucina" frases comuns dos vídeos com que foi treinado
    (legendas, pedidos de inscrição no canal). Se isso chegasse
    ao chat, a Shaula responderia a um comando que ninguém deu.
    """

    FRASES_ALUCINADAS = (
        r"legendas? pela comunidade amara\.org",
        r"legendado por[^.]*",
        r"obrigado por assistir",
        r"inscreva-se no canal",
        r"se inscreva no canal",
    )

    # Variações com que o Whisper costuma escrever o nome da
    # assistente — todas viram "Shaula" antes de ir pro modelo
    # de linguagem.
    VARIACOES_NOME = (
        r"\bxaula\b",
        r"\bchaula\b",
        r"\bshawla\b",
        r"\bshaúla\b",
        r"\bxá ula\b",
    )

    def limpar(
        self,
        texto,
        prompt_inicial=""
    ):
        """
        Devolve o texto pronto para virar mensagem, ou None se
        não sobrou nada que valha enviar.
        """

        if not texto:
            return None

        for padrao in self.FRASES_ALUCINADAS:

            texto = re.sub(
                padrao,
                "",
                texto,
                flags=re.IGNORECASE
            )

        for padrao in self.VARIACOES_NOME:

            texto = re.sub(
                padrao,
                "Shaula",
                texto,
                flags=re.IGNORECASE
            )

        texto = re.sub(
            r"\s+",
            " ",
            texto
        ).strip()

        letras = re.sub(
            r"[\W_]+",
            "",
            texto
        )

        if len(letras) < 2:
            return None

        if prompt_inicial:

            if self._so_repete_o_prompt(
                texto,
                prompt_inicial
            ):
                return None

        return texto

    @staticmethod
    def _normalizar(texto):

        return re.sub(
            r"[\W_]+",
            " ",
            texto.lower()
        ).strip()

    # Eco do prompt só é suspeito quando o trecho é longo. Com
    # qualquer tamanho, comandos curtos e legítimos que aparecem
    # no prompt — "tirar print", "calcular", "criar lembretes" —
    # eram descartados em silêncio como se fossem alucinação.
    MIN_PALAVRAS_ECO = 4

    def _so_repete_o_prompt(
        self,
        texto,
        prompt_inicial
    ):

        normalizado = self._normalizar(texto)

        return (
            len(normalizado.split()) >= self.MIN_PALAVRAS_ECO
            and normalizado in self._normalizar(prompt_inicial)
        )


# ================================================================
# CARGA DO MODELO EM SEGUNDO PLANO
# ================================================================

class _CargaEmSegundoPlano:
    """
    Carrega o modelo do reconhecedor numa thread própria e
    guarda uma eventual falha para ser relançada em quem
    chamar `aguardar()` (uma exceção dentro de uma thread
    secundária, sozinha, se perderia).
    """

    def __init__(self, reconhecedor):

        self._reconhecedor = reconhecedor

        self._pronta = threading.Event()

        self._erro = None

        self._fio = threading.Thread(
            target=self._carregar,
            daemon=True
        )

    @property
    def concluida(self):

        return self._pronta.is_set()

    def iniciar(self):

        self._fio.start()

    def _carregar(self):

        try:

            self._reconhecedor.carregar_modelo()

        except BaseException as erro:

            self._erro = erro

        finally:

            self._pronta.set()

    def aguardar(self, timeout=None):

        self._pronta.wait(timeout)

        if self._pronta.is_set() and self._erro is not None:

            erro, self._erro = self._erro, None

            raise erro


# ================================================================
# FACHADA
# ================================================================

class GerenciadorVoz:
    """
    Ponto único que a interface usa: `escutar()` grava até a
    pessoa mandar parar, transcreve e devolve o texto — que daí
    segue exatamente o mesmo caminho de uma mensagem digitada
    (mesmo modelo, mesmas ferramentas, mesmo histórico). Por isso
    a voz não tem um "interpretador de comandos" próprio: o
    tool-calling do modelo já faz isso.

    Tudo é injetável (gravador, reconhecedor, limpador) — os
    testes montam um GerenciadorVoz com fontes e motores falsos,
    sem microfone nem modelo.
    """

    def __init__(
        self,
        gravador=None,
        reconhecedor=None,
        limpador=None,
        tempo_ocioso_s=180
    ):

        # O modelo só é carregado quando o microfone é ativado
        # (e enquanto a pessoa fala, sem fazê-la esperar). Depois
        # de `tempo_ocioso_s` segundos sem uso ele é liberado: o
        # Whisper "medium" ocupa ~1,5 GB de RAM e várias threads
        # de CPU, que fazem falta ao Ollama. None = nunca libera;
        # 0 = libera logo após cada uso (recarrega toda vez).
        self.tempo_ocioso_s = tempo_ocioso_s

        self._timer_ocioso = None

        self._trava_ocioso = threading.Lock()

        self.gravador = (
            gravador
            or Gravador(
                MicrofoneSounddevice()
            )
        )

        self.reconhecedor = (
            reconhecedor
            or ReconhecedorFasterWhisper()
        )

        self.limpador = (
            limpador
            or LimpadorTranscricao()
        )

    def pre_aquecer(self):
        """
        Carrega o modelo em segundo plano, sem bloquear nada, para
        o primeiro clique no microfone já encontrá-lo pronto. Só
        usa modelo que já esteja no disco (nunca baixa nada
        sozinho, pra não puxar centenas de MB sem a pessoa
        saber) e engole qualquer falha — se não deu agora, o
        clique no microfone tenta de novo e mostra o motivo.

        Devolve a thread (para os testes poderem esperar por ela).
        """

        def carregar():

            try:

                self.reconhecedor.carregar_modelo(
                    somente_local=True
                )

            except Exception:
                pass

        fio = threading.Thread(
            target=carregar,
            daemon=True
        )

        fio.start()

        return fio

    def escutar(
        self,
        parar=None,
        cancelado=None,
        notificar_estado=None,
        notificar_nivel=None
    ):
        """Ver _escutar. Agenda a liberação do modelo ao final."""

        self._cancelar_liberacao()

        try:

            return self._escutar(
                parar,
                cancelado,
                notificar_estado,
                notificar_nivel
            )

        finally:

            self._agendar_liberacao()

    def _cancelar_liberacao(self):

        with self._trava_ocioso:

            if self._timer_ocioso is not None:

                self._timer_ocioso.cancel()

                self._timer_ocioso = None

    def _agendar_liberacao(self):

        if self.tempo_ocioso_s is None:
            return

        if self.tempo_ocioso_s <= 0:

            self._liberar_modelo()

            return

        with self._trava_ocioso:

            self._timer_ocioso = threading.Timer(
                self.tempo_ocioso_s,
                self._liberar_modelo
            )

            self._timer_ocioso.daemon = True

            self._timer_ocioso.start()

    def _liberar_modelo(self):

        descarregar = getattr(
            self.reconhecedor,
            "descarregar_modelo",
            None
        )

        if descarregar is not None:
            descarregar()

    def _escutar(
        self,
        parar=None,
        cancelado=None,
        notificar_estado=None,
        notificar_nivel=None
    ):
        """
        Grava até `parar` ser acionado e devolve o texto
        reconhecido; devolve None se ninguém falou, se não deu pra
        entender, ou se foi cancelado (`cancelado` acionado, em
        qualquer momento — inclusive durante a transcrição, cujo
        resultado então é descartado).

        `notificar_estado`, se passado, recebe "preparando"
        (carregando o modelo, só se ainda não estiver pronto),
        "ouvindo" e "transcrevendo". `notificar_nivel` recebe o
        volume (0.0 a 1.0) a cada bloco gravado.

        Levanta VozIndisponivel se faltar biblioteca, microfone
        ou modelo.
        """

        def avisar(estado):

            if notificar_estado is not None:
                notificar_estado(estado)

        def foi_cancelado():

            return (
                cancelado is not None
                and cancelado.is_set()
            )

        # O modelo carrega em segundo plano ENQUANTO a pessoa
        # fala. Antes, a gravação só começava depois da carga
        # (vários segundos olhando "Preparando..."), e a mensagem
        # prometia "só na primeira vez" mesmo quando se repetia.
        carga = None

        if not self.reconhecedor.carregado:

            carga = _CargaEmSegundoPlano(self.reconhecedor)

            carga.iniciar()

            # Falhas imediatas (biblioteca não instalada) são
            # avisadas antes de a pessoa gastar tempo falando.
            carga.aguardar(timeout=0.3)

        if foi_cancelado():
            return None

        avisar("ouvindo")

        audio = self.gravador.gravar(
            parar,
            cancelado,
            notificar_nivel
        )

        if audio is None or foi_cancelado():
            return None

        if carga is not None:

            if not carga.concluida:
                avisar("preparando")

            carga.aguardar()

        avisar("transcrevendo")

        bruto = self.reconhecedor.transcrever(
            audio,
            TAXA_AMOSTRAGEM
        )

        if foi_cancelado():
            return None

        return self.limpador.limpar(
            bruto,
            self.reconhecedor.prompt_inicial
        )


# ================================================================
# python -m tools.voz  -> baixa o modelo de voz (usado pelo
# instalador, quando já há internet disponível)
# ================================================================

if __name__ == "__main__":

    import sys

    reconhecedor = ReconhecedorFasterWhisper()

    print(
        f"Baixando o modelo de voz '{reconhecedor.modelo}' "
        "(pode levar alguns minutos)..."
    )

    try:

        reconhecedor.carregar_modelo()

    except VozIndisponivel as erro:

        print(erro)

        sys.exit(1)

    print("Modelo de voz pronto.")
